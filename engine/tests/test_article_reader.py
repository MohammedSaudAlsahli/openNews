import asyncio
import json
import pytest
from eis_engine import news
from eis_engine.article_reader import extract_reader, READER_VERSION
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


@pytest.mark.parametrize('fragment', [True, False])
@pytest.mark.parametrize('lines', [
    '<div class="token-line"><span>static double cross(double ax, double ay)</span><br></div><div class="token-line">{<br></div><div class="token-line">    return ax * ay;<br></div><div class="token-line">}<br></div>',
    '<span class="line">static double cross(double ax, double ay)</span><span class="line">{</span><span class="line">    return ax * ay;</span><span class="line">}</span>',
    'static double cross(double ax, double ay)<br>{<br>    return ax * ay;<br>}',
])
def test_publisher_code_lines_survive_extraction(fragment, lines):
    body = '<article><p>'+PARA+'</p><pre class="language-cpp"><code>'+lines+'</code></pre><p>'+PARA+'</p></article>'
    reader = extract_reader(body, BASE, fragment=fragment)
    text = '\n'.join(b.get('text', '') for b in reader['blocks'])
    assert '```cpp\nstatic double cross(double ax, double ay)\n{\n    return ax * ay;\n}\n```' in text


@pytest.mark.parametrize('fragment', [True, False])
def test_empty_adjacent_and_nested_inline_formatting_does_not_emit_markdown_stars(fragment):
    markup = ('<p><strong>Part of <em>our series</em>.</strong> '
              '<strong><a href="/series">Read more</a></strong><strong>. </strong><strong></strong> After.</p>'
              '<h3>Permafrost<strong></strong></h3><p><strong>Outer <b>inner</b></strong> tail.</p>')
    detail = 'Frozen ground stores carbon, and thawing changes the surrounding landscape. ' * 15
    reader = extract_reader('<article><p>'+PARA+'</p>'+markup+'<p>'+detail+'</p></article>', BASE, fragment=fragment)
    text = '\n'.join(b.get('text', '') for b in reader['blocks'])
    assert '**' not in text
    assert '<strong>Part of <em>our series</em>.</strong>' in text
    assert '[Read more](https://publisher.example/series)' in text
    assert text.count('After.') == 1 and text.count('tail.') == 1
    if fragment:  # Full-page extraction may discard short standalone headings.
        assert '### Permafrost' in text


def test_preformatted_source_is_not_rewritten_as_code_formatter():
    from eis_engine.article_reader import preformatted_text
    from lxml import html
    source = 'if (x) { return "<u>literal</u>"; }\n\n\t// keep blank lines\n'
    from html import escape
    assert preformatted_text(html.fromstring('<pre>'+escape(source)+'</pre>')) == source.strip('\n')


@pytest.mark.parametrize('language,source', [
    ('python', 'def read(url):\n    return {"url": url}\n\nprint(read("news"))'),
    ('javascript', 'const read = (url) => {\n  return { url };\n};'),
    ('typescript', 'function read(url: string): string {\n  return url;\n}'),
    ('html', '<article>\n  <strong>News & updates</strong>\n</article>'),
    ('sql', 'SELECT title, published_at\nFROM articles\nWHERE is_read = 0;'),
    ('rust', 'fn main() {\n    println!("news");\n}'),
    ('bash', '#!/bin/sh\nfor file in *.md; do\n  printf "%s\\n" "$file"\ndone'),
    ('yaml', 'news:\n  sources:\n    - title: "News"\n      enabled: true'),
    ('unknown-language', 'A & B < C\n    literal **markers**\n\tkeep tabs'),
])
def test_code_line_recovery_is_language_independent(language, source):
    from html import escape
    markup = ''.join('<span class="line">'+escape(line)+'</span>' for line in source.split('\n'))
    reader = extract_reader('<article><pre><code class="language-'+language+'">'+markup+'</code></pre></article>', BASE, fragment=True)
    text = '\n'.join(b.get('text', '') for b in reader['blocks'])
    assert '```'+language+'\n'+source+'\n```' in text


def test_inline_publisher_code_keeps_literal_markdown_punctuation():
    from html import unescape
    reader = extract_reader('<p>Use <code>a*b[0] &lt; limit</code> and <u>underlined</u>.</p>', BASE, fragment=True)
    text = reader['blocks'][0]['text']
    assert '<code>a*b[0] < limit</code>' in unescape(text)
    assert '<u>underlined</u>' in text


def test_saved_reader_format_upgrade_is_cached_and_preserves_old_content_on_failure(saved):
    manager, store, calls = saved
    legacy = {'version':4, 'origin':'feed', 'blocks':[{'type':'text','text':'Previously saved article'}]}
    store.db.execute('UPDATE news_articles SET reader_json=?', (json.dumps(legacy),)); store.db.commit()
    assert manager.article('article', mark_read=False)['reader_upgrade_required'] is True
    updated = asyncio.run(manager.reader('article'))
    assert updated['reader']['version'] == READER_VERSION
    assert updated['reader_upgrade_required'] is False
    asyncio.run(manager.reader('article'))
    assert calls == [BASE]
    store.db.execute('UPDATE news_articles SET reader_json=?', (json.dumps(legacy),)); store.db.commit()
    async def offline(*args):
        calls.append('offline')
        raise news.NewsError('offline')
    manager.fetch = offline
    failed = asyncio.run(manager.reader('article'))
    assert failed['reader']['blocks'] == legacy['blocks']
    assert failed['reader']['refresh_failed'] is True
    asyncio.run(manager.reader('article'))
    assert calls.count('offline') == 1


