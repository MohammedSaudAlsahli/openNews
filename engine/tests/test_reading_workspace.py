import asyncio
import json
from datetime import datetime, timedelta, timezone
import pytest
from eis_engine.news import NewsManager
from eis_engine.storage import Store, uid, now, encode
from eis_engine.service import Service
from eis_engine.contracts import Failure
from eis_engine.article_reader import extract_reader
from eis_engine.article_summary import ArticleSummary


@pytest.fixture
def manager(tmp_path):
    store = Store(tmp_path)
    manager = NewsManager(store)
    sub = asyncio.run(manager.add({'url':'https://example.com/rss','title':'Publisher'},sync=False))
    for index in range(110):
        stamp = (datetime.now(timezone.utc)-timedelta(days=index)).isoformat()
        with store.db:
            store.db.execute('INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary,text) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (str(index),store.workspace,sub,str(index),f'Article {index}',f'https://example.com/{index}',stamp,stamp,'Short excerpt','Deep reading 100% code_block' if index==109 else 'Other body'))
    yield manager
    store.close()


def test_saved_articles_survive_recent_limit_restart_and_unbookmark(manager):
    manager.bookmark({'article_id':'109','saved':True})
    assert '109' not in [a['id'] for a in manager.snapshot()['articles']]
    reopened = NewsManager(manager.store)
    result = reopened.list_articles({'scope':'saved'})
    assert [a['id'] for a in result['articles']] == ['109']
    assert result['articles'][0]['is_bookmarked'] is True
    assert reopened.article('109',mark_read=False)['is_read'] is False
    reopened.bookmark({'article_id':'109','saved':False})
    assert reopened.list_articles({'scope':'saved'})['articles'] == []


def test_search_full_text_phrase_literal_wildcards_and_filters(manager):
    assert [a['id'] for a in manager.list_articles({'query':'"Deep reading" 100%'})['articles']] == ['109']
    assert manager.list_articles({'query':'missing%'})['articles'] == []
    assert manager.list_articles({'query':'"Deep reading"','days':7})['articles'] == []
    manager.article('0')
    assert all(a['id']!='0' for a in manager.list_articles({'scope':'unread'})['articles'])
    first = manager.list_articles({'limit':60})
    second = manager.list_articles({'limit':60,'offset':60})
    assert first['has_more'] and not second['has_more']
    assert len({a['id'] for a in first['articles']+second['articles']}) == 110


def test_invalid_filters_and_cross_workspace_mutation_are_rejected(manager):
    for params in [{'limit':True},{'scope':'anything'},{'query':[]},{'days':-1},{'offset':-1}]:
        with pytest.raises(Failure): manager.list_articles(params)
    with pytest.raises(Failure): manager.bookmark({'article_id':'0','saved':'false'})
    manager.ws = 'other-workspace'
    assert manager.list_articles({})['articles'] == []
    with pytest.raises(Failure): manager.bookmark({'article_id':'0','saved':True})


@pytest.mark.parametrize('fragment',[True,False])
def test_reader_keeps_code_indentation_and_quotes(fragment):
    paragraph = 'Useful article context and evidence. '*35
    body = '<article><h1>Formatting</h1><p>'+paragraph+'</p><pre><code>if ready:\n    print("hello")\n    values[0] = 1</code></pre><blockquote><p>A quoted statement.</p><p>A second paragraph.</p></blockquote><p>'+paragraph+'</p></article>'
    text = '\n'.join(b.get('text','') for b in extract_reader(body,'https://example.com/article',fragment=fragment)['blocks'])
    assert '```\nif ready:\n    print("hello")\n    values[0] = 1\n```' in text
    assert '> A quoted statement.' in text and '> A second paragraph.' in text
    assert 'OPENSTUDIOPRESERVED' not in text


def test_summary_requires_permission_uses_existing_model_and_caches(manager):
    class Factory:
        calls = []
        async def run(self,profile,instructions,data,schema):
            self.calls.append((profile,instructions,data,schema))
            return ArticleSummary(summary='- A concise summary.')
    service = Service(manager.store,Factory())
    async def run():
        pid = (await service.dispatch('providers.save',{'provider_key':'openai','model_id':'test-model'}))['profile_id']
        with service.db:
            service.db.execute('INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)',(pid,service.ws,encode([{'id':'test-model','available':True}]),'fixture',now(),None,9999999999))
        await service.dispatch('agents.assign',{'role':'writer','profile_id':pid,'model_id':'test-model'})
        payload = {'article_id':'109','language':'en'}
        with pytest.raises(Failure): await service.dispatch('news.summarize',payload)
        assert service.factory.calls == []
        result = await service.dispatch('news.summarize',payload|{'consent':True})
        cached = await service.dispatch('news.summarize',payload|{'consent':True})
        assert not result['cached'] and cached['cached'] and len(service.factory.calls)==1
        profile,instructions,data,schema = service.factory.calls[0]
        assert profile['model_id']=='test-model' and schema is ArticleSummary
        assert 'English.' in instructions and 'untrusted' in instructions
        assert data['text']=='Deep reading 100% code_block'
        assert not service.store.rows('SELECT * FROM chat_messages')
    asyncio.run(run())


def test_site_icon_never_returns_html_or_private_url(manager):
    calls=[]
    async def fetch(url, conditional):
        calls.append(url)
        return {'body':b'<html>Not an icon</html>'}
    manager.fetch = fetch
    assert asyncio.run(manager.site_icon('http://127.0.0.1/secret')) == {'path':''}
    assert not calls
    assert asyncio.run(manager.site_icon('https://example.com/story?private-query=yes')) == {'path':''}
    assert calls == ['https://example.com/favicon.ico']
