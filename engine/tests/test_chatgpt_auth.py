import asyncio
import json
import stat
import time
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit,urlencode
import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from eis_engine import chatgpt_auth as auth
from eis_engine.contracts import Failure,ChatReply
from eis_engine.service import Service
from eis_engine.storage import Store

@pytest.fixture
def service(tmp_path):
    s=Service(Store(tmp_path))
    yield s
    s.store.close()

@pytest.fixture
def signing():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())); jwk.update(kid="test",use="sig",alg="RS256")
    return key,jwk


def install_transport(monkeypatch,signing,nonce,claims=None,token_changes=None,requests=None):
    key,jwk=signing
    def handle(request):
        if requests is not None: requests.append(request)
        if str(request.url)==auth.DISCOVERY:
            return httpx.Response(200,json={"issuer":auth.ISSUER,"authorization_endpoint":auth.AUTHORIZE,"token_endpoint":auth.TOKEN,"jwks_uri":auth.JWKS})
        if str(request.url)==auth.JWKS: return httpx.Response(200,json={"keys":[jwk]})
        if str(request.url)==auth.TOKEN:
            identity={"sub":"person-one","aud":"oaiapp_test","iss":auth.ISSUER,"iat":int(time.time()),"exp":int(time.time())+3600,"nonce":nonce,**(claims or {})}
            token=jwt.encode(identity,key,algorithm="RS256",headers={"kid":"test"})
            return httpx.Response(200,json={"id_token":token,"access_token":"access-secret","refresh_token":"refresh-secret","token_type":"Bearer","scope":auth.SCOPES,"expires_in":3600,**(token_changes or {})})
        if str(request.url)==auth.RESOURCE+"/models":
            assert request.headers["authorization"]=="Bearer access-secret"
            return httpx.Response(200,json={"models":[{"slug":"account-model","display_name":"Account model","visibility":"list"},{"slug":"hidden","visibility":"hide"}]})
        raise AssertionError(str(request.url))
    monkeypatch.setattr(auth,"client",lambda:httpx.AsyncClient(transport=httpx.MockTransport(handle),trust_env=False))

async def callback(s,start,**changes):
    attempt=s.chatgpt_auth.attempts[start["auth_id"]]
    params={"state":attempt.get("state",""),"code":"auth-code","client_id":"oaiapp_test",**changes}
    async with httpx.AsyncClient(trust_env=False) as client:
        return await client.get(attempt["redirect_uri"],params=params)

async def signin(s,monkeypatch,signing,**kwargs):
    start=await s.dispatch("providers.auth.start",{"provider_key":"openai"})
    attempt=s.chatgpt_auth.attempts[start["auth_id"]]
    install_transport(monkeypatch,signing,attempt["nonce"],**kwargs)
    response=await callback(s,start)
    return start,response,s.chatgpt_auth.status(start["auth_id"])


def test_real_loopback_protocol_private_storage_and_models(service,monkeypatch,signing):
    async def run():
        s=service; requests=[]
        start,response,status=await signin(s,monkeypatch,signing,requests=requests)
        query=parse_qs(urlsplit(start["authorization_url"]).query)
        assert query["client_id"]==["dynamic_agent_client"]
        assert query["code_challenge_method"]==["S256"] and query["code_challenge"]
        assert query["redirect_uri"][0].startswith("http://127.0.0.1:")
        assert response.status_code==200 and status["status"]=="complete"
        assert "secret" not in json.dumps(status) and "secret" not in response.text
        profile=s.profile(status["profile_id"])
        path=auth.credential_path(profile)
        assert stat.S_IMODE(path.stat().st_mode)==0o600
        assert auth.read_record(path)["client_id"]=="oaiapp_test"
        assert "secret" not in json.dumps(s.snapshot())
        catalog=await s.models(profile["id"],True)
        assert [m["id"] for m in catalog["models"]]==["account-model"]
        exchange=next(r for r in requests if str(r.url)==auth.TOKEN)
        form=parse_qs(exchange.content.decode())
        assert form["redirect_uri"]==query["redirect_uri"] and form["client_id"]==["oaiapp_test"]
        assert form["resource"]==[auth.RESOURCE]
        await s.chatgpt_auth.close()
    asyncio.run(run())

