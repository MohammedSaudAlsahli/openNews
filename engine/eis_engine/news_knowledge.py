"""Durable RSS hybrid retrieval: FTS, local vectors, original evidence and dates."""
import asyncio
import re
import struct
import time
from datetime import date

from .contracts import Failure
from .news_embeddings import LocalNewsEmbeddings, MODEL_ID, MODEL_REVISION

INDEX_MODEL = MODEL_ID + "@" + MODEL_REVISION + ":768"


SCHEMA = """
CREATE TABLE IF NOT EXISTS news_embedding_choice(workspace_id TEXT PRIMARY KEY, name TEXT NOT NULL, dimensions INTEGER NOT NULL, digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS news_search_settings(workspace_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS news_search_pending(article_id TEXT PRIMARY KEY REFERENCES news_articles(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS news_search_chunks(
 id INTEGER PRIMARY KEY, article_id TEXT NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
 ordinal INTEGER NOT NULL, text TEXT NOT NULL, vector BLOB, model TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS news_search_article ON news_search_chunks(article_id);
CREATE VIRTUAL TABLE IF NOT EXISTS news_search_fts USING fts5(text, content='news_search_chunks', content_rowid='id', tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS news_search_chunk_insert AFTER INSERT ON news_search_chunks BEGIN
 INSERT INTO news_search_fts(rowid,text) VALUES(new.id,new.text); END;
CREATE TRIGGER IF NOT EXISTS news_search_chunk_delete AFTER DELETE ON news_search_chunks BEGIN
 INSERT INTO news_search_fts(news_search_fts,rowid,text) VALUES('delete',old.id,old.text); END;
CREATE TRIGGER IF NOT EXISTS news_search_new AFTER INSERT ON news_articles BEGIN
 INSERT OR IGNORE INTO news_search_pending VALUES(new.id); END;
CREATE TRIGGER IF NOT EXISTS news_search_changed AFTER UPDATE OF title,text,summary,published_at,body_status,url ON news_articles
WHEN new.title!=old.title OR new.text!=old.text OR new.summary!=old.summary OR new.published_at IS NOT old.published_at OR new.body_status!=old.body_status OR new.url!=old.url
BEGIN
 DELETE FROM news_search_chunks WHERE article_id=new.id;
 INSERT OR IGNORE INTO news_search_pending VALUES(new.id);
END;
INSERT OR IGNORE INTO news_search_pending SELECT id FROM news_articles a
 WHERE NOT EXISTS(SELECT 1 FROM news_search_chunks c WHERE c.article_id=a.id);
"""


def chunks(text, size=1400, overlap=180):
    """Bound inference size while retaining the entire original text, including its tail."""
    for start in range(0, len(text), size-overlap):
        yield text[start:start+size]
        if start+size >= len(text): break


