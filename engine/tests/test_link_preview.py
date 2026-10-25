"""Reader hover previews reuse evidence without model use or article mutations."""
import asyncio
import pytest
from eis_engine.contracts import Failure
from eis_engine.storage import Store
from eis_engine.service import Service
from test_news_digest import service, FakeModel
from test_summary_evidence import configure

URL = 'https://other.example/report'


def link(service, url=URL):
    with service.db:
        service.db.execute("UPDATE news_articles SET text=text || ? WHERE id='story'", (f' [Report]({url})',))


def test_hover_reuses_summary_sources_and_preserves_read_state(service):
    async def run():
        await configure(service)
        link(service)
        fetched=[]
        async def fetch(url, _):
            fetched.append(url)
            return {'url':url,'headers':{'content-type':'text/html'},'body':b'<html><head><title>Original report</title></head><body><article><p>The public report explains the proposal and the positions of participants. The process remains under review.</p></article></body></html>'}
        service.news.fetch=fetch
        assert await service.news_digest.prepare_next()
        calls=list(service.factory.calls)
        before=service.news_digest.preview('story','en')
        for _ in range(3):
            result=await service.dispatch('news.link.preview',{'article_id':'story','url':URL+'#context'})
            assert result['title']=='Original report' and result['cached']
            assert 'proposal' in result['excerpt']
        assert fetched==[URL] and service.factory.calls==calls
        assert service.news.article('story',mark_read=False)['is_read'] is False
        assert service.news_digest.preview('story','en')==before
        assert before['model']=='economy' and before['generated_at']
    asyncio.run(run())


def test_saved_article_preview_never_fetches_or_marks_read(service):
    async def run():
        async def forbidden(*_): raise AssertionError('No network needed')
        service.news.fetch=forbidden
        value=await service.dispatch('news.link.preview',{'article_id':'story','url':'https://publisher.example/story'})
        assert value['title']=='Important story' and value['cached']
        assert service.news.article('story',mark_read=False)['is_read'] is False
        assert service.factory.calls==[]
    asyncio.run(run())


@pytest.mark.parametrize('url',['https://unlinked.example/report','http://127.0.0.1/private','javascript:alert(1)'])
def test_preview_rejects_unlinked_or_unsafe_urls(service,url):
    with pytest.raises(Failure):
        asyncio.run(service.dispatch('news.link.preview',{'article_id':'story','url':url}))
    assert service.factory.calls==[]


def test_unavailable_post_and_non_text_are_cached(service):
    async def run():
        for url, mime in [('https://x.com/person/status/123','text/html'),('https://other.example/file.pdf','application/pdf')]:
            link(service,url)
            calls=[]
            async def fetch(address, _):
                calls.append(address)
                if 'x.com' in address: raise OSError('Sign-in required')
                return {'url':address,'headers':{'content-type':mime},'body':b'%PDF'}
            service.news.fetch=fetch
            first=await service.dispatch('news.link.preview',{'article_id':'story','url':url})
            second=await service.dispatch('news.link.preview',{'article_id':'story','url':url})
            assert first['status'] in {'unavailable','unsupported'}
            assert not first['excerpt'] and second['cached'] and calls==[url]
        assert service.factory.calls==[]
    asyncio.run(run())


def test_concurrent_previews_share_fetch_and_survive_restart(service):
    async def run():
        link(service)
        fetched=[]
        async def fetch(url,_):
            fetched.append(url)
            await asyncio.sleep(0)
            return {'url':url,'headers':{'content-type':'text/plain'},'body':('Public report context. '*30).encode()}
        service.news.fetch=fetch
        results=await asyncio.gather(*(service.dispatch('news.link.preview',{'article_id':'story','url':URL}) for _ in range(3)))
        assert len(fetched)==1 and all(r['status']=='read' for r in results)
        reopened=Service(Store(service.store.path.parent),FakeModel())
        try:
            async def forbidden(*_): raise AssertionError('Evidence must survive restart')
            reopened.news.fetch=forbidden
            result=await reopened.dispatch('news.link.preview',{'article_id':'story','url':URL})
            assert result['cached'] and result['excerpt']==results[0]['excerpt']
            assert reopened.factory.calls==[]
        finally: reopened.store.close()
    asyncio.run(run())


def test_persisted_summary_and_model_are_returned_after_engine_restart(service):
    async def run():
        await configure(service)
        assert await service.news_digest.prepare_next()
        original=service.news_digest.preview('story','en')
        reopened=Service(Store(service.store.path.parent),FakeModel())
        try:
            for _ in range(3):
                result=await reopened.dispatch('news.preview',{'article_id':'story'})
                assert result['prepared_summary']==original
                assert not result['is_read']
            assert original['model']=='economy' and original['cached'] and original['generated_at']
            assert reopened.factory.calls==[]
            assert not await reopened.news_digest.prepare_next()
        finally: reopened.store.close()
    asyncio.run(run())
