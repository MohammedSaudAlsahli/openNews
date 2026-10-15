"""Complete read-only RSS.mobi OPML catalog, cached locally for search."""
import asyncio
import hashlib
import json
import re
import time
from datetime import datetime, timezone

import xml.etree.ElementTree as ElementTree

from .contracts import Failure
from .news import canonical_url, fetch_public, NewsError

TTL = 3600
MAX_STALE = 7 * 86400
PAGE_SIZE = 30
MAX_PAGES = 40
UNAVAILABLE = "تعذّر تحميل دليل RSS.mobi. أعد المحاولة أو أضف رابط المصدر مباشرة."


def normalize(payload):
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
    return {"feeds": feeds, "next_cursor": ""}


def parse_opml(body, category="all"):
    if len(body) > 4 * 1024 * 1024 or b"\x00" in body or re.search(br"<!\s*(DOCTYPE|ENTITY)", body, re.I):
        raise ValueError("Directory too large")
    try:
        root = ElementTree.fromstring(body)
    except (ElementTree.ParseError, ValueError) as exc:
        raise ValueError("Invalid directory XML") from exc
    if root.tag != "opml" or root.find("body") is None:
        raise ValueError("Invalid OPML directory")
    feeds, seen = [], set()
    for node in root.findall(".//outline"):
        if len(feeds) >= 10000:
            raise ValueError("Directory too large")
        url = node.get("xmlUrl")
        if not url:
            continue
        row = {"title": node.get("title") or node.get("text") or url,
               "url": url, "siteUrl": node.get("htmlUrl"), "status": "active",
               "format": "rss", "tags": [category] if category != "all" else []}
        for feed in normalize({"feeds": [row]})["feeds"]:
            if feed["url"] not in seen:
                feeds.append(feed)
                seen.add(feed["url"])
    return {"feeds": feeds, "next_cursor": ""}


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
        # The official complete OPML export avoids the failing paginated JSON API.
        # Search locally across the whole export, never just the first page.
        request = "opml-v1:" + tag
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
                return self.filtered_result(cached, fetched, query, cached=True)
            try:
                response = await self.fetch("https://rss.mobi/" + ("opml.xml" if tag == "all" else "tag/" + tag + "/opml.xml"))
                if response["status"] != 200:
                    raise ValueError("Directory unavailable")
                page = parse_opml(response["body"], tag)
            except (NewsError, ValueError, TypeError, KeyError, OSError):
                if cached is not None and 0 <= age < MAX_STALE:
                    return self.filtered_result(cached, fetched, query, cached=True, stale=True)
                raise Failure("DIRECTORY_UNAVAILABLE", UNAVAILABLE) from None
            fetched = time.time()
            with self.store.db:
                self.store.db.execute("INSERT OR REPLACE INTO feed_directory_cache VALUES(?,?,?,?)", (self.store.workspace, request, fetched, json.dumps(page)))
                self.store.db.execute("DELETE FROM feed_directory_cache WHERE workspace_id=? AND request NOT IN (SELECT request FROM feed_directory_cache WHERE workspace_id=? ORDER BY fetched DESC LIMIT ?)", (self.store.workspace, self.store.workspace, MAX_PAGES))
            return self.filtered_result(page, fetched, query)

    @classmethod
    def filtered_result(cls, page, fetched, query, **flags):
        terms = query.casefold().split()
        feeds = [f for f in page["feeds"] if all(term in (f["title"] + " " + f["url"]).casefold() for term in terms)]
        return cls.result({**page, "feeds": feeds, "total": len(page["feeds"])}, fetched, **flags)

    @staticmethod
    def result(page, fetched, cached=False, stale=False):
        return {**page, "provider": "RSS.mobi", "fetched_at": datetime.fromtimestamp(fetched, timezone.utc).isoformat(timespec="seconds"), "cached": cached, "stale": stale}
