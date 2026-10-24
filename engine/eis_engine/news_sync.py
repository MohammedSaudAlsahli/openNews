"""Subscription lifecycle, feed sync and background polling."""
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urljoin
from .contracts import Failure
from .news_urls import MAX_TEXT, NewsError, canonical_url
from .feed_parser import HTMLInfo, parse_feed, normalize_subscription, extract_markdown, source_description
from .storage import uid, now

class NewsSyncMixin:
    async def add(self, payload, sync=True):
        try:
            url, feed, kind = normalize_subscription(payload.get("url", ""), payload.get("kind", "auto"))
            interval = self._interval(payload.get("interval_minutes", 5))
        except NewsError as error: raise Failure("VALIDATION_ERROR", str(error)) from None
        existing = self.store.one("SELECT id FROM news_subscriptions WHERE workspace_id=? AND url=?", (self.ws,url))
        if existing:
            with self.db:
                self.db.execute("UPDATE news_subscriptions SET removed_at=NULL,enabled=1 WHERE id=?", (existing["id"],))
            if sync: await self.sync(existing["id"])
            return existing["id"]
        identifier = uid()
        title = str(payload.get("title", "")).strip()[:300] or urlsplit(url).hostname
        with self.db:
            self.db.execute("INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,enabled,interval_minutes,created_at) VALUES(?,?,?,?,?,?,1,?,?)", (identifier,self.ws,title,url,feed,kind,interval,now()))
        if sync: await self.sync(identifier)
        return identifier

    @staticmethod
    def _interval(value):
        if isinstance(value,bool) or not isinstance(value,int) or not 1 <= value <= 10080: raise NewsError("فترة التحديث بين دقيقة واحدة وأسبوع.")
        return value

    def update(self, payload):
        identifier = payload.get("subscription_id")
        row = self.store.one("SELECT * FROM news_subscriptions WHERE id=? AND workspace_id=?", (identifier,self.ws))
        if not row: raise Failure("VALIDATION_ERROR", "اشتراك الأخبار غير موجود.")
        enabled = payload.get("enabled", bool(row["enabled"]))
        if not isinstance(enabled,bool): raise Failure("VALIDATION_ERROR", "قيمة تشغيل المتابعة غير صالحة.")
        try: interval = self._interval(payload.get("interval_minutes",row["interval_minutes"]))
        except NewsError as error: raise Failure("VALIDATION_ERROR", str(error)) from None
        title = str(payload.get("title",row["title"])).strip()[:300]
        if not title: raise Failure("VALIDATION_ERROR", "أدخل اسمًا للاشتراك.")
        with self.db:
            self.db.execute("UPDATE news_subscriptions SET title=?,enabled=?,interval_minutes=? WHERE id=? AND workspace_id=?", (title,int(enabled),interval,identifier,self.ws))
        return {"subscription_id":identifier,"enabled":enabled}

    def due(self, row):
        if not row["last_checked"]: return True
        return datetime.now(timezone.utc) - datetime.fromisoformat(row["last_checked"]) >= timedelta(minutes=row["interval_minutes"])

    async def sync(self, identifier=None, force=False):
        async with self.lock:
            rows = self.store.rows("SELECT * FROM news_subscriptions WHERE workspace_id=? AND enabled=1 AND removed_at IS NULL" + (" AND id=?" if identifier else ""), (self.ws,identifier) if identifier else (self.ws,))
            if identifier and not rows:
                exists = self.store.one("SELECT id FROM news_subscriptions WHERE workspace_id=? AND id=?", (self.ws,identifier))
                if not exists: raise Failure("VALIDATION_ERROR", "اشتراك الأخبار غير موجود.")
            updated = failed = 0
            for row in rows:
                if identifier or force or self.due(row):
                    if await self._sync_one(row, refresh_full=bool(identifier or force)): updated += 1
                    else: failed += 1
            return {"updated":updated,"failed":failed}

    async def _sync_one(self, row, refresh_full=False):
        with self.db:
            self.db.execute("UPDATE news_subscriptions SET last_checked=?,status='syncing',error=NULL WHERE id=?", (now(),row["id"]))
        try:
            changed_articles = set()
            conditional = {"If-None-Match":row["etag"],"If-Modified-Since":row["last_modified"]}
            response = await self.fetch(row["feed_url"], None if refresh_full else conditional)
            if response["status"] != 304:
                body = response["body"]
                description = source_description(body)
                page_mode = False
                if re.search(br"<\s*(?:!doctype\s+html|html)\b", body[:4000], re.I):
                    page = HTMLInfo(); page.feed(body.decode("utf-8", "replace"))
                    if page.feeds:
                        feed_url = canonical_url(urljoin(response["url"], page.feeds[0]))
                        response = await self.fetch(feed_url, None)
                        body = response["body"]
                        description = description or source_description(body)
                        title, entries = parse_feed(body, response["url"], row["kind"])
                    else:
                        from .page_feed import parse_page
                        title, entries = parse_page(body, response["url"])
                        page_mode = True
                else:
                    title, entries = parse_feed(body,response["url"],row["kind"])
                with self.db:
                    if description:
                        self.db.execute("UPDATE news_subscriptions SET description=? WHERE id=?", (description,row['id']))
                    if page_mode:
                        self.db.execute("UPDATE news_subscriptions SET kind='webpage' WHERE id=?", (row['id'],))
                    for entry in entries:
                        reddit_post = entry['reader'].get('origin') == 'reddit'
                        if reddit_post:
                            # Legacy external-link identities could conflate two
                            # independent posts that happened to mention one site.
                            match = self.store.one('''SELECT id FROM news_articles WHERE workspace_id=?
                                AND (url=? OR (subscription_id=? AND guid=?)) ORDER BY url=? DESC LIMIT 1''',
                                (self.ws,entry['url'],row['id'],entry['guid'],entry['url']))
                            article_id = match['id'] if match else None
                        else:
                            article_id = self.archive.find(row['id'],entry['guid'],entry['url'])
                        existing = self.store.one("SELECT * FROM news_articles WHERE id=?", (article_id,)) if article_id else None
                        article_id = article_id or uid()
                        if existing:
                            # Existing unread/read state and body remain; a feed refresh is not a new article.
                            self.db.execute("UPDATE news_articles SET title=?,summary=?,published_at=coalesce(?,published_at) WHERE id=?", (entry["title"],entry["summary"],entry["published_at"],existing["id"]))
                            if existing["body_status"] == "summary_only" and existing["text"] == existing["summary"]:
                                self.db.execute("UPDATE news_articles SET text=? WHERE id=?", (entry["summary"],existing["id"]))
                            try: previous_reader = json.loads(existing["reader_json"])
                            except (TypeError, ValueError): previous_reader = {}
                            if (not reddit_post and existing['body_status'] == 'full' and previous_reader.get('origin') != 'feed'
                                    and (existing['title'] != entry['title'] or existing['summary'] != entry['summary'])):
                                changed_articles.add(article_id)
                            if not reddit_post and previous_reader.get("origin") == "feed":
                                fresh_reader = entry["reader"] | {k:previous_reader[k] for k in ("checked_at", "refresh_failed", "render_retry_after") if k in previous_reader}
                                self.db.execute("UPDATE news_articles SET reader_json=? WHERE id=?", (json.dumps(fresh_reader), existing["id"]))
                        else:
                            self.db.execute("INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary) VALUES(?,?,?,?,?,?,?,?,?)", (article_id,self.ws,row["id"],entry["guid"],entry["title"],entry["url"],entry["published_at"],now(),entry["summary"]))
                        if reddit_post:
                            self.save_reddit_post(article_id,entry)
                        elif entry.get("full_text") and (not existing or existing["body_status"] != "full" or previous_reader.get("origin") == "feed"):
                            # content:encoded / Atom content is saved before any website request.
                            self.db.execute("UPDATE news_articles SET text=?,body_status='full',reader_json=? WHERE id=?",
                                            (entry["full_text"],json.dumps(entry["reader"]),article_id))
                        self.db.execute("UPDATE news_articles SET reader_json=? WHERE id=? AND reader_json='{}'", (json.dumps(entry['reader']), article_id))
                        if entry.get("media_only"):
                            # Never download or pretend to transcribe an enclosure.
                            self.db.execute("UPDATE news_articles SET text=?,body_status='media_summary' WHERE id=?", (entry["summary"],article_id))
                        self.archive.register(article_id,row['id'],entry['guid'],entry['url'])
                        self.archive.capture(article_id)
                    self.db.execute("UPDATE news_subscriptions SET feed_url=?,title=?,etag=?,last_modified=? WHERE id=?", (response["url"],title if row["title"] == urlsplit(row["url"]).hostname and title else row["title"],response["headers"].get("etag"),response["headers"].get("last-modified"),row["id"]))
            # Recheck full website articles only when their feed evidence changed.
            for article_id in changed_articles:
                await self.reader(article_id, force=True)
            # Unchanged feed entries reuse their full saved text.
            await self._fetch_bodies(row["id"], refresh_full=refresh_full)
            with self.db:
                self.db.execute("UPDATE news_subscriptions SET last_success=?,status='ready',error=NULL WHERE id=?", (now(),row["id"]))
            return True
        except asyncio.CancelledError:
            with self.db: self.db.execute("UPDATE news_subscriptions SET status='pending' WHERE id=?", (row["id"],))
            raise
        except Exception as error:
            message = str(error) if isinstance(error,NewsError) else "تعذّر تحديث هذا المصدر. بقيت الأخبار المحفوظة، وستتم المحاولة لاحقًا."
            with self.db: self.db.execute("UPDATE news_subscriptions SET status='error',error=? WHERE id=?", (message,row["id"]))
            return False

    async def _fetch_bodies(self, identifier, refresh_full=False):
        # Drain the backlog independently of whether the RSS feed changed.
        # Retrying failures must not starve articles that have never been fetched.
        rows = self.store.rows("""SELECT a.* FROM news_articles a
            WHERE a.workspace_id=? AND a.body_status NOT IN ('full','media_summary')
              AND EXISTS (SELECT 1 FROM news_article_origins o JOIN news_subscriptions s ON s.id=o.subscription_id
                  WHERE o.article_id=a.id AND s.enabled=1 AND s.removed_at IS NULL
                  AND (? IS NULL OR s.id=?))
              AND (a.body_attempts=0 OR a.last_body_attempt IS NULL OR
                  julianday(a.last_body_attempt) <= julianday('now') -
                  (CASE WHEN a.body_attempts=1 THEN 5 WHEN a.body_attempts=2 THEN 30 ELSE 360 END)/1440.0)
            ORDER BY a.body_attempts=0 DESC, a.last_body_attempt, a.discovered_at DESC LIMIT 20""",
            (self.ws, identifier, identifier))
        semaphore = asyncio.Semaphore(3)
        async def fetch_article(row):
            async with semaphore, self.reader_locks.setdefault(row["id"], asyncio.Lock()):
                row = self.store.one("SELECT * FROM news_articles WHERE id=? AND workspace_id=?", (row["id"], self.ws))
                if not row or row["body_status"] in {"full", "media_summary"}: return
                status, text = ("full", row["text"]) if row["body_status"] == "full" else ("summary_only", row["summary"])
                try:
                    response = await self.fetch(row["url"], None)
                    content_type = response["headers"].get("content-type", "").lower()
                    if content_type and not any(x in content_type for x in ("html","text/plain","xhtml")): raise NewsError("المقال ليس نصًا مقروءًا.")
                    if "text/plain" in content_type:
                        extracted = response["body"].decode("utf-8","replace")
                    else:
                        extracted = await asyncio.to_thread(extract_markdown, response["body"], response["url"])
                    if extracted and len(extracted.strip()) >= 80:
                        text, status = extracted.strip()[:MAX_TEXT], "full"
                        if "text/plain" not in content_type:
                            from .article_reader import extract_reader
                            reader = await asyncio.to_thread(extract_reader, response["body"], response["url"])
                            reader["checked_at"] = now()
                            with self.db:
                                self.db.execute("UPDATE news_articles SET reader_json=? WHERE id=? AND body_status!='full'", (json.dumps(reader), row["id"]))
                except asyncio.CancelledError: raise
                except Exception: pass
                with self.db:
                    self.db.execute("UPDATE news_articles SET text=?,body_status=?,body_attempts=body_attempts+1,last_body_attempt=? WHERE id=? AND body_status!='full'", (text,status,now(),row["id"]))
                    self.archive.capture(row['id'])
        await asyncio.gather(*(fetch_article(row) for row in rows))

    async def poll(self):
        while True:
            try:
                await self.sync()
                async with self.lock:
                    await self._fetch_bodies(None)
            except asyncio.CancelledError: raise
            except Exception: pass
            await asyncio.sleep(60)
