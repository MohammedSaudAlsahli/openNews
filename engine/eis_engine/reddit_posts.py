"""Reddit post identity and authored content, separate from embedded destinations."""
import re
from urllib.parse import urlsplit
from .news_urls import canonical_url, NewsError


def post_url(value):
    try:
        url = canonical_url(value)
        parts = urlsplit(url)
        if parts.hostname in {'reddit.com', 'www.reddit.com', 'old.reddit.com'} and re.match(
            r'^/(?:r/[^/]+/)?comments/[A-Za-z0-9]+(?:/|$)', parts.path
        ):
            return url
    except (NewsError, ValueError, TypeError, AttributeError):
        pass
    return None


def saved_post_url(row):
    reader = row.get('reader', {})
    for value in (reader.get('source_url'), row.get('url')):
        if url := post_url(value): return url
    # Prefer the feed's comments footer over another Reddit post quoted by the
    # author. Some old conflated rows also retained the wrong t3 identifier.
    summary = row.get('summary', '')
    footer = re.findall(r'\[(?:\\\[)?comments(?:\\\])?\]\((https?://[^\s)]+)\)', summary, re.I)
    if '<a' in summary:
        from lxml import html
        tree = html.fragment_fromstring(summary, create_parent='div')
        footer += [a.get('href') for a in tree.xpath('.//a[@href]') if a.text_content().strip().lower() == '[comments]']
    for value in reversed(footer):
        if url := post_url(value): return url
    if match := re.fullmatch(r't3_([A-Za-z0-9]+)', row.get('guid', '')):
        for value in re.findall(r'''https?://[^\s<>()\[\]"']+''', summary):
            if (url := post_url(value)) and re.search(r'/comments/'+re.escape(match[1])+r'(?:/|$)',url):
                return url
        return 'https://www.reddit.com/comments/' + match[1] + '/'
    return None


def authored_markup(value):
    from lxml import html
    tree = html.fragment_fromstring(value or '<p></p>', create_parent='div')
    nodes = tree.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " md ")]')
    # Reddit's outer table is a thumbnail/submitter wrapper, not an author table.
    # Selecting .md retains the author's own tables, code, images and links.
    if nodes:
        body = ''.join(html.tostring(n, encoding='unicode', with_tail=False) for n in nodes)
        links = {u for n in nodes for u in n.xpath('.//a/@href')}
        for link in tree.xpath('//a[@href]'):
            if link.text_content().strip() == '[link]' and link.get('href') not in links:
                body += '<p>' + html.tostring(link, encoding='unicode', with_tail=False) + '</p>'
        return '<article>' + body + '</article>'
    return value


def mark_reader(reader, url):
    reader.update(origin='reddit', source_url=url)
    return reader
