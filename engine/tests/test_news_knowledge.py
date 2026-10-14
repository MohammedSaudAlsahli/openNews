"""Persistent hybrid retrieval, exact dates and stale evidence exclusion."""
import asyncio
from pathlib import Path
import pytest
from eis_engine.news import NewsManager
from eis_engine.news_knowledge import NewsKnowledge, chunks
from eis_engine.storage import Store, now


class Embeddings:
    def __init__(self): self.calls = 0
    def encode(self, texts, query=False):
        self.calls += 1
        return [[1.,0.] if ('Claude' in text or 'ذكاء' in text) else [0.,1.] for text in texts]


@pytest.fixture
def knowledge(tmp_path):
    store = Store(tmp_path)
    news = NewsManager(store)
    with store.db:
        store.db.execute("INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,created_at) VALUES('feed',?,'Publisher','https://example.com/feed','https://example.com/feed','rss',?)",(store.workspace,now()))
        for key,title,day in [('ai','Claude release','2025-08-05'),('sport','Football','2025-08-06')]:
            store.db.execute("INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary,text,body_status) VALUES(?,?,'feed',?,?,?,?,?,'',?,'full')", (key,store.workspace,key,title,'https://example.com/'+key,day,now(),title+' evidence '*20))
    value = NewsKnowledge(news,Embeddings())
    yield value
    store.close()


def test_semantic_cross_language_and_exact_date_filter(knowledge):
    async def run():
        k=knowledge
        while k.index_next(): pass
        assert [r['id'] for r in await k.search('Claude')] == ['ai']
        assert await k.search('ذكاء') == []
        k.configure({'enabled':True})
        while await k.embed_next(): pass
        assert [r['id'] for r in await k.search('ذكاء')] == ['ai']
        assert await k.search('ذكاء','2025-08-06','2025-08-06') == []
        assert (await k.search('ذكاء','2025-08-05','2025-08-05'))[0]['url']=='https://example.com/ai'
        assert await k.search('Claude','2024-01-01','2024-12-31')==[]
    asyncio.run(run())


def test_reopen_uses_saved_vectors_and_changes_invalidate_immediately(knowledge):
    async def run():
        k=knowledge
        while k.index_next(): pass
        k.configure({'enabled':True})
        while await k.embed_next(): pass
        restored=NewsKnowledge(k.news,Embeddings())
        assert await restored.embed_next() is False
        assert restored.embedder.calls==0
        with k.db:
            k.db.execute("UPDATE news_articles SET title='Corrected',text='Different evidence' WHERE id='ai'")
        assert await restored.search('Claude')==[]
        assert restored.index_next()
        assert await restored.embed_next()
        with k.db: k.db.execute("DELETE FROM news_articles WHERE id='sport'")
        assert k.db.execute("SELECT count(*) FROM news_search_chunks WHERE article_id='sport'").fetchone()[0]==0
        assert all(r['id']!='sport' for r in await restored.search('Football'))
    asyncio.run(run())


def test_index_contains_tail_and_does_not_change_read_or_bookmark_state(knowledge):
    k=knowledge
    with k.db: k.db.execute("UPDATE news_articles SET text=? WHERE id='ai'",('begin '*1000+'uniquetailword',))
    while k.index_next(): pass
    found=asyncio.run(k.search('uniquetailword'))
    assert found[0]['id']=='ai' and 'uniquetailword' in found[0]['text']
    assert not k.news.article('ai',mark_read=False)['is_read']
    assert ''.join(chunks('x'*5000)).count('x')>=5000


def test_download_failure_keeps_keyword_search(knowledge):
    class Broken:
        def encode(self,*args,**kwargs): raise OSError('offline')
    async def run():
        k=knowledge
        while k.index_next(): pass
        k.embedder=Broken();k.configure({'enabled':True})
        assert await k.embed_next() is False
        assert k.status()['phase']=='unavailable'
        assert (await k.search('Claude'))[0]['id']=='ai'
    asyncio.run(run())
