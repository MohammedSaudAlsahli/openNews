"""RSS/Atom discovery and bounded article text extraction."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
from .news_urls import MAX_BYTES, MAX_TEXT, NewsError, canonical_url

class HTMLInfo(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.feeds, self.links, self.icons = [], [], [], []
        self.ignored = 0
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"script","style","noscript"}: self.ignored += 1
        if tag == "link" and "alternate" in attributes.get("rel", "").lower().split() and attributes.get("type", "").lower() in {"application/rss+xml","application/atom+xml"}:
            self.feeds.append(attributes.get("href", ""))
        if tag == "link" and "icon" in attributes.get("rel", "").lower().split():
            self.icons.append(attributes.get("href", ""))
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
        full_markup = node_markup(entry, {"encoded"}) or node_markup(entry, {"content"})
        summary = node_markup(entry, {"description", "summary"}) or full_markup
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
        description = summary_markdown(summary, link)
        # Hacker News descriptions often contain only a link to its comment
        # thread. That link is not an excerpt of the publisher's article.
        if urlsplit(base).hostname == "news.ycombinator.com" and re.fullmatch(
            r"\[Comments\]\(https://news\.ycombinator\.com/item\?id=\d+\)", description, re.I
        ):
            description = ""
        from .article_reader import extract_reader
        try: reader = extract_reader((full_markup or summary) if description else '<p></p>', link, fragment=True)
        except Exception: reader = {}
        # RSS media/enclosure thumbnails may exist outside the HTML description.
        # An explicit feed thumbnail is the publisher's cover, even when the
        # article body begins with a newsletter logo or banner.
        for media in entry.iter():
            if local_name(media.tag) in {'thumbnail', 'content', 'enclosure', 'image'}:
                media_type = media.get('type', '')
                if local_name(media.tag) in {'content', 'enclosure'} and not (media_type.startswith('image/') or media.get('medium') == 'image'): continue
                from .article_reader import image_url
                cover = image_url(media.get('url') or media.get('href'), link)
                if cover:
                    blocks = reader.setdefault('blocks', [])
                    blocks[:] = [b for b in blocks if b.get('url') != cover]
                    blocks.insert(0, {'type':'image','id':'feed-cover','url':cover,'alt':'','caption':''})
                    break
        full_text = summary_markdown(full_markup, link) if full_markup and not media_only else ""
        result.append({"full_text":full_text if len(plain(full_markup)) >= 120 else "", "reader":reader,"guid":guid,"title":plain(node_text(entry,{"title"}))[:500] or "خبر بلا عنوان", "url":link,
                       "published_at":date_value(node_text(entry,{"pubdate","published","date"})), "summary":("وصف الحلقة من الخلاصة، وليس تفريغًا للصوت أو الفيديو.\n\n" if media_only else "") + description, "media_only":media_only})
    return title, result


def normalize_subscription(url, kind="auto"):
    if isinstance(url, str):
        url = url.strip()
        if kind == "reddit" and re.fullmatch(r"(?:r/)?[A-Za-z0-9_]{2,40}", url):
            url = "https://www.reddit.com/r/" + url.removeprefix("r/") + "/"
    canonical = canonical_url(url)
    p = urlsplit(canonical)
    if p.hostname in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        raise NewsError("أضف رابط RSS الذي توفره خدمة التحويل، وليس رابط حساب X.")
    if kind in {"x_rss", "reddit_rss"}:
        if p.hostname in {"reddit.com", "www.reddit.com", "old.reddit.com"}:
            raise NewsError("اختر Reddit المباشر لرابط المجتمع، أو أدخل رابط RSS من خدمة التحويل.")
        return canonical, canonical, kind
    is_reddit = p.hostname in {"reddit.com", "www.reddit.com", "old.reddit.com"}
    if kind == "reddit" or is_reddit:
        match = re.match(r"^/r/([A-Za-z0-9_]{2,40})(?:/.*)?$", p.path)
        if not is_reddit or not match: raise NewsError("أدخل رابط مجتمع Reddit مثل https://www.reddit.com/r/science/.")
        name = match.group(1)
        return f"https://www.reddit.com/r/{name.lower()}/", f"https://www.reddit.com/r/{name}/new/.rss", "reddit"
    if kind not in {"auto", "rss", "webpage"}: raise NewsError("نوع مصدر الأخبار غير مدعوم.")
    return canonical, canonical, "webpage" if kind == "webpage" else "rss"
