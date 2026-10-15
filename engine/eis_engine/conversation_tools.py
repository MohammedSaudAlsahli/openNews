"""Read-only Agno conversation tools; RSS is the library, web is optional research."""
import asyncio
import json
from urllib.parse import urlsplit

from .news_urls import canonical_url, NewsError
from .storage import uid


class ConversationTools:
    def __init__(self, news, evidence, notify, allow_library=True, allow_web=True, searcher=None):
        self.news = news
        self.evidence = {item['id']: item for item in evidence}
        self.notify = notify
        self.allow_library, self.allow_web = allow_library, allow_web
        self.searcher = searcher
        self.calls = 0
        self.saved_searches = {}

    @property
    def functions(self):
        result = [self.search_saved_articles, self.read_saved_article] if self.allow_library else []
        if self.allow_web: result += [self.search_web, self.read_web_page]
        return result

    def begin(self, kind, detail):
        self.calls += 1
        if self.calls > 10: return False
        self.notify(kind, detail[:180])
        return True

    def remember(self, item):
        previous = next((value for value in self.evidence.values() if value['url'] == item['url']), None)
        if previous:
            item = {**item, 'id': previous['id']}
        if len(self.evidence) >= 60 and not previous: return None
        self.evidence[item['id']] = item
        return item

    @staticmethod
    def output(value):
        return json.dumps(value, ensure_ascii=False)

    async def search_saved_articles(self, query: str = '', from_date: str = '', to_date: str = '') -> str:
        """Search the user's saved RSS articles first. Empty query lists recent stories across sources.

        Args:
            query: Topic, company, or natural-language description in Arabic or English.
            from_date: Optional inclusive publication date YYYY-MM-DD, e.g. 2026-08-05.
            to_date: Optional inclusive publication date YYYY-MM-DD. Omit both dates to search all saved history.
        """
        key = (query.strip().casefold(), from_date, to_date)
        if self.allow_library and key in self.saved_searches: return self.saved_searches[key]
        if not self.allow_library or not self.begin('library', query or 'RSS'): return self.output({'error': 'Tool limit reached or library disabled'})
        try:
            knowledge = getattr(self.news, 'knowledge', None)
            if knowledge is None:
                from .news_knowledge import NewsKnowledge
                knowledge = self.news.knowledge = NewsKnowledge(self.news)
            found = await knowledge.search(query, from_date, to_date)
            for item in found: self.remember(item)
            result = self.output({'articles': found, 'matched_at_least': len(found),
                                'scope': 'Saved RSS library only. If results do not answer the question, use search_web.'})
            self.saved_searches[key] = result
            return result
        except (ValueError, TypeError):
            return self.output({'error': 'Use valid YYYY-MM-DD dates.'})

    async def read_saved_article(self, article_id: str) -> str:
        """Read the full text of an RSS article returned by search_saved_articles or supplied in context."""
        if not self.allow_library or not self.begin('reading', self.evidence.get(article_id, {}).get('title', 'RSS')): return self.output({'error': 'Tool limit reached or library disabled'})
        try:
            row = self.news.article(article_id, mark_read=False)
            self.notify('reading', row['title'])
            if row['body_status'] not in {'full', 'media_summary'}: row = await self.news.reader(article_id)
            item = {key: row.get(key) for key in ('id', 'title', 'url', 'source_title', 'source_kind', 'published_at', 'discovered_at', 'body_status')}
            item['text'] = (row.get('text') or row.get('summary') or '')[:16000]
            return self.output(self.remember(item))
        except Exception:
            return self.output({'error': 'Could not read this saved article. Do not invent its contents.'})

    async def search_web(self, query: str) -> str:
        """Search web engines through Agno for missing evidence or when the user explicitly asks to search online.
        Search RSS first otherwise. Use date/company terms in the query for historical research; no fixed recency filter.
        Results are snippets, not full articles. Call read_web_page on the relevant primary sources before drawing conclusions.

        Args:
            query: A focused public search query. Never include private chat, credentials, or writing samples.
        """
        if not self.allow_web or not self.begin('web', query): return self.output({'error': 'Tool limit reached or web search disabled'})
        if not query.strip() or len(query) > 300: return self.output({'error': 'Use a query of 1 to 300 characters.'})
        try:
            if self.searcher is None:
                from agno.tools.websearch import WebSearchTools
                self.searcher = WebSearchTools(enable_news=False, fixed_max_results=6, timeout=12)
            raw = await asyncio.wait_for(asyncio.to_thread(self.searcher.web_search, query), timeout=25)
            results = []
            for hit in json.loads(raw)[:6]:
                try: url = canonical_url(hit.get('href') or hit.get('url') or '')
                except NewsError: continue
                item = self.remember({'id': uid(), 'url': url, 'title': str(hit.get('title') or url)[:500],
                    'source_title': urlsplit(url).hostname, 'published_at': None, 'origin': 'web',
                    'body_status': 'search_snippet', 'text': str(hit.get('body') or hit.get('description') or '')[:1800]})
                if item: results.append(item)
            return self.output({'results': results, 'note': 'Search snippets are unverified; read pages. Do not invent dates or pad requested counts.'})
        except Exception:
            return self.output({'error': 'Web search is temporarily unavailable. Say so; do not claim there are no relevant reports.'})

    async def read_web_page(self, url: str) -> str:
        """Read a public article from a web result, prior citation, or user-provided URL. Does not add an RSS subscription."""
        if not self.allow_web or not self.begin('reading', url): return self.output({'error': 'Tool limit reached or web search disabled'})
        try:
            from .article_reader import extract_reader
            address = canonical_url(url)
            response = await self.news.fetch(address, None)
            reader = await asyncio.to_thread(extract_reader, response['body'], response['url'])
            text = '\n\n'.join(block['text'] for block in reader['blocks'] if block.get('type') == 'text' and block.get('text'))
            if len(text.strip()) < 80: return self.output({'error': 'Full public text unavailable. Do not infer claims from the title.', 'url': address})
            previous = next((item for item in self.evidence.values() if item['url'] in {address, response['url']}), {})
            from lxml import html
            tree = html.fromstring(response['body'], parser=html.HTMLParser(no_network=True))
            title = (tree.xpath('//meta[@property="og:title"]/@content') or tree.xpath('//title/text()') or [previous.get('title', address)])[0]
            published = (tree.xpath('//meta[@property="article:published_time"]/@content') or [previous.get('published_at')])[0]
            from .feed_parser import date_value
            item = self.remember({**previous, 'id': previous.get('id') or uid(), 'url': address,
                'title': title[:500], 'source_title': urlsplit(response['url']).hostname,
                'published_at': date_value(published), 'body_status': 'full', 'text': text[:16000], 'origin': 'web'})
            self.notify('reading', title[:180])
            return self.output(item)
        except Exception:
            return self.output({'error': 'Could not retrieve this public page. Do not invent its content.'})
