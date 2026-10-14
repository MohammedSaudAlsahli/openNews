"""Subscription lifecycle, feed sync and background polling."""
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urljoin
from .contracts import Failure
from .news_urls import MAX_TEXT, NewsError, canonical_url
from .feed_parser import HTMLInfo, parse_feed, normalize_subscription, extract_markdown
from .storage import uid, now

class NewsSyncMixin:
    async def add(self, payload, sync=True):
        try:
            url, feed, kind = normalize_subscription(payload.get("url", ""), payload.get("kind", "auto"))
            interval = self._interval(payload.get("interval_minutes", 60))
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
        if isinstance(value,bool) or not isinstance(value,int) or not 15 <= value <= 10080: raise NewsError("فترة التحديث بين 15 دقيقة وأسبوع.")
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
            response = await self.fetch(row["feed_url"], conditional)
            if response["status"] != 304:
                body = response["body"]
                if re.search(br"<\s*(?:!doctype\s+html|html)\b", body[:4000], re.I):
                    page = HTMLInfo(); page.feed(body.decode("utf-8", "replace"))
                    if not page.feeds: raise NewsError("لم يُعلن الموقع خلاصة RSS أو Atom. أضف رابط الخلاصة المباشر.")
                    feed_url = canonical_url(urljoin(response["url"], page.feeds[0]))
                    response = await self.fetch(feed_url, None)
                    body = response["body"]
                title, entries = parse_feed(body,response["url"],row["kind"])
                with self.db:
                    for entry in entries:
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
                            if (existing['body_status'] == 'full' and previous_reader.get('origin') != 'feed'
                                    and (existing['title'] != entry['title'] or existing['summary'] != entry['summary'])):
                                changed_articles.add(article_id)
                            if previous_reader.get("origin") == "feed":
                                fresh_reader = entry["reader"] | {k:previous_reader[k] for k in ("checked_at", "refresh_failed") if k in previous_reader}
                                self.db.execute("UPDATE news_articles SET reader_json=? WHERE id=?", (json.dumps(fresh_reader), existing["id"]))
                        else:
                            self.db.execute("INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary) VALUES(?,?,?,?,?,?,?,?,?)", (article_id,self.ws,row["id"],entry["guid"],entry["title"],entry["url"],entry["published_at"],now(),entry["summary"]))
                        if entry.get("full_text") and (not existing or existing["body_status"] != "full" or previous_reader.get("origin") == "feed"):
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
        retry_before = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        rows = self.store.rows("""SELECT * FROM news_articles
            WHERE id IN (SELECT article_id FROM news_article_origins WHERE subscription_id=?) AND body_status!='media_summary'
              AND body_status!='full' AND (body_attempts=0 OR last_body_attempt<?)
            ORDER BY CASE WHEN body_attempts=0 THEN 0 ELSE 1 END,
                     discovered_at DESC LIMIT 20""", (identifier, retry_before))
        semaphore = asyncio.Semaphore(3)
        async def fetch_article(row):
            async with semaphore:
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
                                self.db.execute("UPDATE news_articles SET reader_json=? WHERE id=?", (json.dumps(reader), row["id"]))
                except asyncio.CancelledError: raise
                except Exception: pass
                with self.db:
                    self.db.execute("UPDATE news_articles SET text=?,body_status=?,body_attempts=body_attempts+1,last_body_attempt=? WHERE id=?", (text,status,now(),row["id"]))
                    self.archive.capture(row['id'])
        await asyncio.gather(*(fetch_article(row) for row in rows))

    async def poll(self):
        while True:
            try: await self.sync()
            except asyncio.CancelledError: raise
            except Exception: pass
            await asyncio.sleep(60)
