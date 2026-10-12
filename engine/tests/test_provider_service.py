"""Provider account/catalog boundaries; all discovery and model calls are local fakes."""
import asyncio
import json
import sqlite3
import sys
import types

import pytest

from eis_engine.contracts import Failure
from eis_engine.service import Service
from eis_engine.storage import SCHEMA, Store, now, uid


@pytest.fixture
def service(tmp_path):
    instance = Service(Store(tmp_path))
    yield instance
    instance.store.close()


def discovery(monkeypatch, callback):
    module = types.ModuleType("eis_engine.model_catalog")
    module.discover = callback
    monkeypatch.setitem(sys.modules, "eis_engine.model_catalog", module)


async def account(service, label="Personal", **extra):
    return await service.dispatch("providers.save", {"provider_key": "openai", "label": label, **extra})


async def discover_two(profile):
    return {"models": [{"id": "alpha", "name": "Alpha"}, {"id": "beta", "name": "Beta"}], "source": "mock API"}


def test_accounts_can_share_provider_without_model_id(service):
    async def scenario():
        first = await account(service, "Personal")
        second = await account(service, "Work")
        assert first["profile_id"] != second["profile_id"]
        rows = service.snapshot()["profiles"]
        assert {r["label"] for r in rows} == {"Personal", "Work"}
        assert all(r["model_id"] == "" for r in rows)
        assert all(r["auto_refresh"] == 1 for r in rows)
        assert service.profile(first["profile_id"])["credential_path"] != service.profile(second["profile_id"])["credential_path"]
    asyncio.run(scenario())


def test_catalog_is_cached_and_failed_refresh_retains_last_success(service, monkeypatch):
    calls = []
    async def fetch(profile):
        calls.append(profile["id"])
        if len(calls) > 1:
            raise Failure("NETWORK_ERROR", "offline")
        return await discover_two(profile)
    discovery(monkeypatch, fetch)
    async def scenario():
        pid = (await account(service))["profile_id"]
        first = await service.dispatch("providers.models", {"profile_id": pid, "refresh": True})
        cached = await service.dispatch("providers.models", {"profile_id": pid})
        assert cached == first
        assert calls == [pid]
        failed = await service.dispatch("providers.models", {"profile_id": pid, "refresh": True})
        assert failed["models"] == first["models"]
        assert failed["updated_at"] == first["updated_at"]
        assert failed["source"] == first["source"]
        assert failed["error"] == "offline"
    asyncio.run(scenario())


def test_auto_refresh_disabled_retains_expired_cache_but_explicit_refresh_works(service, monkeypatch):
    calls = []
    async def fetch(profile):
        calls.append(profile["id"])
        return await discover_two(profile)
    discovery(monkeypatch, fetch)
    async def scenario():
        pid = (await account(service))["profile_id"]
        await service.dispatch("providers.models", {"profile_id": pid})
        await service.dispatch("providers.update", {"profile_id": pid, "auto_refresh": False})
        with service.db:
            service.db.execute("UPDATE model_catalogs SET next_refresh=0 WHERE profile_id=?", (pid,))
        await service.dispatch("providers.models", {"profile_id": pid})
        assert len(calls) == 1
        await service.dispatch("providers.models", {"profile_id": pid, "refresh": True})
        assert len(calls) == 2
    asyncio.run(scenario())


def test_assignments_are_independent_and_reject_unlisted_models(service, monkeypatch):
    discovery(monkeypatch, discover_two)
    async def scenario():
        first = (await account(service))["profile_id"]
        second = (await account(service, "Work"))["profile_id"]
        for pid in (first, second):
            await service.dispatch("providers.models", {"profile_id": pid})
        await service.dispatch("agents.assign", {"role": "writer", "profile_id": first, "model_id": "alpha"})
        await service.dispatch("agents.assign", {"role": "analyst", "profile_id": second, "model_id": "beta"})
        assert {(a["role"], a["profile_id"], a["model_id"]) for a in service.snapshot()["assignments"]} == {("writer", first, "alpha"), ("analyst", second, "beta")}
        for role, model in (("writer", "invented"), ("unknown-role", "alpha")):
            with pytest.raises(Failure):
                await service.dispatch("agents.assign", {"role": role, "profile_id": first, "model_id": model})
        assert len(service.snapshot()["assignments"]) == 2
    asyncio.run(scenario())