class NewsKnowledge:
    def __init__(self, news, embedder=None):
        self.news, self.store, self.db, self.ws = news, news.store, news.db, news.ws
        self.embedder = embedder or LocalNewsEmbeddings(self.store.path.parent / "models")
        self.lock = asyncio.Lock()
        self.query_cache = {}
        self.phase, self.current_title, self.retry_at = "idle", "", 0
        self.db.executescript(SCHEMA)
        choice = self.store.one("SELECT * FROM news_embedding_choice WHERE workspace_id=?", (self.ws,))
        if choice and embedder is None:
            self.embedder = LocalNewsEmbeddings(name=choice['name'], dimensions=choice['dimensions'], digest=choice['digest'])
        # An encoder change must never mix incompatible vector spaces.
        with self.db:
            self.db.execute("UPDATE news_search_chunks SET vector=NULL,model='' WHERE model!=?", (self.index_model,))

    @property
    def index_model(self):
        return getattr(self.embedder, 'fingerprint', INDEX_MODEL)

    async def select_model(self, name, dimensions, digest):
        async with self.lock:
            encoder = LocalNewsEmbeddings(name=name, dimensions=dimensions, digest=digest)
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO news_embedding_choice VALUES(?,?,?,?)", (self.ws,name,dimensions,digest))
                self.db.execute("UPDATE news_search_chunks SET vector=NULL,model='' WHERE model!=?", (encoder.fingerprint,))
            self.embedder = encoder
            self.query_cache.clear()
            self.phase, self.retry_at = 'idle', 0
            self.configure({'enabled':True})

    async def ensure_runtime(self):
        if isinstance(self.embedder, LocalNewsEmbeddings):
            if not self.embedder.digest: raise RuntimeError('Choose an embedding model')
            await self.news.digest.local.start_runtime()

    def status(self):
        setting = self.store.one("SELECT enabled FROM news_search_settings WHERE workspace_id=?", (self.ws,))
        counts = self.store.one("""SELECT count(DISTINCT c.article_id) AS indexed,
            count(DISTINCT CASE WHEN NOT EXISTS(SELECT 1 FROM news_search_chunks missing WHERE missing.article_id=c.article_id AND missing.vector IS NULL) THEN c.article_id END) AS semantic
            FROM news_search_chunks c JOIN news_articles a ON a.id=c.article_id WHERE a.workspace_id=?""", (self.ws,))
        total = self.store.one("SELECT count(*) AS n FROM news_articles WHERE workspace_id=?", (self.ws,))["n"]
        phase = self.phase
        digest = getattr(self.news, 'digest', None)
        if setting and setting['enabled'] and total > counts['semantic'] and digest and phase in {'idle','indexing'}:
            phase = digest.budget.phase() or ('waiting_model' if digest.service.model_lock.locked() else phase)
        return {"enabled":bool(setting and setting['enabled']), "model":getattr(self.embedder, "name", MODEL_ID), **counts,
                "pending":max(0,total-counts['semantic']), "phase":("needs_download" if isinstance(self.embedder, LocalNewsEmbeddings) and not self.embedder.digest else phase), "current_title":self.current_title}

    def configure(self, payload):
        if type(payload.get('enabled')) is not bool: raise Failure('VALIDATION_ERROR', 'إعداد البحث غير صالح.')
        with self.db:
            self.db.execute("INSERT INTO news_search_settings VALUES(?,?) ON CONFLICT(workspace_id) DO UPDATE SET enabled=excluded.enabled", (self.ws,int(payload['enabled'])))
        return self.status()

    def index_next(self):
        row = self.store.one("""SELECT a.* FROM news_search_pending p JOIN news_articles a ON a.id=p.article_id
            WHERE a.workspace_id=? ORDER BY a.discovered_at DESC LIMIT 1""", (self.ws,))
        if not row: return False
        text = row['text'] or row['summary'] or row['title']
        with self.db:
            self.db.execute("DELETE FROM news_search_chunks WHERE article_id=?", (row['id'],))
            for ordinal, part in enumerate(chunks(text)):
                self.db.execute("INSERT INTO news_search_chunks(article_id,ordinal,text) VALUES(?,?,?)", (row['id'],ordinal,f"title: {row['title']} | text: {part}"))
            self.db.execute("DELETE FROM news_search_pending WHERE article_id=?", (row['id'],))
        return True

    async def embed_next(self):
        setting = self.store.one('SELECT enabled FROM news_search_settings WHERE workspace_id=?', (self.ws,))
        if not setting or not setting['enabled'] or self.lock.locked() or time.monotonic() < self.retry_at: return False
        digest = getattr(self.news, 'digest', None)
        if digest and (digest.budget.phase() or digest.service.model_lock.locked()): return False
        rows = self.store.rows("""SELECT c.id,c.text,a.title FROM news_search_chunks c JOIN news_articles a ON a.id=c.article_id
            WHERE a.workspace_id=? AND c.vector IS NULL ORDER BY a.discovered_at DESC,c.ordinal LIMIT 2""", (self.ws,))
        if not rows:
            self.phase = 'ready'
            return False
        async with self.lock:
            started = time.monotonic()
            if digest: await digest.service.model_lock.acquire()
            self.phase, self.current_title = ('preparing' if getattr(self.embedder,'model',None) is None else 'indexing'), rows[0]['title']
            try:
                await self.ensure_runtime()
                vectors = await asyncio.to_thread(self.embedder.encode, [r['text'] for r in rows])
                with self.db:
                    for row, vector in zip(rows,vectors,strict=True):
                        self.db.execute("UPDATE news_search_chunks SET vector=?,model=? WHERE id=? AND text=?", (struct.pack(f'{len(vector)}f',*vector),self.index_model,row['id'],row['text']))
                self.phase = 'indexing'
                return True
            except asyncio.CancelledError: raise
            except Exception:
                self.phase, self.retry_at = 'unavailable', time.monotonic()+300
                return False
            finally:
                self.current_title = ''
                if digest:
                    digest.service.model_lock.release()
                    digest.budget.finished(time.monotonic()-started)

    async def search(self, query='', from_date='', to_date='', limit=12):
        clauses, values = ['a.workspace_id=?', "s.kind!='manual'", 'a.id NOT IN (SELECT article_id FROM news_article_duplicates)'], [self.ws]
        for bound, op in [(from_date, '>='), (to_date, '<=')]:
            if bound:
                date.fromisoformat(bound)
                clauses.append(f'substr(a.published_at,1,10){op}?')
                values.append(bound)
        where = ' AND '.join(clauses)
        base = "FROM news_search_chunks c JOIN news_articles a ON a.id=c.article_id JOIN news_subscriptions s ON s.id=a.subscription_id"
        terms = re.findall(r'\w+', query, re.UNICODE)[:20]
        rankings = []
        if terms:
            match = ' OR '.join('"'+t+'"' for t in terms)
            lexical = self.store.rows(f"SELECT c.article_id,c.text {base} JOIN news_search_fts f ON f.rowid=c.id WHERE {where} AND news_search_fts MATCH ? ORDER BY bm25(news_search_fts) LIMIT 60", (*values,match))
            rankings.append(lexical)
            if self.status()['enabled'] and self.status()['semantic'] > 0 and self.store.vec_version and self.phase not in {'unavailable','preparing'}:
                rankings.append(await self.semantic(query,base,where,values))
        scores, excerpts = {}, {}
        for ranking in rankings:
            seen = set()
            for rank, row in enumerate(ranking):
                key = row['article_id']
                if key in seen: continue
                seen.add(key)
                scores[key] = scores.get(key,0)+1/(60+rank)
                excerpts.setdefault(key,row['text'])
        # Include newly arrived articles before background FTS indexing has caught up.
        if not terms or not scores:
            extra, args = '', list(values)
            for term in terms:
                extra += " AND instr(lower(a.title || ' ' || a.text || ' ' || a.summary),?)>0"
                args.append(term.lower())
            recent = self.store.rows(f"SELECT a.id FROM news_articles a JOIN news_subscriptions s ON s.id=a.subscription_id WHERE {where}{extra} ORDER BY a.published_at DESC LIMIT ?", (*args,limit))
            for r in recent: scores[r['id']] = 0
        result, urls = [], set()
        for article_id in sorted(scores,key=scores.get,reverse=True):
            row = self.news.article(article_id,mark_read=False)
            if row['url'] in urls: continue
            urls.add(row['url'])
            item = {k:row.get(k) for k in ('id','title','url','published_at','discovered_at','body_status','source_title','source_kind')}
            item['text'] = excerpts.get(article_id,row['text'] or row['summary'])[:1800]
            digest = getattr(self.news,'digest',None)
            if digest and (preview := digest.preview(article_id)): item['prepared_summary'] = preview['summary']
            result.append(item)
            if len(result)>=limit: break
        return result

    async def semantic(self, query, base, where, values):
        try:
            await asyncio.wait_for(self.lock.acquire(), timeout=3)
        except TimeoutError:
            return []
        digest = getattr(self.news, 'digest', None)
        acquired = False
        try:
            if digest:
                try: await asyncio.wait_for(digest.service.model_lock.acquire(),timeout=.25)
                except TimeoutError: return []
                acquired = True
            await self.ensure_runtime()
            vector = self.query_cache.get(query)
            if vector is None:
                vector = (await asyncio.to_thread(self.embedder.encode,[query],query=True))[0]
                if len(self.query_cache)>=64: self.query_cache.pop(next(iter(self.query_cache)))
                self.query_cache[query] = vector
            packed = struct.pack(f'{len(vector)}f',*vector)
            rows = self.store.rows(f"SELECT c.article_id,c.text,vec_distance_cosine(c.vector,?) AS distance {base} WHERE {where} AND c.vector IS NOT NULL AND c.model=? ORDER BY distance LIMIT 60", (packed,*values,self.index_model))
            return [r for r in rows if r['distance'] < .65]
        except Exception:
            self.phase = "unavailable"
            return []
        finally:
            if acquired: digest.service.model_lock.release()
            self.lock.release()

    async def poll(self):
        while True:
            progressed = False
            try:
                # Small bounded batches, yielding to UI and chat between batches.
                for _ in range(5):
                    if not self.index_next(): break
                    progressed = True
                if not self.news.store.one("SELECT id FROM jobs WHERE state IN ('queued','running') LIMIT 1"):
                    progressed = await self.embed_next() or progressed
            except asyncio.CancelledError: raise
            except Exception: self.phase = 'unavailable'
            await asyncio.sleep(1 if progressed else 10)
