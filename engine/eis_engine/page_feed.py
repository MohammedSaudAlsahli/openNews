"""Bounded discovery of article links in public, server-rendered listing pages.

No browser runtime, script execution, model calls, or crawling of pagination.
Only article cards are accepted; navigation and cross-origin links are excluded.
"""
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from lxml import html
from .feed_parser import date_value
from .news_urls import MAX_BYTES, NewsError, canonical_url


def parse_page(body, base):
    if len(body) > MAX_BYTES:
        raise NewsError('صفحة المصدر أكبر من الحد المسموح.')
    tree = html.fromstring(body, parser=html.HTMLParser(no_network=True, remove_comments=True))
    for node in tree.xpath('//script|//style|//noscript|//nav|//footer|//header|//aside|//form'):
        node.drop_tree()
    title = ' '.join(tree.xpath('//title/text()'))[:300]
    origin = urlsplit(base)
    entries = {}
    for anchor in tree.xpath('//a[@href]')[:2000]:
        href = anchor.get('href', '')
        if not href or href.startswith(('#', '?')): continue
        try:
            url = canonical_url(urljoin(base, href))
        except NewsError: continue
        parts = urlsplit(url)
        if parts.netloc != origin.netloc or parts.path.rstrip('/') == origin.path.rstrip('/'): continue
        segments = set(parts.path.lower().strip('/').split('/'))
        if segments & {'tag','tags','category','categories','author','authors','page','login','signup'}: continue
        headings = anchor.xpath('.//h2|.//h3|.//h4')
        parent = anchor.getparent()
        if not headings and parent is not None and parent.tag in {'h2','h3','h4'}: headings = [parent]
        cards = anchor.xpath('ancestor::article[1]')
        if not headings and not cards: continue
        # Headings are preferred over card text, which can contain dates and excerpts.
        label = ' '.join(' '.join((headings[0] if headings else anchor).itertext()).split())[:500]
        if len(label) < 8 or label.lower() in {'read more', 'read article', 'learn more', 'view all articles'}: continue
        query = urlencode([(k,v) for k,v in parse_qsl(parts.query, keep_blank_values=True)
                           if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}])
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, query, ''))
        card = cards[0] if cards else anchor
        times = card.xpath('.//time/@datetime')
        published = date_value(times[0]) if times else None
        # Some publishers expose a plain, fully specified date instead of <time>.
        if not published:
            for text in card.xpath('.//p/text()'):
                try:
                    published = datetime.strptime(text.strip(), '%B %d, %Y').replace(tzinfo=timezone.utc).isoformat()
                    break
                except ValueError: pass
        entries.setdefault(url, {'guid':url,'url':url,'title':label,'published_at':published,
                                 'summary':'','reader':{},'full_text':'','media_only':False})
        if len(entries) >= 30: break
    if not entries:
        raise NewsError('لم نعثر على روابط مقالات واضحة. قد تحتاج الصفحة JavaScript أو تمنع القراءة؛ جرّب رابط صفحة المدونة أو RSS.')
    return title, list(entries.values())
