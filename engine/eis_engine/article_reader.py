"""Structured, image-aware reading content, separate from model evidence text."""
import re
from itertools import islice
from urllib.parse import urljoin
from lxml import html
from trafilatura import extract
from .news import MAX_TEXT, MarkdownSummary, canonical_url, NewsError, plain, safe_content_link

MAX_IMAGES = 30
MARKER = 'https://openstudio.invalid/reader-image/'


def image_url(value, base):
    try:
        # Image requests use the same pinned public-network transport as feeds.
        return canonical_url(urljoin(base, (value or '').strip())) if value else None
    except (NewsError, ValueError):
        return None


def image_source(node, base):
    for key in ('data-src', 'data-original', 'data-lazy-src', 'src'):
        value = image_url(node.get(key), base)
        if value:
            return value
    for key in ('data-srcset', 'srcset'):
        candidates = re.split(r',\s+(?=\S)', node.get(key, '').strip())
        for candidate in reversed(candidates):
            if candidate.strip():
                value = image_url(candidate.strip().split()[0], base)
                if value: return value
    parent = next(iter(node.iterancestors('picture')), None)
    if parent is not None and node.tag != 'source':
        for source in parent.xpath('.//source'):
            value = image_source(source, base)
            if value: return value
    return None


def prepare_tree(body, base):
    tree = html.fromstring(body, parser=html.HTMLParser(no_network=True, remove_comments=True))
    for node in tree.xpath('//script|//style|//iframe|//object|//embed|//base|//svg|//noscript'):
        node.drop_tree()
    for node in tree.xpath('//a[@href]'):
        target = safe_content_link(node.get('href'), base)
        if target: node.set('href', target)
        else: node.attrib.pop('href', None)
    # Image-only links are lightbox controls, not prose links. Unwrap them
    # before splitting Markdown into text and image blocks.
    for anchor in list(tree.xpath('//a[.//img]')):
        if not anchor.text_content().strip():
            anchor.drop_tag()
    images = []
    seen = set()
    for node in tree.xpath('//img'):
        url = image_source(node, base)
        decorative = bool(re.search(r'(^|[ _-])(emoji|avatar|icon)([ _-]|$)', node.get('class', ''), re.I)) or '/images/core/emoji/' in (url or '')
        tiny = any(re.fullmatch(r'\d+', node.get(k, '')) and int(node.get(k)) <= 2 for k in ('width', 'height'))
        if not url or tiny or decorative or url in seen or len(images) >= MAX_IMAGES:
            node.drop_tree(); continue
        seen.add(url)
        figure = next(iter(node.iterancestors('figure')), None)
        captions = figure.xpath('.//figcaption') if figure is not None else []
        if not captions:
            for parent in islice(node.iterancestors(), 4):
                if len(parent.xpath('.//img')) == 1 and parent.xpath('.//figcaption'):
                    captions = parent.xpath('.//figcaption'); break
        caption = plain(captions[0].text_content())[:1000] if captions else ''
        images.append({'type':'image', 'id':str(len(images)), 'url':url,
                       'alt':plain(node.get('alt', ''))[:1000], 'caption':caption})
        node.attrib.clear()
        node.set('src', MARKER + str(len(images) - 1) + '.jpg')
        node.set('alt', 'image')
        # Captions belong to their figure block, not a second prose paragraph.
        for caption_node in captions:
            if caption_node.getparent() is not None: caption_node.drop_tree()
    return tree, images


def blocks_from_markdown(markdown, images):
    blocks, used = [], set()
    cursor = 0
    for match in re.finditer(r'!\[[^\]]*\]\(' + re.escape(MARKER) + r'(\d+)\.jpg\)', markdown):
        prefix = markdown[cursor:match.start()].strip()
        if prefix: blocks.append({'type':'text', 'text':prefix})
        index = int(match[1])
        if index < len(images) and index not in used:
            blocks.append(images[index]); used.add(index)
        cursor = match.end()
    suffix = markdown[cursor:].strip()
    if suffix: blocks.append({'type':'text', 'text':suffix})
    return blocks


class ReaderSummary(MarkdownSummary):
    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.ignored:
            source = dict(attrs).get('src', '')
            if source.startswith(MARKER): self.parts.append('\n\n![image](' + source + ')\n\n')
        else: super().handle_starttag(tag, attrs)


def preserve_special_blocks(tree, base):
    """Protect preformatted/quoted content from article extraction whitespace folding."""
    replacements = {}
    for node in list(tree.xpath('//pre|//blockquote')):
        if node.getparent() is None or any(p.tag in {'pre','blockquote'} for p in node.iterancestors()):
            continue
        if node.tag == 'pre':
            value = node.text_content().strip('\n')
            fence = '`' * max(3, max((len(m[0])+1 for m in re.finditer(r'`+',value)), default=3))
            classes = ' '.join(element.get('class', '') for element in [node, *node.iterdescendants('code')])
            match = re.search(r'(?:language-|lang-)([A-Za-z0-9_+.-]+)', classes)
            language = match[1] if match else ''
            value = fence + language + '\n' + value + '\n' + fence
        else:
            parser = ReaderSummary(base)
            parser.feed(html.tostring(node,encoding='unicode'))
            value = ''.join(parser.parts).strip().removeprefix('> ').strip()
            value = '\n'.join('> '+line for line in value.splitlines())
        token = 'OPENSTUDIOPRESERVEDBLOCK' + str(len(replacements)) + 'END'
        replacements[token] = value
        replacement = html.Element('p')
        replacement.text = token
        replacement.tail = node.tail
        node.getparent().replace(node,replacement)
    return replacements


def extract_reader(body, base, fragment=False):
    tree, images = prepare_tree(body, base)
    special = preserve_special_blocks(tree, base)
    if fragment:
        parser = ReaderSummary(base)
        parser.feed(html.tostring(tree, encoding='unicode'))
        markdown = ''.join(parser.parts)[:MAX_TEXT]
    else:
        markdown = extract(tree, url=base, output_format='markdown', include_formatting=True,
                           include_links=True, include_images=True, include_comments=False,
                           include_tables=True, favor_precision=True) or ''
    for token, value in special.items():
        markdown = markdown.replace(token, value)
    blocks = blocks_from_markdown(markdown[:MAX_TEXT], images)
    # Prefer the publisher's explicit editorial cover over inline logos/banners.
    meta = tree.xpath('//meta[@property="og:image"]/@content | //meta[@name="twitter:image"]/@content')
    cover = next((url for value in meta if (url := image_url(value, base))), None)
    if cover:
        existing = next((b for b in blocks if b.get('url') == cover), None)
        if existing:
            blocks.remove(existing)
            blocks.insert(0, existing)
        else:
            blocks.insert(0, {'type':'image','id':'cover','url':cover,'alt':'','caption':''})
    authors = tree.xpath('//meta[@name="author"]/@content')
    return {'version':3, 'blocks':blocks, 'author':plain(authors[0])[:300] if authors else '',
            'origin':'feed' if fragment else 'article'}
