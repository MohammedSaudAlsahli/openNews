import asyncio
import json
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from eis_engine.contracts import Failure
from eis_engine.feed_directory import normalize, TTL, MAX_STALE, MAX_PAGES
from eis_engine.news import NewsError
from eis_engine.service import Service
from eis_engine.storage import Store


def entry(**changes):
    return {"title": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "siteUrl": "https://www.theverge.com/", "status": "active", "format": "rss", "lang": "en", "description": "Technology news", "tags": ["technology", "news"], **changes}


@pytest.fixture
def service(tmp_path):
    service = Service(Store(tmp_path / "workspace"))
    yield service
    service.store.close()


def test_metadata_validation_and_deduplication():
    page = normalize({"feeds": [entry(), entry(), entry(url="http://127.0.0.1/feed"), entry(url="https://x.example/rss", siteUrl="javascript:bad", lang=None), entry(status="retired"), entry(format="json"), None]})
    assert len(page["feeds"]) == 2
    assert page["feeds"][1]["language"] == "und"
    assert page["feeds"][1]["publisher_url"] == ""
    assert page["feeds"][0]["verified_at"] == ""  # directory inclusion isn't publisher verification


@pytest.mark.parametrize("next_url", [23, {"before": "invalid"}, "https://evil.example/?before=x", "//evil.example/api/v1/feeds", "/api/v1/feeds?before=wrong", "/api/v1/feeds?before=2026-10-01", "/wrong?before=2026-10-01T00:00:00Z"])
def test_untrusted_pagination_cannot_select_endpoint(next_url):
    with pytest.raises(ValueError):
        normalize({"feeds": [], "next": next_url})


def test_search_cache_pagination_and_subscribe(service, monkeypatch):
    network, scheduled = [], []
    monkeypatch.setattr(service, "start_feed_sync", scheduled.append)
    async def fetch(url):
        network.append(url)
        return {"status": 200, "body": json.dumps({"feeds": [entry()], "next": None if "before=" in url else "/api/v1/feeds?before=2026-10-01T00%3A00%3A00Z"}).encode()}
    service.feed_directory.fetch = fetch
    async def scenario():
        params = {"query": "AI & أخبار", "category": "technology"}
        first = await service.dispatch("news.directory", params)
        assert len(first["feeds"]) == 1 and not first["cached"]
        assert (await service.dispatch("news.directory", params))["cached"]
        assert len(network) == 1
        assert parse_qs(urlsplit(network[0]).query)["q"] == ["AI & أخبار"]
        assert service.news.snapshot()["subscriptions"] == []
        await service.dispatch("news.directory", {**params, "cursor": first["next_cursor"]})
        assert len(network) == 2
        item = first["feeds"][0]
        a = await service.dispatch("news.subscribe", {"url": item["url"], "title": item["title"], "kind": "rss"})
        b = await service.dispatch("news.subscribe", {"url": item["url"], "title": item["title"], "kind": "rss"})
        assert a["id"] == b["id"]
        assert len(service.news.snapshot()["subscriptions"]) == 1
        assert scheduled == [a["id"], a["id"]]
        assert not (service.store.path.parent / "sources.yml").exists()
    asyncio.run(scenario())


def test_offline_expiry_and_refresh(service):
    async def good(url):
        return {"status": 200, "body": json.dumps({"feeds": [entry()]}).encode()}
    async def offline(url):
        raise NewsError("offline")
    async def scenario():
        service.feed_directory.fetch = good
        await service.dispatch("news.directory", {})
        service.feed_directory.fetch = offline
        with service.db:
            service.db.execute("UPDATE feed_directory_cache SET fetched=?", (time.time() - TTL - 1,))
        fallback = await service.dispatch("news.directory", {})
        assert fallback["stale"] and fallback["cached"] and len(fallback["feeds"]) == 1
        with service.db:
            service.db.execute("UPDATE feed_directory_cache SET fetched=?", (time.time() - MAX_STALE - 1,))
        with pytest.raises(Failure, match="RSS.mobi"):
            await service.dispatch("news.directory", {})
        service.feed_directory.fetch = good
        assert not (await service.dispatch("news.directory", {"refresh": True}))["stale"]
    asyncio.run(scenario())


def test_validation_cache_bound_and_local_preservation(service):
    async def fetch(url):
        return {"status": 200, "body": b'{"feeds":[]}'}
    service.feed_directory.fetch = fetch
    async def scenario():
        local = await service.dispatch("news.library", {})
        path = service.store.path.parent / "sources.yml"
        original = path.read_bytes()
        for params in ({"query": "x" * 101}, {"category": "//bad"}, {"cursor": "bad"}):
            with pytest.raises(Failure):
                await service.dispatch("news.directory", params)
        for number in range(MAX_PAGES + 2):
            await service.dispatch("news.directory", {"query": str(number)})
        assert service.db.execute("SELECT count(*) FROM feed_directory_cache").fetchone()[0] == MAX_PAGES
        assert path.read_bytes() == original
        assert (await service.dispatch("news.library", {}))["feeds"] == local["feeds"]
    asyncio.run(scenario())
