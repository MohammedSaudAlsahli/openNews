"""Saved article reading, image and site-icon caches."""
import asyncio
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit, urljoin
from .contracts import Failure
from .news_urls import MAX_BYTES, MAX_TEXT, NewsError, canonical_url
from .feed_parser import HTMLInfo
from .storage import now, uid

class NewsReaderMixin:
    async def import_article(self, address):
        """Attach a public article to chat without subscribing to its entire site."""
        url = canonical_url(address)
        existing = self.store.one("SELECT id FROM news_articles WHERE workspace_id=? AND url=?", (self.ws,url))
        if existing:
            saved = await self.reader(existing["id"])
            if saved["body_status"] != "full":
                raise Failure("VALIDATION_ERROR", "لم أتمكن من قراءة نص المقالة الكامل من هذا الرابط. جرّب رابطًا آخر.")
            return {"article_id":saved["id"], "title":saved["title"]}
        response = await self.fetch(url, None)
        if "html" not in response["headers"].get("content-type", "text/html").lower():
            raise Failure("VALIDATION_ERROR", "الرابط لا يشير إلى مقالة قابلة للقراءة.")
        from lxml import html
        from .article_reader import extract_reader
        tree = html.fromstring(response["body"], parser=html.HTMLParser(no_network=True))
        title = (tree.xpath('//meta[@property="og:title"]/@content') or tree.xpath('//title/text()') or tree.xpath('//h1/text()') or [""])[0].strip()[:500]
        if not title: raise Failure("VALIDATION_ERROR", "تعذّر العثور على عنوان المقالة.")
        reader = await asyncio.to_thread(extract_reader, response["body"], response["url"])
        body = "\n\n".join(block["text"] for block in reader["blocks"] if block.get("type") == "text" and block.get("text"))[:MAX_TEXT]
        if len(body.strip()) < 80:
            raise Failure("VALIDATION_ERROR", "لم يتوفر نص عام كافٍ في المقالة. جرّب رابطًا آخر.")
        date = (tree.xpath('//meta[@property="article:published_time"]/@content') or [None])[0]
        from .feed_parser import date_value
        published = date_value(date)
        source = self.store.one("SELECT id FROM news_subscriptions WHERE workspace_id=? AND kind='manual'", (self.ws,))
        source_id = source["id"] if source else uid()
        article_id = uid()
        with self.db:
            if source is None:
                self.db.execute("INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,enabled,created_at) VALUES(?,?,?,?,?,?,0,?)",
                                (source_id,self.ws,"Attached articles","https://openstudio.invalid/attached/"+self.ws,
                                 "https://openstudio.invalid/attached/"+self.ws,"manual",now()))
            self.db.execute("INSERT OR IGNORE INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary,text,body_status,reader_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (article_id,self.ws,source_id,response["url"],title,response["url"],published,now(),"",body,"full",json.dumps(reader)))
        saved = self.store.one("SELECT id FROM news_articles WHERE workspace_id=? AND url=?", (self.ws,response["url"]))
        return {"article_id":saved["id"], "title":title}

    async def reader(self, identifier, force=False):
        # Upgrade older saved text on first reading, without touching model context.
        lock = self.reader_locks.setdefault(identifier, asyncio.Lock())
        async with lock:
            row = self.article(identifier, mark_read=False)
            checked = row["reader"].get("checked_at")
            if not force and checked and row["reader"].get("version", 1) >= 2:
                if row["reader"].get("origin") == "article" or row["body_status"] == "full":
                    return row
                try:
                    if datetime.now(timezone.utc) - datetime.fromisoformat(checked) < timedelta(hours=6):
                        return row
                except (ValueError, TypeError):
                    pass
            if row["body_status"] == "media_summary": return row
            reader = row["reader"]
            full_text = ""
            try:
                response = await self.fetch(row["url"], None)
                content_type = response["headers"].get("content-type", "").lower()
                if content_type and not any(t in content_type for t in ("html", "xhtml")):
                    raise NewsError("المقال ليس نصًا مقروءًا.")
                from .article_reader import extract_reader
                candidate = await asyncio.to_thread(extract_reader, response["body"], response["url"])
                full_text = "\n\n".join(b["text"] for b in candidate["blocks"] if b.get("type") == "text" and b.get("text"))[:MAX_TEXT]
                if len(full_text.strip()) >= 80:
                    reader = candidate
                else:
                    full_text = ""
                reader.pop("refresh_failed", None)
            except asyncio.CancelledError: raise
            except Exception:
                reader["refresh_failed"] = True
            reader["checked_at"] = now()
            with self.db:
                self.db.execute("UPDATE news_articles SET reader_json=? WHERE id=? AND workspace_id=?", (json.dumps(reader), identifier, self.ws))
                if full_text:
                    self.db.execute("UPDATE news_articles SET text=?,body_status='full' WHERE id=? AND workspace_id=?", (full_text, identifier, self.ws))
            return self.article(identifier, mark_read=False)

    def capture_public_reader(self, identifier, html):
        """Cache a rendered public article when ordinary HTTP extraction was incomplete."""
        row = self.article(identifier, mark_read=False)
        if row["body_status"] == "full": return row
        if row["body_status"] == "media_summary" or not isinstance(html, str) or len(html.encode("utf-8")) > 512 * 1024:
            raise Failure("VALIDATION_ERROR", "نص الصفحة غير صالح.")
        from .article_reader import extract_reader
        reader = extract_reader(html.encode("utf-8"), row["url"])
        full_text = "\n\n".join(block["text"] for block in reader["blocks"] if block.get("type") == "text" and block.get("text"))[:MAX_TEXT]
        if len(full_text.strip()) < 80:
            raise Failure("VALIDATION_ERROR", "لم يتوفر نص عام كافٍ في الصفحة.")
        reader["checked_at"] = now()
        with self.db:
            self.db.execute("UPDATE news_articles SET text=?,body_status='full',reader_json=? WHERE id=? AND workspace_id=?",
                            (full_text,json.dumps(reader),identifier,self.ws))
        return self.article(identifier, mark_read=False)

    async def image(self, identifier, image_id):
        row = self.article(identifier, mark_read=False)
        block = next((b for b in row["reader"].get("blocks", []) if b.get("type") == "image" and b.get("id") == image_id), None)
        if not block: raise Failure("VALIDATION_ERROR", "الصورة غير موجودة في هذا المقال.")
        cache = self.store.path.parent / "reader-images"
        cache.mkdir(mode=0o700, exist_ok=True)
        path = cache / (hashlib.sha256(block["url"].encode()).hexdigest() + ".image")
        async with self.image_slots:
            if not path.exists():
                response = await self.fetch(block["url"], None)
                body = response["body"]
                # Raster formats only. Never execute SVG, HTML, scripts or remote embeds.
                raster = (body.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'GIF87a', b'GIF89a')) or
                          (body.startswith(b'RIFF') and body[8:12] == b'WEBP') or
                          (body[4:8] == b'ftyp' and body[8:12] in (b'avif', b'avis', b'heic', b'heix')))
                if not raster or len(body) > MAX_BYTES:
                    raise Failure("VALIDATION_ERROR", "تعذّر تحميل صورة المقال.")
                files = sorted(cache.glob('*.image'), key=lambda f: f.stat().st_mtime)
                size = sum(f.stat().st_size for f in files)
                while files and size + len(body) > 100 * 1024 * 1024:
                    oldest = files.pop(0); size -= oldest.stat().st_size; oldest.unlink(missing_ok=True)
                # Different reader windows may request the same image concurrently.
                with tempfile.NamedTemporaryFile(dir=cache, suffix='.tmp', delete=False) as temporary:
                    temporary.write(body)
                try: os.replace(temporary.name, path)
                finally:
                    if os.path.exists(temporary.name): os.unlink(temporary.name)
        return {"path":str(path)}

    async def site_icon(self, address):
        try:
            parts = urlsplit(canonical_url(address))
            origin = urlunsplit((parts.scheme,parts.netloc,'/','',''))
        except (NewsError,ValueError):
            return {"path":""}
        cached = self.icon_results.get(origin)
        if cached and time.time()-cached[0] < 3600:
            return cached[1]
        if origin not in self.icon_pending:
            self.icon_pending[origin] = asyncio.create_task(self._site_icon(origin))
        task = self.icon_pending[origin]
        result = await asyncio.shield(task)
        self.icon_pending.pop(origin,None)
        if len(self.icon_results) >= 300: self.icon_results.pop(next(iter(self.icon_results)))
        self.icon_results[origin] = (time.time(),result)
        return result

    async def _site_icon(self, address):
        try:
            parts = urlsplit(canonical_url(address))
            url = urlunsplit((parts.scheme,parts.netloc,'/favicon.ico','',''))
            cache = self.store.path.parent / 'site-icons'
            cache.mkdir(mode=0o700, exist_ok=True)
            path = cache / (hashlib.sha256(url.encode()).hexdigest()+'.image')
            missing = cache / (hashlib.sha256(url.encode()).hexdigest()+'.missing')
            # A verified icon is durable; opening Discover never waits for a
            # network refresh merely because the file is a week old.
            if path.exists(): return {'path':str(path)}
            if missing.exists() and time.time()-missing.stat().st_mtime < 86400:
                return {'path':''}
            async with self.image_slots:
                async def icon_bytes(candidate):
                    try:
                        response = await asyncio.wait_for(self.fetch(candidate,None),timeout=6)
                        body = response['body']
                        if len(body)<=512*1024 and body.startswith((b'\x00\x00\x01\x00',b'\x89PNG',b'\xff\xd8\xff',b'GIF8',b'RIFF')):
                            return body
                    except (NewsError, ValueError, OSError, TimeoutError):
                        pass
                    return None
                body = await icon_bytes(url)
                candidates = []
                try:
                    if body is None:
                        homepage = await asyncio.wait_for(self.fetch(address,None), timeout=6)
                    if body is None and 'html' in homepage.get('headers',{}).get('content-type','text/html').lower() and len(homepage['body']) <= 512*1024:
                        page = HTMLInfo(); page.feed(homepage['body'].decode('utf-8','replace'))
                        for item in page.icons[:5]:
                            try: candidates.append(canonical_url(urljoin(address,item)))
                            except NewsError: pass
                except (NewsError, ValueError, OSError, TimeoutError):
                    pass
                for candidate in dict.fromkeys(candidates):
                    body = await icon_bytes(candidate)
                    if body is not None: break
                if body is not None:
                    with tempfile.NamedTemporaryFile(dir=cache,suffix='.tmp',delete=False) as temporary:
                        temporary.write(body)
                    try: os.replace(temporary.name,path)
                    finally:
                        if os.path.exists(temporary.name): os.unlink(temporary.name)
                    missing.unlink(missing_ok=True)
                    for old in sorted(cache.glob('*.image'),key=lambda f:f.stat().st_mtime)[:-300]: old.unlink(missing_ok=True)
                    return {'path':str(path)}
                missing.touch()
                return {'path':''}
        except (NewsError,ValueError,OSError,TimeoutError):
            return {'path':''}
