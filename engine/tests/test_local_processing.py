"""Responsiveness, durable scheduling and acknowledged cancellation regressions."""
import asyncio
import json
import time
import sqlite3
from unittest.mock import patch, Mock
from types import SimpleNamespace
import httpx
import pytest
from eis_engine.background_budget import BackgroundBudget
from eis_engine.contracts import Failure
from eis_engine.news_embeddings import LocalNewsEmbeddings
from test_news_digest import service

DEVICE = {'idle_seconds':600,'thermal':'nominal','low_power':False,'on_battery':False,'memory_pressure':'normal'}


def test_processing_policy_is_strict_persistent_and_device_is_protective(service):
    async def run():
        assert (await service.dispatch('news.local.policy',{}))['phase']=='waiting_device'
        result=await service.dispatch('news.local.policy.set',{'mode':'balanced','index_on_battery':True,'paused':True})
        assert result['paused'] and result['mode']=='balanced'
        restored=BackgroundBudget(service.store)
        assert restored.paused and restored.index_on_battery and restored.mode=='balanced'
        for invalid in ({'mode':'fast'},{'paused':1},{'index_on_battery':'yes'},{'anything':True},{}):
            with pytest.raises(Failure): restored.configure(invalid)
        restored.configure({'paused':False})
        assert restored.update({'idle_seconds':600,'thermal':'nominal','low_power':False})['phase']=='waiting_device'
        assert restored.update({**DEVICE,'on_battery':True})['phase']=='ready'
        restored.configure({'index_on_battery':False})
        assert restored.phase()=='waiting_charger'
        for pressure in ('warning','critical'):
            assert restored.update({**DEVICE,'memory_pressure':pressure})['phase']=='memory_pressure'
        restored.update(DEVICE)
        restored.updated-=31
        assert restored.phase()=='waiting_device'
    asyncio.run(run())


def test_balanced_and_quiet_have_bounded_batches_without_minute_floor():
    with patch('eis_engine.background_budget.time.monotonic',return_value=100):
        b=BackgroundBudget();b.update(DEVICE)
        assert b.batch_size==4
        b.finished(1)
        assert b.next_at==101
        b.configure({'mode':'balanced'})
        assert b.batch_size==12
        b.finished(1)
        assert b.next_at==100.25
        b.finished(100)
        assert b.next_at==102  # Long work cannot schedule an unbounded cool-off.


def test_pause_returns_promptly_but_retains_lease_until_server_stops(service,monkeypatch):
    async def run():
        k=service.news.knowledge
        k.configure({'enabled':True});k.index_next()
        k.embedder=LocalNewsEmbeddings(name='test:small',dimensions=2,digest='abc')
        service.news_digest.device_state(DEVICE)
        started,unloading,stopped=asyncio.Event(),asyncio.Event(),asyncio.Event()
        async def handler(request):
            path=request.url.path
            if path=='/api/tags': return httpx.Response(200,json={'models':[{'name':'test:small','digest':'abc'}]})
            if path=='/api/embed':
                started.set()
                await asyncio.Event().wait()  # HTTP client cancels; server still busy.
            if path=='/api/generate':
                unloading.set()
                return httpx.Response(200,json={'done':True})
            if path=='/api/ps': return httpx.Response(200,json={'models':[] if stopped.is_set() else [{'name':'test:small'}]})
            raise AssertionError(path)
        real=httpx.AsyncClient
        monkeypatch.setattr(httpx,'AsyncClient',lambda **kw: real(transport=httpx.MockTransport(handler)))
        async def runtime(): pass
        k.ensure_runtime=runtime
        worker=asyncio.create_task(k.embed_next())
        await asyncio.wait_for(started.wait(),1)
        before=time.monotonic()
        policy=await service.dispatch('news.local.policy.set',{'paused':True})
        assert time.monotonic()-before<.05 and policy['phase']=='stopping'
        await asyncio.wait_for(unloading.wait(),1)
        assert service.model_lock.locked() and not worker.done()
        # Repeat native pressure notifications must not abandon cleanup.
        service.news_digest.device_state({**DEVICE,'memory_pressure':'critical'})
        await asyncio.sleep(.01)
        assert service.model_lock.locked()
        stopped.set()
        assert await asyncio.wait_for(worker,1) is False
        assert not service.model_lock.locked() and not k.lock.locked()
        assert k.db.execute('SELECT count(vector) FROM news_search_chunks').fetchone()[0]==0
        assert service.news_digest.policy_status()['phase']=='paused'
    asyncio.run(run())


