"""Local, opt-in public feed subscriptions. Feed/article content is untrusted data.

Transport pins the TCP connection to a validated public DNS answer while retaining
TLS hostname verification. No cookies, account credentials, proxies or browser bypass.
"""
import asyncio
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
 enabled INTEGER NOT NULL DEFAULT 1, interval_minutes INTEGER NOT NULL DEFAULT 60,
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
MAX_BYTES = 4 * 1024 * 1024
MAX_TEXT = 120_000


class NewsError(Exception):
    pass


def public_ip(value):
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast or address.is_reserved or address.is_unspecified:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped and not public_ip(str(address.ipv4_mapped)): return False
        if address.sixtofour and not public_ip(str(address.sixtofour)): return False
        if address.teredo and not all(public_ip(str(x)) for x in address.teredo): return False
    return True


def canonical_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\x00-\x20\x7f]", value):
        raise NewsError("أدخل رابط HTTP أو HTTPS عامًا وصحيحًا.")
    try:
        p = urlsplit(value)
        host = (p.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        port = p.port
        if p.scheme not in {"http", "https"} or not host or p.username is not None or p.password is not None:
            raise ValueError()
        if port not in {None, 80 if p.scheme == "http" else 443}: raise ValueError()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "%" in host:
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host: raise ValueError()
        else:
            if not public_ip(str(address)): raise ValueError()
        netloc = f"[{host}]" if ":" in host else host
        return urlunsplit((p.scheme, netloc, p.path or "/", p.query, ""))
    except (ValueError, UnicodeError):
        raise NewsError("الرابط يجب أن يكون عامًا، دون بيانات دخول أو منفذ خاص.") from None


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
            connection_socket = getattr(connection, "sock", None)
            if connection_socket:
                try: connection_socket.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                connection_socket.close()
        timer = threading.Timer(remaining, expire)
        timer.daemon = True
        timer.start()
        headers = {"User-Agent":"EditorialIntelligenceStudio/0.1 (+public-feed-reader)", "Accept":"application/rss+xml, application/atom+xml, text/html;q=0.8, */*;q=0.1", "Accept-Encoding":"identity"}
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


class HTMLInfo(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.feeds, self.links = [], [], []
        self.ignored = 0
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"script","style","noscript"}: self.ignored += 1
        if tag == "link" and "alternate" in attributes.get("rel", "").lower().split() and attributes.get("type", "").lower() in {"application/rss+xml","application/atom+xml"}:
            self.feeds.append(attributes.get("href", ""))
        if tag == "a" and attributes.get("href"): self.links.append(attributes["href"])
    def handle_endtag(self, tag):
        if tag in {"script","style","noscript"} and self.ignored: self.ignored -= 1
        if tag in {"p","div","br","li"}: self.parts.append("\n")
    def handle_data(self, data):
        if not self.ignored: self.parts.append(data)


def plain(value):
    parser = HTMLInfo()
    parser.feed(value[:MAX_TEXT * 2])
    return re.sub(r"[ \t]+", " ", "".join(parser.parts)).strip()[:MAX_TEXT]



def safe_content_link(value, base):
    """A clickable content link, never an instruction to fetch it automatically."""
    from urllib.parse import quote
    try:
        joined = urljoin(base, value.strip())
        normalized = canonical_url(joined)
        fragment = urlsplit(joined).fragment
        if fragment: normalized += "#" + fragment
        return quote(normalized, safe="/:?=&%+;@!$,*~-._#")
    except (NewsError, ValueError, AttributeError):
        return None


class MarkdownSummary(HTMLParser):
    """Small allowed-format converter for RSS fragments, without scripts or remote images."""
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.parts, self.ignored, self.links = base, [], 0, []
        self.lists = []
    def handle_starttag(self, tag, attrs):
        tag = tag.rsplit(":", 1)[-1]
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "iframe", "object"}: self.ignored += 1; return
        if self.ignored: return
        if tag in {"p", "div", "section", "article"}: self.parts.append("\n\n")
        elif tag == "br": self.parts.append("\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}: self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in {"strong", "b"}: self.parts.append("**")
        elif tag in {"em", "i"}: self.parts.append("*")
        elif tag == "blockquote": self.parts.append("\n\n> ")
        elif tag in {"ul", "ol"}: self.lists.append([tag, 0]); self.parts.append("\n")
        elif tag == "li":
            if self.lists: self.lists[-1][1] += 1
            marker = str(self.lists[-1][1]) + ". " if self.lists and self.lists[-1][0] == "ol" else "- "
            self.parts.append("\n" + "  " * max(0, len(self.lists) - 1) + marker)
        elif tag == "a":
            target = safe_content_link(attrs.get("href", ""), self.base) if attrs.get("href") else None
            self.links.append(target)
            if target: self.parts.append("[")
        elif tag == "code": self.parts.append("`")
    def handle_endtag(self, tag):
        tag = tag.rsplit(":", 1)[-1]
        if tag in {"script", "style", "noscript", "iframe", "object"}:
            self.ignored = max(0, self.ignored - 1); return
        if self.ignored: return
        if tag in {"strong", "b"}: self.parts.append("**")
        elif tag in {"em", "i"}: self.parts.append("*")
        elif tag in {"p", "div", "section", "article", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}: self.parts.append("\n\n")
        elif tag in {"ul", "ol"}:
            if self.lists: self.lists.pop()
            self.parts.append("\n")
        elif tag == "a" and self.links:
            target = self.links.pop()
            if target: self.parts.append("](" + target + ")")
        elif tag == "code": self.parts.append("`")
    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]"))


