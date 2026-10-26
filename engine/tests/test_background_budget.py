import asyncio
from unittest.mock import patch
from eis_engine.background_budget import BackgroundBudget
from test_news_digest import service


def test_thermal_power_cooldown_and_stale_device_signals():
    with patch('eis_engine.background_budget.time.monotonic', return_value=100) as clock:
        budget = BackgroundBudget()
        assert budget.phase() == 'waiting_device'
        for state in ('fair','serious','critical'):
            budget.update({'thermal':state,'low_power':False,'memory_pressure':'normal','on_battery':False})
            assert budget.phase() == 'cooling'
        budget.update({'thermal':'nominal','low_power':True,'memory_pressure':'normal','on_battery':False})
        assert budget.phase() == 'low_power'
        budget.update({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False})
        assert budget.phase() == ''
        budget.finished(30)
        assert budget.next_at == 108
        assert budget.phase() == 'resting'
        clock.return_value = 221
        assert budget.phase() == 'waiting_device'
        budget.update({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False})
        assert budget.phase() == ''


def test_hot_signal_interrupts_local_work_and_blocks_restart(service):
    async def scenario():
        digest = service.news_digest
        digest.local.installed = {'custom:small':100}
        digest.configure({'enabled':True,'engine':'local','local_model':'custom:small'})
        digest.active_request = asyncio.create_task(asyncio.sleep(100))
        digest.device_state({'thermal':'serious','low_power':False,'memory_pressure':'normal','on_battery':False})
        await asyncio.gather(digest.active_request, return_exceptions=True)
        assert digest.active_request.cancelled()
        digest.active_request = None
        assert not await digest.prepare_next()
        assert digest.status()['phase'] == 'cooling'
    asyncio.run(scenario())


def test_digest_status_does_not_rescan_unchanged_archive(service):
    digest = service.news_digest
    with patch.object(digest.cache, 'rows', side_effect=AssertionError('Idle full-body scan')):
        digest.status()
        digest.status()
        with service.db:
            service.db.execute("UPDATE news_articles SET text=text || ' Correction' WHERE id='story'")
        assert digest.status()['pending'] == 1


def test_local_generation_releases_model_on_cancellation(service, monkeypatch):
    import httpx
    from types import SimpleNamespace
    from agno.agent import Agent
    from eis_engine.article_summary import ArticleSummary
    async def scenario():
        local = service.news_digest.local
        local.runtime = True
        async def checked(name): return name
        local.check_generation = checked
        local.capacity = lambda name: {'fit':'fits'}
        started = asyncio.Event()
        async def generate(self, *args, **kwargs):
            started.set()
            await asyncio.Event().wait()
        monkeypatch.setattr(Agent, 'arun', generate)
        requests = []
        real_client = httpx.AsyncClient
        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={'models':[]} if request.url.path=='/api/ps' else {'done':True})
        monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handle)))
        task = asyncio.create_task(local.run('custom:small','Summarize',{'text':'Evidence'},ArticleSummary))
        await asyncio.wait_for(started.wait(),2)
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        assert task.cancelled()
        import json
        assert any(r.url.path=='/api/generate' and json.loads(r.content)['keep_alive']==0 for r in requests)
    asyncio.run(scenario())


def test_automatic_embeddings_share_quiet_budget_and_yield_to_conversation(service):
    async def scenario():
        knowledge = service.news.knowledge
        knowledge.configure({'enabled':True})
        knowledge.index_next()
        class Encoder:
            calls = 0
            def encode(self, texts):
                self.calls += 1
                return [[0.1]*256 for _ in texts]
        knowledge.embedder = Encoder()
        assert not await knowledge.embed_next()  # no native device signal yet
        service.news_digest.device_state({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False})
        async with service.model_lock:
            assert not await knowledge.embed_next()
        assert await knowledge.embed_next()
        assert knowledge.embedder.calls == 1
        assert not service.model_lock.locked()
        assert service.news_digest.budget.phase() == 'resting'
        assert not await knowledge.embed_next()
    asyncio.run(scenario())


def test_summary_idle_gate_and_duty_cycle_do_not_slow_search():
    with patch('eis_engine.background_budget.time.monotonic',return_value=100):
        b=BackgroundBudget()
        healthy={'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False}
        b.update(healthy)
        assert b.phase() == ''
        assert b.summary_phase() == 'waiting_device'
        b.update({**healthy,'idle_seconds':0})
        assert b.summary_phase() == 'waiting_idle'
        assert b.summary_phase(manual=True) == ''
        b.update({**healthy,'idle_seconds':60})
        assert b.summary_phase() == ''
        assert b.summary_phase(archive=True) == 'waiting_idle'
        b.update({**healthy,'idle_seconds':200})
        assert b.summary_phase(archive=True) == ''
        b.summary_finished(40)
        assert b.summary_next_at == 180
        assert b.phase() == ''  # Embeddings are not held by the summary rest.
        assert b.summary_phase() == 'resting'
        assert b.summary_phase(manual=True) == ''
        b.configure({'index_on_battery':True})
        b.update({**healthy,'idle_seconds':200,'on_battery':True})
        assert b.summary_phase(archive=True) == 'waiting_charger'


def test_returning_user_cancels_only_automatic_summary(service):
    async def run():
        d=service.news_digest
        d.local.installed={'custom:small':100}
        d.configure({'enabled':True,'engine':'local','local_model':'custom:small'})
        d.active_request=asyncio.create_task(asyncio.sleep(100))
        d.device_state({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False,'idle_seconds':0})
        await asyncio.gather(d.active_request,return_exceptions=True)
        assert d.active_request.cancelled()
        d.active_request=asyncio.create_task(asyncio.sleep(100))
        d.manual_pending=True
        d.device_state({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False,'idle_seconds':0})
        await asyncio.sleep(0)
        assert not d.active_request.cancelled()
        d.active_request.cancel()
        await asyncio.gather(d.active_request,return_exceptions=True)
        d.active_request=None
        d.manual_pending=False
    asyncio.run(run())


def test_invalid_idle_signals_are_not_treated_as_idle():
    import pytest
    from eis_engine.contracts import Failure
    b=BackgroundBudget()
    for value in (-1, float('nan'), float('inf'), True, '600'):
        with pytest.raises(Failure):
            b.update({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False,'idle_seconds':value})


def test_busy_device_does_not_fetch_bodies_or_hold_generation_weights(service):
    from unittest.mock import AsyncMock
    async def run():
        d=service.news_digest
        d.local.installed={'custom:small':100}
        d.configure({'enabled':True,'engine':'local','local_model':'custom:small'})
        d.device_state({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False,'idle_seconds':0})
        d.local.release_generation=AsyncMock()
        with patch.object(d.cache,'candidate',side_effect=AssertionError('Body fetched while user active')):
            assert not await d.prepare_next()
        d.local.release_generation.assert_awaited_once()
        assert not d.has_pending()  # Do not reserve the search model's next turn.
        assert d.status()['phase']=='waiting_idle'
    asyncio.run(run())


def test_archive_needs_longer_idle_than_current_news():
    from datetime import datetime,timedelta,timezone
    from eis_engine.news_digest import NewsDigest
    assert not NewsDigest.is_archive({'published_at':datetime.now(timezone.utc).isoformat()})
    assert NewsDigest.is_archive({'published_at':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()})
    assert NewsDigest.is_archive({})