@pytest.mark.parametrize("claims,changes",[
    ({"nonce":"wrong"},{}),({"aud":"wrong-client"},{}),({"iss":"https://wrong.example"},{}),
    ({"exp":1},{}),({}, {"scope":"openid email"}),({}, {"token_type":"MAC"}),
    ({"sub":""},{}),({}, {"id_token":"not-a-jwt"}),
])
def test_rejects_invalid_identity_and_scope(service,monkeypatch,signing,claims,changes):
    async def run():
        _,response,status=await signin(service,monkeypatch,signing,claims=claims,token_changes=changes)
        assert status["status"]=="failed" and response.status_code==400
        assert service.store.rows("SELECT * FROM provider_profiles")==[]
        assert "secret" not in json.dumps(status)
        await service.chatgpt_auth.close()
    asyncio.run(run())

def test_bad_state_does_not_consume_attempt_and_cancel_closes_listener(service,monkeypatch,signing):
    async def run():
        start=await service.dispatch("providers.auth.start",{"provider_key":"openai"})
        result=await callback(service,start,state="wrong")
        assert result.status_code==400
        assert service.chatgpt_auth.status(start["auth_id"])["status"]=="waiting"
        await service.dispatch("providers.auth.cancel",{"auth_id":start["auth_id"]})
        assert service.chatgpt_auth.status(start["auth_id"])["status"]=="cancelled"
        assert not service.chatgpt_auth.attempts[start["auth_id"]]["server"].is_serving()
        await service.chatgpt_auth.close()
    asyncio.run(run())

def test_refresh_rotates_once_and_preserves_account(service,monkeypatch,signing):
    async def run():
        _,_,status=await signin(service,monkeypatch,signing)
        profile=service.profile(status["profile_id"]); path=auth.credential_path(profile)
        record=auth.read_record(path); record["expires_at"]=0; auth.write_record(path,record)
        requests=[]
        install_transport(monkeypatch,signing,"unused",token_changes={"access_token":"rotated-access","refresh_token":"rotated-refresh"},requests=requests)
        results=await asyncio.gather(auth.access_token(profile),auth.access_token(profile))
        assert results==["rotated-access"]*2
        exchanges=[r for r in requests if str(r.url)==auth.TOKEN]
        assert len(exchanges)==1 and parse_qs(exchanges[0].content.decode())["grant_type"]==["refresh_token"]
        assert auth.read_record(path)["refresh_token"]=="rotated-refresh"
        await service.chatgpt_auth.close()
    asyncio.run(run())

def test_reauthorization_uses_issued_client_and_rejects_different_identity(service,monkeypatch,signing):
    async def run():
        _,_,status=await signin(service,monkeypatch,signing)
        pid=status["profile_id"]
        start=await service.dispatch("providers.auth.start",{"provider_key":"openai","profile_id":pid})
        query=parse_qs(urlsplit(start["authorization_url"]).query)
        assert query["client_id"]==["oaiapp_test"] and "agent_name_hint" not in query
        attempt=service.chatgpt_auth.attempts[start["auth_id"]]
        install_transport(monkeypatch,signing,attempt["nonce"],claims={"sub":"another-person"})
        await callback(service,start)
        assert service.chatgpt_auth.status(start["auth_id"])["status"]=="failed"
        assert auth.read_record(auth.credential_path(service.profile(pid)))["subject"]=="person-one"
        await service.chatgpt_auth.close()
    asyncio.run(run())

def test_rejects_insecure_credential_file(service,monkeypatch,signing):
    async def run():
        _,_,status=await signin(service,monkeypatch,signing)
        profile=service.profile(status["profile_id"]); path=auth.credential_path(profile)
        path.chmod(0o644)
        with pytest.raises(Failure): await auth.access_token(profile)
        await service.chatgpt_auth.close()
    asyncio.run(run())

@pytest.mark.parametrize("terminal",["response.completed","response.failed","response.incomplete",None])
def test_agno_adapter_uses_required_stream_contract(monkeypatch,terminal):
    from agno.models.message import Message
    from openai.types.responses import Response
    async def run():
        response=Response.model_validate({"id":"resp_test","object":"response","created_at":1,"model":"account-model","status":"completed","output":[{"type":"message","id":"msg_test","role":"assistant","status":"completed","content":[{"type":"output_text","text":"hello","annotations":[]}]}],"parallel_tool_calls":False,"tool_choice":"auto","tools":[]})
        class Stream:
            closed=False
            def __aiter__(self): return self.events()
            async def events(self):
                if terminal: yield SimpleNamespace(type=terminal,response=response)
            async def close(self): self.closed=True
        stream=Stream(); calls=[]
        async def create(**kwargs): calls.append(kwargs); return stream
        model=auth.ChatGPTResponses(id="account-model",api_key="fake")
        monkeypatch.setattr(auth.ChatGPTResponses,"get_async_client",lambda self:SimpleNamespace(responses=SimpleNamespace(create=create)))
        if terminal=="response.completed":
            result=await model.ainvoke([Message(role="system",content="Rules"),Message(role="user",content="Hi")],Message(role="assistant"))
            assert result.content=="hello"
        else:
            with pytest.raises(Failure): await model.ainvoke([Message(role="user",content="Hi")],Message(role="assistant"))
        assert calls[0]["stream"] is True and calls[0]["store"] is False
        assert set(calls[0])=={"model","input","stream","store"}
        assert all(item["role"]!="system" for item in calls[0]["input"])
        assert stream.closed
    asyncio.run(run())

