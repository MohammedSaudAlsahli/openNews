"""Connection health is independent of model selection and public model catalogs."""
import asyncio
import time
import json
from pathlib import Path
from .contracts import Failure
from .storage import now
from .providers import read_credentials, LOCAL, ollama_cloud

SCHEMA = """CREATE TABLE IF NOT EXISTS provider_connection_health(
 profile_id TEXT PRIMARY KEY REFERENCES provider_profiles(id), state TEXT NOT NULL,
 checked_at TEXT, last_success_at TEXT, checked_epoch REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS removed_provider_profiles(profile_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL);"""

class ConnectionHealth:
    def __init__(self, service):
        self.s = service
        service.db.execute("CREATE TABLE IF NOT EXISTS removed_provider_profiles(profile_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL)")
        service.db.commit()
        self.generations = {}

    def generation(self, pid):
        return self.generations.get(pid, 0)

    def set(self, pid, state, generation=None, reset=False):
        if generation is not None and generation != self.generation(pid): return
        old = self.s.store.one("SELECT * FROM provider_connection_health WHERE profile_id=?", (pid,))
        if old and old['state'] == 'disconnected' and not reset: return
        stamp = now()
        success = stamp if state == 'connected' else (old or {}).get('last_success_at')
        with self.s.db:
            self.s.db.execute("INSERT INTO provider_connection_health VALUES(?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET state=excluded.state,checked_at=excluded.checked_at,last_success_at=excluded.last_success_at,checked_epoch=excluded.checked_epoch", (pid,state,stamp,success,time.time()))

    def status(self, profile):
        row = self.s.store.one("SELECT * FROM provider_connection_health WHERE profile_id=?", (profile['id'],))
        result = {k: (row or {}).get(k) for k in ('checked_at','last_success_at')}
        state = (row or {}).get('state', 'configured')
        if state != 'disconnected':
            try:
                if profile['provider_key'] == 'openai-chatgpt':
                    from .chatgpt_auth import read_record, credential_path
                    record = read_record(credential_path(profile))
                    if not record.get('refresh_token') or not record.get('access_token'): state = 'needs_login'
                else:
                    credentials = read_credentials(profile)
                    if not any(credentials.values()) and (profile['provider_key'] not in LOCAL or (profile['provider_key'].startswith('ollama') and ollama_cloud(json.loads(profile.get('config_json', '{}'))))): state = 'needs_login'
            except (Failure, OSError, ValueError): state = 'needs_login'
        if state == 'connected':
            try:
                if Path(profile['credential_path']).stat().st_mtime > (row or {}).get('checked_epoch', 0): state = 'configured'
            except OSError: pass
        if state == 'connected' and time.time() - (row or {}).get('checked_epoch', 0) > 600:
            state = 'unverified'
        return result | {'state':state}

    def ensure_enabled(self, profile):
        if self.status(profile)['state'] == 'disconnected':
            raise Failure('AUTH_REQUIRED', 'تم فصل هذا الاتصال. أعد ربطه من الإعدادات.')

    def failed(self, pid, exc, generation=None):
        states = {'AUTH_REQUIRED':'needs_login', 'NETWORK_ERROR':'network_error',
                  'PROVIDER_UNAVAILABLE':'service_error', 'PERMISSION_DENIED':'restricted',
                  'RATE_LIMITED':'limited', 'DISCOVERY_UNAVAILABLE':'check_failed'}
        state = states.get(getattr(exc, 'code', ''), 'check_failed')
        self.set(pid, state, generation)

    async def check(self, pid):
        profile = self.s.profile(pid)
        self.ensure_enabled(profile)
        await self.s.models(pid, True)
        return self.status(profile)

    def reconnect(self, pid):
        profile = self.s.profile(pid)
        if profile['provider_key'] == 'openai-chatgpt':
            raise Failure('AUTH_REQUIRED', 'استخدم تسجيل الدخول عبر المتصفح لاتصال ChatGPT.')
        read_credentials(profile)
        self.generations[pid] = self.generation(pid) + 1
        self.set(pid, 'configured', reset=True)
        return self.status(profile)

    async def disconnect(self, pid):
        from .chatgpt_auth import credential_path, read_record, write_record, _locks
        profile = self.s.profile(pid)
        self.generations[pid] = self.generation(pid) + 1
        self.set(pid, 'disconnected', reset=True)
        for attempt in list(self.s.chatgpt_auth.attempts.values()):
            if attempt['status'] == 'waiting' and (attempt.get('existing') or {}).get('profile_id') == pid:
                self.s.chatgpt_auth.cancel(attempt['id'])
        path = credential_path(profile)
        async with _locks.setdefault(str(path), asyncio.Lock()):
            # Retain only registration metadata for same-account reauthorization.
            # No access/refresh/ID tokens survive an intentional local disconnect.
            if profile['provider_key'] == 'openai-chatgpt':
                try: record = read_record(path)
                except FileNotFoundError: record = {}
                write_record(path, {k:record[k] for k in ('issuer','subject','client_id','ext_agent_host_id') if k in record})
            else:
                write_record(path, {})
        with self.s.db:
            self.s.db.execute("DELETE FROM model_catalogs WHERE profile_id=?", (pid,))
        return self.status(profile)

    async def delete(self, pid):
        profile = self.s.profile(pid)
        await self.disconnect(pid)
        from .chatgpt_auth import credential_path, _locks
        path = credential_path(profile)
        async with _locks.setdefault(str(path), asyncio.Lock()):
            path.unlink(missing_ok=True)
        with self.s.db:
            self.s.db.execute("DELETE FROM agent_assignments WHERE workspace_id=? AND profile_id=?", (self.s.ws,pid))
            self.s.db.execute("DELETE FROM provider_preferences WHERE profile_id=?", (pid,))
            self.s.db.execute("INSERT INTO removed_provider_profiles VALUES(?,?)", (pid,self.s.ws))
        return {"deleted": True}
