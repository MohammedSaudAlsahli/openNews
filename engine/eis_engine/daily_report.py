"""Durable opt-in daily news reports, checked while the app is running."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .contracts import Failure
from .storage import now
from .article_summary import ArticleSummary
from .editorial_instructions import load, directory


class DailyReports:
    def __init__(self, service):
        self.service, self.store, self.db, self.ws = service, service.store, service.db, service.ws
        self.task = None
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS daily_report_settings(workspace_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0,
            hour INTEGER NOT NULL DEFAULT 22, minute INTEGER NOT NULL DEFAULT 0, timezone TEXT NOT NULL DEFAULT 'Asia/Riyadh', language TEXT NOT NULL DEFAULT 'ar');
        CREATE TABLE IF NOT EXISTS daily_reports(workspace_id TEXT NOT NULL, day TEXT NOT NULL, state TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(workspace_id, day));
        ''')
        with self.db:
            self.db.execute("UPDATE daily_reports SET state='failed',error='توقف التطبيق أثناء إعداد التقرير.' WHERE workspace_id=? AND state='running'",(self.ws,))

    def settings(self):
        r = self.store.one('SELECT * FROM daily_report_settings WHERE workspace_id=?',(self.ws,)) or {
            'enabled':False,'hour':22,'minute':0,'timezone':'Asia/Riyadh','language':'ar'}
        return {k:bool(v) if k=='enabled' else v for k,v in r.items() if k!='workspace_id'}

    def status(self):
        settings = self.settings()
        local = datetime.now(ZoneInfo(settings['timezone']))
        due = local.replace(hour=settings['hour'],minute=settings['minute'],second=0,microsecond=0)
        today = self.store.one('SELECT state FROM daily_reports WHERE workspace_id=? AND day=?',(self.ws,local.date().isoformat()))
        if today and today['state']=='ready': due += timedelta(days=1)
        return {'settings':settings,'next_at':due.isoformat() if settings['enabled'] else None,
            'reports':self.store.rows('SELECT day,state,body,error,created_at FROM daily_reports WHERE workspace_id=? ORDER BY day DESC LIMIT 30',(self.ws,)),
            'instructions_path':str(directory(self.store))}

    def configure(self, p):
        s = self.settings() | p
        try: ZoneInfo(s['timezone'])
        except (ZoneInfoNotFoundError, ValueError, TypeError): raise Failure('VALIDATION_ERROR','المنطقة الزمنية غير صالحة.') from None
        if (type(s['enabled']) is not bool or type(s['hour']) is not int or not 0<=s['hour']<=23 or
                type(s['minute']) is not int or not 0<=s['minute']<=59 or s['language'] not in {'ar','en'}):
            raise Failure('VALIDATION_ERROR','وقت التقرير أو لغته غير صالح.')
        if s['enabled'] and not self.service.news_digest.assignment():
            raise Failure('VALIDATION_ERROR','اختر نموذجًا من إعدادات تلخيص الأخبار أولًا.')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO daily_report_settings VALUES(?,?,?,?,?,?)',
                (self.ws,int(s['enabled']),s['hour'],s['minute'],s['timezone'],s['language']))
        if not s['enabled'] and self.task: self.task.cancel()
        return self.status()

    def check(self, current=None):
        settings = self.settings()
        if not settings['enabled'] or (self.task and not self.task.done()): return self.status()
        local = (current or datetime.now(timezone.utc)).astimezone(ZoneInfo(settings['timezone']))
        due = local.replace(hour=settings['hour'],minute=settings['minute'],second=0,microsecond=0)
        if local < due or self.service.model_lock.locked(): return self.status()
        day = local.date().isoformat()
        previous = self.store.one('SELECT * FROM daily_reports WHERE workspace_id=? AND day=?',(self.ws,day))
        if previous:
            if previous['state']=='ready' or previous['attempts']>=3: return self.status()
            if local - datetime.fromisoformat(previous['created_at']) < timedelta(minutes=10): return self.status()
        self.task = asyncio.create_task(self.create(day,settings,previous['attempts'] if previous else 0))
        return self.status()

    async def create(self, day, settings, attempts):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO daily_reports VALUES(?,?,?,?,?,?,?)',(self.ws,day,'running','','',now(),attempts+1))
        try:
            # Use fetched local news; a slow publisher must not block the scheduled report.
            start = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo(settings['timezone']))
            end = start + timedelta(days=1)
            rows = self.store.rows('''SELECT a.title,a.url,a.text,a.summary,a.body_status,s.title AS source
                FROM news_articles a JOIN news_subscriptions s ON s.id=a.subscription_id
                WHERE a.workspace_id=? AND s.enabled=1 AND s.removed_at IS NULL
                AND julianday(coalesce(a.published_at,a.discovered_at))>=julianday(?)
                AND julianday(coalesce(a.published_at,a.discovered_at))<julianday(?)
                AND a.id NOT IN (SELECT article_id FROM news_article_duplicates)
                ORDER BY coalesce(a.published_at,a.discovered_at) DESC''', (self.ws,start.isoformat(),end.isoformat()))
            if not rows:
                body = 'لا توجد أخبار محفوظة من مصادرك لهذا اليوم حتى الآن.' if settings['language']=='ar' else 'No saved news from your followed sources for today yet.'
            else:
                digest = self.service.news_digest
                assignment = digest.assignment()
                if not assignment: raise Failure('VALIDATION_ERROR','اختر نموذج التلخيص أولًا.')
                if assignment['profile_id']=='local-summary':
                    if digest.budget.phase(): raise Failure('BUSY','بانتظار جاهزية الجهاز لإعداد التقرير.')
                    profile = {'id':'local-summary','model_id':assignment['model_id']}
                else:
                    if not digest.cache.reserve(digest.settings()['daily_limit']): raise Failure('BUSY','وصلت إلى حد طلبات اليوم.')
                    profile = self.service.profile(assignment['profile_id']) | {'model_id':assignment['model_id']}
                digest.interrupt_for_user()
                evidence = [{**r,'text':(r['text'] or r['summary'])[:1200],'excerpt':True} for r in rows[:20]]
                result = await digest.generate(profile,load(self.store,'daily-report'),
                    {'output_language':'Arabic.' if settings['language']=='ar' else 'English.', 'day':day,
                     'timezone':settings['timezone'],'available_count':len(rows),'included_count':len(evidence),'articles':evidence},ArticleSummary)
                body = result.summary
            with self.db: self.db.execute("UPDATE daily_reports SET state='ready',body=?,error='' WHERE workspace_id=? AND day=?",(body,self.ws,day))
        except asyncio.CancelledError:
            with self.db: self.db.execute("UPDATE daily_reports SET state='failed',error=? WHERE workspace_id=? AND day=?",('توقف إعداد التقرير.',self.ws,day))
            raise
        except Exception as exc:
            message = exc.message if isinstance(exc,Failure) else 'تعذّر إعداد التقرير. ستتم إعادة المحاولة أثناء تشغيل التطبيق.'
            with self.db: self.db.execute("UPDATE daily_reports SET state='failed',error=? WHERE workspace_id=? AND day=?",(message,self.ws,day))

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task,return_exceptions=True)