@pytest.mark.parametrize('fragment', [True, False])
def test_tables_keep_rows_cells_caption_merged_cells_and_safe_links(fragment):
    from lxml import html
    table = ('<table style="width:99999px" onclick="bad()"><caption>Model comparison</caption>'
             '<thead><tr><th scope="col">Feature</th><th colspan="2">Models</th></tr></thead>'
             '<tbody><tr><th rowspan="2" scope="row">Latency</th><td><a href="/paper">185 ms</a></td><td>216 ms</td></tr>'
             '<tr><td>1.25</td><td><strong>2.40</strong></td></tr></tbody></table>')
    reader = extract_reader('<article><p>'+PARA+'</p>'+table+'<p>After comparison.</p></article>', BASE, fragment=fragment)
    text = '\n'.join(b.get('text', '') for b in reader['blocks'])
    parsed = html.fromstring('<div>'+text+'</div>')
    assert len(parsed.xpath('.//table//tr')) == 3
    assert parsed.xpath('.//table//td//text()') == ['185 ms', '216 ms', '1.25', '2.40']
    assert parsed.xpath('.//caption/text()') == ['Model comparison']
    assert parsed.xpath('.//th[@colspan="2"]') and parsed.xpath('.//th[@rowspan="2"]')
    assert parsed.xpath('.//td/a/@href') == ['https://publisher.example/paper']
    assert not parsed.xpath('.//table//@style | .//table//@onclick')
    assert text.count('After comparison.') == 1


def test_table_serialization_does_not_invent_boundaries_or_links():
    from eis_engine.article_reader import table_markup
    from lxml import html
    node = html.fromstring('<table><tr><td><a>12345</a> &lt;script&gt;literal&lt;/script&gt;</td><td><a href="javascript:bad()">Unsafe</a><script>execute()</script></td></tr></table>')
    result = table_markup(node, BASE)
    parsed = html.fromstring(result)
    assert len(parsed.xpath('.//td')) == 2
    assert not parsed.xpath('.//a/@href | .//script')
    assert parsed.xpath('.//td')[0].text_content() == '12345 <script>literal</script>'
    assert 'execute()' not in result


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


def test_empty_extraction_keeps_saved_text_and_allows_explicit_retry(saved):
    manager, store, calls = saved
    async def empty(url, conditional=None):
        return result(url, b'<html><body></body></html>')
    manager.fetch = empty
    failed = asyncio.run(manager.reader('article', force=True))
    assert failed['text'] == 'Original evidence'
    assert failed['reader']['refresh_failed'] is True
    async def recovered(url, conditional=None):
        return result(url, HTML)
    manager.fetch = recovered
    recovered = asyncio.run(manager.reader('article', force=True))
    assert recovered['body_status'] == 'full'
    assert 'Article evidence' in recovered['text']
    assert not recovered['reader'].get('refresh_failed')


def test_short_failed_refresh_does_not_replace_full_evidence(saved):
    manager, store, _ = saved
    before = asyncio.run(manager.reader('article'))
    async def short(url, conditional=None):
        return result(url, b'<html><article><p>Temporarily unavailable.</p></article></html>')
    manager.fetch = short
    after = asyncio.run(manager.reader('article', force=True))
    assert after['text'] == before['text']
    assert after['reader']['blocks'] == before['reader']['blocks']
    assert after['reader']['refresh_failed'] is True


def test_utf8_fragments_preserve_arabic_and_smart_punctuation():
    text = 'شرح المقالة بالعربية — Why don’t we read “full articles”? ' * 8
    reader = extract_reader(('<article><p>' + text + '</p></article>').encode('utf-8'), BASE)
    body = '\n'.join(b.get('text', '') for b in reader['blocks'])
    assert 'شرح المقالة بالعربية' in body
    assert 'don’t' in body and '“full articles”' in body
    assert 'â' not in body


def test_site_banner_and_gravatar_are_not_article_images():
    from eis_engine.article_reader import extract_reader
    body = '<html><head><meta property="og:image" content="https://secure.gravatar.com/blavatar/site?s=200"></head><body><div id="header-image"><img src="https://example.com/banner.jpg"></div><article><p>' + ('A useful article about science and mathematics. ' * 35) + '</p><img src="https://example.com/actual.jpg"></article></body></html>'
    reader = extract_reader(body, 'https://example.com/story', fragment=True)
    images = [b['url'] for b in reader['blocks'] if b['type'] == 'image']
    assert images == ['https://example.com/actual.jpg']


def test_newsletter_list_paragraphs_stay_with_markers():
    from eis_engine.article_reader import extract_reader
    result = extract_reader('<article><ul><li><p><strong>أخبار</strong> اليوم</p></li><li><p>تحليلات السوق</p></li></ul><hr/><p>متن المقالة</p></article>', 'https://example.com/story', fragment=True)
    text = '\n'.join(b.get('text', '') for b in result['blocks'])
    assert '- <strong>أخبار</strong> اليوم' in text
    assert text.count('اليوم') == 1
    assert '- تحليلات السوق' in text
    assert '---' in text
