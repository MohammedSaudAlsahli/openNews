import asyncio
import json
import pytest
from eis_engine import news
from eis_engine.article_reader import extract_reader
from eis_engine.contracts import Failure
from eis_engine.storage import Store

BASE = 'https://publisher.example/story'
PARA = 'Article evidence with useful context and details. ' * 20
HTML = ('<html><head><meta name="author" content="Reporter"></head><body><article><h1>Headline</h1><p>'+PARA+'</p><figure><img data-src="/photo.jpg" alt="Landscape"><figcaption>Photographer credit</figcaption></figure><h2>More detail</h2><p>'+PARA+'</p></article></body></html>').encode()
PNG = b'\x89PNG\r\n\x1a\nfixture'

def result(url, body, kind='text/html'):
    return {'url':url,'body':body,'headers':{'content-type':kind},'status':200}


def test_reader_preserves_image_position_captions_and_evidence_separation():
    reader = extract_reader(HTML, BASE)
    assert [b['type'] for b in reader['blocks']] == ['text','image','text']
    image = reader['blocks'][1]
    assert image['url'] == 'https://publisher.example/photo.jpg'
    assert image['alt'] == 'Landscape' and image['caption'] == 'Photographer credit'
    assert reader['author'] == 'Reporter'
    assert 'Photographer credit' not in reader['blocks'][2]['text']
    assert 'photo.jpg' not in news.extract_markdown(HTML, BASE)


def test_reader_rejects_active_content_private_images_pixels_and_duplicate_images():
    fragment = '<p>Before</p><img src="javascript:bad"><img src="http://127.0.0.1/private"><img src="/pixel.png" width="1"><script><img src="/hidden.jpg">secret</script><img src="/photo.jpg"><img src="/photo.jpg"><p>After</p>'
    reader = extract_reader(fragment, BASE, fragment=True)
    images = [b for b in reader['blocks'] if b['type']=='image']
    assert len(images) == 1 and images[0]['url']=='https://publisher.example/photo.jpg'
    text = json.dumps(reader)
    assert 'secret' not in text and '127.0.0.1' not in text and 'pixel.png' not in text


def test_reader_handles_srcset_og_cover_and_rss_enclosures():
    reader = extract_reader('<p>Text</p><picture><source srcset="/small.webp 320w, /large.webp 1200w"><img alt="Responsive"></picture>',BASE,fragment=True)
    assert next(b for b in reader['blocks'] if b['type']=='image')['url'].endswith('/large.webp')
    reader = extract_reader(('<html><head><meta property="og:image" content="/cover.jpg"></head><body><article><p>'+PARA+'</p></article></body></html>').encode(),BASE)
    assert reader['blocks'][0]['id']=='cover'
    feed=b'<rss><channel><item><title>Title</title><link>https://publisher.example/story</link><description>Summary</description><enclosure url="https://publisher.example/cover.jpg" type="image/jpeg"/></item></channel></rss>'
    assert news.parse_feed(feed,BASE)[1][0]['reader']['blocks'][0]['id']=='feed-cover'


@pytest.fixture
def saved(tmp_path):
    store = Store(tmp_path/'workspace')
    calls=[]
    async def fetch(url, conditional=None):
        calls.append(url)
        return result(url, PNG, 'image/png') if url.endswith('photo.jpg') else result(url,HTML)
    manager=news.NewsManager(store,fetch)
    async def setup():
        subscription=await manager.add({'url':'https://publisher.example/feed'},sync=False)
        store.db.execute("INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,discovered_at,summary,text,body_status) VALUES(?,?,?,?,?,?,?,?,?,?)",('article',store.workspace,subscription,'guid','Headline',BASE,news.now(),'Summary','Original evidence','full'))
        store.db.commit()
    asyncio.run(setup())
    yield manager,store,calls
    store.close()


def test_reader_backfills_old_articles_and_caches_full_text_without_marking_read(saved):
    manager,store,calls=saved
    row=asyncio.run(manager.reader('article'))
    assert 'Article evidence with useful context' in row['text'] and row['is_read']==0
    assert row['body_status']=='full'
    assert row['reader']['blocks'][1]['type']=='image'
    asyncio.run(manager.reader('article'))
    assert calls==[BASE]
    async def fail(*args): raise news.NewsError('offline')
    manager.fetch=fail
    again=asyncio.run(manager.reader('article',force=True))
    assert again['reader']['blocks']==row['reader']['blocks']
    assert again['reader']['refresh_failed'] is True


def test_images_only_fetch_article_allowlist_and_use_bounded_local_cache(saved):
    manager,store,calls=saved
    asyncio.run(manager.reader('article'))
    path=asyncio.run(manager.image('article','0'))['path']
    assert open(path,'rb').read()==PNG
    assert asyncio.run(manager.image('article','0'))['path']==path
    assert calls.count('https://publisher.example/photo.jpg')==1
    with pytest.raises(Failure): asyncio.run(manager.image('article','https://evil.example'))
    with pytest.raises(Failure): asyncio.run(manager.image('foreign-article','0'))
    assert manager.article('article',mark_read=False)['is_read']==0