def test_fast_lexical_deadline_tracks_cleanup_and_releases_both_locks(service):
    import struct
    async def run():
        k=service.news.knowledge;k.index_next();k.configure({'enabled':True})
        class Delayed:
            async def aencode(self,texts,query=False): await asyncio.sleep(10)
        k.embedder=Delayed()
        with service.db: service.db.execute('UPDATE news_search_chunks SET vector=?,model=?',(struct.pack('2f',1.,0.),k.index_model))
        before=time.monotonic()
        result=await k.search('Important')
        assert result[0]['id']=='story' and time.monotonic()-before<.5
        assert k.cleanup_tasks  # Bounded cold warmup is tracked after lexical return.
        await asyncio.wait_for(asyncio.gather(*list(k.cleanup_tasks)),4)
        await asyncio.sleep(0)
        assert not k.cleanup_tasks and not k.lock.locked() and not service.model_lock.locked()
    asyncio.run(run())


def test_idle_digest_poll_and_status_never_load_article_bodies(service,monkeypatch):
    digest=service.news_digest
    assignment={'profile_id':'fixture','model_id':'fixture'}
    monkeypatch.setattr(digest,'assignment',lambda:assignment)
    with service.db:
        service.db.execute("INSERT INTO news_digest_settings(workspace_id,enabled,language,daily_limit,engine,local_model) VALUES(?,1,'en',20,'provider','')",(service.ws,))
    row=digest.cache.candidate('en',assignment,time.time())
    digest.cache.save(row,'en',assignment,'A complete English summary with verified context.')
    traced=[];service.db.set_trace_callback(traced.append)
    def metadata_only(action, table, column, *_):
        return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_READ and table=='news_articles' and column=='text' else sqlite3.SQLITE_OK
    service.db.set_authorizer(metadata_only)
    with patch('eis_engine.news_digest_cache.fingerprint',side_effect=AssertionError('Idle body hashing')):
        for _ in range(5):
            digest.status()
            assert digest.article_states(['story'])['states']['story']=='ready'
            assert not digest.cache.has_pending('en',assignment,time.time())
            assert digest.cache.candidate('en',assignment,time.time()) is None
    # SQLite rejects body reads, including from the card-state path.
    assert traced
    service.db.set_authorizer(None)
    service.db.set_trace_callback(None)


@pytest.mark.parametrize('column,value', [('title','Corrected title'),('url','https://publisher.example/new'),('published_at','2026-10-24'),('text','Revised evidence '*20),('body_status','summary_only')])
def test_durable_queue_invalidates_every_source_identity_field(service,column,value):
    cache=service.news_digest.cache;assignment={'profile_id':'fixture','model_id':'fixture'}
    row=cache.candidate('en',assignment,time.time())
    cache.save(row,'en',assignment,'A complete English summary with verified context.')
    assert cache.coverage('en',assignment)['prepared']==1
    with service.db: service.db.execute(f'UPDATE news_articles SET {column}=? WHERE id=?',(value,'story'))
    assert cache.coverage('en',assignment)['prepared']==0
    if column!='body_status': assert cache.candidate('en',assignment,time.time())['revision']==2
    else: assert cache.coverage('en',assignment)['total']==0
    with service.db: service.db.execute("DELETE FROM news_articles WHERE id='story'")
    assert service.db.execute('SELECT count(*) FROM news_digest_sources').fetchone()[0]==0