def test_factory_keeps_agno_schema_execution(monkeypatch):
    from openai.types.responses import Response
    from eis_engine.providers import ModelFactory
    async def run():
        calls=[]
        response=Response.model_validate({"id":"resp_test","object":"response","created_at":1,"model":"account-model","status":"completed","output":[{"type":"message","id":"msg_test","role":"assistant","status":"completed","content":[{"type":"output_text","text":'{"message":"A structured reply","article_ids":[],"drafts":[]}',"annotations":[]}]}],"parallel_tool_calls":False,"tool_choice":"auto","tools":[]})
        class Stream:
            def __aiter__(self): return self.events()
            async def events(self):
                yield SimpleNamespace(type="response.output_item.done",output_index=0,item=response.output[0])
                yield SimpleNamespace(type="response.completed",response=response.model_copy(update={"output":[]}))
            async def close(self): pass
        async def create(**kwargs): calls.append(kwargs); return Stream()
        async def token(profile): return "fake-access"
        monkeypatch.setattr(auth,"access_token",token)
        monkeypatch.setattr(auth.ChatGPTResponses,"get_async_client",lambda self:SimpleNamespace(responses=SimpleNamespace(create=create)))
        result=await ModelFactory().run({"provider_key":"openai-chatgpt","model_id":"account-model"},"Editorial rules",{"message":"Discuss"},ChatReply)
        assert result.message=="A structured reply"
        assert calls and calls[0]["store"] is False and calls[0]["stream"] is True
        assert "Editorial rules" in json.dumps(calls[0]["input"])
        # This route does not send text.format: the schema must reach the model
        # through Agno's system prompt, including nested draft definitions.
        system_input=json.dumps([m for m in calls[0]["input"] if m.get("role") in {"system","developer"}])
        assert "article_ids" in system_input and "ChatDraft" in system_input
        assert "youtube_long" in system_input and "drafts" in system_input
    asyncio.run(run())

def test_rejects_wrong_signing_key(monkeypatch,signing):
    async def run():
        key,_=signing
        stranger=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        install_transport(monkeypatch,signing,"nonce")
        forged=jwt.encode({"iss":auth.ISSUER,"aud":"oaiapp_test","sub":"person","iat":int(time.time()),"exp":int(time.time())+60,"nonce":"nonce"},stranger,algorithm="RS256",headers={"kid":"test"})
        async with auth.client() as http:
            with pytest.raises(jwt.InvalidSignatureError): await auth.validate_identity(http,forged,"oaiapp_test","nonce")
    asyncio.run(run())

def test_credentials_reject_symlink_without_touching_target(tmp_path):
    directory=tmp_path/".providers"; directory.mkdir(mode=0o700)
    target=tmp_path/"outside.json"; target.write_text('{"untouched":true}'); target.chmod(0o600)
    link=directory/"link.json"; link.symlink_to(target)
    with pytest.raises((Failure,OSError)): auth.read_record(link)
    with pytest.raises((Failure,OSError)): auth.write_record(link,{"access_token":"secret"})
    assert target.read_text()=='{"untouched":true}'

def test_expiry_and_engine_close_release_callback(service):
    async def run():
        first=await service.chatgpt_auth.start({"provider_key":"openai"})
        service.chatgpt_auth.expire(first["auth_id"])
        assert service.chatgpt_auth.status(first["auth_id"])["status"]=="failed"
        second=await service.chatgpt_auth.start({"provider_key":"openai"})
        await service.chatgpt_auth.close()
        assert service.chatgpt_auth.status(second["auth_id"])["status"]=="cancelled"
        assert all(not a["server"].is_serving() for a in service.chatgpt_auth.attempts.values())
    asyncio.run(run())

