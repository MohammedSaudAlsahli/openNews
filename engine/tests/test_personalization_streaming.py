import asyncio
import json
import sqlite3
import pytest
from pydantic import ValidationError
from eis_engine.contracts import ChatReply, Failure
from eis_engine.personalization import Preferences
from eis_engine.storage import Store, now, uid
from eis_engine.streaming import MessagePreview
from test_conversation import service, setup, FakeChatModel


def test_preferences_persist_isolate_scopes_and_reset(service):
    async def scenario():
        cid = (await setup(service))["conversation_id"]
        for scope,target,text in [("general","","عام"),("agent","writer","كاتب"),("conversation",cid,"محادثة")]:
            await service.dispatch("assistant.save",dict(scope=scope,target_id=target,settings={"style":text}))
        assert [x["settings"]["style"] for x in service.personalization.layers("writer",cid)] == ["عام","كاتب","محادثة"]
        result = await service.dispatch("assistant.get",dict(scope="conversation",target_id=cid))
        assert result["inherited"][0]["settings"]["style"] == "عام"
        await service.dispatch("assistant.reset",dict(scope="conversation",target_id=cid))
        assert service.personalization.read("conversation",cid).style == ""
        assert service.personalization.read("general").style == "عام"
        foreign = uid()
        with service.db:
            service.db.execute("INSERT INTO workspaces VALUES(?,?,?)",(foreign,"Other",now()))
            service.db.execute("INSERT INTO conversations VALUES(?,?,?,?,?)",(foreign,foreign,"Private",now(),now()))
        for command in ["assistant.get","assistant.reset","assistant.save"]:
            payload = dict(scope="conversation",target_id=foreign)
            if command.endswith("save"): payload["settings"] = {"role":"x"}
            with pytest.raises(Failure): await service.dispatch(command,payload)
        with pytest.raises(ValidationError): Preferences(instructions="x"*6001)
        with pytest.raises(ValidationError): Preferences(instructions="x"*6000,knowledge="x"*6000,examples="x"*6000)
        # A new service instance reads the same durable record.
        from eis_engine.service import Service
        assert Service(service.store,FakeChatModel()).personalization.read("general").style == "عام"
    asyncio.run(scenario())


def test_prompt_snapshot_survives_edit_and_retry(service):
    async def scenario():
        payload = await setup(service)
        await service.dispatch("assistant.save",dict(scope="agent",target_id="writer",settings={"developer_prompt":"original-rule"}))
        service.factory.release = asyncio.Event()
        submitted = await service.dispatch("chat.send",payload)
        await service.factory.started.wait()
        await service.dispatch("jobs.cancel",{"job_id":submitted["job_id"]})
        await service.dispatch("assistant.save",dict(scope="agent",target_id="writer",settings={"developer_prompt":"changed-rule"}))
        service.factory.release = None
        await service.dispatch("jobs.resume",{"job_id":submitted["job_id"],"consent":True})
        await service.tasks[submitted["job_id"]]
        assert "original-rule" in service.factory.calls[-1][1]
        assert "changed-rule" not in service.factory.calls[-1][1]
        assert (await service.dispatch("chat.send",payload))["job_id"] == submitted["job_id"]
    asyncio.run(scenario())


@pytest.mark.parametrize("escaped",[True,False])
def test_preview_decodes_every_character_boundary_without_json_or_reasoning(escaped):
    parser = MessagePreview()
    text = 'عنوان عربي 📝\nA "quoted" line \\ path'
    body = json.dumps({"article_ids":[],"message":text,"drafts":[{"message":"not the reply"}]},ensure_ascii=escaped)
    for char in body:
        value = parser.append(char)
        assert text.startswith(value)
        assert not any(0xD800 <= ord(c) <= 0xDFFF for c in value)
    assert parser.message == text
    assert MessagePreview().append('{"drafts":[{"message":"hidden"}]}') == ""


