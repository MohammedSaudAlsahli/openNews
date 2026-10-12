"""Read-only RSS.mobi discovery. Following uses the normal news subscription path.

API contract: https://github.com/dstengine/rss-mobi/blob/main/src/pages/api/v1/feeds/index.ts
Only catalog metadata and explicit search terms leave this module; no workspace content.
"""
import asyncio
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit, parse_qs

from .contracts import Failure
from .news import canonical_url, fetch_public, NewsError

ENDPOINT = "https://rss.mobi/api/v1/feeds"
TTL = 3600
MAX_STALE = 7 * 86400
PAGE_SIZE = 30
MAX_PAGES = 40
UNAVAILABLE = "تعذّر تحميل دليل RSS.mobi. أعد المحاولة أو أضف رابط المصدر مباشرة."


def cursor(value):
    if not value:
        return ""
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Invalid cursor")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Cursor needs timezone")
    return value


def normalize(payload, current_cursor=""):
    if not isinstance(payload, dict) or not isinstance(payload.get("feeds"), list) or len(payload["feeds"]) > PAGE_SIZE:
        raise ValueError("Invalid directory page")
    feeds, seen = [], set()
    for row in payload["feeds"]:
        if not isinstance(row, dict) or row.get("status") != "active" or row.get("format") not in {"rss", "atom", "rdf"}:
            continue
        url = row.get("url")
        title = row.get("title")
        if not isinstance(url, str) or len(url) > 2048 or not isinstance(title, str) or not title.strip():
            continue
        try:
            url = canonical_url(url)
        except (NewsError, ValueError):
            continue
        if url in seen:
            continue
        seen.add(url)
        publisher = row.get("siteUrl")
        try:
            publisher = canonical_url(publisher) if isinstance(publisher, str) and len(publisher) <= 2048 else ""
        except (NewsError, ValueError):
            publisher = ""
        description = row.get("description")
        description = description[:2000] if isinstance(description, str) else ""
        lang = row.get("lang")
        lang = lang.lower() if isinstance(lang, str) and re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", lang) else "und"
        tags = row.get("tags")
        tags = [tag[:80] for tag in tags[:20] if isinstance(tag, str)] if isinstance(tags, list) else []
        feeds.append({"id": "rssmobi-" + hashlib.sha256(url.encode()).hexdigest()[:24],
                      "title": title.strip()[:300], "url": url, "publisher_url": publisher,
                      "category": tags[0] if tags else "general", "tags": tags,
                      "language": lang, "description_ar": description, "description_en": description,
                      "verified_at": ""})
    next_cursor = ""
    if payload.get("next"):
        # Never follow a URL supplied by the directory. Extract only a validated timestamp.
        if not isinstance(payload["next"], str) or len(payload["next"]) > 2048:
            raise ValueError("Invalid next page")
        target = urlsplit(payload["next"])
        if target.scheme or target.netloc or target.path != "/api/v1/feeds":
            raise ValueError("Invalid next page")
        values = parse_qs(target.query).get("before", [])
        if len(values) != 1:
            raise ValueError("Missing cursor")
        next_cursor = cursor(values[0])
        if next_cursor == current_cursor:
            raise ValueError("Repeated cursor")
    return {"feeds": feeds, "next_cursor": next_cursor}


class FeedDirectory:
    def __init__(self, store):
        self.store = store
        self.fetch = fetch_public
        self.lock = asyncio.Lock()
        store.db.execute("""CREATE TABLE IF NOT EXISTS feed_directory_cache (
            workspace_id TEXT NOT NULL, request TEXT NOT NULL, fetched REAL NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(workspace_id, request))""")
        store.db.commit()

    async def search(self, params):
        query = params.get("query", "")
        tag = params.get("category", "all")
        if not isinstance(query, str) or len(query) > 100 or not isinstance(tag, str) or not re.fullmatch(r"[a-z0-9-]{1,80}", tag):
            raise Failure("VALIDATION_ERROR", "أدخل بحثًا لا يتجاوز 100 حرف وتصنيفًا صالحًا.")
        try:
            before = cursor(params.get("cursor", ""))
        except (ValueError, TypeError):
            raise Failure("VALIDATION_ERROR", "صفحة دليل المصادر غير صالحة.") from None
        values = {"limit": PAGE_SIZE}
        if query.strip(): values["q"] = query.strip()
        if tag != "all": values["tag"] = tag
        if before: values["before"] = before
        request = urlencode(values)
        async with self.lock:
            row = self.store.db.execute("SELECT fetched,payload FROM feed_directory_cache WHERE workspace_id=? AND request=?", (self.store.workspace, request)).fetchone()
            cached, fetched = None, 0
            if row:
                try:
                    fetched, cached = float(row[0]), json.loads(row[1])
                    if not isinstance(cached, dict) or not isinstance(cached.get("feeds"), list): cached = None
                except (ValueError, TypeError):
                    cached = None
            age = time.time() - fetched
            if cached is not None and 0 <= age < TTL and params.get("refresh") is not True:
                return self.result(cached, fetched, cached=True)
            try:
                response = await self.fetch(ENDPOINT + "?" + request)
                if response["status"] != 200:
                    raise ValueError("Directory unavailable")
                page = normalize(json.loads(response["body"]), before)
            except (NewsError, ValueError, TypeError, KeyError, OSError):
                if cached is not None and 0 <= age < MAX_STALE:
                    return self.result(cached, fetched, cached=True, stale=True)
                raise Failure("DIRECTORY_UNAVAILABLE", UNAVAILABLE) from None
            fetched = time.time()
            with self.store.db:
                self.store.db.execute("INSERT OR REPLACE INTO feed_directory_cache VALUES(?,?,?,?)", (self.store.workspace, request, fetched, json.dumps(page)))
                self.store.db.execute("DELETE FROM feed_directory_cache WHERE workspace_id=? AND request NOT IN (SELECT request FROM feed_directory_cache WHERE workspace_id=? ORDER BY fetched DESC LIMIT ?)", (self.store.workspace, self.store.workspace, MAX_PAGES))
            return self.result(page, fetched)

    @staticmethod
    def result(page, fetched, cached=False, stale=False):
        return {**page, "provider": "RSS.mobi", "fetched_at": datetime.fromtimestamp(fetched, timezone.utc).isoformat(timespec="seconds"), "cached": cached, "stale": stale}
