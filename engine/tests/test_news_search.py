"""Explicit article attachment does not subscribe a feed."""
import asyncio
from eis_engine.news import NewsManager
from eis_engine.storage import Store


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
