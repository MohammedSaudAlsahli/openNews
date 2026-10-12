"""Workspace-owned agent presets used by the existing guarded conversation runtime."""
from .contracts import CustomAgentSave, Failure
from .storage import now, uid

AGENT_SCHEMA = """
CREATE TABLE custom_agents(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 name TEXT NOT NULL, instructions TEXT NOT NULL, profile_id TEXT NOT NULL REFERENCES provider_profiles(id),
 model_id TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX custom_agents_workspace ON custom_agents(workspace_id,updated_at);
"""

class CustomAgents:
    def __init__(self, service):
        self.service = service

    def listing(self):
        s = self.service
        return {"agents":s.store.rows("SELECT * FROM custom_agents WHERE workspace_id=? ORDER BY updated_at DESC,id",(s.ws,))}

    def save(self, payload):
        data = CustomAgentSave.model_validate(payload)
        s = self.service
        if data.id is not None:
            s.require("custom_agents",data.id)
        profile = s.profile(data.profile_id)
        s.validate_model(profile["id"],data.model_id)
        identifier = str(data.id) if data.id else uid()
        with s.db:
            if data.id:
                s.db.execute("UPDATE custom_agents SET name=?,instructions=?,profile_id=?,model_id=?,updated_at=? WHERE id=? AND workspace_id=?",(data.name,data.instructions,profile["id"],data.model_id,now(),identifier,s.ws))
            else:
                s.db.execute("INSERT INTO custom_agents VALUES(?,?,?,?,?,?,?,?)",(identifier,s.ws,data.name,data.instructions,profile["id"],data.model_id,now(),now()))
        return {"agent_id":identifier}

    def delete(self, identifier):
        s = self.service
        agent = s.require("custom_agents",identifier)
        with s.db:
            s.db.execute("DELETE FROM custom_agents WHERE id=? AND workspace_id=?",(agent["id"],s.ws))
        return {"deleted":True}

    def snapshot(self, identifier, profile_id, model_id):
        agent = self.service.require("custom_agents",identifier)
        if agent["profile_id"] != str(profile_id) or agent["model_id"] != model_id:
            raise Failure("VALIDATION_ERROR", "إعدادات الوكيل تغيرت؛ اختر الوكيل مجددًا قبل الإرسال.")
        return agent
