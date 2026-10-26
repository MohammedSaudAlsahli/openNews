import asyncio
import json
import stat
import time
from urllib.parse import parse_qs, urlsplit
import httpx
import pytest
from eis_engine import google_auth as auth
from eis_engine.chatgpt_auth import credential_path, read_record, write_record
from eis_engine.contracts import Failure
from eis_engine.service import Service
from eis_engine.storage import Store

REG = {'client_id':'123-test.apps.googleusercontent.com','client_secret':'client-secret'}
CONFIG = {'project_id':'opennews-test','location':'us-central1'}

@pytest.fixture
def service(tmp_path):
    s=Service(Store(tmp_path)); yield s; s.store.close()

async def start(s):
    return await s.dispatch('providers.auth.start',dict(provider_key='google-oauth',registration=REG,config=CONFIG))

async def callback(s,result,**params):
    attempt=s.google_auth.attempts[result['auth_id']]
    async with httpx.AsyncClient(trust_env=False) as client:
        return await client.get(attempt['redirect_uri'],params={'state':attempt.get('state',''),'code':'code',**params})


def transport(monkeypatch, invalid=False):
    requests=[]
    def handle(request):
        requests.append(request)
        assert str(request.url)==auth.TOKEN
        return httpx.Response(200,json={'access_token':'access-secret','refresh_token':'refresh-secret','expires_in':3600,'token_type':'Bearer','scope':'wrong' if invalid else auth.SCOPE})
    monkeypatch.setattr(auth,'client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    return requests


def test_google_pkce_private_storage_refresh_and_disconnect(service,monkeypatch):
    async def run():
        requests=transport(monkeypatch)
        result=await start(service)
        params=parse_qs(urlsplit(result['authorization_url']).query)
        assert params['code_challenge_method']==['S256']
        assert 'client_secret' not in params
        assert params['scope']==[auth.SCOPE]
        response=await callback(service,result)
        assert response.status_code==200
        status=await service.dispatch('providers.auth.status',{'auth_id':result['auth_id']})
        assert status['status']=='complete'
        profile=service.profile(status['profile_id']); path=credential_path(profile)
        assert stat.S_IMODE(path.stat().st_mode)==0o600
        assert 'secret' not in json.dumps(service.snapshot())
        assert 'secret' not in response.text
        assert service.connections.status(profile)['state']=='configured'
        record=read_record(path); record['expires_at']=0; write_record(path,record)
        assert await auth.access_token(profile)=='access-secret'
        assert parse_qs(requests[-1].content.decode())['grant_type']==['refresh_token']
        await service.connections.disconnect(profile['id'])
        assert 'refresh_token' not in read_record(path)
        again=await service.dispatch('providers.auth.start',{'provider_key':'google-oauth','profile_id':profile['id']})
        await service.dispatch('providers.auth.cancel',{'auth_id':again['auth_id']})
        assert service.google_auth.status(again['auth_id'])['status']=='cancelled'
        await service.google_auth.close()
    asyncio.run(run())

@pytest.mark.parametrize('kind',['state','scope','cancel','denied'])
def test_invalid_callbacks_never_save_accounts(service,monkeypatch,kind):
    async def run():
        requests=transport(monkeypatch,invalid=kind=='scope')
        result=await start(service)
        if kind=='cancel':
            service.google_auth.cancel(result['auth_id'])
            assert not service.google_auth.attempts[result['auth_id']].get('registration')
        else:
            response=await callback(service,result,**({'state':'wrong'} if kind=='state' else {'error':'access_denied'} if kind=='denied' else {}))
            assert response.status_code==400
            if kind in {'state','denied'}: assert requests==[]
        assert not service.snapshot()['profiles']
        await service.google_auth.close()
    asyncio.run(run())


def test_missing_registration_is_actionable(service):
    async def run():
        with pytest.raises(Failure) as e:
            await service.dispatch('providers.auth.start',{'provider_key':'google-oauth'})
        assert e.value.code=='VALIDATION_ERROR'
        assert not service.google_auth.attempts
    asyncio.run(run())


def test_google_generation_uses_agno_vertex_adapter(service, monkeypatch):
    from types import SimpleNamespace
    from pydantic import BaseModel
    from eis_engine.providers import ModelFactory
    import agno.agent
    class Answer(BaseModel):
        text: str
    seen = {}
    class Agent:
        def __init__(self, **kwargs): seen.update(kwargs)
        async def arun(self, *args, **kwargs): return SimpleNamespace(content=Answer(text='ok'))
    monkeypatch.setattr(agno.agent, 'Agent', Agent)
    async def run():
        transport(monkeypatch)
        result = await start(service)
        await callback(service, result)
        profile = service.profile(service.google_auth.status(result['auth_id'])['profile_id'])
        profile['model_id'] = 'gemini-test'
        answer = await ModelFactory().run(profile, 'test', {}, Answer)
        assert answer.text == 'ok'
        model = seen['model']
        assert model.__class__.__module__ == 'agno.models.google.gemini'
        assert model.vertexai is True
        assert model.project_id == CONFIG['project_id']
        assert model.credentials.token == 'access-secret'
        assert seen['telemetry'] is False
        await service.google_auth.close()
    asyncio.run(run())


def test_refresh_without_new_refresh_token_preserves_session():
    record = auth.tokens_record({'access_token':'new','expires_in':3600,'token_type':'Bearer'},
                               {'refresh_token':'original','scope':auth.SCOPE})
    assert record['refresh_token'] == 'original'
