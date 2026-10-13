"""Current-news discovery and explicit article attachments use bounded public evidence."""
import asyncio
from datetime import datetime, timezone, timedelta
from html import escape
from urllib.parse import quote

from eis_engine.news_search import discover, research, research_query
from eis_engine.news import NewsManager
from eis_engine.storage import Store


def test_research_query_keeps_named_product_and_unwraps_publisher(tmp_path):
    assert research_query("عطني آخر خبر عن ChatGPT عشان أنزله في تويتر") == "ChatGPT"
    published = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    old = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    destination = "https://publisher.example/news?id=42"
    wrapped = "https://www.bing.com/news/apiclick.aspx?url=" + quote(destination, safe="")
    xml = (f"<rss><channel><title>News</title><item><title>New ChatGPT feature</title>"
           f"<link>{escape(wrapped)}</link><pubDate>{published}</pubDate></item>"
           f"<item><title>Old ChatGPT item</title><link>https://other.example/old</link><pubDate>{old}</pubDate></item>"
           "</channel></rss>").encode()
    async def fetch(url, conditional):
        return {"url":url,"headers":{"content-type":"application/rss+xml"},"body":xml}
    found = asyncio.run(discover(fetch, "ChatGPT"))
    assert len(found) == 1
    assert found[0]["url"] == destination


def test_research_reads_only_accessible_article_text():
    published = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    xml = (f"<rss><channel><title>News</title><item><title>ChatGPT launches a feature</title>"
           f"<link>https://publisher.example/story</link><pubDate>{published}</pubDate></item>"
           "</channel></rss>").encode()
    html = ("<html><head><title>ChatGPT launches a feature</title></head><body><article>" +
            "<p>" + "A report with enough publicly readable article content. " * 8 + "</p></article></body></html>").encode()
    async def fetch(url, conditional):
        if "bing.com" in url: return {"url":url,"headers":{"content-type":"application/rss+xml"},"body":xml}
        return {"url":url,"headers":{"content-type":"text/html"},"body":html}
    found = asyncio.run(research(fetch, "آخر خبر عن ChatGPT"))
    assert len(found) == 1
    assert found[0]["origin"] == "web" and found[0]["body_status"] == "full"
    assert "publicly readable" in found[0]["text"]


def test_import_article_does_not_add_a_feed_subscription(tmp_path):
    store = Store(tmp_path)
    html = ("<html><head><title>Article example</title></head><body><article>" +
            "<p>" + "A public article the user explicitly attached to the chat. " * 8 + "</p>" +
            "</article></body></html>").encode()
    async def fetch(url, conditional):
        return {"url":url,"headers":{"content-type":"text/html"},"body":html}
    manager = NewsManager(store, fetch)
    first = asyncio.run(manager.import_article("https://publisher.example/article"))
    with store.db:
        store.db.execute("UPDATE news_articles SET text='', body_status='summary', reader_json='{}' WHERE id=?", (first["article_id"],))
    second = asyncio.run(manager.import_article("https://publisher.example/article"))
    assert first == second
    assert manager.article(first["article_id"], mark_read=False)["body_status"] == "full"
    assert manager.snapshot()["subscriptions"] == []
    store.close()
