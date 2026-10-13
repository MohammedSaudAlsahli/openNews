"""Bounded public news discovery for requests that explicitly need current reporting.

Search results are leads, not verified facts. Only successfully read public
articles become evidence; the model still has to compare them critically.
"""
import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote, urlsplit

from .feed_parser import parse_feed
from .news_urls import NewsError, canonical_url
from .storage import uid


STOPWORDS = {"آخر", "اخر", "خبر", "أخبار", "اخبار", "عشان", "انزله", "أنزله", "انزلها", "أنزلها", "تويتر",
             "اكس", "للنشر", "عطني", "ابي", "أبي", "عن", "في", "من", "وش", "ايش",
             "latest", "news", "about", "post", "twitter", "the", "for", "and"}


def research_query(message):
    words = re.findall(r"[A-Za-z][A-Za-z0-9.+-]*|[\u0600-\u06ff]{3,}", message)
    terms = [word for word in words if word.casefold() not in STOPWORDS]
    latin = [term for term in terms if term[0].isascii()]
    # A named product in a mixed Arabic/English request is a much sharper
    # search than stray Arabic request verbs with inconsistent spelling.
    return " ".join((latin or terms)[:5])[:100]


def publisher_url(search_link):
    """Bing RSS wraps the publisher URL; never send its tracking link as evidence."""
    parts = urlsplit(search_link)
    if parts.hostname in {"bing.com", "www.bing.com"} and parts.path == "/news/apiclick.aspx":
        wrapped = parse_qs(parts.query).get("url", [""])[0]
        return canonical_url(wrapped)
    return canonical_url(search_link)


async def discover(fetch, query, days=7):
    if not query: return []
    endpoint = "https://www.bing.com/news/search?q=" + quote(query, safe="") + "&format=rss&qft=sortbydate"
    response = await fetch(endpoint, None)
    _, entries = parse_feed(response["body"], response["url"])
    now = datetime.now(timezone.utc)
    candidates = []
    seen = set()
    for entry in entries:
        try:
            url = publisher_url(entry["url"])
            stamp = datetime.fromisoformat((entry.get("published_at") or "").replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp > now or (now - stamp).days > days:
                continue
            if url in seen: continue
            seen.add(url)
            candidates.append({**entry, "url": url})
        except (NewsError, ValueError, TypeError):
            continue
    candidates.sort(key=lambda item: item["published_at"], reverse=True)
    return candidates[:8]


async def read_candidates(fetch, candidates, limit=8):
    from .article_reader import extract_reader
    async def read(item):
        try:
            response = await fetch(item["url"], None)
            if "html" not in response["headers"].get("content-type", "text/html").lower(): return None
            reader = await asyncio.to_thread(extract_reader, response["body"], response["url"])
            body = "\n\n".join(block["text"] for block in reader["blocks"] if block.get("type") == "text" and block.get("text"))
            if len(body.strip()) < 100: return None
            return {"id":uid(), "title":item["title"], "url":response["url"],
                    "source_title":urlsplit(response["url"]).hostname or "", "published_at":item["published_at"],
                    "discovered_at":datetime.now(timezone.utc).isoformat(), "body_status":"full",
                    "text":body[:8000], "prepared_summary":"", "origin":"web"}
        except Exception:
            # A single publisher's malformed page must not abort the whole
            # research request. Cancellation still propagates on Python 3.11+.
            return None
    read_results = await asyncio.gather(*(read(item) for item in candidates[:limit]))
    return [item for item in read_results if item][:4]


async def official_openai_candidates(fetch):
    """Supplement third-party discovery with the publisher's own dated feed."""
    try:
        response = await fetch("https://openai.com/news/rss.xml", None)
        _, entries = parse_feed(response["body"], response["url"])
    except (NewsError, ValueError, OSError):
        return []
    now = datetime.now(timezone.utc)
    candidates = []
    for item in entries:
        try:
            stamp = datetime.fromisoformat((item.get("published_at") or "").replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp > now or (now - stamp).days > 14: continue
            if "chatgpt" not in (item["title"] + " " + item["summary"]).casefold(): continue
            candidates.append(item)
        except (ValueError, TypeError):
            continue
    candidates.sort(key=lambda item:item["published_at"], reverse=True)
    return candidates[:8]


async def research(fetch, message):
    query = research_query(message)
    if not query: return []
    try: candidates = await discover(fetch, query)
    except (NewsError, ValueError, OSError): candidates = []
    third_party = await read_candidates(fetch, candidates)
    if "chatgpt" not in query.casefold() and "openai" not in query.casefold(): return third_party
    official = await read_candidates(fetch, await official_openai_candidates(fetch))
    seen = {item["url"] for item in third_party}
    return third_party + [item for item in official if item["url"] not in seen][:4]