@pytest.mark.parametrize('terminal_output', ['empty', 'full'])
def test_stream_preserves_finalized_items_without_duplication(monkeypatch, terminal_output):
    from agno.models.message import Message
    from openai.types.responses import Response
    async def run():
        response=Response.model_validate({'id':'resp_test','object':'response','created_at':1,'model':'account-model','status':'completed','output':[{'type':'message','id':'msg_test','role':'assistant','status':'completed','content':[{'type':'output_text','text':'Connection OK','annotations':[]}]}],'parallel_tool_calls':False,'tool_choice':'auto','tools':[]})
        item=response.output[0]
        terminal=response if terminal_output=='full' else response.model_copy(update={'output':[]})
        class Stream:
            closed=False
            def __aiter__(self): return self.events()
            async def events(self):
                yield SimpleNamespace(type='response.output_text.delta',delta='Connection ')
                yield SimpleNamespace(type='response.output_item.done',output_index=0,item=item)
                yield SimpleNamespace(type='response.output_item.done',output_index=0,item=item)
                yield SimpleNamespace(type='response.completed',response=terminal)
            async def close(self): self.closed=True
        stream=Stream()
        async def create(**kwargs): return stream
        monkeypatch.setattr(auth.ChatGPTResponses,'get_async_client',lambda self:SimpleNamespace(responses=SimpleNamespace(create=create)))
        result=await auth.ChatGPTResponses(id='account-model',api_key='fake').ainvoke([Message(role='user',content='Test')],Message(role='assistant'))
        assert result.content=='Connection OK'
        assert stream.closed
    asyncio.run(run())

@pytest.mark.parametrize('terminal', [None, 'response.incomplete', 'response.failed'])
def test_finalized_text_is_not_success_without_completed_event(monkeypatch, terminal):
    from agno.models.message import Message
    async def run():
        class Stream:
            closed=False
            def __aiter__(self): return self.events()
            async def events(self):
                yield SimpleNamespace(type='response.output_item.done',output_index=0,item=SimpleNamespace(type='message'))
                if terminal: yield SimpleNamespace(type=terminal,response=SimpleNamespace(error=None))
            async def close(self): self.closed=True
        stream=Stream()
        async def create(**kwargs): return stream
        monkeypatch.setattr(auth.ChatGPTResponses,'get_async_client',lambda self:SimpleNamespace(responses=SimpleNamespace(create=create)))
        with pytest.raises(Failure) as caught:
            await auth.ChatGPTResponses(id='account-model',api_key='fake').ainvoke([Message(role='user',content='Test')],Message(role='assistant'))
        assert caught.value.code=='MODEL_RESPONSE_INCOMPLETE'
        assert stream.closed
    asyncio.run(run())

@pytest.mark.parametrize('code,status,expected', [
    ('subscription_sharing_usage_limit_exceeded',None,'RATE_LIMITED'),
    ('subscription_sharing_usage_unavailable',503,'PROVIDER_UNAVAILABLE'),
    ('subscription_sharing_user_not_eligible',403,'PERMISSION_DENIED'),
    ('subscription_sharing_unsupported_capability',400,'MODEL_REQUEST_REJECTED'),
    ('subscription_sharing_invalid_user',401,'AUTH_REQUIRED'),
    (None,503,'PROVIDER_UNAVAILABLE'),
])
def test_chatgpt_errors_explain_recovery_without_exposing_provider_body(code,status,expected):
    error=auth.response_failure({'code':code,'message':'secret prompt and Bearer token'},status)
    assert error.code==expected
    assert 'secret' not in error.message and 'Bearer' not in error.message


