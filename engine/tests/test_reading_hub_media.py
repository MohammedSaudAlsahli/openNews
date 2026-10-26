import asyncio
import json
import pytest
from eis_engine.service import Service
from eis_engine.storage import Store, uid, now
from eis_engine.reading_workspace import dispatch
from eis_engine.contracts import Failure
from eis_engine.source_media import load, media_type


@pytest.fixture
def fixture(tmp_path):
    service = Service(Store(tmp_path))
    sid, aid, bid = uid(),uid(),uid()
    with service.db:
        service.db.execute('INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,created_at) VALUES(?,?,?,?,?,?,?)',(sid,service.ws,'Publisher','https://example.org','https://example.org/rss','rss',now()))
        for identifier,title,text in [(aid,'Space mission','A mission launched today with new scientific instruments. '*20),(bid,'Space agency','The agency described its engineering plans in a public interview. '*20)]:
            service.db.execute('INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,discovered_at,summary,text,body_status,reader_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(identifier,service.ws,sid,identifier,title,'https://example.org/'+identifier,now(),text,text,'full',json.dumps({'blocks':[{'type':'audio','id':'a','url':'https://example.org/voice.mp3'}]})))
    yield service,aid,bid
    service.store.close()


def test_queue_topics_quotes_and_catchup_persist_without_models(fixture):
    s,a,b=fixture
    assert dispatch(s,{'action':'queue','article_id':a,'enabled':True})['queue']==[a]
    assert dispatch(s,{'action':'briefing','view':'queue'})['articles'][0]['id']==a
    dispatch(s,{'action':'topic','topic':'Space'})
    assert len(dispatch(s,{'action':'briefing','view':'topic','topic':'Space'})['articles'])==2
    quote=dispatch(s,{'action':'quote','article_id':a,'text':'A mission launched today.'})['quotes'][0]
    assert quote['url'].endswith(a)
    dispatch(s,{'action':'caught_up','article_ids':[a]})
    assert [r['id'] for r in dispatch(s,{'action':'briefing','view':'catchup'})['articles']]==[b]
    dispatch(s,{'action':'mute','topic':'Space'})
    assert dispatch(s,{'action':'briefing','view':'catchup'})['articles']==[]
    dispatch(s,{'action':'mute','topic':'Space','enabled':False})
    assert dispatch(s,{'action':'get'})['topics']==['Space']
    assert dispatch(s,{'action':'comparison','article_id':a,'other_id':b})['method']=='literal_excerpt_comparison'


def test_five_minutes_is_bounded_and_invalid_actions_do_not_write(fixture):
    s,a,b=fixture
    report=dispatch(s,{'action':'briefing','view':'five'})
    assert sum(r['reading_minutes'] for r in report['articles'])<=5
    with pytest.raises(Failure): dispatch(s,{'action':'queue','article_id':'foreign','enabled':True})
    assert dispatch(s,{})['queue']==[]


def test_media_never_fetches_unrecorded_url_and_rejects_html(fixture):
    s,a,b=fixture
    calls=[]
    async def fetch(url, headers):
        calls.append(url)
        return {'body':b'<html>fake audio</html>'}
    s.news.fetch=fetch
    async def run():
        with pytest.raises(Failure): await load(s,{'article_id':a,'url':'https://example.org/not-recorded.mp3'})
        assert calls==[]
        with pytest.raises(Failure): await load(s,{'article_id':a,'url':'https://example.org/voice.mp3'})
        assert len(calls)==1
        async def audio(url,headers): return {'body':b'ID3test'}
        s.news.fetch=audio
        result=await load(s,{'article_id':a,'url':'https://example.org/voice.mp3'})
        assert result['mime']=='audio/mpeg'
        assert result['path'].endswith('.media')
        async def forbidden(*args): raise AssertionError('Cached media must not download again')
        s.news.fetch=forbidden
        assert await load(s,{'article_id':a,'url':'https://example.org/voice.mp3'}) == result
    asyncio.run(run())
    assert media_type(b'<svg/>') is None


def test_public_state_omits_internal_indexes_and_bounds_quotes():
    from eis_engine.reading_workspace import public_state
    state = public_state({'quotes':[{'text':'x'*4000} for _ in range(500)],
        'visits':{'private':'internal'}, 'catchup_seen':['internal']})
    assert len(state['quotes']) == 40
    assert state['quotes_total'] == 500
    assert 'visits' not in state and 'catchup_seen' not in state
    assert len(json.dumps(state).encode()) < 1024*1024