def test_durable_queue_identity_retry_duplicate_and_reopen(service):
    from eis_engine.news_digest import NewsDigest
    cache=service.news_digest.cache;assignment={'profile_id':'fixture','model_id':'fixture'}
    row=cache.candidate('en',assignment,time.time())
    cache.save(row,'en',assignment,attempts=1,retry_after=time.time()+300)
    assert cache.candidate('en',assignment,time.time()) is None
    assert cache.candidate('en',{'profile_id':'other','model_id':'fixture'},time.time())
    assert cache.candidate('ar',assignment,time.time())
    cache.save(row,'en',assignment,'A complete English summary with verified context.')
    restored=NewsDigest(service).cache
    assert restored.coverage('en',assignment)['prepared']==1
    assert restored.candidate('en',assignment,time.time()) is None


def test_external_runtime_is_not_terminated_and_unload_ack_is_not_enough(service,monkeypatch):
    async def run():
        local=service.news_digest.local
        checks=0
        async def handler(request):
            nonlocal checks
            if request.url.path=='/api/generate': return httpx.Response(200,json={'done':True})
            checks+=1
            return httpx.Response(200,json={'models':[{'name':'test:small'}] if checks<3 else []})
        real=httpx.AsyncClient
        monkeypatch.setattr(httpx,'AsyncClient',lambda **kw: real(transport=httpx.MockTransport(handler)))
        assert local.process is None
        await local.stop_inference('test:small')
        assert checks==3 and local.process is None
    asyncio.run(run())


def test_only_owned_runtime_can_be_terminated_after_failed_unload(service,monkeypatch):
    async def run():
        local=service.news_digest.local
        class Process:
            returncode=None
            terminated=False
            def terminate(self): self.terminated=True
            def kill(self): raise AssertionError('Graceful termination should suffice')
            async def wait(self): self.returncode=0
        process=Process();local.process=process
        async def handler(request): return httpx.Response(500)
        real=httpx.AsyncClient
        monkeypatch.setattr(httpx,'AsyncClient',lambda **kw: real(transport=httpx.MockTransport(handler)))
        with patch('eis_engine.local_summary.time',SimpleNamespace(monotonic=Mock(side_effect=[0,4]))):
            await local.stop_inference('test:small')
        assert process.terminated and not local.runtime
    asyncio.run(run())


def test_summary_and_embeddings_take_turns_and_conversation_preempts(service):
    from eis_engine.article_summary import ArticleSummary
    async def run():
        digest,k=service.news_digest,service.news.knowledge
        digest.local.installed={'test:small':100}
        digest.configure({'enabled':True,'engine':'local','local_model':'test:small','language':'en'})
        digest.device_state(DEVICE)
        async def start(): pass
        async def generate(*args): return ArticleSummary(summary='A complete English summary with verified context.')
        digest.local.start_runtime=start;digest.local.run=generate
        class Encoder:
            def encode(self,texts): return [[1.,0.]]*len(texts)
        k.embedder=Encoder();k.configure({'enabled':True});k.index_next()
        assert await k.embed_next()
        digest.budget.next_at=0
        assert not await k.embed_next()  # The pending summary gets the next lease.
        assert await digest.prepare_next()
        assert digest.last_worker=='summary'
        assert digest.status()['prepared']==1
        # A visible conversation takes precedence even after the budget rests.
        digest.budget.next_at=0
        with service.db:
            service.db.execute("UPDATE news_articles SET text=text || ' correction' WHERE id='story'")
            service.db.execute("INSERT INTO jobs(id,workspace_id,type,state,payload_json,idempotency_key,created_at,updated_at) VALUES('active',?,'chat.send','queued','{}','key','now','now')",(service.ws,))
        assert not await digest.prepare_next()
    asyncio.run(run())


