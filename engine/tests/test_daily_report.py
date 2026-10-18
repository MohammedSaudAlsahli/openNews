import asyncio
from datetime import datetime, timezone
import pytest
from eis_engine.service import Service
from eis_engine.storage import Store, now
from eis_engine.article_summary import ArticleSummary
from eis_engine.contracts import Failure
from eis_engine.editorial_instructions import load, directory

@pytest.fixture
def service(tmp_path):
    s = Service(Store(tmp_path/'workspace'))
    s.news_digest.assignment = lambda: {'profile_id':'local-summary','model_id':'fixture'}
    s.news_digest.budget.phase = lambda: None
    yield s
    s.store.close()


def test_report_opt_in_time_and_once_per_day_persistence(service):
    async def scenario():
        r = service.daily_reports
        due = datetime(2026,10,18,19,0,tzinfo=timezone.utc)
        r.check(due); assert r.task is None
        r.configure({'enabled':True,'hour':22,'minute':0})
        r.check(due.replace(hour=18)); assert r.task is None
        r.check(due); await r.task
        assert r.status()['reports'][0]['state']=='ready'
        first = r.task
        r.check(due); assert r.task is first
        from eis_engine.daily_report import DailyReports
        reopened = DailyReports(service)
        reopened.check(due); assert reopened.task is None
        r.configure({'enabled':False});r.check(due.replace(day=19));assert r.task is first
    asyncio.run(scenario())


def test_report_local_day_boundaries_and_language(service):
    async def scenario():
        service.db.execute("INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,created_at) VALUES('s',?,'source','https://example.com','https://example.com/feed','rss',?)",(service.ws,now()))
        for ident, date in [('today','2026-10-17T21:30:00+00:00'),('yesterday','2026-10-17T20:30:00+00:00')]:
            service.db.execute('INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,discovered_at,published_at,text,body_status,summary) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(ident,service.ws,'s',ident,ident,'https://example.com/'+ident,date,date,'Evidence ' * 100,'full','Excerpt'))
        service.db.commit()
        calls=[]
        async def generate(profile,instructions,data,schema):
            calls.append(data)
            return ArticleSummary(summary='تقرير عربي يشرح الأخبار المتاحة مع المصادر.')
        service.news_digest.generate=generate
        r=service.daily_reports;r.configure({'enabled':True,'hour':22,'minute':0})
        r.check(datetime(2026,10,18,19,tzinfo=timezone.utc));await r.task
        assert calls[0]['output_language']=='Arabic.'
        assert [a['title'] for a in calls[0]['articles']]==['today']
        assert r.status()['reports'][0]['state']=='ready'
    asyncio.run(scenario())


def test_settings_validation_and_editable_instructions(service):
    for invalid in ({'hour':24},{'minute':-1},{'timezone':'Not/AZone'},{'language':'xx'}):
        with pytest.raises(Failure): service.daily_reports.configure(invalid)
    path=directory(service.store)/'article-summary.md'
    assert '250–450' in path.read_text()
    path.write_text('Explain more carefully.')
    assert load(service.store,'article-summary')=='Explain more carefully.'


def test_summary_language_repair_is_bounded(service):
    async def scenario():
        calls=[]
        async def run(name,instructions,data,schema):
            calls.append(data)
            return ArticleSummary(summary='English summary of the source.' if len(calls)==1 else 'هذا شرح عربي واضح يحافظ على تفاصيل المقالة وأهم نتائجها.')
        service.news_digest.local.run=run
        out=await service.news_digest.generate({'id':'local-summary','model_id':'fixture'},'Explain',{'output_language':'Arabic.'},ArticleSummary)
        assert out.summary.startswith('هذا') and len(calls)==2
        calls.clear()
        async def wrong(*args):
            calls.append(1);return ArticleSummary(summary='English only despite request.')
        service.news_digest.local.run=wrong
        with pytest.raises(Failure,match='اللغة'):
            await service.news_digest.generate({'id':'local-summary','model_id':'fixture'},'Explain',{'output_language':'Arabic.'},ArticleSummary)
        assert len(calls)==2
    asyncio.run(scenario())
