"""Local, opt-in public feed subscriptions. Feed/article content is untrusted data.

Transport pins the TCP connection to a validated public DNS answer while retaining
TLS hostname verification. No cookies, account credentials, proxies or browser bypass.
"""
import asyncio
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import http.client
import ipaddress
import re
import socket
import ssl
import threading
import time
from urllib.parse import urlsplit, urlunsplit, urljoin
import xml.etree.ElementTree as ET
import zlib
from .contracts import Failure
from .storage import uid, now

NEWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS news_subscriptions (
 id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 title TEXT NOT NULL, url TEXT NOT NULL, feed_url TEXT NOT NULL, kind TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1, interval_minutes INTEGER NOT NULL DEFAULT 5,
 created_at TEXT NOT NULL, last_checked TEXT, last_success TEXT,
 error TEXT, status TEXT NOT NULL DEFAULT 'pending', etag TEXT, last_modified TEXT,
 UNIQUE(workspace_id,url)
);
CREATE TABLE IF NOT EXISTS news_articles (
 id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
 subscription_id TEXT NOT NULL REFERENCES news_subscriptions(id), guid TEXT NOT NULL,
 title TEXT NOT NULL, url TEXT NOT NULL, published_at TEXT, discovered_at TEXT NOT NULL,
 summary TEXT NOT NULL, text TEXT NOT NULL DEFAULT '', body_status TEXT NOT NULL DEFAULT 'pending',
 is_read INTEGER NOT NULL DEFAULT 0, body_attempts INTEGER NOT NULL DEFAULT 0,
 last_body_attempt TEXT, UNIQUE(subscription_id,url), UNIQUE(subscription_id,guid)
);
CREATE INDEX IF NOT EXISTS news_articles_discovered ON news_articles(workspace_id,discovered_at);
"""
from .news_urls import MAX_BYTES, MAX_TEXT, NewsError, public_ip, canonical_url

def resolve_public(host, port):
    try:
        addresses = list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
    except OSError:
        raise NewsError("تعذّر العثور على خادم المصدر. حاول لاحقًا.") from None
    if not addresses or any(not public_ip(item) for item in addresses):
        raise NewsError("عنوان المصدر يحيل إلى شبكة خاصة أو محلية؛ لا يمكن فتحه.")
    return addresses


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, address, secure):
        super().__init__(host, port, timeout=12)
        self.address, self.secure = address, secure
    def request(self, method, url, body=None, headers=None, *, encode_chunked=False):
        import sys
        if sys.platform == 'darwin' and method == 'GET' and body is None:
            from .public_transport import start
            self.public_process = start(self.host, self.port, self.address, self.secure, url, headers or {}, self.timeout)
            return
        return super().request(method, url, body, headers or {}, encode_chunked=encode_chunked)

    def getresponse(self):
        if getattr(self, 'public_process', None):
            from .public_transport import response
            return response(self.public_process)
        return super().getresponse()

    def close(self):
        process = getattr(self, 'public_process', None)
        if process and process.poll() is None:
            process.kill()
            process.wait()
        super().close()

    def connect(self):
        # Numeric address only: no second DNS lookup can change the destination.
        family = socket.AF_INET6 if ":" in self.address else socket.AF_INET
        connection = socket.socket(family, socket.SOCK_STREAM)
        connection.settimeout(self.timeout)
        self.sock = connection
        try:
            connection.connect((self.address, self.port))
            if ipaddress.ip_address(connection.getpeername()[0]) != ipaddress.ip_address(self.address):
                raise NewsError("تغيّر عنوان الاتصال بالمصدر.")
            if self.secure:
                connection = ssl.create_default_context().wrap_socket(connection, server_hostname=self.host, do_handshake_on_connect=False)
                self.sock = connection
                connection.do_handshake()
            self.sock = connection
        except BaseException:
            connection.close()
            raise


def _fetch(url, conditional=None):
    current = canonical_url(url)
    original_origin = urlsplit(current).netloc
    deadline = time.monotonic() + 30
    for _ in range(6):
        p = urlsplit(current)
        addresses = resolve_public(p.hostname, 443 if p.scheme == "https" else 80)
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise NewsError("انتهت مهلة قراءة المصدر.")
        connection = PinnedHTTP(p.hostname, 443 if p.scheme == "https" else 80, addresses[0], p.scheme == "https")
        connection.timeout = min(12, remaining)
        # A wall-clock deadline also interrupts slow-drip headers and bodies.
        def expire(connection=connection):
            process = getattr(connection, "public_process", None)
            if process and process.poll() is None: process.kill()
            connection_socket = getattr(connection, "sock", None)
            if connection_socket:
                try: connection_socket.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                connection_socket.close()
        timer = threading.Timer(remaining, expire)
        timer.daemon = True
        timer.start()
        headers = {"User-Agent":"OpenStudio/0.1 (+public-feed-reader)", "Accept":"application/rss+xml, application/atom+xml, text/html;q=0.8, */*;q=0.1", "Accept-Encoding":"identity"}
        if conditional and p.netloc == original_origin:
            for key in ("If-None-Match", "If-Modified-Since"):
                value = conditional.get(key)
                if value and len(value) <= 1000 and not re.search(r"[\r\n]", value): headers[key] = value
        try:
            path = urlunsplit(("", "", p.path or "/", p.query, ""))
            # Escape non-ASCII path characters without changing existing %-encoded data.
            from urllib.parse import quote
            connection.request("GET", quote(path, safe="/%?=&:+,;@!$'()*[]~-._"), headers=headers)
            response = connection.getresponse()
            status = response.status
            response_headers = {k.lower():v for k,v in response.getheaders()}
            if status in {301,302,303,307,308}:
                location = response_headers.get("location")
                if not location: raise NewsError("إعادة توجيه غير صالحة من المصدر.")
                current = canonical_url(urljoin(current, location))
                continue
            if status == 304: return {"url":current,"status":304,"headers":response_headers,"body":b""}
            if status in {401,403}: raise NewsError("المصدر يمنع الوصول العام أو يتطلب تسجيل دخول. لم تتم محاولة تجاوز الحظر.")
            if status == 429: raise NewsError("المصدر حدّ عدد الطلبات. ستتم المحاولة في التحديث التالي.")
            if status < 200 or status >= 300: raise NewsError("تعذّر جلب المصدر في الوقت الحالي.")
            length = response_headers.get("content-length", "")
            if length.isdigit() and int(length) > MAX_BYTES: raise NewsError("حجم الصفحة يتجاوز الحد المسموح.")
            chunks, size = [], 0
            while True:
                if time.monotonic() >= deadline: raise NewsError("انتهت مهلة قراءة المصدر.")
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk: break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES: raise NewsError("حجم الصفحة يتجاوز الحد المسموح.")
            body = b"".join(chunks)
            if len(body) > MAX_BYTES: raise NewsError("حجم الصفحة يتجاوز الحد المسموح.")
            encoding = response_headers.get("content-encoding", "identity").lower()
            if encoding in {"gzip", "deflate"}:
                decoder = zlib.decompressobj(31 if encoding == "gzip" else zlib.MAX_WBITS)
                body = decoder.decompress(body, MAX_BYTES + 1)
                if len(body) > MAX_BYTES or decoder.unconsumed_tail or not decoder.eof: raise NewsError("حجم الصفحة المضغوطة غير مسموح.")
            elif encoding != "identity": raise NewsError("تنسيق ضغط الصفحة غير مدعوم.")
            return {"url":current,"status":status,"headers":response_headers,"body":body}
        finally:
            timer.cancel()
            connection.close()
    raise NewsError("تجاوز المصدر عدد عمليات إعادة التوجيه المسموح.")


async def fetch_public(url, conditional=None):
    try:
        return await asyncio.wait_for(asyncio.to_thread(_fetch, url, conditional), timeout=35)
    except NewsError:
        raise
    except Exception:
        raise NewsError("تعذّر الاتصال الآمن بالمصدر. ستتم المحاولة في التحديث التالي.") from None


from .feed_parser import (HTMLInfo, plain, safe_content_link, MarkdownSummary,
                          summary_markdown, extract_markdown, node_markup, date_value,
                          local_name, node_text, parse_feed, normalize_subscription)
from .news_reader import NewsReaderMixin
from .news_sync import NewsSyncMixin

class NewsManager(NewsReaderMixin, NewsSyncMixin):
    def __init__(self, store, fetcher=None):
        self.store, self.db, self.ws = store, store.db, store.workspace
        self.fetch = fetcher or fetch_public
        self.lock = asyncio.Lock()
        self.db.executescript(NEWS_SCHEMA)
        if 'reader_json' not in {row[1] for row in self.db.execute('PRAGMA table_info(news_articles)')}:
            self.db.execute("ALTER TABLE news_articles ADD COLUMN reader_json TEXT NOT NULL DEFAULT '{}'")
        if 'is_bookmarked' not in {row[1] for row in self.db.execute('PRAGMA table_info(news_articles)')}:
            self.db.execute("ALTER TABLE news_articles ADD COLUMN is_bookmarked INTEGER NOT NULL DEFAULT 0")
        if 'description' not in {row[1] for row in self.db.execute('PRAGMA table_info(news_subscriptions)')}:
            self.db.execute("ALTER TABLE news_subscriptions ADD COLUMN description TEXT NOT NULL DEFAULT ''")
        self.reader_locks = {}
        self.image_slots = asyncio.Semaphore(3)
        self.icon_results, self.icon_pending = {}, {}
        self.db.execute("UPDATE news_subscriptions SET status='pending' WHERE workspace_id=? AND status='syncing'", (self.ws,))
        self.db.commit()
        from .news_archive import NewsArchive
        self.archive = NewsArchive(self)
        self.repair_reddit_posts()

    def snapshot(self):
        subscriptions = self.store.rows("""SELECT s.id,s.title,s.url,s.feed_url,s.kind,s.enabled,s.interval_minutes,s.last_checked,s.last_success,s.error,s.status,s.description,
            (SELECT count(*) FROM news_articles a WHERE a.subscription_id=s.id AND a.is_read=0) AS unread_count
            FROM news_subscriptions s WHERE workspace_id=? AND kind!='manual' AND removed_at IS NULL ORDER BY created_at DESC""", (self.ws,))
        for row in subscriptions: row["enabled"] = bool(row["enabled"])
        return {"subscriptions":subscriptions,"articles":self.list_articles({"limit":100})["articles"]}

    def list_articles(self, params):
        query = params.get("query", "")
        source = params.get("source_id", "")
        scope = params.get("scope", "all")
        order = params.get("order", "newest")
        days = params.get("days", 0)
        limit, offset = params.get("limit", 60), params.get("offset", 0)
        if (not isinstance(query, str) or len(query) > 200 or not isinstance(source, str)
                or scope not in {"all", "unread", "saved"} or order not in {"newest", "oldest"}
                or type(days) is not int or days not in {0, 1, 7, 30}
                or type(limit) is not int or not 1 <= limit <= 100
                or type(offset) is not int or not 0 <= offset <= 100000):
            raise Failure("VALIDATION_ERROR", "خيارات بحث المقالات غير صالحة.")
        clauses, args = ["a.workspace_id=?", "a.id NOT IN (SELECT article_id FROM news_article_duplicates)"], [self.ws]
        if source: clauses.append("a.id IN (SELECT article_id FROM news_article_origins WHERE subscription_id=?)"); args.append(source)
        if scope == "unread": clauses.append("a.is_read=0")
        if scope == "saved": clauses.append("a.is_bookmarked=1")
        if days:
            clauses.append("coalesce(a.published_at,a.discovered_at)>=?")
            args.append((datetime.now(timezone.utc)-timedelta(days=days)).isoformat())
        # Every term must occur; quoted phrases remain together. Bound and parameterize all input.
        terms = re.findall(r'"([^"\n]+)"|(\S+)', query.strip())
        for phrase, word in terms[:20]:
            term = (phrase or word).replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            clauses.append("(a.title || ' ' || s.title || ' ' || a.summary || ' ' || a.text) LIKE ? ESCAPE '\\'")
            args.append('%'+term+'%')
        direction = "DESC" if order == "newest" else "ASC"
        rows = self.store.rows("""SELECT a.id,a.subscription_id,s.title AS source_title,a.title,a.url,a.published_at,
            a.discovered_at,substr(a.summary,1,500) AS summary,a.body_status,a.is_read,a.is_bookmarked,(SELECT json_extract(value,'$.id') FROM json_each(a.reader_json,'$.blocks') WHERE json_extract(value,'$.type')='image' LIMIT 1) AS cover_image_id
            FROM news_articles a JOIN news_subscriptions s ON a.subscription_id=s.id WHERE """ + " AND ".join(clauses) +
            " ORDER BY coalesce(a.published_at,a.discovered_at) " + direction + ",a.id " + direction + " LIMIT ? OFFSET ?", (*args,limit+1,offset))
        for row in rows:
            row["is_read"], row["is_bookmarked"] = bool(row["is_read"]), bool(row["is_bookmarked"])
        return {"articles":rows[:limit], "has_more":len(rows)>limit}

    def bookmark(self, params):
        if type(params.get("saved")) is not bool:
            raise Failure("VALIDATION_ERROR", "حالة الحفظ غير صالحة.")
        row = self.article(params.get("article_id"), mark_read=False)
        with self.db:
            self.db.execute("UPDATE news_articles SET is_bookmarked=? WHERE id=? AND workspace_id=?", (int(params["saved"]),row["id"],self.ws))
        return {"saved":params["saved"]}

    def article(self, identifier, mark_read=True):
        row = self.store.one("""SELECT a.*,s.title AS source_title,s.kind AS source_kind FROM news_articles a JOIN news_subscriptions s ON a.subscription_id=s.id WHERE a.id=? AND a.workspace_id=?""", (identifier,self.ws))
        if not row: raise Failure("VALIDATION_ERROR", "الخبر غير موجود في مساحة العمل.")
        if mark_read:
            with self.db: self.db.execute("UPDATE news_articles SET is_read=1 WHERE id=? AND workspace_id=?", (identifier,self.ws))
            row["is_read"] = True
        row["is_read"] = bool(row["is_read"])
        row["is_bookmarked"] = bool(row["is_bookmarked"])
        row["reader"] = json.loads(row.pop("reader_json", "{}"))
        from .article_reader import READER_VERSION
        row["reader_upgrade_required"] = row["body_status"] == "full" and (row["reader"].get("version", 1) < READER_VERSION or bool(row["reader"].get('reddit_needs_refresh')))
        return row
