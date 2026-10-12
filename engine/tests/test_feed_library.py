"""Bundled feed discovery is metadata-only until a user subscribes."""
import asyncio
from datetime import date
from urllib.parse import urlsplit
import pytest
from eis_engine.news import canonical_url
from eis_engine.service import Service
from eis_engine.storage import Store


@pytest.fixture
def service(tmp_path):
    instance = Service(Store(tmp_path / "workspace"))
    yield instance
    instance.store.close()


def test_packaged_library_complete_unique_safe_and_bilingual(service, monkeypatch):
    def no_sync(*args):
        raise AssertionError("Reading the library must not subscribe or start network work")
    monkeypatch.setattr(service, "start_feed_sync", no_sync)
    result = asyncio.run(service.dispatch("news.library", {}))
    assert result["version"] == 1
    feeds = result["feeds"]
    assert len(feeds) == 12
    assert len({row["id"] for row in feeds}) == len(feeds)
    assert len({canonical_url(row["url"]) for row in feeds}) == len(feeds)
    assert {row["category"] for row in feeds} == {"general", "news", "technology", "ai", "science", "business", "sports", "podcasts"}
    assert {row["language"] for row in feeds} == {"ar", "en"}
    for row in feeds:
        assert row["title"].strip()
        assert row["description_ar"].strip() and row["description_en"].strip()
        assert date.fromisoformat(row["verified_at"])
        for field in ("url", "publisher_url"):
            normalized = canonical_url(row[field])
            assert urlsplit(normalized).scheme == "https"
            assert urlsplit(normalized).hostname
            assert not urlsplit(normalized).username
    assert service.news.snapshot()["subscriptions"] == []


def test_library_subscribe_uses_real_dispatch_and_canonical_dedup(service, monkeypatch):
    scheduled = []
    network = []
    monkeypatch.setattr(service, "start_feed_sync", scheduled.append)
    async def fetch(url, conditional=None):
        network.append(url)
        return {"url":url, "status":200, "headers":{}, "body":b"<rss><channel><title>Selected feed</title></channel></rss>"}
    service.news.fetch = fetch
    async def scenario():
        entry = (await service.dispatch("news.library", {}))["feeds"][0]
        payload = {"url":entry["url"], "title":entry["title"], "kind":"rss"}
        first = await service.dispatch("news.subscribe", payload)
        second = await service.dispatch("news.subscribe", {**payload, "url":entry["url"] + "#same-feed"})
        assert first["subscription_id"] == second["subscription_id"]
        assert first["id"] == first["subscription_id"]
        snapshot = await service.dispatch("news.snapshot", {})
        assert len(snapshot["subscriptions"]) == 1
        row = snapshot["subscriptions"][0]
        assert row["title"] == entry["title"] and row["enabled"] is True
        assert row["url"] == canonical_url(entry["url"])
        assert scheduled == [first["id"], first["id"]]
        assert network == []  # The service queues work instead of blocking subscribe.
        outcome = await service.news.sync(first["id"])
        assert outcome == {"updated":1, "failed":0}
        assert network == [entry["url"]]
        assert service.news.snapshot()["subscriptions"][0]["status"] == "ready"
    asyncio.run(scenario())


def test_news_update_pause_and_resume_preserve_subscription(service, monkeypatch):
    scheduled = []
    network = []
    monkeypatch.setattr(service, "start_feed_sync", scheduled.append)
    async def fetch(url, conditional=None):
        network.append(url)
        return {"url":url, "status":200, "headers":{}, "body":b"<rss><channel><title>Feed</title></channel></rss>"}
    service.news.fetch = fetch
    async def scenario():
        entry = (await service.dispatch("news.library", {}))["feeds"][1]
        subscribed = await service.dispatch("news.subscribe", {"url":entry["url"], "title":entry["title"], "kind":"rss"})
        identifier = subscribed["id"]
        paused = await service.dispatch("news.update", {"subscription_id":identifier, "enabled":False})
        assert paused["enabled"] is False
        assert await service.news.sync(force=True) == {"updated":0, "failed":0}
        assert network == []
        resumed = await service.dispatch("news.update", {"subscription_id":identifier, "enabled":True})
        assert resumed["enabled"] is True
        assert await service.news.sync() == {"updated":1, "failed":0}
        snapshot = await service.dispatch("news.snapshot", {})
        assert len(snapshot["subscriptions"]) == 1
        assert snapshot["subscriptions"][0]["id"] == identifier
        assert snapshot["subscriptions"][0]["title"] == entry["title"]
        assert network == [entry["url"]]
    asyncio.run(scenario())


