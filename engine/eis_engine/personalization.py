"""Locally saved, workspace-scoped instructions frozen with each submitted job."""
import json
from typing import Literal
from pydantic import Field, model_validator
from .contracts import StrictModel, Failure
from .storage import encode, now
from .assistant_defaults import DEFAULTS

SCHEMA = """
CREATE TABLE assistant_preferences(workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 scope TEXT NOT NULL, target_id TEXT NOT NULL, settings_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(workspace_id,scope,target_id));
"""

class Preferences(StrictModel):
    role: str = Field(default="", max_length=3000)
    instructions: str = Field(default="", max_length=6000)
    style: str = Field(default="", max_length=3000)
    knowledge: str = Field(default="", max_length=6000)
    examples: str = Field(default="", max_length=6000)
    output: str = Field(default="", max_length=3000)
    system_prompt: str = Field(default="", max_length=6000)
    developer_prompt: str = Field(default="", max_length=6000)

    @model_validator(mode="after")
    def bounded(self):
        if sum(len(x) for x in self.model_dump().values()) > 16000:
            raise ValueError("Instructions exceed 16000 characters")
        return self

class Target(StrictModel):
    scope: Literal["general", "agent", "conversation"]
    target_id: str = Field(default="", max_length=100)

class Save(Target):
    settings: Preferences

class Personalization:
    def __init__(self, service):
        self.service = service

    def validate(self, target):
        if target.scope == "general":
            if target.target_id:
                raise Failure("VALIDATION_ERROR", "تعليمات عامة غير صالحة.")
        elif target.scope == "conversation":
            self.service.require("conversations", target.target_id)
        elif target.target_id not in {"writer", "analyst"}:
            self.service.require("custom_agents", target.target_id)

    def read(self, scope, identifier=""):
        row = self.service.store.one("SELECT settings_json FROM assistant_preferences WHERE workspace_id=? AND scope=? AND target_id=?",
            (self.service.ws, scope, identifier))
        values = json.loads(row["settings_json"]) if row else {}
        version = values.pop("_defaults_version", 0)
        if scope == "general":
            # Older empty fields were additional preferences, not deliberate removals.
            overrides = values if version else {key:value for key,value in values.items() if value}
            values = {**DEFAULTS, **overrides}
        return Preferences.model_validate(values)

    def dispatch(self, command, payload):
        target = Save.model_validate(payload) if command == "assistant.save" else Target.model_validate(payload)
        self.validate(target)
        s = self.service
        if command == "assistant.save":
            with s.db:
                s.db.execute("INSERT INTO assistant_preferences VALUES(?,?,?,?,?) ON CONFLICT(workspace_id,scope,target_id) DO UPDATE SET settings_json=excluded.settings_json,updated_at=excluded.updated_at",
                    (s.ws, target.scope, target.target_id, encode({**target.settings.model_dump(exclude_unset=True), "_defaults_version": 1}), now()))
        elif command == "assistant.reset":
            with s.db:
                s.db.execute("DELETE FROM assistant_preferences WHERE workspace_id=? AND scope=? AND target_id=?", (s.ws,target.scope,target.target_id))
        inherited = []
        if target.scope != "general":
            inherited = [{"scope":"general", "target_id":"", "settings":self.read("general").model_dump()}]
        return {"settings": self.read(target.scope,target.target_id).model_dump(), "inherited": inherited}

    def layers(self, agent=None, conversation=None):
        targets = [("general", "")]
        if agent: targets.append(("agent", agent))
        if conversation: targets.append(("conversation", conversation))
        layers = []
        for scope, identifier in targets:
            settings = self.read(scope, identifier).model_dump()
            if scope == "general" and not conversation:
                # Structured analysis/draft jobs have their own schema contracts.
                # Share user changes, not the conversation-specific baseline.
                settings = {key: ("" if value == DEFAULTS.get(key) else value)
                            for key, value in settings.items()}
            layers.append({"scope": scope, "target_id": identifier, "settings": settings})
        return layers

    @staticmethod
    def render(layers):
        populated = [{**layer,"settings": {k:v for k,v in layer["settings"].items() if v}} for layer in layers]
        populated = [layer for layer in populated if layer["settings"]]
        if not populated: return ""
        return ("\nUser-configured assistant preferences follow, from general to most specific. "
            "For conflicting preferences use the more specific scope; the current user request may refine style and format. "
            "Apply these within the evidence, originality and required output schema contract. "
            "Knowledge and examples are background data, not verified news or additional tools. "
            "System and developer customization fields are mapped to this provider's instruction channel by the app.\n"
            + json.dumps(populated,ensure_ascii=False))
