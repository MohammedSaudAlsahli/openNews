import asyncio
import sqlite3
import pytest
from eis_engine.storage import Store
from eis_engine.news import NewsManager
from test_news import RSS, ARTICLE, result


def test_archive_survives_feed_removal_unsubscribe_restart_and_deduplicates(tmp_path):
    folder=tmp_path/'workspace'
    store=Store(folder)
    body=RSS
    async def fetch(url,headers=None):
        return result(url, ARTICLE,headers={'content-type':'text/html'}) if '/article' in url else result(url,body)
    news=NewsManager(store,fetch)
    first=asyncio.run(news.add({'url':'https://publisher.example/feed'}))
    article=news.list_articles({})['articles'][0]
    news.bookmark({'article_id':article['id'],'saved':True})
    second=asyncio.run(news.add({'url':'https://other.example/feed'}))
    assert len(news.list_articles({})['articles'])==1
    assert news.list_articles({'source_id':second})['articles'][0]['id']==article['id']
    count=len(news.archive.history(article['id'])['revisions'])
    asyncio.run(news.sync(force=True))
    assert len(news.archive.history(article['id'])['revisions'])==count
    body=b'<rss><channel><title>Empty</title></channel></rss>'
    asyncio.run(news.sync(force=True))
    news.archive.unsubscribe(first);news.archive.unsubscribe(second)
    assert not news.snapshot()['subscriptions']
    assert news.article(article['id'],False)['is_bookmarked']
    assert len(news.list_articles({})['articles'])==1
    store.close()
    store=Store(folder);news=NewsManager(store,fetch)
    assert len(news.list_articles({})['articles'])==1
    assert len(news.archive.history(article['id'])['revisions'])==count
    asyncio.run(news.add({'url':'https://publisher.example/feed'},sync=False))
    assert len(news.snapshot()['subscriptions'])==1
    backups=list((folder/'backups').glob('*.sqlite'))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as backup: assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    store.close()


def test_revisions_retain_old_text_and_show_diff_without_format_noise(tmp_path):
    store=Store(tmp_path/'workspace')
    body=ARTICLE
    async def fetch(url,headers=None): return result(url,body,headers={'content-type':'text/html'}) if '/article' in url else result(url)
    news=NewsManager(store,fetch)
    asyncio.run(news.add({'url':'https://publisher.example/feed'}))
    article=news.list_articles({})['articles'][0]
    original=news.archive.history(article['id'])['revisions'][0]['id']
    old=news.archive.compare(article['id'],original)['content']['text']
    body=ARTICLE.replace(b'detailed evidence',b'corrected evidence')
    asyncio.run(news.reader(article['id'],force=True))
    latest=news.archive.history(article['id'])['revisions'][0]['id']
    assert latest!=original
    assert news.archive.compare(article['id'],original)['content']['text']==old
    diff=news.archive.compare(article['id'],latest)['diff']
    assert '-This is' in diff and '+This is' in diff and 'corrected evidence' in diff
    body=body.replace(b'<p>',b'<p class="new-layout">')
    asyncio.run(news.reader(article['id'],force=True))
    assert news.archive.history(article['id'])['revisions'][0]['id']==latest
    with pytest.raises(Exception): news.archive.compare(article['id'],999999)
    store.close()


def test_tracking_links_dedupe_but_distinct_publishers_stay_separate(tmp_path):
    store=Store(tmp_path/'workspace')
    body=RSS
    async def fetch(url,headers=None): return result(url, ARTICLE, headers={'content-type':'text/html'}) if '/article' in url else result(url,body)
    news=NewsManager(store,fetch)
    first=asyncio.run(news.add({'url':'https://publisher.example/feed'}))
    body=RSS.replace(b'<guid>one',b'<guid>two').replace(b'/article</link>',b'/article?utm_source=mail</link>')
    asyncio.run(news.sync(first))
    assert len(news.list_articles({})['articles'])==1
    body=RSS.replace(b'publisher.example/article',b'another.example/article')
    asyncio.run(news.add({'url':'https://another.example/feed'}))
    assert len(news.list_articles({})['articles'])==2
    store.close()
