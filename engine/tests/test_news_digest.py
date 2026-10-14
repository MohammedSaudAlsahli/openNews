"""Public article caching and opt-in background summary contracts."""
import asyncio

import pytest

from eis_engine.article_summary import ArticleSummary
from eis_engine.contracts import Failure
from eis_engine.service import Service
from eis_engine.storage import Store, encode, now


class FakeModel:
    def __init__(self): self.calls = []
    async def run(self, profile, instructions, data, schema):
        self.calls.append((profile["model_id"], data["title"]))
        return ArticleSummary(summary="A grounded, short summary.")


@pytest.fixture
def service(tmp_path):
    value = Service(Store(tmp_path / "workspace"), FakeModel())
    with value.db:
        value.db.execute("""INSERT INTO news_subscriptions
            (id,workspace_id,title,url,feed_url,kind,created_at)
            VALUES('feed',?,?,?,?,?,?)""", (value.ws,"Publisher","https://publisher.example/feed","https://publisher.example/feed","rss",now()))
        value.db.execute("""INSERT INTO news_articles
            (id,workspace_id,subscription_id,guid,title,url,discovered_at,summary,text,body_status)
            VALUES('story',?,'feed','story','Important story','https://publisher.example/story',?,?,?,'full')""",
            (value.ws,now(),"Feed excerpt","A full public story with enough factual context. " * 20))
    yield value
    value.store.close()


def test_digest_requires_assignment_and_opt_in(service):
    with pytest.raises(Failure): service.news_digest.configure({"enabled":True,"language":"en"})
    assert asyncio.run(service.news_digest.prepare_next()) is False
    assert service.factory.calls == []


def test_digest_uses_selected_model_once_and_keeps_cached_preview(service):
    async def scenario():
        saved = await service.dispatch("providers.save", {"provider_key":"openai","model_id":"economy"})
        profile_id = saved["profile_id"]
        with service.db:
            service.db.execute("INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)",
                               (profile_id,service.ws,encode([{"id":"economy","available":True}]),"fixture",now(),None,9999999999))
        await service.dispatch("agents.assign", {"role":"news","profile_id":profile_id,"model_id":"economy"})
        service.news_digest.configure({"enabled":True,"language":"en"})
        assert await service.news_digest.prepare_next() is True
        assert service.news_digest.preview("story","en")["summary"] == "A grounded, short summary."
        assert service.factory.calls == [("economy","Important story")]
        assert await service.news_digest.prepare_next() is False
        with service.db:
            service.db.execute("UPDATE news_articles SET text=text || ' Corrected detail.' WHERE id='story'")
        assert service.news_digest.preview("story","en") is None
        assert await service.news_digest.prepare_next() is True
        assert len(service.factory.calls) == 2
        service.news_digest.configure({"enabled":False,"language":"en"})
        assert await service.news_digest.prepare_next() is False
    asyncio.run(scenario())


def test_rendered_public_page_is_saved_for_future_reading(service):
    with service.db:
        service.db.execute("UPDATE news_articles SET body_status='summary_only',text='Feed excerpt' WHERE id='story'")
    page = "<html><body><article><h1>Important story</h1><p>" + ("Public evidence and context. " * 20) + "</p></article></body></html>"
    article = service.news.capture_public_reader("story",page)
    assert article["body_status"] == "full"
    assert "Public evidence" in article["text"]
    assert article["is_read"] is False
    assert service.news.capture_public_reader("story","<html></html>")["text"] == article["text"]


def test_user_message_can_interrupt_background_summary(service):
    async def scenario():
        saved = await service.dispatch("providers.save", {"provider_key":"openai","model_id":"economy"})
        profile_id = saved["profile_id"]
        with service.db:
            service.db.execute("INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)",
                               (profile_id,service.ws,encode([{"id":"economy","available":True}]),"fixture",now(),None,9999999999))
        await service.dispatch("agents.assign", {"role":"news","profile_id":profile_id,"model_id":"economy"})
        service.news_digest.configure({"enabled":True,"language":"en"})
        started = asyncio.Event()
        async def slow_model(*args, **kwargs):
            started.set()
            await asyncio.Event().wait()
        service.factory.run = slow_model
        task = asyncio.create_task(service.news_digest.prepare_next())
        await asyncio.wait_for(started.wait(), 2)
        service.news_digest.interrupt_for_user()
        assert await asyncio.wait_for(task, 2) is False
        assert not service.model_lock.locked()
        assert service.news_digest.current_title == ""
    asyncio.run(scenario())


def test_daily_budget_counts_failures_and_survives_reopen(service):
    from eis_engine.news_digest import NewsDigest
    async def run():
        saved=await service.dispatch('providers.save',{'provider_key':'openai','model_id':'economy'})
        pid=saved['profile_id']
        with service.db:
            service.db.execute('INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)',(pid,service.ws,encode([{'id':'economy','available':True}]),'fixture',now(),None,9999999999))
        await service.dispatch('agents.assign',{'role':'news','profile_id':pid,'model_id':'economy'})
        service.news_digest.configure({'enabled':True,'language':'en','daily_limit':1})
        async def fail(*args,**kwargs): raise OSError('provider unavailable')
        service.factory.run=fail
        assert await service.news_digest.prepare_next()
        reopened=NewsDigest(service)
        assert reopened.status()['used_today']==1
        assert await reopened.prepare_next() is False
        assert reopened.preview('story') is None
        assert reopened.status()['pending']==1
    asyncio.run(run())


def test_incomplete_articles_never_enter_background_queue(service):
    with service.db: service.db.execute("UPDATE news_articles SET body_status='summary_only' WHERE id='story'")
    assert service.news_digest.status()['pending']==0
    assert service.news_digest.cache.rows()==[]


def test_metadata_changes_invalidate_summary_status(service):
    async def run():
        saved=await service.dispatch('providers.save',{'provider_key':'openai','model_id':'economy'})
        pid=saved['profile_id']
        with service.db:
            service.db.execute('INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)',(pid,service.ws,encode([{'id':'economy','available':True}]),'fixture',now(),None,9999999999))
        await service.dispatch('agents.assign',{'role':'news','profile_id':pid,'model_id':'economy'})
        service.news_digest.configure({'enabled':True,'language':'en'})
        await service.news_digest.prepare_next()
        assert service.news_digest.status()['prepared']==1
        with service.db: service.db.execute("UPDATE news_articles SET title='Correction' WHERE id='story'")
        assert service.news_digest.status()['prepared']==0
        assert service.news_digest.preview('story') is None
    asyncio.run(run())


def test_manual_summary_is_available_on_reopen_without_background_request(service):
    async def scenario():
        saved = await service.dispatch('providers.save', {'provider_key':'openai','model_id':'economy'})
        pid = saved['profile_id']
        with service.db:
            service.db.execute('INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)',
                (pid,service.ws,encode([{'id':'economy','available':True}]),'fixture',now(),None,9999999999))
        await service.dispatch('agents.assign', {'role':'news','profile_id':pid,'model_id':'economy'})
        from eis_engine.article_summary import summarize
        from eis_engine.news_digest import NewsDigest
        await summarize(service, {'consent':True,'article_id':'story','language':'en'})
        reopened = NewsDigest(service)
        assert reopened.preview('story','en')['summary'] == 'A grounded, short summary.'
        assert len(service.factory.calls) == 1
        reopened.configure({'enabled':True,'language':'en'})
        assert await reopened.prepare_next() is False
        assert reopened.status()['phase'] == 'ready'
    asyncio.run(scenario())
