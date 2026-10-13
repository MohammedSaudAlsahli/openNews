"""Provider-model availability and catalog refresh operations."""
import asyncio
import json
import time
from .contracts import Failure
from .providers import catalog
from .storage import encode, now

class ServiceModelsMixin:
    def validate_model(self, profile_id, model_id):
        if not isinstance(model_id,str) or not model_id or len(model_id)>200:
            raise Failure("VALIDATION_ERROR", "اختر نموذجًا صالحًا.")
        cached = self.store.one("SELECT models_json FROM model_catalogs WHERE profile_id=? AND workspace_id=?",(profile_id,self.ws))
        if not cached or not any(m["id"] == model_id and m.get("available",True) for m in json.loads(cached["models_json"])):
            raise Failure("MODEL_UNSUPPORTED", "النموذج غير متاح في قائمة هذا الاتصال؛ حدّث القائمة أولًا.")

    async def models(self, identifier, refresh=False):
        profile = self.profile(identifier)
        self.connections.ensure_enabled(profile)
        lock = self.catalog_locks.setdefault(profile["id"], asyncio.Lock())
        async with lock:
            self.connections.ensure_enabled(profile)
            generation = self.connections.generation(profile["id"])
            cached = self.store.one("SELECT * FROM model_catalogs WHERE profile_id=? AND workspace_id=?",(profile["id"],self.ws))
            pref = self.store.one("SELECT auto_refresh FROM provider_preferences WHERE profile_id=?",(profile["id"],))
            due = not cached or (cached["next_refresh"] <= time.time() and (not pref or pref["auto_refresh"]))
            if refresh or due:
                from .model_catalog import discover
                error = None
                try:
                    result = await asyncio.wait_for(discover(profile),timeout=45)
                    models = result["models"]
                    if not isinstance(models,list) or len(models)>10000:
                        raise ValueError("catalog size")
                    # A gateway can expose thousands of models; cap display metadata, never IDs.
                    models = list({m["id"]:{"id":m["id"],"name":str(m.get("name",m["id"]))[:200],"available":bool(m.get("available",True))} for m in models if isinstance(m.get("id"),str) and 0<len(m["id"])<=200}.values())
                    source,updated = result.get("source",""),now()
                    # Public catalogs cannot prove account authorization.
                    previous = self.connections.status(profile)["state"]
                    if profile["provider_key"] == "openai-chatgpt":
                        self.connections.set(profile["id"], "connected", generation)
                    elif previous not in {"connected", "unverified", "needs_login"}:
                        self.connections.set(profile["id"], "configured", generation)
                except Failure as exc:
                    self.connections.failed(profile["id"], exc, generation)
                    error = exc.message
                except Exception:
                    self.connections.set(profile["id"], "check_failed", generation)
                    error = "تعذر تحديث قائمة النماذج. تحقق من ملف المفتاح وإعدادات الاتصال ثم أعد المحاولة."
                if generation != self.connections.generation(profile["id"]):
                    raise Failure("AUTH_REQUIRED", "تغير الاتصال أثناء التحقق. حاول مجددًا.")
                if error:
                    models = json.loads(cached["models_json"]) if cached else []
                    source,updated = (cached["source"],cached["updated_at"]) if cached else ("",None)
                with self.db:
                    self.db.execute("INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET models_json=excluded.models_json,source=excluded.source,updated_at=excluded.updated_at,error=excluded.error,next_refresh=excluded.next_refresh",(profile["id"],self.ws,encode(models),source,updated,error,time.time()+(300 if error else 3600)))
                cached = self.store.one("SELECT * FROM model_catalogs WHERE profile_id=?",(profile["id"],))
            return {"models":json.loads(cached["models_json"]),"source":cached["source"],"updated_at":cached["updated_at"],"error":cached["error"]}

    async def refresh_catalogs(self):
        while True:
            profiles = self.store.rows("SELECT p.id FROM provider_profiles p LEFT JOIN provider_preferences v ON v.profile_id=p.id WHERE p.workspace_id=? AND p.id NOT IN (SELECT profile_id FROM removed_provider_profiles) AND (coalesce(v.auto_refresh,1)=1 OR p.provider_key='openai-chatgpt')",(self.ws,))
            for profile in profiles:
                try:
                    current = self.profile(profile["id"])
                    status = self.store.one("SELECT checked_epoch FROM provider_connection_health WHERE profile_id=?", (profile["id"],))
                    force = current["provider_key"] == "openai-chatgpt" and (not status or time.time()-status["checked_epoch"] >= 300)
                    await self.models(profile["id"], force)
                except Exception:
                    pass
            await asyncio.sleep(60)
