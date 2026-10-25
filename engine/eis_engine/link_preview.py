"""Text-only reader previews. No inference, imports, read flags or remote embeds."""
import re
from urllib.parse import urlsplit, urlunsplit

from .contracts import Failure
from .news_urls import canonical_url, NewsError
from .summary_evidence import links_in


def normalized(address):
    parts = urlsplit(canonical_url(address))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))


async def preview(service, params):
    article = service.news.article(params.get('article_id'), mark_read=False)
    try:
        url = normalized(params.get('url', ''))
    except (NewsError, ValueError, TypeError):
        raise Failure('VALIDATION_ERROR', 'رابط غير صالح للمعاينة.')
    text = '\n'.join(b.get('text', '') for b in article['reader'].get('blocks', []) if b.get('type') == 'text')
    allowed = {normalized(article['url']), *links_in(text + '\n' + article['text'] + '\n' + article['summary'], article['url'])}
    if url not in allowed:
        raise Failure('VALIDATION_ERROR', 'المعاينة متاحة لروابط المقالة فقط.')
    # Prefer a saved article, even offline; never mark it read or enqueue a model.
    saved = service.store.one('SELECT title,text,summary,body_status FROM news_articles WHERE workspace_id=? AND url=?', (service.ws, url))
    if saved and (saved['text'] or saved['summary']):
        source = {'title': saved['title'], 'text': saved['text'] or saved['summary'],
                  'status': 'read', 'truncated': saved['body_status'] != 'full'}
        cached = True
    else:
        cached = bool(service.store.one('SELECT url FROM summary_web_cache WHERE workspace_id=? AND url=? AND checked>strftime(\'%s\',\'now\')-86400', (service.ws, url)))
        source = await service.news_digest.evidence.source(url)
    excerpt = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', source.get('text', ''))
    excerpt = re.sub(r'\s+', ' ', excerpt).strip()
    return {'url': url, 'title': source.get('title', ''), 'excerpt': excerpt[:1200],
            'status': source['status'], 'cached': cached,
            'truncated': bool(source.get('truncated') or len(excerpt) > 1200),
            'kind': 'post' if urlsplit(url).hostname in {'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'} and '/status/' in urlsplit(url).path else 'article'}
