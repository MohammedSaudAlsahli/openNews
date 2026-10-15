"""Summary cache identities and durable per-day request accounting."""
from datetime import datetime, timezone
import re
from .storage import digest, encode


def fingerprint(row):
    return digest(encode({k: row.get(k) for k in ('title','url','published_at','text','body_status')}))


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

    def day(self):
        return datetime.now(timezone.utc).date().isoformat()

    def used(self):
        row = self.store.one('SELECT requests FROM news_digest_usage WHERE workspace_id=? AND day=?', (self.ws,self.day()))
        return row['requests'] if row else 0

    def reserve(self, limit):
        # Reserve before the network call, so failures/cancellation/restarts cannot bypass the cap.
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO news_digest_usage VALUES(?,?,0)', (self.ws,self.day()))
            result = self.db.execute('UPDATE news_digest_usage SET requests=requests+1 WHERE workspace_id=? AND day=? AND requests<?', (self.ws,self.day(),limit))
        return result.rowcount == 1

    def rows(self):
        return self.store.rows('''SELECT a.id,a.title,a.url,a.text,a.published_at,a.body_status,s.title AS source_title,s.kind AS source_kind,
            r.source_hash,r.language AS saved_language,r.summary,r.model_id,r.profile_id,r.attempts,r.retry_after
            FROM news_articles a JOIN news_subscriptions s ON s.id=a.subscription_id
            LEFT JOIN news_digest_results r ON r.workspace_id=a.workspace_id AND r.article_id=a.id
            WHERE a.workspace_id=? AND a.id NOT IN (SELECT article_id FROM news_article_duplicates) AND a.body_status='full' AND length(a.text)>=120
            ORDER BY a.discovered_at DESC''', (self.ws,))

    @staticmethod
    def valid(row, language, assignment):
        return bool(matches_language(row.get('saved_summary', row.get('summary', '')), language) and assignment and row['source_hash']==fingerprint(row) and
                    row['saved_language']==language and row['model_id']==assignment['model_id'] and
                    row['profile_id']==assignment['profile_id'])

    def save(self, row, language, assignment, summary='', attempts=0, retry_after=0):
        from .storage import now
        from .contracts import Failure
        if not matches_language(summary, language):
            raise Failure('SUMMARY_LANGUAGE', 'لم يلتزم النموذج بلغة التلخيص المحددة. ستتم إعادة المحاولة.')
        with self.db:
            self.db.execute('''INSERT INTO news_digest_results
                (workspace_id,article_id,source_hash,language,summary,model_id,attempts,retry_after,updated_at,profile_id)
                VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(workspace_id,article_id) DO UPDATE SET
                source_hash=excluded.source_hash,language=excluded.language,summary=excluded.summary,
                model_id=excluded.model_id,attempts=excluded.attempts,retry_after=excluded.retry_after,
                updated_at=excluded.updated_at,profile_id=excluded.profile_id''',
                (self.ws,row['id'],fingerprint(row),language,summary,assignment['model_id'],attempts,retry_after,now(),assignment['profile_id']))
