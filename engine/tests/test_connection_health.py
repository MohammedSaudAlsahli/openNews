import asyncio
import json
import time
import httpx
import pytest
from eis_engine import chatgpt_auth as auth
from eis_engine.contracts import Failure, GeneratedDraft
from eis_engine.service import Service
from eis_engine.storage import Store
from test_chatgpt_auth import signing, signin

@pytest.fixture
def service(tmp_path):
    s = Service(Store(tmp_path))
    yield s
    s.store.close()

def test_account_status_disconnect_reconnect_and_restart(service, monkeypatch, signing):
    async def run():
        s = service
        _, page, result = await signin(s, monkeypatch, signing)
        pid = result['profile_id']; profile = s.profile(pid)
        assert page.headers['content-type'].startswith('text/html')
        assert 'Authorization successful' in page.text and 'access-secret' not in page.text
        assert s.connections.status(profile)['state'] == 'connected'
        old = s.connections.generation(pid)
        await s.connections.disconnect(pid)
        record = auth.read_record(auth.credential_path(profile))
        assert set(record) == {'issuer','subject','client_id','ext_agent_host_id'}
        s.connections.set(pid, 'connected', old)
        assert s.connections.status(profile)['state'] == 'disconnected'
        with pytest.raises(Failure): await s.models(pid, True)
        with pytest.raises(Failure): await s.model(profile, '', {}, GeneratedDraft)
        start = await s.chatgpt_auth.start({'provider_key':'openai', 'profile_id':pid, 'language':'ar'})
        assert s.chatgpt_auth.attempts[start['auth_id']]['existing']['client_id'] == record['client_id']
        await s.connections.disconnect(pid)
        assert s.chatgpt_auth.status(start['auth_id'])['status'] == 'cancelled'
        await s.chatgpt_auth.close()
        reopened = Service(Store(s.store.path.parent))
        assert reopened.connections.status(reopened.profile(pid))['state'] == 'disconnected'
        reopened.store.close()
    asyncio.run(run())

@pytest.mark.parametrize('status,body,expected', [
    (401,{},'needs_login'), (400,{'error':'invalid_grant'},'needs_login'),
    (503,{},'service_error'), (429,{},'limited'), (403,{},'restricted'),
])
def test_refresh_failures_preserve_credentials_and_classify(service, monkeypatch, signing, status, body, expected):
    async def run():
        _, _, result = await signin(service, monkeypatch, signing)
        p = service.profile(result['profile_id']); path = auth.credential_path(p)
        record = auth.read_record(path); record['expires_at'] = 0; auth.write_record(path, record)
        monkeypatch.setattr(auth, 'client', lambda: httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(status,json=body))))
        current = await service.connections.check(p['id'])
        assert current['state'] == expected and current['last_success_at']
        assert auth.read_record(path) == record
        await service.chatgpt_auth.close()
    asyncio.run(run())

def test_network_loss_and_recovery_does_not_sign_out(service, monkeypatch, signing):
    async def run():
        _, _, result = await signin(service, monkeypatch, signing)
        p = service.profile(result['profile_id']); path = auth.credential_path(p)
        record = auth.read_record(path)
        good_client = auth.client
        def offline(r): raise httpx.ConnectError('private details must not escape', request=r)
        monkeypatch.setattr(auth, 'client', lambda:httpx.AsyncClient(transport=httpx.MockTransport(offline)))
        assert (await service.connections.check(p['id']))['state'] == 'network_error'
        assert auth.read_record(path) == record
        assert 'private details' not in json.dumps(service.snapshot())
        monkeypatch.setattr(auth, 'client', good_client)
        assert (await service.connections.check(p['id']))['state'] == 'connected'
        await service.chatgpt_auth.close()
    asyncio.run(run())

