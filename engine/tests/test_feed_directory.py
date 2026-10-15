import asyncio
import time
import pytest
from eis_engine.contracts import Failure
from eis_engine.feed_directory import parse_opml, TTL, MAX_STALE
from eis_engine.news import NewsError
from eis_engine.service import Service
from eis_engine.storage import Store


def opml(count=459):
    rows = ''.join(f'<outline title="Publisher {n}" xmlUrl="https://p{n}.example/rss" htmlUrl="https://p{n}.example/"/>' for n in range(count))
    return ('<opml version="2.0"><body>' + rows + '</body></opml>').encode()


@pytest.fixture
def service(tmp_path):
    service = Service(Store(tmp_path / 'workspace'))
    yield service
    service.store.close()


def test_complete_directory_and_unsafe_links():
    assert len(parse_opml(opml())['feeds']) == 459
    assert parse_opml(opml())['next_cursor'] == ''
    data=b'<opml><body><outline xmlUrl="http://127.0.0.1/feed"/><outline title="ok" xmlUrl="https://example.com/rss"/><outline xmlUrl="https://example.com/rss"/></body></opml>'
    assert len(parse_opml(data)['feeds']) == 1


@pytest.mark.parametrize('body', [b'<html/>', b'<opml/>', b'bad', b'<!DOCTYPE opml [<!ENTITY x "test">]><opml><body/></opml>', b'\x00<opml/>'])
def test_invalid_xml_rejected(body):
    with pytest.raises(ValueError): parse_opml(body)


def test_search_entire_directory_cache_and_no_subscriptions(service):
    calls=[]
    async def fetch(url):
        calls.append(url)
        return {'status':200,'body':opml()}
    service.feed_directory.fetch=fetch
    async def run():
        first=await service.dispatch('news.directory',{})
        assert len(first['feeds'])==459
        assert not first['cached']
        last=await service.dispatch('news.directory',{'query':'Publisher 458'})
        assert len(last['feeds'])==1 and last['feeds'][0]['title']=='Publisher 458'
        assert last['cached'] and len(calls)==1
        assert service.news.snapshot()['subscriptions']==[]
        await service.dispatch('news.directory',{'category':'world-news'})
        assert calls[-1]=='https://rss.mobi/tag/world-news/opml.xml'
        assert not (service.store.path.parent/'sources.yml').exists()
    asyncio.run(run())


def test_offline_preserves_full_directory_and_expiry(service):
    async def good(url): return {'status':200,'body':opml()}
    async def bad(url): raise NewsError('offline')
    async def run():
        service.feed_directory.fetch=good
        await service.dispatch('news.directory',{})
        service.feed_directory.fetch=bad
        with service.db: service.db.execute('UPDATE feed_directory_cache SET fetched=?',(time.time()-TTL-1,))
        page=await service.dispatch('news.directory',{})
        assert page['stale'] and len(page['feeds'])==459
        with service.db: service.db.execute('UPDATE feed_directory_cache SET fetched=?',(time.time()-MAX_STALE-1,))
        with pytest.raises(Failure): await service.dispatch('news.directory',{})
    asyncio.run(run())


@pytest.mark.parametrize('params',[{'query':'a'*101},{'category':'../bad'},{'category':'https://evil.example'}])
def test_invalid_search(service,params):
    with pytest.raises(Failure): asyncio.run(service.dispatch('news.directory',params))