def test_download_rate_uses_observed_deltas_and_no_eta_after_completion(service,monkeypatch):
    from contextlib import asynccontextmanager
    local=service.news_digest.local
    observed=[]
    class Response:
        def raise_for_status(self): pass
        async def aiter_lines(self):
            for event in [{'digest':'one','total':1000,'completed':100},
                          {'digest':'one','total':1000,'completed':300},
                          {'status':'success'}]:
                yield json.dumps(event)
                observed.append(dict(local.status()['download']))
    @asynccontextmanager
    async def stream(*args,**kwargs): yield Response()
    monkeypatch.setattr(httpx.AsyncClient,'stream',stream)
    local.models_path.mkdir(parents=True,exist_ok=True)
    local.installed={'test:small':1000}
    local.download={'phase':'downloading','model':'test:small','completed':0,'total':1000,'error':''}
    async def refresh(): return local.status()
    local.refresh=refresh
    with patch('eis_engine.local_summary.time',SimpleNamespace(monotonic=Mock(side_effect=[0,.1,1.1]))):
        asyncio.run(local.pull('test:small'))
    assert observed[0]['bytes_per_second'] is None
    assert observed[1]['bytes_per_second']==200
    assert observed[1]['seconds_left']==4
    assert local.status()['download']['phase']=='testing'
    assert local.status()['download']['seconds_left'] is None


def test_cold_cross_language_search_reports_warming_then_uses_completed_exact_query(service):
    import struct
    async def run():
        k=service.news.knowledge;k.index_next();k.configure({'enabled':True})
        class Warmup:
            calls=0
            async def aencode(self,texts,query=False):
                self.calls+=1
                await asyncio.sleep(.3)
                return [[1.,0.]]
        k.embedder=Warmup()
        with service.db: service.db.execute('UPDATE news_search_chunks SET vector=?,model=?',(struct.pack('2f',1.,0.),k.index_model))
        report=await k.search('خبر تقني',include_status=True)
        assert report['articles']==[] and report['search']['semantic']=='warming'
        await asyncio.gather(*list(k.cleanup_tasks))
        assert 'خبر تقني' in k.query_cache and 'different query' not in k.query_cache
        again=await k.search('خبر تقني',include_status=True)
        assert again['search']['semantic']=='ready' and again['articles'][0]['id']=='story'
        assert k.embedder.calls==1
    asyncio.run(run())


def test_shutdown_cancels_tracked_semantic_warmup_and_releases_lease(service):
    import struct
    async def run():
        k=service.news.knowledge;k.index_next();k.configure({'enabled':True})
        class Delayed:
            async def aencode(self,texts,query=False): await asyncio.sleep(100)
        k.embedder=Delayed()
        with service.db: service.db.execute('UPDATE news_search_chunks SET vector=?,model=?',(struct.pack('2f',1.,0.),k.index_model))
        report=await k.search('خبر تقني',include_status=True)
        assert report['search']['semantic']=='warming'
        assert k.cleanup_tasks and service.model_lock.locked()
        await asyncio.wait_for(k.close(),1)
        assert not k.cleanup_tasks and not k.lock.locked() and not service.model_lock.locked()
    asyncio.run(run())


def test_both_pending_queues_reuse_bounded_embedding_quantum_then_yield(service):
    from eis_engine.article_summary import ArticleSummary
    async def run():
        d,k=service.news_digest,service.news.knowledge
        with service.db:
            service.db.execute("UPDATE news_articles SET text=? WHERE id='story'",('Detailed public evidence. '*5000,))
        while k.index_next(): pass
        class Encoder:
            calls=0
            def encode(self,texts):
                self.calls+=1
                return [[1.,0.]]*len(texts)
        k.embedder=Encoder();k.configure({'enabled':True})
        d.local.installed={'test:small':100}
        d.configure({'enabled':True,'engine':'local','local_model':'test:small','language':'en'})
        d.device_state(DEVICE)
        async def start(): pass
        async def generate(*args): return ArticleSummary(summary='A grounded complete English summary with factual context.')
        d.local.start_runtime=start;d.local.run=generate
        assert await k.embed_next()
        d.budget.next_at=0
        assert k.has_pending() and d.has_pending()
        assert not await d.prepare_next()  # Other queue cannot force a switch after one batch.
        assert await k.embed_next()
        assert k.embedder.calls==2 and d.quantum_units==8
        # The chunk ceiling forces eventual yield even if all requests are fast.
        for _ in range(6):
            d.budget.next_at=0
            assert await k.embed_next()
        assert d.quantum_units==32
        d.budget.next_at=0
        assert not await k.embed_next()
        assert await d.prepare_next()
        assert d.last_worker=='summary' and d.quantum_units==1
        # Time also expires a quantum, independently of the item ceiling.
        assert not d.worker_allowed('embedding',True)
        d.quantum_started-=11
        assert d.worker_allowed('embedding',True)
        assert not d.worker_allowed('summary',True)
        # A user pause still interrupts between requests without finishing a quantum.
        d.processing_policy({'paused':True})
        d.budget.next_at=0
        assert not await k.embed_next() and not await d.prepare_next()
    asyncio.run(run())