def test_factory_streams_chatgpt_text_before_validated_completion(monkeypatch):
    from openai.types.responses import Response
    from eis_engine.providers import ModelFactory
    async def run():
        deltas=[]
        response=Response.model_validate({"id":"resp_test","object":"response","created_at":1,"model":"account-model","status":"completed","output":[{"type":"message","id":"msg_test","role":"assistant","status":"completed","content":[{"type":"output_text","text":'{"message":"A structured reply","article_ids":[],"drafts":[]}',"annotations":[]}]}],"parallel_tool_calls":False,"tool_choice":"auto","tools":[]})
        class Stream:
            closed=False
            def __aiter__(self): return self.events()
            async def events(self):
                yield SimpleNamespace(type="response.output_text.delta",delta='{"message":"A structured')
                assert deltas == ['{"message":"A structured']
                yield SimpleNamespace(type="response.output_text.delta",delta=' reply","article_ids":[],"drafts":[]}')
                yield SimpleNamespace(type="response.completed",response=response)
            async def close(self): self.closed=True
        stream=Stream()
        async def create(**kwargs): return stream
        async def token(profile): return "fake-access"
        monkeypatch.setattr(auth,"access_token",token)
        monkeypatch.setattr(auth.ChatGPTResponses,"get_async_client",lambda self:SimpleNamespace(responses=SimpleNamespace(create=create)))
        result=await ModelFactory().run_stream({"provider_key":"openai-chatgpt","model_id":"account-model"},"Editorial rules",{"message":"Discuss"},ChatReply,deltas.append)
        assert result.message=="A structured reply" and len(deltas)==2 and stream.closed
    asyncio.run(run())


def test_chatgpt_agno_executes_tool_and_returns_result_to_model(monkeypatch):
    from openai.types.responses import Response
    from eis_engine.providers import ModelFactory
    async def run():
        calls, executed, turns = [], [], []
        async def search_saved_articles(query: str) -> str:
            """Search saved RSS articles by topic."""
            executed.append(query)
            return '{"articles":[],"scope":"RSS"}'
        class Stream:
            def __init__(self, response): self.response = response
            def __aiter__(self): return self.events()
            async def events(self):
                yield SimpleNamespace(type="response.completed", response=self.response)
            async def close(self): pass
        async def create(**kwargs):
            calls.append(kwargs)
            output = ([{"type":"function_call","id":"fc_test","call_id":"call_test","name":"search_saved_articles","arguments":"{\"query\":\"Anthropic\"}","status":"completed"}]
                if len(calls) == 1 else [{"type":"message","id":"msg_test","role":"assistant","status":"completed","content":[{"type":"output_text","text":'{"message":"No saved match","article_ids":[],"drafts":[]}',"annotations":[]}]}])
            return Stream(Response.model_validate({"id":"resp_test","object":"response","created_at":1,"model":"account-model","status":"completed","output":output,"parallel_tool_calls":False,"tool_choice":"auto","tools":[]}))
        async def token(profile): return "fake-access"
        monkeypatch.setattr(auth,"access_token",token)
        monkeypatch.setattr(auth.ChatGPTResponses,"get_async_client",lambda self:SimpleNamespace(responses=SimpleNamespace(create=create)))
        result = await ModelFactory().run({"provider_key":"openai-chatgpt","model_id":"account-model"},"Research",{},ChatReply,
            tools=[search_saved_articles], on_turn=lambda: turns.append(1))
        assert result.message == "No saved match"
        assert executed == ["Anthropic"] and len(turns) == 2
        assert calls[0]["tools"][0]["name"] == "search_saved_articles"
        assert any(item.get("type") == "function_call_output" and 'RSS' in item["output"] for item in calls[1]["input"])
    asyncio.run(run())


def test_public_reasoning_summary_stream_is_separate_from_text(monkeypatch):
    from agno.models.message import Message
    from openai.types.responses import Response
    async def run():
        response = Response.model_validate({'id':'r','object':'response','created_at':1,'model':'test','status':'completed','output':[{'type':'message','id':'m','role':'assistant','status':'completed','content':[{'type':'output_text','text':'answer','annotations':[]}]}],'parallel_tool_calls':False,'tool_choice':'auto','tools':[]})
        class Stream:
            def __aiter__(self): return self.events()
            async def events(self):
                yield SimpleNamespace(type='response.reasoning_summary_text.delta',delta='public summary')
                yield SimpleNamespace(type='response.output_text.delta',delta='answer')
                yield SimpleNamespace(type='response.completed',response=response)
            async def close(self): pass
        async def create(**kwargs):
            assert kwargs["reasoning"] == {"summary":"auto"}
            return Stream()
        monkeypatch.setattr(auth.ChatGPTResponses,'get_async_client',lambda self:SimpleNamespace(responses=SimpleNamespace(create=create)))
        summaries, text = [], []
        model = auth.ChatGPTResponses(id='test',api_key='fake',reasoning_summary='auto',on_reasoning_delta=summaries.append,on_text_delta=text.append)
        result = await model.ainvoke([Message(role='user',content='Test')],Message(role='assistant'))
        assert summaries == ['public summary'] and text == ['answer'] and result.content == 'answer'
    asyncio.run(run())
