import asyncio
import json
import xml.etree.ElementTree as ET
import pytest
from eis_engine.news import NewsManager
from eis_engine.news_urls import NewsError
from eis_engine.feed_parser import parse_feed
from eis_engine.storage import Store, now
from eis_engine.news_digest_cache import fingerprint

FEED = 'https://www.reddit.com/r/LLMDevs/new/.rss'
SITE = 'https://publisher.example/tool'


def permalink(identifier):
    return 'https://www.reddit.com/r/LLMDevs/comments/' + identifier + '/story/'


def feed(posts):
    root = ET.Element('feed', xmlns='http://www.w3.org/2005/Atom')
    ET.SubElement(root, 'title').text = 'LLMDevs'
    for identifier, body in posts:
        entry = ET.SubElement(root, 'entry')
        ET.SubElement(entry, 'id').text = 't3_' + identifier
        ET.SubElement(entry, 'title').text = 'Post ' + identifier
        ET.SubElement(entry, 'link', href=permalink(identifier))
        ET.SubElement(entry, 'content', type='html').text = (
            '<table><tr><td><img src="https://images.example/preview.jpg"></td><td>'
            '<div class="md">' + body + '</div> submitted by <a href="https://www.reddit.com/user/example">example</a>'
            '<a href="' + SITE + '">[link]</a><a href="' + permalink(identifier) + '">[comments]</a></td></tr></table>'
        )
    return ET.tostring(root)


@pytest.mark.parametrize('kind', ['reddit', 'reddit_rss', 'rss'])
def test_reddit_body_is_not_replaced_by_first_external_link(kind):
    body = '<p>My own explanation with <a href="https://first.example">one reference</a> and <a href="'+SITE+'">my tool</a>.</p>'
    _, entries = parse_feed(feed([('abc', body)]), FEED, kind)
    post = entries[0]
    assert post['url'] == permalink('abc')
    assert post['reader']['source_url'] == permalink('abc')
    assert post['reader']['origin'] == 'reddit'
    assert 'My own explanation' in post['full_text'] and 'https://first.example' in post['full_text']
    assert SITE in post['full_text']
    assert 'submitted by' not in post['full_text'] and '<table>' not in post['full_text']


def test_authored_table_and_code_survive_reddit_thumbnail_wrapper_removal():
    body = '<p>My benchmark:</p><table><tr><th>Device</th><th>Speed</th></tr><tr><td>Jetson</td><td>152.5</td></tr></table><pre><code class="language-python">def read():\n    return 42</code></pre>'
    post = parse_feed(feed([('abc', body)]), FEED, 'reddit')[1][0]
    assert post['full_text'].count('<table>') == 1
    assert '<td>Jetson</td><td>152.5</td>' in post['full_text']
    assert '```python\ndef read():\n    return 42\n```' in post['full_text']


def test_normal_article_links_do_not_change_its_identity_or_original_body():
    root = ET.Element('rss'); channel = ET.SubElement(root, 'channel'); item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'title').text = 'Original article'
    ET.SubElement(item, 'link').text = 'https://author.example/story'
    ET.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded').text = '<p>Original author evidence. '+('More details. '*20)+'<a href="'+SITE+'">A reference</a></p>'
    post = parse_feed(ET.tostring(root),'https://author.example/feed')[1][0]
    assert post['url'] == 'https://author.example/story'
    assert 'Original author evidence.' in post['full_text'] and SITE in post['full_text']


def test_legacy_permalink_uses_comments_footer_not_a_referenced_reddit_post():
    from eis_engine.reddit_posts import saved_post_url
    quote = '[another post]('+permalink('other')+')'
    assert saved_post_url({'url':SITE,'guid':'t3_abc','summary':quote+' [\\[comments\\]]('+permalink('abc')+')'}) == permalink('abc')
    assert saved_post_url({'url':SITE,'guid':'t3_abc','summary':quote}) == 'https://www.reddit.com/comments/abc/'
    assert saved_post_url({'url':SITE,'guid':'t3_abc','summary':'<p><a href="'+permalink('other')+'">Another post</a></p><a href="'+permalink('def')+'">[comments]</a>'}) == permalink('def')


def test_short_and_link_only_posts_never_fetch_embedded_sites(tmp_path):
    store = Store(tmp_path/'workspace')
    calls = []
    async def fetch(url, conditional=None):
        calls.append(url)
        assert url == FEED
        return {'url':url,'status':200,'headers':{},'body':feed([('abc','<p>Try this.</p>'),('def','')])}
    manager = NewsManager(store, fetch)
    async def run():
        identifier = await manager.add({'url':'https://www.reddit.com/r/LLMDevs/'})
        rows = manager.list_articles({})['articles']
        assert len(rows) == 2
        for row in rows:
            article = await manager.reader(row['id'])
            assert article['body_status'] == 'full' and article['reader']['origin'] == 'reddit'
            assert article['url'].startswith('https://www.reddit.com/')
            assert SITE in article['text']
        assert calls == [FEED]
        await manager.sync(identifier, force=True)
        assert len(manager.list_articles({})['articles']) == 2
    try: asyncio.run(run())
    finally: store.close()


