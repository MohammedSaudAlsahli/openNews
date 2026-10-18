"""IPC command routing for the local workspace."""
import asyncio
import json
import sqlite3
from urllib.parse import urlsplit
from .contracts import Failure, GeneratedDraft, ImportText, ManualDraft, Profile
from .providers import catalog
from .storage import digest, encode, now, uid

class ServiceCommandsMixin:
    async def dispatch(self, command, p):
        if command in {'instructions.get', 'instructions.save', 'instructions.reset'}:
            from .editorial_instructions import dispatch as instruction_dispatch
            return instruction_dispatch(self.store, command, p)
        if command == 'skills.catalog':
            from .writing_skills import catalog as writing_catalog
            return writing_catalog()
        if command == 'daily.get': return self.daily_reports.status()
        if command == 'daily.set':
            if p.get('enabled') and p.get('consent') is not True:
                raise Failure('PERMISSION_DENIED','فعّل استخدام النماذج أولًا.')
            return self.daily_reports.configure(p)
        if command == 'daily.check':
            if p.get('consent') is not True:
                if self.daily_reports.task: self.daily_reports.task.cancel()
                return self.daily_reports.status()
            return self.daily_reports.check()

        if command in {"assistant.get", "assistant.save", "assistant.reset"}:
            return self.personalization.dispatch(command,p)
        if command == "chat.progress":
            return self.conversations.progress(p["job_id"])
        if command == "chat.list":
            return self.conversations.listing()
        if command == "chat.create":
            return self.conversations.create(p)
        if command == "chat.detail":
            return self.conversations.detail(p["conversation_id"],p.get("before_message_id"))
        if command == "chat.send":
            return self.conversations.submit(p)
        if command == "news.icon":
            return await self.news.site_icon(p.get("url", ""))
        if command == "news.unsubscribe":
            return self.news.archive.unsubscribe(p.get("subscription_id"))
        if command == "news.history":
            return self.news.archive.history(p.get("article_id"))
        if command == "news.revision":
            return self.news.archive.compare(p.get("article_id"),p.get("revision_id"))
        if command == "news.list":
            return self.news.list_articles(p)
        if command == "news.bookmark":
            return self.news.bookmark(p)
        if command == "news.import":
            return await self.news.import_article(p.get("url", ""))
        if command == "news.summarize":
            from .article_summary import summarize
            return await summarize(self, p)
        if command == "news.related":
            return self.news.knowledge.related(p.get("article_id"))
        if command == "news.search.inspect":
            return self.news.knowledge.inspect_articles()
        if command == "news.search.status":
            return self.news.knowledge.status()
        if command == "news.search.set":
            return self.news.knowledge.configure(p)
        if command == "news.digest.device":
            return self.news_digest.device_state(p)
        if command == "news.digest.status":
            return self.news_digest.status()
        if command == "news.digest.set":
            return self.news_digest.configure(p)
        if command == "news.summary.states":
            return self.news_digest.article_states(p.get('ids'))
        if command == "news.local.catalog":
            from .local_summary import CATALOG
            await asyncio.gather(*(self.news_digest.local.inspect(x['id']) for x in CATALOG),return_exceptions=True)
            return await self.news_digest.local.refresh()
        if command == "news.local.search":
            return await self.news_digest.local.library.search(p.get('query',''),p.get('page',1),p.get('capability',''))
        if command == "news.local.variants":
            return await self.news_digest.local.library.variants(p.get('model'))
        if command == "news.local.available":
            return await self.news_digest.local.available(p.get("capability","embedding"))
        if command == "news.local.status":
            return await self.news_digest.local.refresh()
        if command == "news.local.start":
            return await self.news_digest.local.start_runtime()
        if command == "news.local.inspect":
            return await self.news_digest.local.inspect(p.get('model'))
        if command == "news.local.download":
            if p.get('consent') is not True: raise Failure('PERMISSION_DENIED','فعّل استخدام النماذج من إعدادات الصلاحيات للمتابعة.')
            return await self.news_digest.local.begin(p.get('model'),p.get('language','ar'),p.get('purpose','summary'))
        if command == "news.local.cancel":
            return await self.news_digest.local.cancel()
        if command == "news.local.select":
            name = await self.news_digest.local.check_generation(p.get('model'))
            return self.news_digest.configure({'engine':'local','local_model':name,
                'enabled':False,'language':p.get('language',self.news_digest.settings()['language'])})
        if command == "news.directory":
            return await self.feed_directory.search(p)
        if command == "news.library.path":
            from .feed_library import library_path
            return library_path(self.store)
        if command == "news.curated":
            from .feed_library import parse_library, SEED_PATH
            return parse_library(SEED_PATH.read_text(encoding="utf-8"))
        if command == "news.library":
            from .feed_library import library
            return library(self.store)
        if command == "news.subscribe":
            identifier = await self.news.add(p, sync=False)
            self.start_feed_sync(identifier)
            return {"subscription_id":identifier,"id":identifier}
        if command == "news.sync":
            identifier = p.get("subscription_id")
            if identifier:
                self.require("news_subscriptions", identifier)
            self.start_feed_sync(identifier)
            return {"started":True}
        if command == "news.update":
            return self.news.update(p)
        if command == "news.reader.pending":
            return self.news.next_public_capture()
        if command == "news.reader":
            return await self.news.reader(p["article_id"], force=p.get("refresh") is True)
        if command == "news.image":
            return await self.news.image(p["article_id"], p["image_id"])
        if command == "news.preview":
            return self.news.article(p["article_id"], mark_read=False) | {"prepared_summary":self.news_digest.preview(p["article_id"])}
        if command == "news.article":
            return self.news.article(p["article_id"]) | {"prepared_summary":self.news_digest.preview(p["article_id"])}
        if command == "news.reader.capture":
            return self.news.capture_public_reader(p["article_id"],p.get("html"))
        if command == "news.snapshot":
            return self.news.snapshot()
        if command == "sources.set_purpose":
            item = self.require("source_items",p["item_id"])
            purpose = p.get("purpose")
            if purpose not in {"style","reference"}:
                raise Failure("VALIDATION_ERROR", "نوع مصدر غير صالح.")
            source = self.require("sources",item["source_id"])
            if purpose == "style" and source["rights_status"] not in {"owned","licensed"}:
                raise Failure("RIGHTS_RESTRICTED", "أكد ملكية أو ترخيص كتابات الأسلوب أولًا.")
            with self.db:
                self.db.execute("INSERT INTO source_roles VALUES(?,?,?) ON CONFLICT(item_id) DO UPDATE SET purpose=excluded.purpose",(item["id"],self.ws,purpose))
            return {"updated":True}
        if command == "runtime.health":
            return {"engine_version":"0.2.3","schema_version":1,"sqlite_version":sqlite3.sqlite_version,"sqlite_vec":self.store.vec_version,"workspace_id":self.ws,"transport":"unix_socket","release_status":"development"}
        if command == "workspace.snapshot":
            return self.snapshot()
        if command == "sources.detail":
            item = self.require("source_items", p["item_id"])
            version = self.require("item_versions", item["current_version_id"])
            techniques = self.store.rows("""SELECT t.*,c.text AS evidence_text,e.excerpt_start,e.excerpt_end,
                s.title AS source_title,s.canonical_uri,i.id AS item_id,v.id AS item_version_id
                FROM techniques t JOIN technique_evidence e ON e.technique_id=t.id
                JOIN chunks c ON c.id=e.chunk_id JOIN item_versions v ON v.id=c.item_version_id
                JOIN source_items i ON i.id=v.item_id JOIN sources s ON s.id=i.source_id
                WHERE t.workspace_id=? AND v.id=? ORDER BY t.created_at DESC""", (self.ws,version["id"]))
            return {"text":version["text"],"version_id":version["id"],"techniques":techniques}
        if command == "sources.add":
            return self.import_text(ImportText.model_validate(p))
        if command == "providers.auth.start":
            return await self.chatgpt_auth.start(p)
        if command == "providers.auth.status":
            return self.chatgpt_auth.status(p["auth_id"])
        if command == "providers.auth.cancel":
            return self.chatgpt_auth.cancel(p["auth_id"])
        if command == "providers.check":
            return await self.connections.check(p["profile_id"])
        if command == "providers.delete":
            return await self.connections.delete(p["profile_id"])
        if command == "providers.disconnect":
            return await self.connections.disconnect(p["profile_id"])
        if command == "providers.reconnect":
            return self.connections.reconnect(p["profile_id"])
        if command == "providers.catalog":
            return catalog()
        if command == "providers.save":
            profile = Profile.model_validate(p)
            if profile.provider_key == "openai-chatgpt":
                raise Failure("AUTH_REQUIRED", "استخدم تسجيل الدخول عبر المتصفح لاتصال ChatGPT.")
            entry = next((x for x in catalog()["providers"] if x["id"] == profile.provider_key),None)
            if not entry or entry["status"] != "ready" or set(profile.config)-set(entry["fields"]):
                raise Failure("MODEL_UNSUPPORTED", "راجع جاهزية المزود وحقول إعداداته.")
            # Config is an allowlist of nonsecret fields. Credentials have a separate native path.
            if any(len(v)>2000 or "\n" in v for v in profile.config.values()):
                raise Failure("VALIDATION_ERROR", "إعداد مزود غير صالح.")
            for key,value in profile.config.items():
                if key in {"base_url","host","azure_endpoint","url","base_host_url","api_base"}:
                    parts = urlsplit(value)
                    if not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.scheme not in {"http","https"}:
                        raise Failure("VALIDATION_ERROR", "عنوان المزود يجب ألا يتضمن مفتاحًا أو بيانات اعتماد.")
                    if parts.scheme == "http" and parts.hostname not in {"localhost","127.0.0.1","::1"}:
                        raise Failure("VALIDATION_ERROR", "HTTP مسموح فقط لخادم النموذج المحلي.")
            pid = uid()
            with self.db:
                self.db.execute("INSERT INTO provider_profiles VALUES(?,?,?,?,?,?,?,?)",(pid,self.ws,profile.provider_key,profile.model_id,encode(profile.config),pid,now(),now()))
                self.db.execute("INSERT INTO provider_preferences VALUES(?,?,?,1)",(pid,self.ws,profile.label))
            return {"profile_id":pid,"keychain_ref":pid}
        if command == "providers.models":
            return await self.models(p["profile_id"], p.get("refresh") is True)
        if command == "providers.update":
            profile = self.profile(p["profile_id"])
            if "model_id" in p:
                self.validate_model(profile["id"], p["model_id"])
            label = p.get("label")
            if label is not None and (not isinstance(label,str) or len(label)>120):
                raise Failure("VALIDATION_ERROR", "اسم الاتصال غير صالح.")
            if "auto_refresh" in p and not isinstance(p["auto_refresh"],bool):
                raise Failure("VALIDATION_ERROR", "قيمة التحديث غير صالحة.")
            with self.db:
                self.db.execute("INSERT OR IGNORE INTO provider_preferences VALUES(?,?,?,1)",(profile["id"],self.ws,""))
                if label is not None:
                    self.db.execute("UPDATE provider_preferences SET label=? WHERE profile_id=?",(label,profile["id"]))
                if "auto_refresh" in p:
                    self.db.execute("UPDATE provider_preferences SET auto_refresh=? WHERE profile_id=?",(int(p["auto_refresh"]),profile["id"]))
                if "model_id" in p:
                    self.db.execute("UPDATE provider_profiles SET model_id=?,updated_at=? WHERE id=?",(p["model_id"],now(),profile["id"]))
            return {"updated":True}
        if command == "agents.list":
            return self.custom_agents.listing()
        if command == "agents.save":
            return self.custom_agents.save(p)
        if command == "agents.delete":
            return self.custom_agents.delete(p["agent_id"])
        if command == "agents.assign":
            profile = self.profile(p["profile_id"])
            if p.get("role") not in {"writer","analyst","news"}:
                raise Failure("VALIDATION_ERROR", "وكيل غير معروف.")
            self.validate_model(profile["id"], p["model_id"])
            with self.db:
                self.db.execute("INSERT INTO agent_assignments VALUES(?,?,?,?) ON CONFLICT(workspace_id,role) DO UPDATE SET profile_id=excluded.profile_id,model_id=excluded.model_id",(self.ws,p["role"],profile["id"],p["model_id"]))
            return {"saved":True}
        if command == "providers.validate":
            if p.get("consent") is not True:
                raise Failure("PERMISSION_DENIED", "اختبار الاتصال يرسل طلبًا صغيرًا إلى المزود وقد تترتب عليه تكلفة.")
            profile = self.profile(p["profile_id"])
            if p.get("model_id"):
                self.validate_model(profile["id"],p["model_id"])
                profile["model_id"] = p["model_id"]
            if not profile["model_id"]:
                raise Failure("VALIDATION_ERROR", "اختر نموذجًا للاختبار.")
            result = await self.model(profile,"Return JSON with text='Connection OK', alternatives=[], claims=[]",{},GeneratedDraft)
            return {"valid":bool(result.text),"structured_output_validated":True}
        if command in {"analysis.run","drafts.generate"}:
            return self.submit(command,p)
        if command == "dna.approve":
            return self.approve(p)
        if command == "dna.retire":
            rule = self.require("dna_rules",p["rule_id"])
            with self.db:
                self.db.execute("UPDATE dna_rules SET status='retired',updated_at=? WHERE id=?",(now(),rule["id"]))
                if rule["technique_id"]:
                    self.db.execute("UPDATE techniques SET status='suggested' WHERE id=?",(rule["technique_id"],))
                version = self.store.dna_snapshot()
            return {"dna_version_id":version}
        if command == "library.search":
            q = p.get("query","").strip()[:300]
            if not q:
                return {"results":[]}
            expression = '"'+q.replace('"','""')+'"'
            return {"results":self.store.rows("""SELECT c.id,c.text,c.location_json,s.title,s.canonical_uri FROM chunks_fts f
            JOIN chunks c ON c.id=f.chunk_id JOIN item_versions v ON v.id=c.item_version_id JOIN source_items i ON i.id=v.item_id
            JOIN sources s ON s.id=i.source_id WHERE chunks_fts MATCH ? AND c.workspace_id=? AND i.current_version_id=v.id LIMIT 50""",(expression,self.ws))}
        if command == "jobs.get":
            job = self.require("jobs",p["job_id"])
            job.pop("payload_json")
            job["events"] = self.store.rows("SELECT * FROM job_events WHERE job_id=? AND seq>? ORDER BY seq LIMIT 100",(job["id"],max(0,int(p.get("last_event_seq",0)))))
            return job
        if command == "jobs.cancel":
            job = self.require("jobs",p["job_id"])
            task = self.tasks.get(job["id"])
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    # A task cancelled before its first instruction cannot persist its own state.
                    with self.db:
                        self.db.execute("UPDATE jobs SET state='cancelled',updated_at=? WHERE id=?",(now(),job["id"]))
                        self.store.event(job["id"],"cancelled",{})
                    self.tasks.pop(job["id"],None)
            return {"state":self.require("jobs",job["id"])["state"]}
        if command == "jobs.resume":
            job = self.require("jobs",p["job_id"])
            if job["state"] not in {"failed","cancelled","interrupted"}:
                raise Failure("VALIDATION_ERROR", "لا يمكن استئناف هذه المهمة في حالتها الحالية.")
            if json.loads(job["payload_json"]).get("profile_id") and p.get("consent") is not True:
                raise Failure("PERMISSION_DENIED", "الاستئناف قد يعيد طلب النموذج وتكلفته؛ وافق عليه أولًا.")
            if job["type"] == "chat.send":
                self.conversations.check_resume(job)
            with self.db:
                self.db.execute("UPDATE jobs SET state='queued',updated_at=? WHERE id=?",(now(),job["id"]))
            self.tasks[job["id"]] = asyncio.create_task(self.run_job(job["id"]))
            return {"job_id":job["id"],"state":"queued"}
        if command == "drafts.create":
            data = ManualDraft.model_validate(p)
            draft, version = uid(), uid()
            dna = self.store.dna_snapshot()
            with self.db:
                self.db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?)",(draft,self.ws,data.format,data.language,data.topic,version,now(),now()))
                self.db.execute("INSERT INTO draft_versions VALUES(?,?,?,?,?,?,?,?,?)",(version,self.ws,draft,None,dna,data.text,"[]",encode(["مسودة يدوية؛ لم تراجع الوقائع أو الأصالة آليًا."]),now()))
            return {"draft_id":draft,"draft_version_id":version}
        if command == "drafts.detail":
            draft = self.require("drafts",p["draft_id"])
            versions = self.store.rows("SELECT * FROM draft_versions WHERE draft_id=? ORDER BY created_at DESC",(draft["id"],))
            claims = self.store.rows("SELECT * FROM claims WHERE draft_version_id=?",(draft["current_version_id"],))
            for claim in claims:
                claim["evidence"] = self.store.rows("SELECT c.id,c.text,c.location_json FROM claim_evidence e JOIN chunks c ON c.id=e.chunk_id WHERE e.claim_id=?",(claim["id"],))
            return {"draft":draft,"versions":versions,"claims":claims,"news_evidence":self.store.rows("SELECT article_id,title,url,published_at,excerpt FROM draft_news_evidence WHERE draft_version_id=? AND workspace_id=?",(draft["current_version_id"],self.ws))}
        if command == "drafts.save":
            draft = self.require("drafts",p["draft_id"])
            text = p.get("text","").strip()
            if not text or len(text)>60000:
                raise Failure("VALIDATION_ERROR", "النص فارغ أو يتجاوز الحد.")
            prior = self.require("draft_versions",draft["current_version_id"])
            version = uid()
            with self.db:
                self.db.execute("INSERT INTO draft_versions VALUES(?,?,?,?,?,?,?,?,?)",(version,self.ws,draft["id"],prior["id"],prior["dna_version_id"],text,"[]",encode(["تغير النص؛ الأدلة السابقة تحتاج مراجعة جديدة."]),now()))
                self.db.execute("INSERT INTO draft_news_evidence SELECT ?,workspace_id,article_id,title,url,published_at,excerpt FROM draft_news_evidence WHERE draft_version_id=? AND workspace_id=?",(version,prior["id"],self.ws))
                self.db.execute("UPDATE drafts SET current_version_id=?,updated_at=? WHERE id=?",(version,now(),draft["id"]))
                self.db.execute("INSERT INTO feedback_events VALUES(?,?,?,?,?)",(uid(),self.ws,prior["id"],version,now()))
            return {"draft_version_id":version}
        if command == "drafts.export":
            draft = self.require("drafts",p["draft_id"])
            version = self.require("draft_versions",draft["current_version_id"])
            evidence = self.store.rows("SELECT title,url,published_at FROM draft_news_evidence WHERE draft_version_id=? AND workspace_id=?",(version["id"],self.ws))
            references = "\n\n## مصادر الأخبار — للمراجعة\n" + "\n".join("- " + e["title"] + " — " + e["url"] + (" ("+e["published_at"]+")" if e["published_at"] else " — تاريخ النشر غير معروف") for e in evidence) if evidence else ""
            # Export source context without implying that edited claims remain verified.
            return {"filename":"editorial-draft.md","text":"# "+draft["topic"]+"\n\n> مسودة غير معتمدة — تحتاج مراجعة الوقائع والأصالة.\n\n"+version["text"]+"\n\n## تنبيهات\n"+"\n".join("- "+w for w in json.loads(version["warnings_json"]))+references}
        raise Failure("MODEL_UNSUPPORTED", "هذه الوظيفة غير متاحة في المرحلة الحالية.")
