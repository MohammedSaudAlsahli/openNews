"""Permanent article identities and compressed, immutable revision snapshots."""
import difflib
import hashlib
import json
import re
import sqlite3
import zlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from .storage import now
from .contracts import Failure
from .news_urls import canonical_url


def identity(url):
    parts = urlsplit(canonical_url(url))
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'fbclid', 'gclid', 'mc_cid', 'mc_eid'}]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(sorted(query)), ''))


def content(row):
    # Ignore presentation-only whitespace; retain paragraphs, punctuation and facts.
    clean = lambda value: '\n'.join(re.sub(r'[ \t]+', ' ', line).strip() for line in (value or '').splitlines()).strip()
    return {key: clean(row[key]) for key in ('title', 'text', 'summary', 'url', 'published_at', 'body_status')}


class NewsArchive:
    def __init__(self, news):
        self.news, self.store, self.db, self.ws = news, news.store, news.db, news.ws
        if not self.store.one("SELECT name FROM sqlite_master WHERE name='news_revisions'"):
            # SQLite backup includes committed WAL contents and is safe with an open database.
            folder = self.store.path.parent / 'backups'
            folder.mkdir(mode=0o700, exist_ok=True)
            target = folder / ('before-news-archive-' + now().replace(':', '-') + '.sqlite')
            with sqlite3.connect(target) as backup:
                self.db.backup(backup)
            self.db.executescript('''
                BEGIN IMMEDIATE;
                ALTER TABLE news_subscriptions ADD COLUMN removed_at TEXT;
                CREATE TABLE news_article_duplicates(article_id TEXT PRIMARY KEY REFERENCES news_articles(id), original_id TEXT NOT NULL REFERENCES news_articles(id));
                CREATE TABLE news_article_identities(workspace_id TEXT NOT NULL, url TEXT NOT NULL,
                    article_id TEXT NOT NULL REFERENCES news_articles(id), PRIMARY KEY(workspace_id,url));
                CREATE TABLE news_article_origins(subscription_id TEXT NOT NULL REFERENCES news_subscriptions(id),
                    guid TEXT NOT NULL, article_id TEXT NOT NULL REFERENCES news_articles(id),
                    PRIMARY KEY(subscription_id,guid));
                CREATE TABLE news_revision_blobs(hash TEXT PRIMARY KEY, payload BLOB NOT NULL);
                CREATE TABLE news_revisions(id INTEGER PRIMARY KEY, article_id TEXT NOT NULL REFERENCES news_articles(id),
                    content_hash TEXT NOT NULL REFERENCES news_revision_blobs(hash), captured_at TEXT NOT NULL);
                CREATE INDEX news_revision_article ON news_revisions(article_id,id);
                COMMIT;
            ''')
        with self.db:
            for row in self.store.rows('SELECT * FROM news_articles WHERE workspace_id=? AND NOT EXISTS (SELECT 1 FROM news_revisions r WHERE r.article_id=news_articles.id) ORDER BY discovered_at,id', (self.ws,)):
                original = self.find(row['subscription_id'], row['guid'], row['url'])
                if original and original != row['id']:
                    self.db.execute('INSERT OR IGNORE INTO news_article_duplicates VALUES(?,?)', (row['id'],original))
                    self.db.execute('UPDATE news_articles SET is_bookmarked=max(is_bookmarked,?),is_read=max(is_read,?) WHERE id=?', (row['is_bookmarked'],row['is_read'],original))
                self.register(original or row['id'], row['subscription_id'], row['guid'], row['url'])
                self.capture(row['id'])

    def register(self, article_id, subscription_id, guid, url):
        self.db.execute('INSERT OR IGNORE INTO news_article_identities VALUES(?,?,?)', (self.ws,identity(url),article_id))
        self.db.execute('INSERT OR IGNORE INTO news_article_origins VALUES(?,?,?)', (subscription_id,guid,article_id))

    def find(self, subscription_id, guid, url):
        row = self.store.one('SELECT article_id FROM news_article_identities WHERE workspace_id=? AND url=?', (self.ws,identity(url)))
        if row: return row['article_id']
        row = self.store.one('SELECT article_id FROM news_article_origins WHERE subscription_id=? AND guid=?', (subscription_id,guid))
        return row['article_id'] if row else None

    def capture(self, article_id):
        row = self.store.one('SELECT * FROM news_articles WHERE id=? AND workspace_id=?', (article_id,self.ws))
        if not row: return
        value = content(row)
        # Once full content exists, feed teaser changes do not create an article revision.
        if value['text'] and value['body_status'] == 'full': value['summary'] = ''
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
        digest = hashlib.sha256(raw).hexdigest()
        previous = self.store.one('SELECT content_hash FROM news_revisions WHERE article_id=? ORDER BY id DESC LIMIT 1', (article_id,))
        if previous and previous['content_hash'] == digest: return
        self.db.execute('INSERT OR IGNORE INTO news_revision_blobs VALUES(?,?)', (digest,zlib.compress(raw,9)))
        self.db.execute('INSERT INTO news_revisions(article_id,content_hash,captured_at) VALUES(?,?,?)', (article_id,digest,now()))

    def history(self, article_id):
        self.news.article(article_id, mark_read=False)
        return {'revisions':self.store.rows('SELECT id,captured_at FROM news_revisions WHERE article_id=? ORDER BY id DESC', (article_id,))}

    def compare(self, article_id, revision_id):
        self.news.article(article_id, mark_read=False)
        row = self.store.one('SELECT * FROM news_revisions WHERE article_id=? AND id=?', (article_id,revision_id))
        if not row: raise Failure('VALIDATION_ERROR', 'إصدار المقالة غير موجود.')
        previous = self.store.one('SELECT * FROM news_revisions WHERE article_id=? AND id<? ORDER BY id DESC LIMIT 1', (article_id,revision_id))
        def unpack(item):
            if not item: return {}
            blob = self.store.one('SELECT payload FROM news_revision_blobs WHERE hash=?', (item['content_hash'],))
            return json.loads(zlib.decompress(blob['payload']))
        before, after = unpack(previous), unpack(row)
        lines = []
        for field in ('title','text','summary','published_at','url','body_status'):
            if before.get(field) == after.get(field): continue
            lines.extend(difflib.unified_diff(before.get(field,'').splitlines(),after.get(field,'').splitlines(),fromfile=field+' (before)',tofile=field+' (after)',lineterm=''))
        return {'id':row['id'],'captured_at':row['captured_at'],'previous_id':previous['id'] if previous else None,
                'content':after,'diff':'\n'.join(lines)}

    def unsubscribe(self, identifier):
        with self.db:
            changed = self.db.execute('UPDATE news_subscriptions SET enabled=0,removed_at=? WHERE id=? AND workspace_id=?', (now(),identifier,self.ws))
            if not changed.rowcount: raise Failure('VALIDATION_ERROR','اشتراك الأخبار غير موجود.')
        return {'removed':True,'articles_preserved':True}