def legacy(store, manager, summary, guid='t3_abc'):
    source = asyncio.run(manager.add({'url':'https://www.reddit.com/r/LLMDevs/'}, sync=False))
    with store.db:
        store.db.execute('''INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,discovered_at,summary,text,body_status,reader_json,is_read,is_bookmarked)
            VALUES(?,?,?,?,?,?,?,?,?,'full',?,1,1)''',
            ('legacy',store.workspace,source,guid,'Post',SITE,now(),summary,'External website navigation and labels',json.dumps({'version':6,'origin':'article','blocks':[]})))
        manager.archive.register('legacy',source,guid,SITE)
        manager.archive.capture('legacy')
    return source


def test_legacy_repair_retains_identity_flags_history_and_author_text_offline(tmp_path):
    store = Store(tmp_path/'workspace')
    manager = NewsManager(store)
    summary = 'Author explanation: [my tool]('+SITE+'). [comments]('+permalink('abc')+')'
    legacy(store,manager,summary)
    old = manager.article('legacy',mark_read=False)
    calls = []
    async def offline(url, conditional=None):
        calls.append(url)
        raise NewsError('offline')
    try:
        manager = NewsManager(store,offline)
        repaired = manager.article('legacy',mark_read=False)
        assert repaired['id'] == old['id'] and repaired['is_read'] and repaired['is_bookmarked']
        assert repaired['url'] == permalink('abc') and repaired['text'] == summary
        assert fingerprint(repaired) != fingerprint(old)
        assert store.one('SELECT article_id FROM news_article_identities WHERE url=?',(SITE,)) is None
        assert len(manager.archive.history('legacy')['revisions']) == 2
        again = asyncio.run(manager.reader('legacy',force=True))
        assert again['text'] == summary and again['url'] == permalink('abc')
        asyncio.run(manager.reader('legacy'))
        assert calls == [permalink('abc') + '.rss']
        manager.capture_public_reader('legacy','<p>Unrelated website content</p>')
        assert manager.article('legacy',mark_read=False)['text'] == summary
        manager = NewsManager(store,offline)
        assert len(manager.archive.history('legacy')['revisions']) == 2
    finally: store.close()


def test_two_posts_mentioning_one_site_are_independent_after_legacy_conflation(tmp_path):
    store = Store(tmp_path/'workspace')
    manager = NewsManager(store)
    source = legacy(store,manager,'Second author text. [comments]('+permalink('def')+')')
    calls = []
    async def fetch(url, conditional=None):
        calls.append(url)
        assert url == FEED
        return {'url':url,'status':200,'headers':{},'body':feed([('abc','<p>First author.</p>'),('def','<p>Second author.</p>')])}
    try:
        manager = NewsManager(store,fetch)
        assert manager.article('legacy',mark_read=False)['guid'] == 't3_def'
        asyncio.run(manager.sync(source,force=True))
        rows = store.rows('SELECT id,guid,url,text,is_read,is_bookmarked FROM news_articles ORDER BY guid')
        assert len(rows) == 2 and rows[0]['id'] != rows[1]['id']
        assert rows[0]['url'] == permalink('abc') and rows[1]['url'] == permalink('def')
        assert 'First author.' in rows[0]['text'] and 'Second author.' in rows[1]['text']
        assert rows[1]['id'] == 'legacy' and rows[1]['is_read'] and rows[1]['is_bookmarked']
        asyncio.run(manager.sync(source,force=True))
        assert len(store.rows('SELECT id FROM news_articles')) == 2
        assert calls == [FEED,FEED]
    finally: store.close()


def test_explicit_refresh_uses_original_post_feed_not_the_linked_site(tmp_path):
    store = Store(tmp_path/'workspace')
    manager = NewsManager(store)
    legacy(store,manager,'Old author text. [comments]('+permalink('abc')+')')
    calls = []
    async def fetch(url, conditional=None):
        calls.append(url)
        assert url == permalink('abc') + '.rss'
        return {'url':url,'status':200,'headers':{},'body':feed([('abc','<p>Updated author text.</p>')])}
    try:
        manager = NewsManager(store,fetch)
        article = asyncio.run(manager.reader('legacy',force=True))
        assert 'Updated author text.' in article['text'] and not article['reader'].get('reddit_needs_refresh')
        assert article['url'] == permalink('abc')
        asyncio.run(manager.reader('legacy'))
        assert calls == [permalink('abc')+'.rss']
    finally: store.close()
