import asyncio
from unittest.mock import patch
from eis_engine.background_budget import BackgroundBudget
from test_news_digest import service


def test_thermal_power_cooldown_and_stale_device_signals():
    with patch('eis_engine.background_budget.time.monotonic', return_value=100) as clock:
        budget = BackgroundBudget()
        assert budget.phase() == 'waiting_device'
        for state in ('fair','serious','critical'):
            budget.update({'thermal':state,'low_power':False})
            assert budget.phase() == 'cooling'
        budget.update({'thermal':'nominal','low_power':True})
        assert budget.phase() == 'low_power'
        budget.update({'thermal':'nominal','low_power':False})
        assert budget.phase() == ''
        budget.finished(30)
        assert budget.next_at == 220
        assert budget.phase() == 'resting'
        clock.return_value = 221
        assert budget.phase() == 'waiting_device'
        budget.update({'thermal':'nominal','low_power':False})
        assert budget.phase() == ''


def test_hot_signal_interrupts_local_work_and_blocks_restart(service):
    async def scenario():
        digest = service.news_digest
        digest.local.installed = {'custom:small':100}
        digest.configure({'enabled':True,'engine':'local','local_model':'custom:small'})
        digest.active_request = asyncio.create_task(asyncio.sleep(100))
        digest.device_state({'thermal':'serious','low_power':False})
        await asyncio.gather(digest.active_request, return_exceptions=True)
        assert digest.active_request.cancelled()
        digest.active_request = None
        assert not await digest.prepare_next()
        assert digest.status()['phase'] == 'cooling'
    asyncio.run(scenario())


def test_digest_status_does_not_rescan_unchanged_archive(service):
    digest = service.news_digest
    with patch.object(digest.cache, 'rows', wraps=digest.cache.rows) as rows:
        digest.status()
        digest.status()
        assert rows.call_count == 1
        with service.db:
            service.db.execute("UPDATE news_articles SET text=text || ' Correction' WHERE id='story'")
        digest.status()
        assert rows.call_count == 2


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
            return httpx.Response(200, json={'done':True})
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
        service.news_digest.device_state({'thermal':'nominal','low_power':False})
        async with service.model_lock:
            assert not await knowledge.embed_next()
        assert await knowledge.embed_next()
        assert knowledge.embedder.calls == 1
        assert not service.model_lock.locked()
        assert service.news_digest.budget.phase() == 'resting'
        assert not await knowledge.embed_next()
    asyncio.run(scenario())
