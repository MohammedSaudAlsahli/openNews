"""Summary cache identities and durable per-day request accounting."""
from datetime import datetime, timezone
import json
import re
from .storage import digest, encode


def fingerprint(row):
    return digest('tldr-4:' + encode({k: row.get(k) for k in ('title','url','published_at','text','body_status')}))


def matches_language(text, language):
    if not text:
        return True  # Empty retry records carry no generated content.
    arabic = len(re.findall(r"[\u0621-\u064a\u066e-\u06d3]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return arabic >= 8 and arabic >= latin * 0.2 if language == 'ar' else latin >= 8 and latin >= arabic * 2


class DigestCache:
    def __init__(self, store):
        self.store, self.db, self.ws = store, store.db, store.workspace
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(news_digest_settings)')}
        if 'daily_limit' not in columns:
            self.db.execute('ALTER TABLE news_digest_settings ADD COLUMN daily_limit INTEGER NOT NULL DEFAULT 20')
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(news_digest_results)')}
        if 'profile_id' not in columns:
            self.db.execute("ALTER TABLE news_digest_results ADD COLUMN profile_id TEXT NOT NULL DEFAULT ''")
        self.db.execute('''CREATE TABLE IF NOT EXISTS news_digest_usage(
            workspace_id TEXT NOT NULL, day TEXT NOT NULL, requests INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(workspace_id,day))''')
        self.db.commit()
        self.initialize_queue()
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(news_digest_results)')}
        if 'evidence_json' not in columns:
            with self.db:
                self.db.execute("ALTER TABLE news_digest_results ADD COLUMN evidence_json TEXT NOT NULL DEFAULT '{}'")
            self.db.executescript('DROP TRIGGER IF EXISTS news_digest_source_insert; DROP TRIGGER IF EXISTS news_digest_source_change;')
            self.initialize_queue()
            with self.db:
                # Re-prepare old explanations once, including short complete news.
                self.db.execute("UPDATE news_digest_sources SET revision=revision+1,eligible=(SELECT body_status='full' AND length(trim(text))>0 FROM news_articles WHERE id=article_id)")
        self.restore_legacy_summaries()

    def restore_legacy_summaries(self):
        """Reconcile the old format once; never regenerate unchanged saved prose."""
        self.db.execute('''CREATE TABLE IF NOT EXISTS news_digest_cache_migrations(
            workspace_id TEXT NOT NULL, version INTEGER NOT NULL,
            PRIMARY KEY(workspace_id,version))''')
        if self.store.one('SELECT 1 FROM news_digest_cache_migrations WHERE workspace_id=? AND version=1', (self.ws,)):
            return
        # Stream only saved results needing reconciliation. Idle status/queue
        # queries remain metadata-only, even for a large archive.
        with self.db:
            rows = self.db.execute('''SELECT a.id,a.title,a.url,a.published_at,a.text,a.body_status,
                d.revision,r.source_revision,r.source_hash,r.language,r.summary,r.evidence_json
                FROM news_digest_results r JOIN news_articles a ON a.id=r.article_id AND a.workspace_id=r.workspace_id
                JOIN news_digest_sources d ON d.article_id=a.id
                WHERE r.workspace_id=? AND (r.source_revision!=d.revision OR r.summary='')
                AND (r.summary!='' OR r.evidence_json!='{}')''', (self.ws,))
            for record in rows:
                row = dict(record)
                evidence = json.loads(row['evidence_json'])
                summary = row['summary'] or evidence.get('legacy_summary', '')
                if not summary or not matches_language(summary, row['language']):
                    continue
                current = fingerprint(row)
                old = digest('explanation-3:' + encode({k: row.get(k) for k in ('title','url','published_at','text','body_status')}))
                retained = not row['summary'] and evidence.get('legacy_hash') == current
                if (not row['summary'] and not retained) or (row['summary'] and row['source_hash'] not in {current, old}):
                    continue  # A real source edit still needs a new summary.
                if retained or row['source_hash'] == old:
                    evidence['coverage'] = {'limited': True, 'unvisited_links': 0}
                    if retained:
                        evidence['legacy_timestamp_unknown'] = True
                    evidence.pop('legacy_summary', None)
                    evidence.pop('legacy_hash', None)
                self.db.execute('''UPDATE news_digest_results SET summary=?,source_hash=?,source_revision=?,evidence_json=?
                    WHERE workspace_id=? AND article_id=?''',
                    (summary,current,row['revision'],encode(evidence),self.ws,row['id']))
            self.db.execute('INSERT INTO news_digest_cache_migrations VALUES(?,1)', (self.ws,))

    def day(self):
        return datetime.now(timezone.utc).date().isoformat()

    def used(self):
        row = self.store.one('SELECT requests FROM news_digest_usage WHERE workspace_id=? AND day=?', (self.ws,self.day()))
        return row['requests'] if row else 0

    def record(self):
        """Record an app-observed provider request without imposing a quota.

        Provider billing and account quotas belong to the provider.  The app keeps
        this count only to make its own activity visible; it must never leave new
        articles permanently unexplained.
        """
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO news_digest_usage VALUES(?,?,0)', (self.ws,self.day()))
            self.db.execute('UPDATE news_digest_usage SET requests=requests+1 WHERE workspace_id=? AND day=?', (self.ws,self.day()))
        return True

    # Kept as a compatibility shim for existing local workspaces and callers.
    def reserve(self, _limit=None):
        return self.record()

    def initialize_queue(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS news_digest_sources(article_id TEXT PRIMARY KEY REFERENCES news_articles(id) ON DELETE CASCADE,
                workspace_id TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, eligible INTEGER NOT NULL, source_hash TEXT NOT NULL DEFAULT '');
            CREATE INDEX IF NOT EXISTS news_digest_eligible ON news_digest_sources(workspace_id,eligible,article_id);
            CREATE TRIGGER IF NOT EXISTS news_digest_source_insert AFTER INSERT ON news_articles BEGIN
                INSERT OR REPLACE INTO news_digest_sources(article_id,workspace_id,eligible)
                VALUES(new.id,new.workspace_id,new.body_status='full' AND length(trim(new.text))>0);
            END;
            CREATE TRIGGER IF NOT EXISTS news_digest_source_change AFTER UPDATE OF title,url,published_at,text,body_status ON news_articles
            WHEN new.title IS NOT old.title OR new.url IS NOT old.url OR new.published_at IS NOT old.published_at OR new.text IS NOT old.text OR new.body_status IS NOT old.body_status
            BEGIN
                UPDATE news_digest_sources SET revision=revision+1,source_hash='',
                    eligible=new.body_status='full' AND length(trim(new.text))>0 WHERE article_id=new.id;
            END;
            INSERT OR IGNORE INTO news_digest_sources(article_id,workspace_id,eligible)
                SELECT id,workspace_id,body_status='full' AND length(trim(text))>0 FROM news_articles
                WHERE id NOT IN (SELECT article_id FROM news_digest_sources);
        """)
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(news_digest_results)')}
        if 'source_revision' not in columns:
            self.db.execute('ALTER TABLE news_digest_results ADD COLUMN source_revision INTEGER NOT NULL DEFAULT 0')
            # One migration preserves valid old summaries; idle polling reads metadata.
            for row in self.rows():
                if row['source_hash']==fingerprint(row) and matches_language(row['summary'],row['saved_language']):
                    self.db.execute('UPDATE news_digest_results SET source_revision=1 WHERE workspace_id=? AND article_id=?',(self.ws,row['id']))
                    self.db.execute('UPDATE news_digest_sources SET source_hash=? WHERE article_id=?',(row['source_hash'],row['id']))
        self.db.commit()

    def rows(self):
        return self.store.rows(self.select()+" WHERE d.workspace_id=? AND d.eligible=1 AND a.id NOT IN (SELECT article_id FROM news_article_duplicates) ORDER BY a.discovered_at DESC",(self.ws,))

    @staticmethod
    def select():
        return """SELECT a.id,a.title,a.url,a.text,a.published_at,a.body_status,s.title AS source_title,s.kind AS source_kind,
            d.revision,r.source_revision,r.source_hash,r.language AS saved_language,r.summary,r.model_id,r.profile_id,r.attempts,r.retry_after
            FROM news_digest_sources d JOIN news_articles a ON a.id=d.article_id JOIN news_subscriptions s ON s.id=a.subscription_id
            LEFT JOIN news_digest_results r ON r.workspace_id=d.workspace_id AND r.article_id=d.article_id"""

    def coverage(self, language, assignment):
        assignment = assignment or {'profile_id':'','model_id':''}
        return self.store.one("""SELECT count(*) AS total,
            coalesce(sum(CASE WHEN r.source_revision=d.revision AND r.language=? AND r.summary!='' THEN 1 ELSE 0 END),0) AS prepared,
            min(CASE WHEN r.source_revision=d.revision AND r.language=? AND r.profile_id=? AND r.model_id=? AND r.summary='' THEN r.retry_after WHEN r.source_revision=d.revision AND r.language=? AND r.summary!='' THEN NULL ELSE 0 END) AS retry_at
            FROM news_digest_sources d LEFT JOIN news_digest_results r ON r.article_id=d.article_id AND r.workspace_id=d.workspace_id
            WHERE d.workspace_id=? AND d.eligible=1 AND d.article_id NOT IN (SELECT article_id FROM news_article_duplicates)""",
            (language,language,assignment['profile_id'],assignment['model_id'],language,self.ws))

    def has_pending(self, language, assignment, current):
        return bool(self.store.one("""SELECT d.article_id FROM news_digest_sources d
            LEFT JOIN news_digest_results r ON r.workspace_id=d.workspace_id AND r.article_id=d.article_id
            WHERE d.workspace_id=? AND d.eligible=1 AND d.article_id NOT IN (SELECT article_id FROM news_article_duplicates)
            AND (r.source_revision IS NULL OR r.source_revision!=d.revision OR r.language!=?
                OR (r.summary='' AND (r.profile_id!=? OR r.model_id!=? OR r.retry_after<=?))) LIMIT 1""",(self.ws,language,assignment['profile_id'],assignment['model_id'],current)))

    def candidate(self, language, assignment, current):
        candidate = self.store.one("""SELECT d.article_id FROM news_digest_sources d
            JOIN news_articles a ON a.id=d.article_id
            LEFT JOIN news_digest_results r ON r.workspace_id=d.workspace_id AND r.article_id=d.article_id
            WHERE d.workspace_id=? AND d.eligible=1
            AND a.id NOT IN (SELECT article_id FROM news_article_duplicates)
            AND (r.source_revision IS NULL OR r.source_revision!=d.revision OR r.language!=?
                OR (r.summary='' AND (r.profile_id!=? OR r.model_id!=? OR r.retry_after<=?))) ORDER BY a.discovered_at DESC LIMIT 1""",
            (self.ws,language,assignment['profile_id'],assignment['model_id'],current))
        if not candidate: return None
        # Fetch a single body only after metadata has selected the next job.
        row = self.store.one(self.select()+' WHERE d.article_id=?',(candidate['article_id'],))
        with self.db:
            self.db.execute('UPDATE news_digest_sources SET source_hash=? WHERE article_id=? AND revision=?',(fingerprint(row),row['id'],row['revision']))
        return row

    @staticmethod
    def valid(row, language, assignment):
        summary = row.get('saved_summary', row.get('summary', ''))
        return bool(matches_language(summary, language) and
                    (row.get('source_revision')==row.get('revision') if row.get('revision') is not None else row['source_hash']==fingerprint(row)) and
                    row['saved_language']==language and (summary or (assignment and
                    row['model_id']==assignment['model_id'] and row['profile_id']==assignment['profile_id'])))

    def save(self, row, language, assignment, summary='', attempts=0, retry_after=0, evidence=None):
        from .storage import now
        from .contracts import Failure
        if not matches_language(summary, language):
            raise Failure('SUMMARY_LANGUAGE', 'لم يلتزم النموذج بلغة التلخيص المحددة. ستتم إعادة المحاولة.')
        revision = row.get('revision')
        if revision is None:
            source = self.store.one('SELECT revision,source_hash FROM news_digest_sources WHERE article_id=?',(row['id'],))
            live = self.store.one('SELECT title,url,published_at,text,body_status FROM news_articles WHERE id=?',(row['id'],))
            revision = source['revision'] if source and live and fingerprint(live)==fingerprint(row) else 0
        with self.db:
            self.db.execute('''INSERT INTO news_digest_results
                (workspace_id,article_id,source_hash,language,summary,model_id,attempts,retry_after,updated_at,profile_id,source_revision,evidence_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(workspace_id,article_id) DO UPDATE SET
                source_hash=excluded.source_hash,language=excluded.language,summary=excluded.summary,
                model_id=excluded.model_id,attempts=excluded.attempts,retry_after=excluded.retry_after,
                updated_at=excluded.updated_at,profile_id=excluded.profile_id,source_revision=excluded.source_revision,evidence_json=excluded.evidence_json''',
                (self.ws,row['id'],fingerprint(row),language,summary,assignment['model_id'],attempts,retry_after,now(),assignment['profile_id'],revision,encode(evidence or {})))