def test_public_catalog_never_proves_api_key_and_disconnect_blocks_stale_result(service, monkeypatch):
    async def run():
        pid = (await service.dispatch('providers.save', {'provider_key':'openai','model_id':''}))['profile_id']
        profile = service.profile(pid)
        auth.write_record(auth.credential_path(profile), {'api_key':'test-only'})
        async def discover(p): return {'models':[{'id':'test','name':'Test'}]}
        monkeypatch.setattr('eis_engine.model_catalog.discover', discover)
        assert (await service.connections.check(pid))['state'] == 'configured'
        service.connections.set(pid, 'connected')
        epoch = service.store.one('SELECT checked_epoch FROM provider_connection_health WHERE profile_id=?',(pid,))['checked_epoch']
        await service.connections.check(pid)
        assert service.store.one('SELECT checked_epoch FROM provider_connection_health WHERE profile_id=?',(pid,))['checked_epoch'] == epoch
        started, finish = asyncio.Event(), asyncio.Event()
        async def slow(p):
            started.set(); await finish.wait(); return {'models':[{'id':'test'}]}
        monkeypatch.setattr('eis_engine.model_catalog.discover',slow)
        task = asyncio.create_task(service.connections.check(pid))
        await started.wait(); await service.connections.disconnect(pid); finish.set()
        with pytest.raises(Failure): await task
        assert service.connections.status(profile)['state'] == 'disconnected'
        assert not service.store.one('SELECT * FROM model_catalogs WHERE profile_id=?',(pid,))
        assert auth.read_record(auth.credential_path(profile)) == {}
    asyncio.run(run())

def test_missing_changed_credentials_and_stale_verification(service):
    async def run():
        pid = (await service.dispatch('providers.save', {'provider_key':'openai','model_id':''}))['profile_id']
        p = service.profile(pid)
        assert service.connections.status(p)['state'] == 'needs_login'
        path = auth.credential_path(p); auth.write_record(path,{'api_key':'test'})
        service.connections.set(pid,'connected')
        with service.db: service.db.execute('UPDATE provider_connection_health SET checked_epoch=? WHERE profile_id=?',(time.time()-1000,pid))
        # Mark file older than check to isolate staleness from external credential edits.
        import os
        os.utime(path,(time.time()-2000,time.time()-2000))
        assert service.connections.status(p)['state'] == 'unverified'
        service.connections.set(pid,'connected')
        auth.write_record(path,{'api_key':'changed'})
        assert service.connections.status(p)['state'] == 'configured'
        path.unlink()
        assert service.connections.status(p)['state'] == 'needs_login'
    asyncio.run(run())

def test_callback_pages_arabic_failure_and_no_reflected_data():
    from eis_engine.auth_page import callback_page
    page = callback_page(True,'ar').decode()
    assert 'dir="rtl"' in page and 'تم تسجيل الدخول بنجاح' in page
    assert 'Authorization successful' not in callback_page(False).decode()

def test_delete_connection_hides_it_revokes_credentials_and_preserves_other_profiles(service):
    async def run():
        s = service
        saved = await s.dispatch("providers.save", {"provider_key":"ollama", "model_id":"", "config":{"host":"http://localhost:11434"}})
        other = await s.dispatch("providers.save", {"provider_key":"ollama", "model_id":"", "config":{"host":"http://localhost:11434"}})
        pid = saved["profile_id"]
        profile = s.profile(pid)
        auth.write_record(auth.credential_path(profile), {"api_key":"test-only-secret"})
        with s.db:
            s.db.execute("INSERT INTO agent_assignments VALUES(?,?,?,?)", (s.ws,"writer",pid,"test-model"))
        assert await s.dispatch("providers.delete", {"profile_id":pid}) == {"deleted":True}
        assert auth.read_record(auth.credential_path(profile)) == {}
        assert [p['id'] for p in s.snapshot()['profiles']] == [other['profile_id']]
        assert not s.snapshot()['assignments']
        with pytest.raises(Failure): s.profile(pid)
        s.connections.set(pid, 'connected', 0)
        assert s.connections.status(profile)['state'] == 'disconnected'
        reopened = Service(Store(s.store.path.parent))
        assert [p['id'] for p in reopened.snapshot()['profiles']] == [other['profile_id']]
        reopened.store.close()
    asyncio.run(run())
