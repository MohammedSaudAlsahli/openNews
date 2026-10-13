"""RSS-first tools preserve dates, citations and explicit web permissions."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from eis_engine.conversation_tools import ConversationTools
from eis_engine.news import NewsManager
from eis_engine.storage import Store, uid, now


def test_searches_history_dates_and_does_not_fetch_full_cached_article(tmp_path):
    store=Store(tmp_path);news=NewsManager(store);sid,aid=uid(),uid()
    store.db.execute('INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,created_at) VALUES(?,?,?,?,?,?,?)',(sid,news.ws,'Official','https://example.com','https://example.com/rss','rss',now()))
    store.db.execute('INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary,text,body_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(aid,news.ws,sid,aid,'Anthropic announcement','https://example.com/story','2025-08-05T09:00:00Z',now(),'Summary','Full saved article','full'))
    async def forbidden(*args): raise AssertionError('Cached article should not be downloaded')
    news.fetch=forbidden
    async def run():
        tools=ConversationTools(news,[],lambda *args:None)
        found=json.loads(await tools.search_saved_articles('Anthropic','2025-08-05','2025-08-05'))
        assert [v['id'] for v in found['articles']]==[aid]
        assert json.loads(await tools.search_saved_articles('Anthropic','2025-08-06','2025-08-06'))['articles']==[]
        assert json.loads(await tools.read_saved_article(aid))['text']=='Full saved article'
        assert news.article(aid,mark_read=False)['is_read']==0
    asyncio.run(run());store.close()


def test_web_search_read_citation_and_no_new_subscription(tmp_path):
    store=Store(tmp_path)
    async def fetch(url,conditional):
        return {'url':url,'body':b'<html><head><title>Official announcement</title><meta property="article:published_time" content="2025-08-05T12:00:00Z"></head><body><article><p>'+b'Public factual article content. '*20+b'</p></article></body></html>'}
    news=NewsManager(store,fetch)
    class Search:
        def web_search(self, query):
            assert query=='Anthropic August 5 2025'
            return json.dumps([{'title':'Official announcement','href':'https://example.com/story','body':'Search excerpt'}])
    async def run():
        tools=ConversationTools(news,[],lambda *args:None,searcher=Search())
        found=json.loads(await tools.search_web('Anthropic August 5 2025'))['results'][0]
        full=json.loads(await tools.read_web_page(found['url']))
        assert full['id']==found['id'] and full['body_status']=='full'
        assert full['published_at'].startswith('2025-08-05')
        assert len(tools.evidence)==1
        assert store.rows('SELECT id FROM news_subscriptions')==[]
        disabled=ConversationTools(news,[],lambda *args:None,allow_web=False)
        assert [f.__name__ for f in disabled.functions]==['search_saved_articles','read_saved_article']
        assert 'error' in json.loads(await disabled.search_web('query'))
    asyncio.run(run());store.close()


def test_diverse_context_prevents_busy_feed_crowding_out_other_sources():
    from eis_engine.news_context import diverse_articles
    rows=[{'id':str(i),'url':f'https://dev.example/{i}','source_title':'Busy'} for i in range(100)]
    rows += [{'id':'official','url':'https://official.example','source_title':'Official'}]
    assert diverse_articles(rows,3)[1]['id']=='official'
