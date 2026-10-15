import asyncio
import pytest
from eis_engine.feed_parser import normalize_subscription
from eis_engine.news_urls import NewsError
from eis_engine.storage import Store
from eis_engine.service import Service


def test_reddit_short_name_and_bridge_normalization():
    assert normalize_subscription("r/LocalLLaMA", "reddit")[1] == "https://www.reddit.com/r/LocalLLaMA/new/.rss"
    assert normalize_subscription("LocalLLaMA", "reddit")[2] == "reddit"
    for kind in ("x_rss", "reddit_rss"):
        assert normalize_subscription("https://feeds.example/public.xml", kind)[2] == kind
        with pytest.raises(NewsError): normalize_subscription("http://127.0.0.1/feed", kind)
    with pytest.raises(NewsError): normalize_subscription("https://x.com/OpenAI", "x_rss")
    with pytest.raises(NewsError): normalize_subscription("https://twitter.com/OpenAI", "auto")


def test_x_feed_archives_and_preserves_social_provenance(tmp_path):
    service = Service(Store(tmp_path / "workspace"))
    async def scenario():
        feed = "https://feeds.example/account.xml"
        body = b'<rss><channel><title>X account</title><item><guid>post-1</guid><title>Announcement</title><link>https://x.com/example/status/123</link><description>Early announcement from the account</description></item></channel></rss>'
        async def fetch(url, conditional=None):
            if url != feed: raise NewsError("Unavailable")
            return {"url":url,"status":200,"headers":{},"body":body}
        service.news.fetch = fetch
        ident = await service.news.add({"url":feed,"kind":"x_rss","title":"@example"})
        row = service.store.one("SELECT id FROM news_articles WHERE subscription_id=?", (ident,))
        assert row
        article = service.news.article(row["id"], mark_read=False)
        assert article["source_kind"] == "x_rss"
        assert article["url"] == "https://x.com/example/status/123"
        await service.news.sync(ident)
        assert service.store.one("SELECT count(*) AS n FROM news_articles")["n"] == 1
    try: asyncio.run(scenario())
    finally: service.store.close()