def test_models_updates_and_assignments_do_not_cross_workspace(service, monkeypatch):
    discovery(monkeypatch, discover_two)
    async def scenario():
        pid = (await account(service))["profile_id"]
        await service.dispatch("providers.models", {"profile_id": pid})
        original = service.ws
        service.ws = uid()
        try:
            for command, extra in (("providers.models", {}), ("providers.update", {"label": "changed"}), ("agents.assign", {"role": "writer", "model_id": "alpha"})):
                with pytest.raises(Failure):
                    await service.dispatch(command, {"profile_id": pid, **extra})
            assert service.snapshot()["profiles"] == []
            assert service.snapshot()["assignments"] == []
        finally:
            service.ws = original
        assert service.snapshot()["profiles"][0]["label"] == "Personal"
    asyncio.run(scenario())


def test_submitted_analysis_freezes_model_override(service, monkeypatch):
    discovery(monkeypatch, discover_two)
    async def scenario():
        pid = (await account(service, model_id="legacy-direct-model"))["profile_id"]
        await service.dispatch("providers.models", {"profile_id": pid})
        source = await service.dispatch("sources.add", {"title": "Sample", "text": "How does this work?", "rights_status": "owned"})
        async def hold_job(_):
            await asyncio.Event().wait()
        monkeypatch.setattr(service, "run_job", hold_job)
        submitted = await service.dispatch("analysis.run", {"item_ids": [source["item_id"]], "profile_id": pid, "model_id": "beta", "consent": True, "idempotency_key": uid()})
        try:
            await service.dispatch("providers.update", {"profile_id": pid, "model_id": "alpha"})
            await service.dispatch("agents.assign", {"role": "analyst", "profile_id": pid, "model_id": "alpha"})
            payload = json.loads(service.require("jobs", submitted["job_id"])["payload_json"])
            assert payload["profile_snapshot"]["model_id"] == "beta"
            assert service.profile(pid)["model_id"] == "alpha"
        finally:
            task = service.tasks[submitted["job_id"]]
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())


def test_v1_migration_preserves_existing_provider(tmp_path):
    path = tmp_path / "editorial.sqlite"
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    workspace, profile = uid(), uid()
    db.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace, "Existing", now()))
    db.execute("INSERT INTO provider_profiles VALUES(?,?,?,?,?,?,?,?)", (profile, workspace, "openai", "legacy-direct-model", "{}", profile, now(), now()))
    db.commit()
    db.close()
    store = Store(tmp_path)
    try:
        service = Service(store)
        row = service.snapshot()["profiles"][0]
        assert row["id"] == profile
        assert row["model_id"] == "legacy-direct-model"
        assert row["label"] == "" and row["auto_refresh"] == 1
        assert store.db.execute("PRAGMA user_version").fetchone()[0] == 5
        assert service.snapshot()["assignments"] == []
    finally:
        store.close()


@pytest.mark.parametrize("field", ["base_url", "host", "azure_endpoint", "url", "base_host_url", "api_base"])
@pytest.mark.parametrize("address", ["https://user:secret@example.org", "https://example.org?api_key=secret", "http://example.org"])
def test_all_endpoint_aliases_reject_embedded_credentials_and_remote_http(service, monkeypatch, field, address):
    # Every adapter-specific URL spelling must share the same safe persistence boundary.
    monkeypatch.setattr("eis_engine.service.catalog", lambda: {"providers": [{"id": "test-adapter", "status": "ready", "fields": [field]}]})
    async def scenario():
        with pytest.raises(Failure):
            await service.dispatch("providers.save", {"provider_key": "test-adapter", "config": {field: address}})
        assert service.snapshot()["profiles"] == []
    asyncio.run(scenario())