def test_background_summary_reuses_warm_model_then_embedding_releases_it(service,monkeypatch):
    from agno import agent
    from agno.models import ollama
    from eis_engine.article_summary import ArticleSummary
    async def run():
        local=service.news_digest.local;local.runtime=True
        captures=[];requests=[]
        def model(**kwargs): captures.append(kwargs);return object()
        class FakeAgent:
            def __init__(self,**kwargs): pass
            async def arun(self,prompt): return SimpleNamespace(content=ArticleSummary(summary='A complete English summary with factual context.'))
        monkeypatch.setattr(ollama,'Ollama',model);monkeypatch.setattr(agent,'Agent',FakeAgent)
        async def checked(name): return name
        local.check_generation=checked;local.capacity=lambda name:{'fit':'fits'}
        def handler(request):
            requests.append(request.url.path)
            return httpx.Response(200,json={'models':[]} if request.url.path=='/api/ps' else {'done':True})
        real=httpx.AsyncClient
        monkeypatch.setattr(httpx,'AsyncClient',lambda **kw: real(transport=httpx.MockTransport(handler)))
        for _ in range(2):
            task=asyncio.create_task(local.run('test:small','Summarize',{'text':'Evidence'},ArticleSummary))
            service.news_digest.active_request=task
            await task
            service.news_digest.active_request=None
        assert [c['keep_alive'] for c in captures]==['30s','30s']
        assert not requests and local.generation_name=='test:small'
        assert not service.model_lock.locked()  # Foreground gets the lease after every article.
        class Encoder:
            async def aencode(self,texts,query=False):
                assert local.generation_name==''
                return [[1.,0.]]
        service.news.knowledge.embedder=Encoder()
        async with service.model_lock:
            assert await service.news.knowledge.encode(['query'])==[[1.,0.]]
        assert requests==['/api/generate','/api/ps']
        assert local.generation_used==0
    asyncio.run(run())


def test_warm_quantum_excludes_cold_first_request_and_caps_summaries(service):
    d=service.news_digest
    with patch('eis_engine.news_digest.time.monotonic',return_value=100) as clock:
        d.begin_worker('summary')
        clock.return_value=150  # Slow cold load and first generation.
        d.finish_worker('summary',1)
        assert d.quantum_started==150
        clock.return_value=159
        assert d.worker_allowed('summary',True)
        assert not d.worker_allowed('embedding',True)
        d.finish_worker('summary',1)
        assert not d.worker_allowed('summary',True)
        assert d.worker_allowed('embedding',True)


def test_pressure_and_idle_release_retained_generation(service):
    async def run():
        d,k=service.news_digest,service.news.knowledge
        released=[]
        async def stop(name): released.append(name)
        d.local.stop_inference=stop
        d.device_state(DEVICE)
        d.local.generation_name='test:small';d.local.generation_used=time.monotonic()-21
        await k.release_idle()
        assert released==['test:small'] and not d.local.generation_name
        d.local.generation_name='test:small';d.local.generation_used=time.monotonic()
        d.device_state({**DEVICE,'memory_pressure':'critical'})
        await k.release_idle()
        assert released==['test:small','test:small'] and not d.local.generation_name
    asyncio.run(run())
