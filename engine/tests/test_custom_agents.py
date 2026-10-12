"""Custom agents execute through guarded editorial jobs; never call a live provider."""
import asyncio
import json
import stat

import pytest
from pydantic import ValidationError

from eis_engine.contracts import ChatReply, Failure
from eis_engine.service import Service
from eis_engine.storage import Store, encode, now, uid

class FakeModel:
    def __init__(self): self.calls = []
    async def run(self, profile, instructions, data, schema):
        self.calls.append((profile,instructions,data))
        return ChatReply(message="Custom response")

@pytest.fixture
def service(tmp_path):
    s = Service(Store(tmp_path),FakeModel())
    yield s
    s.store.close()

async def config(s):
    profile = await s.dispatch("providers.save",{"provider_key":"openai","model_id":"test-model"})
    with s.db:
        s.db.execute("INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)",(profile["profile_id"],s.ws,encode([{"id":"test-model","available":True}]),"fixture",now(),None,9999999999))
    return {"name":"محرر علمي","instructions":"Explain scientific uncertainty clearly.","profile_id":profile["profile_id"],"model_id":"test-model"}

def test_crud_persists_and_preserves_builtin_assignments(service,tmp_path):
    async def check():
        s=service
        data=await config(s)
        await s.dispatch("agents.assign",{"role":"writer","profile_id":data["profile_id"],"model_id":data["model_id"]})
        aid=(await s.dispatch("agents.save",data))["agent_id"]
        await s.dispatch("agents.save",dict(data,id=aid,name="Updated"))
        assert (await s.dispatch("agents.list",{}))["agents"][0]["name"] == "Updated"
        other=Store(tmp_path)
        assert other.one("SELECT instructions FROM custom_agents WHERE id=?",(aid,))["instructions"]==data["instructions"]
        other.close()
        await s.dispatch("agents.delete",{"agent_id":aid})
        assert (await s.dispatch("agents.list",{}))["agents"]==[]
        assert len(s.snapshot()["assignments"])==1
        with pytest.raises(Failure): await s.dispatch("agents.delete",{"agent_id":"writer"})
    asyncio.run(check())

def test_workspace_scope_and_validation(service):
    async def check():
        s=service
        data=await config(s)
        aid=(await s.dispatch("agents.save",data))["agent_id"]
        foreign=uid()
        with s.db:
            s.db.execute("INSERT INTO workspaces VALUES(?,?,?)",(foreign,"Other",now()))
            s.db.execute("UPDATE custom_agents SET workspace_id=? WHERE id=?",(foreign,aid))
        assert (await s.dispatch("agents.list",{}))["agents"]==[]
        for command,payload in [("agents.save",dict(data,id=aid)),("agents.delete",{"agent_id":aid})]:
            with pytest.raises(Failure): await s.dispatch(command,payload)
        with pytest.raises(ValidationError): await s.dispatch("agents.save",dict(data,name="  "))
        with pytest.raises(Failure): await s.dispatch("agents.save",dict(data,profile_id=uid()))
    asyncio.run(check())

def test_job_freezes_agent_route_and_instructions_after_edit_delete(service):
    async def check():
        s=service
        data=await config(s)
        aid=(await s.dispatch("agents.save",data))["agent_id"]
        cid=(await s.dispatch("chat.create",{}))["conversation_id"]
        payload={"agent_id":aid,"conversation_id":cid,"message":"Explain", "profile_id":data["profile_id"],"model_id":data["model_id"],"consent":True,"include_news":False,"idempotency_key":uid()}
        submitted=await s.dispatch("chat.send",payload)
        await s.dispatch("agents.save",dict(data,id=aid,instructions="New instruction"))
        await s.dispatch("agents.delete",{"agent_id":aid})
        await s.tasks[submitted["job_id"]]
        job=await s.dispatch("jobs.get",{"job_id":submitted["job_id"]})
        assert job["state"]=="completed"
        assert data["instructions"] in s.factory.calls[0][1]
        assert "New instruction" not in s.factory.calls[0][1]
        assert "Never invent news" in s.factory.calls[0][1]
        assert s.factory.calls[0][0]["id"]==data["profile_id"]
        assert (await s.dispatch("chat.send",payload))["job_id"]==submitted["job_id"]
    asyncio.run(check())

def test_route_mismatch_rejected_before_job_or_message(service):
    async def check():
        s=service
        data=await config(s)
        aid=(await s.dispatch("agents.save",data))["agent_id"]
        cid=(await s.dispatch("chat.create",{}))["conversation_id"]
        with pytest.raises(Failure,match="إعدادات الوكيل"):
            await s.dispatch("chat.send",{"agent_id":aid,"conversation_id":cid,"message":"Explain","profile_id":data["profile_id"],"model_id":"different","consent":True,"idempotency_key":uid()})
        assert s.store.rows("SELECT * FROM jobs")==[]
        assert s.store.rows("SELECT * FROM chat_messages")==[]
    asyncio.run(check())

def test_v3_upgrade_backed_up_and_existing_data_retained(tmp_path):
    store=Store(tmp_path)
    workspace=store.workspace
    store.db.executescript("DROP TABLE custom_agents; PRAGMA user_version=3;")
    store.close()
    upgraded=Store(tmp_path)
    assert upgraded.workspace==workspace
    assert upgraded.db.execute("PRAGMA user_version").fetchone()[0]==5
    assert upgraded.rows("SELECT * FROM custom_agents")==[]
    backup=tmp_path/"editorial-before-v4.sqlite"
    assert backup.exists() and stat.S_IMODE(backup.stat().st_mode)==0o600
    upgraded.close()