def test_image_endpoint_rejects_html_and_svg(saved):
    manager,_,_=saved
    asyncio.run(manager.reader('article'))
    async def bad(url,conditional=None): return result(url,b'<svg onload="bad"/>','image/svg+xml')
    manager.fetch=bad
    with pytest.raises(Failure): asyncio.run(manager.image('article','0'))


def test_preserved_code_retains_language_and_literal_source():
    from lxml import html
    from eis_engine.article_reader import preserve_special_blocks
    tree = html.fromstring('<article><pre><code class="language-python"># عربي\nprint("hello")</code></pre></article>')
    blocks = preserve_special_blocks(tree, 'https://example.com')
    assert list(blocks.values()) == ['```python\n# عربي\nprint("hello")\n```']


def test_linked_figures_do_not_leave_markdown_wrappers():
    body = '<article><p>'+PARA+'</p><a href="https://cdn.example/full.jpg"><picture><img src="https://cdn.example/photo.jpg"></picture></a><p>'+PARA+'</p></article>'
    for fragment in (True, False):
        reader = extract_reader(body, BASE, fragment=fragment)
        text = '\n'.join(b['text'] for b in reader['blocks'] if b['type'] == 'text')
        assert 'full.jpg' not in text
        assert '](' not in text
        assert any(b.get('url') == 'https://cdn.example/photo.jpg' for b in reader['blocks'])


def test_feed_cover_precedes_newsletter_branding_and_preserves_body_images():
    feed = b'''<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>
    <title>Story</title><link>https://publisher.example/story</link>
    <description>Summary</description><enclosure type="image/jpeg" url="https://cdn.example/editorial.jpg"/>
    <content:encoded><![CDATA[<img src="https://cdn.example/logo.jpg"><p>Article</p><img src="https://cdn.example/body.jpg">]]></content:encoded>
    </item></channel></rss>'''
    blocks = news.parse_feed(feed, BASE)[1][0]['reader']['blocks']
    assert blocks[0]['url'] == 'https://cdn.example/editorial.jpg'
    assert [b['url'] for b in blocks if b['type'] == 'image'] == [
        'https://cdn.example/editorial.jpg', 'https://cdn.example/logo.jpg', 'https://cdn.example/body.jpg']


def test_metadata_cover_wins_over_inline_logo_and_no_image_is_valid():
    for meta in ('property="og:image"', 'name="twitter:image"'):
        reader = extract_reader('<html><head><meta '+meta+' content="/editorial.jpg"></head><body><article><img src="/logo.png"><p>'+PARA+'</p></article></body></html>', BASE)
        assert reader['blocks'][0]['url'] == 'https://publisher.example/editorial.jpg'
    reader = extract_reader('<p>'+PARA+'</p>', BASE, fragment=True)
    assert all(b['type'] == 'text' for b in reader['blocks'])


def test_concurrent_image_requests_download_once_and_disk_survives_restart(saved):
    manager, store, calls = saved
    async def run():
        await manager.reader('article')
        paths = await asyncio.gather(*(manager.image('article','0') for _ in range(8)))
        assert len({p['path'] for p in paths}) == 1
        assert calls.count('https://publisher.example/photo.jpg') == 1
        async def offline(*args): raise AssertionError('Disk cache must not fetch')
        reopened = news.NewsManager(store, offline)
        assert await reopened.image('article','0') == paths[0]
        # Even when every network image slot is occupied, cached reads complete.
        await reopened.image_slots.acquire()
        try:
            assert await asyncio.wait_for(reopened.image('article','0'), .1) == paths[0]
        finally: reopened.image_slots.release()
    asyncio.run(run())


def test_responsive_image_urls_keep_cdn_transformation_commas():
    reader = extract_reader('<picture><source srcset="https://cdn.example/image/fetch/w_400,q_auto/photo.jpg 400w, https://cdn.example/image/fetch/w_900,q_auto/photo.jpg 900w"><img></picture>', BASE, fragment=True)
    assert reader['blocks'][0]['url'] == 'https://cdn.example/image/fetch/w_900,q_auto/photo.jpg'


def test_decorative_wordpress_icons_are_not_article_photos():
    reader = extract_reader('<p>Text</p><img src="https://s.w.org/images/core/emoji/17.0.2/72x72/25b6.png"><img class="avatar" src="/author.jpg"><img src="/photo.jpg">', BASE, fragment=True)
    assert [b['url'] for b in reader['blocks'] if b['type']=='image'] == ['https://publisher.example/photo.jpg']
