import hashlib
import json
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


SCHEMA = """
CREATE TABLE workspaces(id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 identity TEXT NOT NULL, title TEXT NOT NULL, canonical_uri TEXT NOT NULL, author TEXT NOT NULL,
 rights_status TEXT NOT NULL, access_method TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(workspace_id,identity));
CREATE TABLE source_items(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 source_id TEXT NOT NULL REFERENCES sources(id), content_hash TEXT NOT NULL, current_version_id TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE item_versions(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 item_id TEXT NOT NULL REFERENCES source_items(id), version_no INTEGER NOT NULL, text TEXT NOT NULL,
 text_hash TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(item_id,version_no));
CREATE TABLE chunks(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 item_version_id TEXT NOT NULL REFERENCES item_versions(id), ordinal INTEGER NOT NULL, text TEXT NOT NULL,
 location_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE analysis_runs(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 item_version_id TEXT NOT NULL REFERENCES item_versions(id), signature TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL, model_profile_id TEXT, extractor_version TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE techniques(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id), category TEXT NOT NULL, name TEXT NOT NULL,
 description TEXT NOT NULL, applicability TEXT NOT NULL, confidence REAL NOT NULL, method TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'suggested', created_at TEXT NOT NULL);
CREATE TABLE technique_evidence(technique_id TEXT NOT NULL REFERENCES techniques(id),
 workspace_id TEXT NOT NULL REFERENCES workspaces(id), chunk_id TEXT NOT NULL REFERENCES chunks(id),
 excerpt_start INTEGER NOT NULL, excerpt_end INTEGER NOT NULL, PRIMARY KEY(technique_id,chunk_id));
CREATE TABLE dna_rules(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 technique_id TEXT REFERENCES techniques(id), statement TEXT NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE dna_versions(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 rules_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE provider_profiles(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 provider_key TEXT NOT NULL, model_id TEXT NOT NULL, config_json TEXT NOT NULL, keychain_ref TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE drafts(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 format TEXT NOT NULL, language TEXT NOT NULL, topic TEXT NOT NULL, current_version_id TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE draft_versions(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 draft_id TEXT NOT NULL REFERENCES drafts(id), parent_version_id TEXT REFERENCES draft_versions(id),
 dna_version_id TEXT NOT NULL REFERENCES dna_versions(id), text TEXT NOT NULL, alternatives_json TEXT NOT NULL,
 warnings_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE claims(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 draft_version_id TEXT NOT NULL REFERENCES draft_versions(id), text TEXT NOT NULL, claim_type TEXT NOT NULL,
 verdict TEXT NOT NULL, rationale TEXT NOT NULL, high_impact INTEGER NOT NULL, reviewed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE claim_evidence(claim_id TEXT NOT NULL REFERENCES claims(id), workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 chunk_id TEXT NOT NULL REFERENCES chunks(id), PRIMARY KEY(claim_id,chunk_id));
CREATE TABLE jobs(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 type TEXT NOT NULL, state TEXT NOT NULL, payload_json TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 result_json TEXT, error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(workspace_id,type,idempotency_key));
CREATE TABLE job_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 job_id TEXT NOT NULL REFERENCES jobs(id), event TEXT NOT NULL, data_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE feedback_events(id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 before_version_id TEXT NOT NULL REFERENCES draft_versions(id), after_version_id TEXT NOT NULL REFERENCES draft_versions(id),
 created_at TEXT NOT NULL);
CREATE INDEX chunks_version ON chunks(item_version_id);
CREATE INDEX analysis_version ON analysis_runs(item_version_id,status);
CREATE INDEX events_job ON job_events(job_id,seq);
PRAGMA user_version=1;
"""


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        self.path = directory / "editorial.sqlite"
        self.db = sqlite3.connect(self.path)
        os.chmod(self.path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 6:
            raise RuntimeError("Database was created by a newer application")
        if version == 0:
            self.db.executescript("BEGIN;" + SCHEMA + "COMMIT;")
        if version == 1:
            backup_path = directory / "editorial-before-v2.sqlite"
            if backup_path.is_symlink():
                raise RuntimeError("Unsafe migration backup path")
            if not backup_path.exists():
                fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                backup = sqlite3.connect(backup_path)
                try:
                    self.db.backup(backup)
                finally:
                    backup.close()
        if version < 2:
            self.db.executescript("""BEGIN;
            CREATE TABLE provider_preferences(profile_id TEXT PRIMARY KEY REFERENCES provider_profiles(id),
              workspace_id TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', auto_refresh INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE model_catalogs(profile_id TEXT PRIMARY KEY REFERENCES provider_profiles(id), workspace_id TEXT NOT NULL,
              models_json TEXT NOT NULL DEFAULT '[]', source TEXT NOT NULL DEFAULT '', updated_at TEXT, error TEXT, next_refresh REAL NOT NULL DEFAULT 0);
            CREATE TABLE agent_assignments(workspace_id TEXT NOT NULL, role TEXT NOT NULL,
              profile_id TEXT NOT NULL REFERENCES provider_profiles(id), model_id TEXT NOT NULL, PRIMARY KEY(workspace_id,role));
            PRAGMA user_version=2; COMMIT;""")
        if version < 3:
            if version in (1, 2):
                backup_path = directory / "editorial-before-v3.sqlite"
                if backup_path.is_symlink():
                    raise RuntimeError("Unsafe migration backup path")
                if not backup_path.exists():
                    fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    backup = sqlite3.connect(backup_path)
                    try:
                        self.db.backup(backup)
                    finally:
                        backup.close()
            from .news import NEWS_SCHEMA
            from .conversation import CONVERSATION_SCHEMA
            self.db.executescript("BEGIN;" + NEWS_SCHEMA + CONVERSATION_SCHEMA + "PRAGMA user_version=3; COMMIT;")
        if version < 4:
            if version > 0:
                backup_path = directory / "editorial-before-v4.sqlite"
                if backup_path.is_symlink():
                    raise RuntimeError("Unsafe migration backup path")
                if not backup_path.exists():
                    fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    backup = sqlite3.connect(backup_path)
                    try:
                        self.db.backup(backup)
                    finally:
                        backup.close()
            from .custom_agents import AGENT_SCHEMA
            self.db.executescript("BEGIN;" + AGENT_SCHEMA + "PRAGMA user_version=4; COMMIT;")
        if version < 5:
            if version > 0:
                backup_path = directory / "editorial-before-v5.sqlite"
                if backup_path.is_symlink(): raise RuntimeError("Unsafe migration backup path")
                if not backup_path.exists():
                    fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    backup = sqlite3.connect(backup_path)
                    try: self.db.backup(backup)
                    finally: backup.close()
            from .connection_health import SCHEMA as HEALTH_SCHEMA
            self.db.executescript("BEGIN;" + HEALTH_SCHEMA + "PRAGMA user_version=5; COMMIT;")
        if version < 6:
            if version > 0:
                backup_path = directory / "editorial-before-v6.sqlite"
                if backup_path.is_symlink(): raise RuntimeError("Unsafe migration backup path")
                if not backup_path.exists():
                    fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    backup = sqlite3.connect(backup_path)
                    try: self.db.backup(backup)
                    finally: backup.close()
            from .personalization import SCHEMA as PREFERENCES_SCHEMA
            self.db.executescript("BEGIN;" + PREFERENCES_SCHEMA + "PRAGMA user_version=6; COMMIT;")
        with self.db:
            row = self.db.execute("SELECT id FROM workspaces").fetchone()
            self.workspace = row[0] if row else uid()
            if not row:
                self.db.execute("INSERT INTO workspaces VALUES(?,?,?)", (self.workspace, "مساحتي التحريرية", now()))
                self.dna_snapshot()
            self.db.execute("UPDATE jobs SET state='interrupted', error_code='ENGINE_CRASHED' WHERE state IN ('queued','running')")
        self.vec_version = None
        try:
            import sqlite_vec
            self.db.enable_load_extension(True)
            sqlite_vec.load(self.db)
            self.vec_version = self.db.execute("SELECT vec_version()").fetchone()[0]
        except (ImportError, sqlite3.Error, AttributeError):
            pass
        finally:
            if hasattr(self.db, "enable_load_extension"):
                self.db.enable_load_extension(False)

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def one(self, sql, args=()):
        row = self.db.execute(sql, args).fetchone()
        return dict(row) if row else None

    def dna_snapshot(self):
        version = uid()
        rules = self.rows("SELECT id,statement FROM dna_rules WHERE workspace_id=? AND status='approved' ORDER BY created_at,id", (self.workspace,))
        self.db.execute("INSERT INTO dna_versions VALUES(?,?,?,?)", (version, self.workspace, encode(rules), now()))
        return version

    def event(self, job, event, data):
        self.db.execute("INSERT INTO job_events(workspace_id,job_id,event,data_json,created_at) VALUES(?,?,?,?,?)",
                        (self.workspace, job, event, encode(data), now()))

    def close(self):
        self.db.close()