def summary_markdown(value, base):
    parser = MarkdownSummary(base)
    parser.feed(value[:MAX_TEXT * 2])
    return re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", "".join(parser.parts)).strip()[:MAX_TEXT]


def extract_markdown(body, base):
    from lxml import html
    from trafilatura import extract
    tree = html.fromstring(body, parser=html.HTMLParser(no_network=True, remove_comments=True))
    for node in tree.xpath("//script|//style|//iframe|//object|//embed|//base"):
        node.drop_tree()
    for node in tree.xpath("//a[@href]"):
        target = safe_content_link(node.get("href"), base)
        if target: node.set("href", target)
        else: node.attrib.pop("href", None)
    return extract(tree, url=base, output_format="markdown", include_formatting=True,
                   include_links=True, include_images=False, include_comments=False,
                   include_tables=False, favor_precision=True)


def node_markup(node, names):
    for child in node:
        if local_name(child.tag) in names:
            if len(child): return (child.text or "") + "".join(ET.tostring(x, encoding="unicode", method="html") for x in child)
            return child.text or ""
    return ""

def date_value(value):
    if not value: return None
    try:
        try: date = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError: date = parsedate_to_datetime(value.strip())
        if date.tzinfo is None: date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError): return None


def local_name(tag): return tag.rsplit("}", 1)[-1].lower()


def node_text(node, names):
    for child in node:
        if local_name(child.tag) in names:
            return "".join(child.itertext()).strip()
    return ""


def parse_feed(body, base, kind="rss"):
    if len(body) > MAX_BYTES or re.search(br"<!\s*(DOCTYPE|ENTITY)", body, re.I):
        raise NewsError("يحتوي ملف الخلاصة على بنية XML غير مسموحة.")
    try: root = ET.fromstring(body)
    except ET.ParseError: raise NewsError("الرابط لا يعرض خلاصة RSS أو Atom صالحة.") from None
    if local_name(root.tag) not in {"rss", "feed", "rdf"}: raise NewsError("الرابط لا يعرض خلاصة RSS أو Atom صالحة.")
    channel = next((child for child in root if local_name(child.tag) == "channel"), root)
    title = plain(node_text(channel, {"title"}))[:300]
    entries = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}][:50]
    result = []
    for entry in entries:
        link = ""
        for child in entry:
            if local_name(child.tag) == "link" and child.attrib.get("rel", "alternate") == "alternate":
                link = child.attrib.get("href") or (child.text or "").strip()
                if link: break
        summary = node_markup(entry, {"description", "summary", "content", "encoded"})
        if kind == "reddit":
            # Reddit feeds include the original external article as [link], before comments.
            parser = HTMLInfo(); parser.feed(summary)
            external = [u for u in parser.links if urlsplit(urljoin(base,u)).hostname not in {"www.reddit.com","reddit.com","old.reddit.com"}]
            if external: link = external[0]
        media_only = False
        if not link:
            # Podcast feeds may identify episodes only through an audio/video enclosure.
            enclosure = next((child for child in entry if local_name(child.tag) == "enclosure"
                              and child.attrib.get("type", "").lower().startswith(("audio/", "video/"))), None)
            if enclosure is not None:
                link = enclosure.attrib.get("url", "")
                media_only = True
        if not link: continue
        try: link = canonical_url(urljoin(base, link))
        except NewsError: continue
        guid = node_text(entry, {"guid", "id"})[:2000] or link
        result.append({"guid":guid,"title":plain(node_text(entry,{"title"}))[:500] or "خبر بلا عنوان", "url":link,
                       "published_at":date_value(node_text(entry,{"pubdate","published","date"})), "summary":("وصف الحلقة من الخلاصة، وليس تفريغًا للصوت أو الفيديو.\n\n" if media_only else "") + summary_markdown(summary, link), "media_only":media_only})
    return title, result


def normalize_subscription(url, kind="auto"):
    canonical = canonical_url(url)
    p = urlsplit(canonical)
    is_reddit = p.hostname in {"reddit.com", "www.reddit.com", "old.reddit.com"}
    if kind == "reddit" or is_reddit:
        match = re.match(r"^/r/([A-Za-z0-9_]{2,40})(?:/.*)?$", p.path)
        if not is_reddit or not match: raise NewsError("أدخل رابط مجتمع Reddit مثل https://www.reddit.com/r/science/.")
        name = match.group(1)
        return f"https://www.reddit.com/r/{name.lower()}/", f"https://www.reddit.com/r/{name}/new/.rss", "reddit"
    if kind not in {"auto", "rss"}: raise NewsError("نوع مصدر الأخبار غير مدعوم.")
    return canonical, canonical, "rss"