@pytest.mark.parametrize("outcome",["success","cancel","invalid"])
def test_progress_precedes_completion_and_never_saves_unvalidated_reply(service,outcome):
    async def scenario():
        released,started = asyncio.Event(),asyncio.Event()
        class StreamModel(FakeChatModel):
            async def run_stream(self,profile,instructions,payload,schema,on_delta):
                on_delta('{"message":"نص جارٍ')
                started.set()
                await released.wait()
                if outcome == "invalid": raise Failure("MODEL_RESPONSE_INVALID","invalid")
                on_delta(' مكتمل","article_ids":[],"drafts":[]}')
                return ChatReply(message="نص جارٍ مكتمل")
        service.factory = StreamModel()
        payload = await setup(service)
        job = (await service.dispatch("chat.send",payload))["job_id"]
        task = service.tasks[job]
        await started.wait()
        progress = await service.dispatch("chat.progress",{"job_id":job})
        assert progress["state"] == "running" and progress["message"] == "نص جارٍ"
        assert progress["stage"] == "generating"
        assert service.store.rows("SELECT id FROM chat_messages WHERE role='assistant'") == []
        if outcome == "cancel": await service.dispatch("jobs.cancel",{"job_id":job})
        else: released.set()
        await task
        assert (await service.dispatch("chat.progress",{"job_id":job}))["message"] == ""
        saved = service.store.rows("SELECT content FROM chat_messages WHERE role='assistant'")
        assert len(saved) == (1 if outcome == "success" else 0)
        assert job not in service.conversations.previews
    asyncio.run(scenario())


def test_v5_migration_backs_up_without_losing_content(tmp_path):
    old = Store(tmp_path)
    ws = old.workspace
    with old.db:
        old.db.execute("DROP TABLE assistant_preferences")
        old.db.execute("PRAGMA user_version=5")
    old.close()
    new = Store(tmp_path)
    assert new.workspace == ws
    assert new.db.execute("PRAGMA user_version").fetchone()[0] == 6
    with sqlite3.connect(tmp_path/"editorial-before-v6.sqlite") as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 5
        assert backup.execute("SELECT id FROM workspaces").fetchone()[0] == ws
    new.close()


def test_agno_generic_provider_really_streams_structured_message(monkeypatch):
    from types import SimpleNamespace
    from agno.models.openai import OpenAIChat
    from openai.types.chat import ChatCompletionChunk
    from eis_engine.providers import ModelFactory
    async def scenario():
        received=[]
        class Stream:
            def __aiter__(self): return self.events()
            async def events(self):
                chunks=['{"message":"Hello', ' world","article_ids":[],"drafts":[]}']
                for i,content in enumerate(chunks):
                    if i: assert received == [chunks[0]]
                    yield ChatCompletionChunk(id="test",created=1,model="test",object="chat.completion.chunk",choices=[{"index":0,"delta":{"content":content},"finish_reason":None}])
                yield ChatCompletionChunk(id="test",created=1,model="test",object="chat.completion.chunk",choices=[{"index":0,"delta":{},"finish_reason":"stop"}])
        async def create(**kwargs):
            assert kwargs["stream"] is True
            return Stream()
        monkeypatch.setattr(OpenAIChat,"get_async_client",lambda self:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
        factory=ModelFactory()
        monkeypatch.setattr(factory,"create",lambda profile:OpenAIChat(id="test",api_key="fake"))
        result=await factory.run_stream({"provider_key":"openai","model_id":"test"},"Return the schema",{"request":"hello"},ChatReply,received.append)
        assert result.message == "Hello world" and len(received)==2
    asyncio.run(scenario())


@pytest.mark.parametrize("status,expected",[(401,"AUTH_REQUIRED"),(429,"RATE_LIMITED"),(503,"PROVIDER_UNAVAILABLE")])
def test_stream_errors_keep_connection_classification(monkeypatch,status,expected):
    from agno.models.openai import OpenAIChat
    from agno.exceptions import ModelProviderError
    from eis_engine.providers import ModelFactory
    async def scenario():
        model=OpenAIChat(id="test",api_key="fake")
        async def broken(*args,**kwargs):
            raise ModelProviderError(message="private provider details",status_code=status)
            yield
        model.ainvoke_stream=broken
        factory=ModelFactory()
        monkeypatch.setattr(factory,"create",lambda profile:model)
        with pytest.raises(Failure) as error:
            await factory.run_stream({"provider_key":"openai","model_id":"test"},"instructions",{},ChatReply,lambda _:None)
        assert error.value.code==expected
        assert "private provider details" not in str(error.value)
    asyncio.run(scenario())
