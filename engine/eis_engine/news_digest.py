"""Opt-in, budgeted background previews of complete public articles."""
import asyncio
import time
from .article_summary import ArticleSummary
from .editorial_instructions import load as load_instructions
from .contracts import Failure
from .news_digest_cache import DigestCache, fingerprint, matches_language


class NewsDigest:
    def __init__(self, service):
        self.service, self.store, self.db, self.ws = service, service.store, service.db, service.ws
        self.current_title = ''
        self.current_id = ''
        self.active_request = None
        self.manual_pending = False
        from .background_budget import BackgroundBudget
        self.budget = BackgroundBudget(self.store)
        self.last_worker = ""
        self.quantum_started, self.quantum_units = 0.0, 0
        self._counts_key = None
        self._counts = None
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS news_digest_settings(
                workspace_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0,
                language TEXT NOT NULL DEFAULT 'ar');
            CREATE TABLE IF NOT EXISTS news_digest_results(
                workspace_id TEXT NOT NULL, article_id TEXT NOT NULL,
                source_hash TEXT NOT NULL, language TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '', model_id TEXT NOT NULL DEFAULT '',
                attempts INTEGER NOT NULL DEFAULT 0, retry_after REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(workspace_id, article_id));
        ''')
        self.cache = DigestCache(self.store)
        from .local_summary import LocalSummaryModels
        self.local = LocalSummaryModels(service)
        from .summary_evidence import SummaryEvidence
        self.evidence = SummaryEvidence(self)
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(news_digest_settings)')}
        for name, default in [('engine','provider'),('local_model','')]:
            if name not in columns:
                self.db.execute(f"ALTER TABLE news_digest_settings ADD COLUMN {name} TEXT NOT NULL DEFAULT '{default}'")
        self.db.commit()

    def settings(self):
        return self.store.one('SELECT * FROM news_digest_settings WHERE workspace_id=?', (self.ws,)) or {'enabled':0,'language':'ar','daily_limit':20,'engine':'provider','local_model':''}

    def assignment(self):
        setting = self.settings()
        if setting['engine']=='local':
            return {'profile_id':'local-summary','model_id':setting['local_model']} if setting['local_model'] else None
        return self.store.one("SELECT profile_id,model_id FROM agent_assignments WHERE workspace_id=? AND role='news'", (self.ws,))

    def status(self):
        setting, assignment = self.settings(), self.assignment()
        coverage = self.cache.coverage(setting['language'],assignment)
        total,prepared,retry_at = coverage['total'],coverage['prepared'],coverage['retry_at'] or 0
        return {'enabled':bool(setting['enabled']), 'language':setting['language'], 'prepared':prepared,
                'pending':total-prepared, 'current_title':self.current_title, 'phase':self.phase(setting, assignment, total, prepared, retry_at),
                # `used_today` remains for older desktop clients. Both values are
                # observational activity counts, never a request allowance.
                'requests_today':self.cache.used(), 'used_today':self.cache.used(),
                'engine':setting['engine'],'local_model':setting['local_model'],'current_id':self.current_id}

    def phase(self, setting, assignment, total, prepared, retry_at):
        if not setting['enabled']: return 'disabled'
        if total == prepared: return 'ready' if total else 'waiting_articles'
        if not assignment: return 'needs_model'
        if self.current_title: return 'summarizing'
        if setting['engine']=='local' and self.budget.phase(): return self.budget.phase()
        try:
            if setting['engine']=='local':
                if assignment['model_id'] not in self.local.installed: return 'needs_download'
            else: self.service.validate_model(assignment['profile_id'], assignment['model_id'])
        except Failure: return 'needs_model'
        if self.service.model_lock.locked(): return 'waiting_model'
        if retry_at > time.time(): return 'retrying'
        return 'queued'

    def configure(self, payload):
        current = self.settings()
        enabled, language = payload.get('enabled'), payload.get('language',current['language'])
        if type(enabled) is not bool or language not in {'ar','en'}:
            raise Failure('VALIDATION_ERROR', 'إعداد تلخيص الأخبار غير صالح.')
        engine = payload.get('engine',current['engine'])
        local_model = payload.get('local_model',current['local_model'])
        if engine not in {'provider','local'}: raise Failure('VALIDATION_ERROR','اختر طريقة التلخيص.')
        if engine=='local' and (enabled or ('local_model' in payload and local_model)):
            from .local_summary import model_name
            local_model = model_name(local_model)
            if local_model not in self.local.installed: raise Failure('MODEL_UNSUPPORTED','حمّل النموذج قبل اختياره.')
        if enabled and engine!='local':
            assignment = self.store.one("SELECT profile_id,model_id FROM agent_assignments WHERE workspace_id=? AND role='news'",(self.ws,))
            if not assignment: raise Failure('VALIDATION_ERROR', 'اختر نموذجًا أولًا من إعدادات تلخيص الأخبار.')
            profile = self.service.profile(assignment['profile_id'])
            self.service.validate_model(profile['id'],assignment['model_id'])
        with self.db:
            self.db.execute('''INSERT INTO news_digest_settings(workspace_id,enabled,language,daily_limit,engine,local_model) VALUES(?,?,?,?,?,?)
                ON CONFLICT(workspace_id) DO UPDATE SET enabled=excluded.enabled,language=excluded.language,daily_limit=excluded.daily_limit,engine=excluded.engine,local_model=excluded.local_model''', (self.ws,int(enabled),language,current['daily_limit'],engine,local_model))
        self.interrupt_for_user()
        return self.status()

    def device_state(self, payload):
        result = self.budget.update(payload)
        if result['phase'] not in {'ready','resting'}:
            if self.settings()['engine']=='local': self.interrupt_for_user()
            self.service.news.knowledge.interrupt()
        return result

    def processing_policy(self, payload=None):
        if payload is None: return self.policy_status()
        result = self.budget.configure(payload)
        if result['phase'] not in {'ready','resting'}:
            if self.settings()['engine']=='local': self.interrupt_for_user()
            self.service.news.knowledge.interrupt()
        return self.policy_status()

    def policy_status(self):
        result = self.budget.status()
        knowledge = getattr(getattr(self.service,'news',None),'knowledge',None)
        tasks = [self.active_request,getattr(knowledge,'active_request',None)]
        if self.local.stop_lock.locked() or any(t and not t.done() and t.cancelling() for t in tasks):
            result['phase'] = 'stopping'
        return result

    def has_pending(self):
        setting,assignment = self.settings(),self.assignment()
        if setting['engine']!='local' or not assignment or assignment['model_id'] not in self.local.installed: return False
        return bool(setting['enabled'] and self.cache.has_pending(setting['language'],assignment,time.time()))

    def worker_allowed(self, worker, other_pending):
        if not self.last_worker or not other_pending: return True
        cap = 32 if self.last_worker=='embedding' else 2
        expired = time.monotonic()-self.quantum_started>=10 or self.quantum_units>=cap
        return expired if self.last_worker!=worker else not expired

    def begin_worker(self, worker):
        if self.last_worker!=worker:
            self.last_worker = worker
            self.quantum_started, self.quantum_units = time.monotonic(),0

    def finish_worker(self, worker, units):
        if self.last_worker==worker:
            # The warm quantum starts after cold load/first inference. A slow
            # initial summary must still admit a second warm request after rest.
            if not self.quantum_units: self.quantum_started = time.monotonic()
            self.quantum_units += units

    def preview(self, article_id, language=None):
        row = self.store.one('''SELECT a.*,r.source_hash,r.language AS saved_language,r.summary AS saved_summary,r.model_id,r.profile_id,r.evidence_json,r.updated_at AS generated_at
            FROM news_articles a JOIN news_digest_results r ON r.article_id=a.id AND r.workspace_id=a.workspace_id
            WHERE a.workspace_id=? AND a.id=? ''', (self.ws,article_id))
        if not row: return None
        selected_language, assignment = language or self.settings()['language'],self.assignment()
        import json
        evidence = json.loads(row['evidence_json'])
        if not row['saved_summary']:
            if (evidence.get('legacy_summary') and evidence.get('legacy_hash')==fingerprint(row)
                and assignment and row['saved_language']==selected_language and row['model_id']==assignment['model_id']
                and row['profile_id']==assignment['profile_id']):
                return {'summary':evidence['legacy_summary'],'model':row['model_id'],'cached':True,
                        'needs_refresh':True,'coverage':{'limited':True,'unvisited_links':0}}
            return None
        if not self.cache.valid(row,selected_language,assignment):
            from .storage import digest, encode
            old_hash = digest('explanation-3:'+encode({k:row.get(k) for k in ('title','url','published_at','text','body_status')}))
            if (assignment and row['source_hash']==old_hash and row['saved_language']==selected_language
                and row['model_id']==assignment['model_id'] and row['profile_id']==assignment['profile_id']
                and matches_language(row['saved_summary'],selected_language)):
                return {'summary':row['saved_summary'],'model':row['model_id'],'cached':True,
                        'needs_refresh':True,'coverage':{'limited':True,'unvisited_links':0}}
            return None
        import json
        return {**json.loads(row['evidence_json']),'summary':row['saved_summary'],'model':row['model_id'],
                'generated_at':None if evidence.get('legacy_timestamp_unknown') else row['generated_at'],'cached':True}

    def interrupt_for_user(self):
        knowledge = getattr(getattr(self.service,'news',None),'knowledge',None)
        if knowledge: knowledge.interrupt()
        if self.active_request and not self.active_request.done(): self.active_request.cancel()

    async def prepare_next(self):
        setting = self.settings()
        if not setting['enabled'] or self.service.model_lock.locked() or self.active_request or self.manual_pending: return False
        if self.store.one("SELECT id FROM jobs WHERE workspace_id=? AND type IN ('chat.send','analysis.run','draft.generate') AND state IN ('queued','running') LIMIT 1", (self.ws,)): return False
        if setting['engine']=='local' and self.budget.phase(): return False
        assignment = self.assignment()
        if not assignment: return False
        knowledge = self.service.news.knowledge
        if setting['engine']=='local' and not self.worker_allowed('summary',knowledge.has_pending()): return False
        current = time.time()
        row = self.cache.candidate(setting['language'],assignment,current)
        if not row: return False
        try:
            if setting['engine']=='local':
                await self.local.start_runtime()
                if assignment['model_id'] not in self.local.installed: return False
                profile = {'id':'local-summary'}
            else:
                profile = self.service.profile(assignment['profile_id'])
                self.service.validate_model(profile['id'],assignment['model_id'])
        except Failure: return False
        profile['model_id'] = assignment['model_id']
        if row:
            valid = self.cache.valid(row,setting['language'],assignment)
            cached = self.store.one("""SELECT summary,evidence_json FROM news_digest_results WHERE workspace_id=?
                AND source_hash=? AND language=? AND profile_id=? AND model_id=? AND summary!='' LIMIT 1""",
                (self.ws,fingerprint(row),setting['language'],assignment['profile_id'],assignment['model_id']))
            if cached and matches_language(cached["summary"], setting["language"]):
                import json
                self.cache.save(row,setting['language'],assignment,cached['summary'],evidence=json.loads(cached['evidence_json']))
                return True
            # The summary represents a bounded excerpt for very long articles, not invented coverage.
            if setting['engine']!='local': self.cache.record()
            self.current_title, self.current_id = row['title'], row['id']
            started = time.monotonic()
            if setting['engine']=='local': self.begin_worker('summary')
            try:
                self.active_request = asyncio.create_task(self.evidence.prepare(profile,row,setting['language'],
                    load_instructions(self.store, 'article-summary'),ArticleSummary))
                result = await self.active_request
                self.cache.save(row,setting['language'],assignment,result['summary'],evidence=result)
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling(): raise
                return False
            except Exception as error:
                if isinstance(error,Failure) and error.code=='RESOURCE_WAIT': return False
                attempts = (row['attempts'] or 0)+1 if valid else 1
                previous = self.preview(row['id'],setting['language'])
                retained = {'legacy_summary':previous['summary'],'legacy_hash':fingerprint(row)} if previous and previous.get('needs_refresh') else {}
                self.cache.save(row,setting['language'],assignment,attempts=attempts,
                                retry_after=current+min(86400,300*2**min(attempts,8)),evidence=retained)
            finally:
                self.active_request, self.current_title, self.current_id = None, '', ''
                if setting['engine']=='local':
                    self.finish_worker('summary',1)
                    self.budget.finished(time.monotonic()-started)
            return True
        return False

    async def generate(self, profile, instructions, data, schema):
        language = 'ar' if data.get('output_language') == 'Arabic.' else 'en'
        instructions += '\nRequired output language: ' + ('Arabic.' if language == 'ar' else 'English.')
        async def request(prompt, evidence):
            if profile['id']=='local-summary':
                return await self.local.run(profile['model_id'],prompt,evidence,schema)
            return await self.service.model(profile,prompt,evidence,schema)
        result = await request(instructions, data)
        def prose(value):
            return value.summary+' '+ ' '.join(point.text for field in ('key_points','sequence','viewpoints','uncertainties') for point in getattr(value,field,[]))
        if matches_language(prose(result), language): return result
        # One bounded language repair, rather than saving the wrong language or
        # leaving an explicit user request in a perpetual retry state.
        if profile['id'] != 'local-summary': self.cache.record()
        result = await request('Translate the supplied summary faithfully into ' +
            ('Arabic.' if language == 'ar' else 'English.') +
            ' Preserve facts, links, source_ids, original direct quotations and qualifications; add nothing. Translate every prose field in structured_content. Return the required JSON schema.',
            {'summary':result.summary,'structured_content':result.model_dump(), 'output_language':data.get('output_language')})
        if not matches_language(prose(result), language):
            raise Failure('SUMMARY_LANGUAGE', 'تعذّر تجهيز الشرح باللغة المطلوبة. أعد المحاولة لاحقًا أو اختر نموذجًا آخر.')
        return result

    def article_states(self, ids):
        if not isinstance(ids,list) or len(ids)>100 or any(not isinstance(x,str) for x in ids):
            raise Failure('VALIDATION_ERROR','قائمة المقالات غير صالحة.')
        assignment, setting = self.assignment(), self.settings()
        states = {}
        for identifier in ids:
            row = self.store.one("""SELECT a.id,a.body_status,d.revision,r.source_revision,r.language AS saved_language,r.summary AS saved_summary,r.model_id,r.profile_id,r.retry_after
                FROM news_articles a LEFT JOIN news_digest_results r ON r.article_id=a.id AND r.workspace_id=a.workspace_id
                JOIN news_digest_sources d ON d.article_id=a.id
                WHERE a.workspace_id=? AND a.id=?""", (self.ws,identifier))
            if not row: continue
            valid = self.cache.valid(row,setting['language'],assignment)
            states[identifier] = ('summarizing' if identifier==self.current_id else
                'ready' if valid and row['saved_summary'] else
                'outdated' if row['saved_summary'] else
                'retrying' if valid and (row['retry_after'] or 0)>time.time() else
                'incomplete' if row['body_status']!='full' else 'pending')
        return {'states':states}

    async def poll(self):
        while True:
            try: progressed = await self.prepare_next()
            except asyncio.CancelledError: raise
            except Exception: progressed = False
            await asyncio.sleep(1 if progressed else 10)