def test_yaml_library_reloads_custom_categories_without_overwriting(service):
    from pathlib import Path
    first = asyncio.run(service.dispatch("news.library", {}))
    path = Path(first["path"])
    assert path.name == "sources.yml" and path.parent == service.store.path.parent
    edited = 'version: 1\nfeeds:\n  - id: local-choice\n    title: My source\n    url: https://example.com/feed\n    category: my-special-interest\n    language: ar-SA\n'
    path.write_text(edited)
    reloaded = asyncio.run(service.dispatch("news.library", {}))
    assert len(reloaded["feeds"]) == 1
    row = reloaded["feeds"][0]
    assert row["category"] == "my-special-interest"
    assert row["publisher_url"] == row["url"]
    assert row["description_ar"] == row["description_en"] == row["verified_at"] == ""
    assert path.read_text() == edited
    assert service.news.snapshot()["subscriptions"] == []


def test_invalid_yaml_preserved_and_path_endpoint_remains_available(service):
    from pathlib import Path
    from eis_engine.contracts import Failure
    path = Path(asyncio.run(service.dispatch("news.library.path", {}))["path"])
    malformed = 'version: 1\nfeeds: [\n'
    path.write_text(malformed)
    assert asyncio.run(service.dispatch("news.library.path", {}))["path"] == str(path)
    with pytest.raises(Failure, match="السطر"):
        asyncio.run(service.dispatch("news.library", {}))
    assert path.read_text() == malformed


@pytest.mark.parametrize("change", ["duplicate-id", "duplicate-url", "private-url", "reserved-category", "unsafe-tag", "duplicate-yaml-key", "alias"])
def test_invalid_feed_definitions_are_rejected_without_replacement(service, change):
    import yaml
    from pathlib import Path
    from eis_engine.contracts import Failure
    path = Path(asyncio.run(service.dispatch("news.library.path", {}))["path"])
    row = {"id":"example", "title":"Example", "url":"https://example.com/feed", "category":"custom", "language":"en"}
    data = {"version":1, "feeds":[row]}
    if change == "duplicate-id": data["feeds"].append({**row,"url":"https://example.net/feed"})
    elif change == "duplicate-url": data["feeds"].append({**row,"id":"other"})
    elif change == "private-url": row["url"] = "http://127.0.0.1/feed"
    elif change == "reserved-category": row["category"] = "all"
    serialized = yaml.safe_dump(data)
    if change == "unsafe-tag": serialized = '!!python/object/apply:os.system ["echo must-not-run"]'
    elif change == "duplicate-yaml-key": serialized = 'version: 1\nversion: 1\nfeeds: []'
    elif change == "alias": serialized = 'version: 1\nfeeds: &a [*a]'
    path.write_text(serialized)
    with pytest.raises(Failure): asyncio.run(service.dispatch("news.library", {}))
    assert path.read_text() == serialized


def test_feed_library_size_and_count_bounds(service):
    import yaml
    from pathlib import Path
    from eis_engine.contracts import Failure
    from eis_engine.feed_library import MAX_BYTES
    path = Path(asyncio.run(service.dispatch("news.library.path", {}))["path"])
    path.write_bytes(b"#" * (MAX_BYTES + 1))
    with pytest.raises(Failure): asyncio.run(service.dispatch("news.library", {}))
    assert path.stat().st_size == MAX_BYTES + 1
    path.write_text(yaml.safe_dump({"version":1,"feeds":[{"id":str(index)} for index in range(501)]}))
    with pytest.raises(Failure): asyncio.run(service.dispatch("news.library", {}))


def test_existing_empty_user_file_is_not_reseeded(service):
    from eis_engine.contracts import Failure
    path = service.store.path.parent / "sources.yml"
    path.write_text("")
    with pytest.raises(Failure): asyncio.run(service.dispatch("news.library", {}))
    assert path.read_text() == ""