class NewsManager:
    def __init__(self, store, fetcher=None):
        self.store, self.db, self.ws = store, store.db, store.workspace
        self.fetch = fetcher or fetch_public
        self.lock = asyncio.Lock()
        self.db.executescript(NEWS_SCHEMA)
        self.db.execute("UPDATE news_subscriptions SET status='pending' WHERE workspace_id=? AND status='syncing'", (self.ws,))
        self.db.commit()

    def snapshot(self):
        subscriptions = self.store.rows("""SELECT s.id,s.title,s.url,s.feed_url,s.kind,s.enabled,s.interval_minutes,s.last_checked,s.last_success,s.error,s.status,
            (SELECT count(*) FROM news_articles a WHERE a.subscription_id=s.id AND a.is_read=0) AS unread_count
            FROM news_subscriptions s WHERE workspace_id=? ORDER BY created_at DESC""", (self.ws,))
        for row in subscriptions: row["enabled"] = bool(row["enabled"])
        articles = self.store.rows("""SELECT a.id,a.subscription_id,s.title AS source_title,a.title,a.url,a.published_at,a.discovered_at,substr(a.summary,1,350) AS summary,a.body_status,a.is_read
            FROM news_articles a JOIN news_subscriptions s ON a.subscription_id=s.id WHERE a.workspace_id=? ORDER BY coalesce(a.published_at,a.discovered_at) DESC LIMIT 100""", (self.ws,))
        for row in articles: row["is_read"] = bool(row["is_read"])
        return {"subscriptions":subscriptions,"articles":articles}

    def article(self, identifier, mark_read=True):
        row = self.store.one("""SELECT a.*,s.title AS source_title FROM news_articles a JOIN news_subscriptions s ON a.subscription_id=s.id WHERE a.id=? AND a.workspace_id=?""", (identifier,self.ws))
        if not row: raise Failure("VALIDATION_ERROR", "الخبر غير موجود في مساحة العمل.")
        if mark_read:
            with self.db: self.db.execute("UPDATE news_articles SET is_read=1 WHERE id=? AND workspace_id=?", (identifier,self.ws))
            row["is_read"] = True
        return row

    async def add(self, payload, sync=True):
        try:
            url, feed, kind = normalize_subscription(payload.get("url", ""), payload.get("kind", "auto"))
            interval = self._interval(payload.get("interval_minutes", 60))
        except NewsError as error: raise Failure("VALIDATION_ERROR", str(error)) from None
        existing = self.store.one("SELECT id FROM news_subscriptions WHERE workspace_id=? AND url=?", (self.ws,url))
        if existing: return existing["id"]
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
            rows = self.store.rows("SELECT * FROM news_subscriptions WHERE workspace_id=? AND enabled=1" + (" AND id=?" if identifier else ""), (self.ws,identifier) if identifier else (self.ws,))
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
                        existing = self.store.one("SELECT id FROM news_articles WHERE subscription_id=? AND (url=? OR guid=?) LIMIT 1", (row["id"],entry["url"],entry["guid"]))
                        if existing:
                            # Existing unread/read state and body remain; a feed refresh is not a new article.
                            self.db.execute("UPDATE news_articles SET title=?,summary=?,published_at=coalesce(?,published_at) WHERE id=?", (entry["title"],entry["summary"],entry["published_at"],existing["id"]))
                        else:
                            self.db.execute("INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary) VALUES(?,?,?,?,?,?,?,?,?)", (uid(),self.ws,row["id"],entry["guid"],entry["title"],entry["url"],entry["published_at"],now(),entry["summary"]))
                        if entry.get("media_only"):
                            # Never download or pretend to transcribe an enclosure.
                            self.db.execute("UPDATE news_articles SET text=?,body_status='media_summary' WHERE subscription_id=? AND guid=?", (entry["summary"],row["id"],entry["guid"]))
                    self.db.execute("UPDATE news_subscriptions SET feed_url=?,title=?,etag=?,last_modified=? WHERE id=?", (response["url"],title if row["title"] == urlsplit(row["url"]).hostname and title else row["title"],response["headers"].get("etag"),response["headers"].get("last-modified"),row["id"]))
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
        eligibility = "body_status!='media_summary'" if refresh_full else "body_status NOT IN ('full','media_summary') AND body_attempts<3"
        rows = self.store.rows("SELECT * FROM news_articles WHERE subscription_id=? AND " + eligibility + " ORDER BY discovered_at DESC LIMIT 50", (identifier,))
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
                except asyncio.CancelledError: raise
                except Exception: pass
                with self.db:
                    self.db.execute("UPDATE news_articles SET text=?,body_status=?,body_attempts=body_attempts+1,last_body_attempt=? WHERE id=?", (text,status,now(),row["id"]))
        await asyncio.gather(*(fetch_article(row) for row in rows))

    async def poll(self):
        while True:
            try: await self.sync()
            except asyncio.CancelledError: raise
            except Exception: pass
            await asyncio.sleep(60)
