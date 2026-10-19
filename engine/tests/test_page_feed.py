import asyncio
import pytest
from eis_engine.page_feed import parse_page
from eis_engine.news_urls import NewsError
from eis_engine.news import NewsManager
from eis_engine.storage import Store
from test_news import ARTICLE, result

PAGE=b'''<!doctype html><html><head><title>Model tests</title></head><body>
<nav><a href="/account"><h2>Account settings</h2></a></nav>
<a href="/articles/model-a?utm_source=test"><h3>Testing model A</h3><p>October 16, 2026</p></a>
<a href="/articles/model-a"><h3>Testing model A</h3></a>
<a href="https://other.example/post"><h3>Outside sponsored content</h3></a>
<a href="/tags/ai"><h3>Artificial Intelligence</h3></a>
<script><a href="/bad"><h2>Injected article</h2></a></script>
</body></html>'''

def test_listing_filters_navigation_external_tracking_and_duplicates():
    title, items=parse_page(PAGE,'https://publisher.example/articles')
    assert title=='Model tests' and len(items)==1
    assert items[0]['url']=='https://publisher.example/articles/model-a'
    assert items[0]['published_at'].startswith('2026-10-16')
    assert items[0]['summary']=='' and items[0]['full_text']==''


def test_unknown_date_not_invented_and_heading_wrapping_link_supported():
    _,items=parse_page(b'<html><h2><a href="/post">A new model report</a></h2></html>','https://publisher.example/blog')
    assert items[0]['published_at'] is None
    with pytest.raises(NewsError): parse_page(b'<html><a href="/login">Log in</a></html>','https://publisher.example/blog')


def test_page_sync_persists_articles_and_only_adds_new_links(tmp_path):
    store=Store(tmp_path/'workspace')
    page=PAGE
    async def fetch(url,headers=None):
        if url=='https://publisher.example/articles': return result(url,page,headers={'content-type':'text/html'})
        return result(url,ARTICLE,headers={'content-type':'text/html'})
    news=NewsManager(store,fetch)
    identifier=asyncio.run(news.add({'url':'https://publisher.example/articles','kind':'webpage'}))
    assert news.snapshot()['subscriptions'][0]['status']=='ready'
    assert len(news.list_articles({})['articles'])==1
    article=news.list_articles({})['articles'][0]
    news.article(article['id'])
    asyncio.run(news.sync(identifier))
    assert len(news.list_articles({})['articles'])==1
    assert news.article(article['id'],False)['is_read']
    page=PAGE.replace(b'</body>',b'<a href="/articles/model-b"><h3>Testing model B</h3></a></body>')
    asyncio.run(news.sync(identifier))
    assert len(news.list_articles({})['articles'])==2
    row=store.one('SELECT * FROM news_subscriptions WHERE id=?',(identifier,))
    assert row['interval_minutes']==5
    page=b'<html>Login required</html>'
    asyncio.run(news.sync(identifier))
    assert news.snapshot()['subscriptions'][0]['status']=='error'
    assert len(news.list_articles({})['articles'])==2
    store.close()


def test_auto_prefers_advertised_feed_and_reuses_304(tmp_path):
    from test_news import RSS
    store=Store(tmp_path/'workspace'); calls=[]
    async def fetch(url, headers=None):
        calls.append(url)
        if url.endswith('/blog'):
            return result(url,b'<html><head><link rel="alternate" type="application/rss+xml" href="/feed"/></head></html>')
        if url.endswith('/feed'):
            return result(url,RSS) if calls.count(url)==1 else result(url,b'',status=304)
        return result(url,ARTICLE)
    news=NewsManager(store,fetch)
    identifier=asyncio.run(news.add({'url':'https://publisher.example/blog'}))
    asyncio.run(news.sync(identifier))
    assert calls.count('https://publisher.example/blog')==1
    assert len(news.list_articles({})['articles'])==1
    store.close()
