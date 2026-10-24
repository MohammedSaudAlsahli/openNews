import asyncio
import pytest
from eis_engine.contracts import Failure
from eis_engine.local_summary import model_name, LocalSummaryModels
from test_news_digest import service
from eis_engine.article_summary import ArticleSummary

@pytest.mark.parametrize('name',['http://host/model','../model','model;rm','x:cloud','x\nfoo','foo/bar/baz',''])
def test_reject_nonlocal_names(name):
    with pytest.raises(Failure): model_name(name)

def test_custom_registry_namespace():
    assert model_name('publisher/small-model:q4')=='publisher/small-model:q4'
    assert model_name('gemma3')=='gemma3:latest'

def test_local_queue_not_limited_by_cloud_budget_and_invalidates_cache(service):
    async def scenario():
        local = service.news_digest.local
        local.installed={'custom:small':100,'other:small':200}
        async def refresh(): return local.status()
        local.refresh=refresh
        local.start_runtime=refresh
        calls=[]
        async def run(name,instructions,data,schema):
            calls.append(name)
            return ArticleSummary(summary='ملخص المقالة.')
        local.run=run
        service.news_digest.configure({'enabled':True,'engine':'local','local_model':'custom:small','daily_limit':1})
        service.news_digest.device_state({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False})
        service.news_digest.cache.reserve(1)
        assert await service.news_digest.prepare_next()
        assert calls==['custom:small']
        assert service.news_digest.status()['phase']=='resting'
        assert not await service.news_digest.prepare_next()
        assert service.news_digest.preview('story')['summary']=='ملخص المقالة.'
        assert service.news_digest.article_states(['story'])['states']['story']=='ready'
        service.news_digest.configure({'enabled':True,'local_model':'other:small'})
        assert service.news_digest.preview('story') is None
        assert service.news_digest.article_states(['story'])['states']['story']=='pending'
        service.news_digest.budget.next_at = 0
        assert await service.news_digest.prepare_next()
        assert calls==['custom:small','other:small']
        assert service.news_digest.cache.used()==1
        local.installed={}
        service.news_digest.configure({'enabled':False})
        assert not service.news_digest.settings()['enabled']
    asyncio.run(scenario())

def test_local_selection_can_be_pending_without_model(service):
    service.news_digest.configure({'enabled':False,'engine':'local'})
    assert service.news_digest.assignment() is None
    with pytest.raises(Failure): service.news_digest.configure({'enabled':True})

def test_download_rechecks_capacity_before_any_install(service):
    async def run():
        local=service.news_digest.local
        async def inspect(name): return {'can_download':False,'fit':'disk'}
        local.inspect=inspect
        before=service.news_digest.settings()
        await local.begin('custom:small')
        await local.task
        assert local.download['phase']=='failed'
        assert 'المساحة' in local.download['error']
        assert service.news_digest.settings()==before
    asyncio.run(run())

def test_runtime_disconnection_clears_ready_models(service,monkeypatch):
    import httpx
    async def get(*args,**kwargs): raise httpx.ConnectError('offline')
    monkeypatch.setattr(httpx.AsyncClient,'get',get)
    local=service.news_digest.local
    local.installed={'custom:small':100}
    assert asyncio.run(local.refresh())['runtime'] is False
    assert local.installed=={}

def test_arabic_and_english_manual_summary_use_selected_local_model(service):
    from eis_engine.article_summary import summarize
    async def run():
        local=service.news_digest.local
        local.installed={'custom:small':100}
        service.news_digest.configure({'enabled':False,'engine':'local','local_model':'custom:small'})
        prompts=[]
        async def generate(name,instructions,data,schema):
            prompts.append(instructions)
            return ArticleSummary(summary='ملخص عربي للخبر يوضح التفاصيل الأساسية.' if 'Arabic.' in instructions else 'A concise English summary of the story.')
        local.run=generate
        for language in ['ar','en']:
            result=await summarize(service,{'consent':True,'article_id':'story','language':language})
            assert result['model']=='custom:small'
        assert 'Arabic.' in prompts[0] and 'English.' in prompts[1]
        assert service.factory.calls==[]
    asyncio.run(run())

def test_agno_adapter_is_local_bounded_and_returns_validated_output(service,monkeypatch):
    from agno import agent
    from agno.models import ollama
    from types import SimpleNamespace
    captured={}
    def model(**kwargs): captured.update(kwargs); return object()
    class FakeAgent:
        def __init__(self,**kwargs): captured['agent']=kwargs
        async def arun(self,prompt): return SimpleNamespace(content='{"summary":"Verified"}')
    monkeypatch.setattr(ollama,'Ollama',model)
    monkeypatch.setattr(agent,'Agent',FakeAgent)
    async def check(name): return name
    local=service.news_digest.local
    local.check_generation=check
    local.runtime=True
    local.capabilities['custom:small']=['completion','thinking']
    result=asyncio.run(local.run('custom:small','Arabic summary',{'text':'Public article'},ArticleSummary))
    assert result.summary=='Verified'
    assert captured['host']=='http://127.0.0.1:11435'
    assert captured['api_key'] is None
    assert captured['options']['num_ctx']==8192
    assert captured['request_params']=={'think':False}
    assert not service.model_lock.locked()


def test_download_success_requires_installed_model(service,monkeypatch):
    import httpx
    from contextlib import asynccontextmanager
    class Response:
        def raise_for_status(self): pass
        async def aiter_lines(self):
            yield '{"digest":"weights","total":100,"completed":50}'
            yield '{"status":"success"}'
    @asynccontextmanager
    async def stream(*args,**kwargs): yield Response()
    monkeypatch.setattr(httpx.AsyncClient,'stream',stream)
    local=service.news_digest.local
    async def refresh(): return local.status()
    local.refresh=refresh
    local.models_path.mkdir(parents=True,exist_ok=True)
    local.download={'phase':'downloading','model':'custom:small','total':100,'completed':0,'error':''}
    asyncio.run(local.pull('custom:small'))
    assert local.download['phase']=='failed'
    assert local.download['completed']==50
    local.installed={'custom:small':100}
    asyncio.run(local.pull('custom:small'))
    assert local.download['phase']=='testing'
    assert local.download['completed']==100


def test_cancel_download_does_not_stop_shared_runtime(service):
    async def run():
        local=service.news_digest.local
        local.download['phase']='downloading'
        async def worker():
            try: await asyncio.Event().wait()
            except asyncio.CancelledError:
                local.download['phase']='cancelled'
                raise
        local.task=asyncio.create_task(worker())
        await asyncio.sleep(0)
        result=await local.cancel()
        assert result['download']['phase']=='cancelled'
        assert local.task.cancelled()
    asyncio.run(run())

@pytest.mark.parametrize('fails',[True,False])
def test_activation_requires_successful_real_schema_warmup(service,fails):
    async def scenario():
        local=service.news_digest.local
        local.installed={'old:small':100,'new:small':100}
        service.news_digest.configure({'engine':'local','local_model':'old:small','enabled':True})
        async def inspect(name): return {'can_download':True}
        async def start(): pass
        async def check(name): return name
        async def warmup(*args):
            assert service.news_digest.settings()['local_model']=='old:small'
            if fails: raise ValueError('load failed')
            return ArticleSummary(summary='Library hours.')
        local.inspect=inspect; local.start_runtime=start;local.check_generation=check;local.run=warmup
        local.executable=lambda:'managed'
        await local.begin('new:small','en');await local.task
        assert local.download['phase']==('failed' if fails else 'ready')
        assert service.news_digest.settings()['local_model']==('old:small' if fails else 'new:small')
    asyncio.run(scenario())

def test_downloaded_models_survive_stopped_runtime(service,monkeypatch):
    import httpx,json
    local=service.news_digest.local
    digest='a'*64
    blob=local.models_path/'blobs'/('sha256-'+digest)
    blob.parent.mkdir(parents=True);blob.write_bytes(b'model')
    manifest=local.models_path/'manifests/registry.ollama.ai/library/example/small'
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'layers':[{'digest':'sha256:'+digest,'size':5}]}))
    async def offline(*args,**kwargs): raise httpx.ConnectError('stopped')
    monkeypatch.setattr(httpx.AsyncClient,'get',offline)
    result=asyncio.run(local.refresh())
    assert result['runtime'] is False
    assert result['installed']==[{'id':'example:small','size':5}]
    blob.write_bytes(b'incomplete')
    assert asyncio.run(local.refresh())['installed']==[]

def test_shared_inventory_keeps_both_capabilities_and_unknown_models(service, monkeypatch):
    import httpx
    local = service.news_digest.local
    local.installed = {'search:small': 100, 'writer:small': 200, 'offline:small': 300, 'remote:small': 400}
    local.executable = lambda: 'managed'
    async def start(): pass
    local.start_runtime = start
    async def post(self, url, **kwargs):
        name = kwargs['json']['model']
        if name == 'offline:small': raise httpx.ConnectError('unavailable')
        info = {'capabilities': ['embedding'] if name == 'search:small' else ['completion']}
        if name == 'remote:small': info['remote_host'] = 'cloud'
        return httpx.Response(200, json=info, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    rows = asyncio.run(local.available(''))['installed']
    assert [row['id'] for row in rows] == ['search:small', 'writer:small', 'offline:small']
    assert rows[2]['capabilities'] is None
    assert local.capabilities['search:small'] == ['embedding']
    assert [row['id'] for row in asyncio.run(local.available('embedding'))['installed']] == ['search:small']
