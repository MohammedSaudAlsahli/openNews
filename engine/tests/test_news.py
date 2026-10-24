import asyncio
from datetime import datetime, timedelta, timezone
import socket
import pytest
from eis_engine.storage import Store
from eis_engine import news

RSS = b'''<?xml version="1.0"?><rss version="2.0"><channel><title>News feed</title><item><guid>one</guid><title>A real headline</title><link>https://publisher.example/article</link><pubDate>Tue, 01 Oct 2024 12:00:00 GMT</pubDate><description>Feed summary remains available.</description></item></channel></rss>'''
ARTICLE = b'<html><head><title>A real headline</title></head><body><article><h1>A real headline</h1><p>' + b'This is the actual article body with detailed evidence and context. ' * 30 + b'</p></article></body></html>'


def result(url, body=RSS, status=200, headers=None):
    return {"url":url,"body":body,"status":status,"headers":headers or {"content-type":"application/rss+xml", "etag":'"v1"'}}


@pytest.fixture
def store(tmp_path):
    value = Store(tmp_path / "workspace")
    yield value
    value.close()


@pytest.mark.parametrize("url", ["http://localhost/", "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data", "http://[::1]/", "http://[::ffff:127.0.0.1]/", "https://name:password@example.com/feed", "file:///etc/passwd", "https://example.com:8080/feed", "https://example.com/\nsecret", "https://metadata.internal/feed"])
def test_private_or_credential_urls_rejected(url):
    with pytest.raises(news.NewsError): news.canonical_url(url)


def test_dns_mixed_public_private_rejected(monkeypatch):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**kw:[(2,1,6,"",("93.184.216.34",443)),(2,1,6,"",("10.0.0.1",443))])
    with pytest.raises(news.NewsError): news.resolve_public("publisher.example",443)


def test_transport_connects_numeric_ip_with_original_tls_hostname(monkeypatch):
    events=[]
    class Socket:
        def settimeout(self, value): pass
        def connect(self, address): events.append(("connect",address))
        def getpeername(self): return ("93.184.216.34",443)
        def close(self): pass
        def do_handshake(self): pass
    class Context:
        def wrap_socket(self, connection, server_hostname, do_handshake_on_connect):
            events.append(("tls",server_hostname)); return connection
    monkeypatch.setattr(socket,"socket",lambda *a:Socket())
    monkeypatch.setattr(news.ssl,"create_default_context",lambda:Context())
    connection=news.PinnedHTTP("publisher.example",443,"93.184.216.34",True)
    connection.connect()
    assert events == [("connect",("93.184.216.34",443)),("tls","publisher.example")]


def test_redirect_to_private_target_blocked_before_connection(monkeypatch):
    calls=[]
    monkeypatch.setattr(news,"resolve_public",lambda *a:["93.184.216.34"])
    class Response:
        status=302
        def getheaders(self): return [("Location","http://127.0.0.1/admin")]
    class Connection:
        def __init__(self,*a): calls.append(a)
        def request(self,*a,**kw): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(news,"PinnedHTTP",Connection)
    with pytest.raises(news.NewsError): news._fetch("https://publisher.example/feed")
    assert len(calls)==1


def test_xml_dtd_and_entity_are_rejected():
    with pytest.raises(news.NewsError): news.parse_feed(b'<!DOCTYPE rss [<!ENTITY x "secret">]><rss/>',"https://publisher.example/")


def test_atom_date_and_reddit_original_post_identity():
    body=b'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Community</title><entry><id>t3_a</id><title>Headline</title><link href="https://www.reddit.com/r/science/comments/a/"/><published>2024-02-01T10:30:00Z</published><content type="html">&lt;a href="https://publisher.example/story"&gt;[link]&lt;/a&gt;</content></entry></feed>'''
    _, entries=news.parse_feed(body,"https://www.reddit.com/r/science/new/.rss","reddit")
    assert entries[0]["url"]=="https://www.reddit.com/r/science/comments/a/"
    assert 'https://publisher.example/story' in entries[0]['full_text']
    assert entries[0]['reader']['origin'] == 'reddit'
    assert entries[0]["published_at"]=="2024-02-01T10:30:00+00:00"
    assert news.normalize_subscription("https://reddit.com/r/Science/")[1]=="https://www.reddit.com/r/Science/new/.rss"


def test_invalid_or_missing_publication_date_not_replaced_with_now():
    assert news.date_value("not a date") is None
    assert news.date_value("") is None


def test_feed_bounded_to_50_items():
    item=RSS[RSS.index(b'<item>'):RSS.index(b'</item>')+7]
    _, entries=news.parse_feed(b'<rss><channel>'+item*80+b'</channel></rss>',"https://publisher.example/feed")
    assert len(entries)==50


def test_autodiscovery_full_article_dedup_and_read_state(store):
    seen=[]
    async def fetch(url, conditional=None):
        seen.append((url,conditional))
        if url=="https://publisher.example/": return result(url,b'<html><head><link rel="alternate" type="application/rss+xml" href="/feed"/></head></html>',headers={"content-type":"text/html"})
        if url.endswith("/article"): return result(url,ARTICLE,headers={"content-type":"text/html"})
        return result(url)
    manager=news.NewsManager(store,fetch)
    identifier=asyncio.run(manager.add({"url":"https://publisher.example/"}))
    snapshot=manager.snapshot()
    assert snapshot["subscriptions"][0]["feed_url"]=="https://publisher.example/feed"
    assert snapshot["subscriptions"][0]["unread_count"]==1
    assert snapshot["articles"][0]["body_status"]=="full"
    article=manager.article(snapshot["articles"][0]["id"])
    assert "actual article body" in article["text"]
    assert article["published_at"].startswith("2024-10-01")
    assert article["discovered_at"] != article["published_at"]
    asyncio.run(manager.sync(identifier))
    assert len(manager.snapshot()["articles"])==1
    assert manager.snapshot()["subscriptions"][0]["unread_count"]==0
    # Explicit refresh reprocesses saved feed content after parser fixes.
    assert [headers for url, headers in seen if url.endswith("/feed")][-1] is None
    row = store.one("SELECT * FROM news_subscriptions WHERE id=?", (identifier,))
    asyncio.run(manager._sync_one(row))
    assert [headers for url, headers in seen if url.endswith("/feed")][-1]["If-None-Match"]=='"v1"'


def test_304_retries_pending_body_without_losing_summary(store):
    feed_calls=0
    article_calls=0
    async def fetch(url, conditional=None):
        nonlocal feed_calls,article_calls
        if url.endswith("/article"):
            article_calls+=1
            if article_calls==1: raise news.NewsError("Public access blocked")
            return result(url,ARTICLE,headers={"content-type":"text/html"})
        feed_calls+=1
        return result(url,status=200 if feed_calls==1 else 304,body=RSS if feed_calls==1 else b"")
    manager=news.NewsManager(store,fetch)
    identifier=asyncio.run(manager.add({"url":"https://publisher.example/feed"}))
    article=manager.snapshot()["articles"][0]
    assert article["body_status"]=="summary_only"
    assert manager.article(article["id"])["text"]=="Feed summary remains available."
    # Failed bodies retry after the cooldown, including when the feed replies 304.
    with store.db:
        store.db.execute("UPDATE news_articles SET last_body_attempt='2020-01-01T00:00:00+00:00' WHERE id=?",(article["id"],))
    asyncio.run(manager.sync(identifier))
    assert manager.snapshot()["articles"][0]["body_status"]=="full"


def test_feed_failure_keeps_subscription_and_previous_articles(store):
    failing=False
    async def fetch(url, conditional=None):
        if failing: raise news.NewsError("المصدر يمنع الوصول العام.")
        return result(url,ARTICLE if url.endswith('/article') else RSS,headers={"content-type":"text/html"} if url.endswith('/article') else None)
    manager=news.NewsManager(store,fetch)
    identifier=asyncio.run(manager.add({"url":"https://publisher.example/feed"}))
    failing=True
    outcome=asyncio.run(manager.sync(identifier))
    assert outcome=={"updated":0,"failed":1}
    snapshot=manager.snapshot()
    assert len(snapshot["articles"])==1
    assert snapshot["subscriptions"][0]["status"]=="error"
    assert snapshot["subscriptions"][0]["last_success"]


def test_initial_403_subscription_persists_and_disabled_does_not_fetch(store):
    calls=[]
    async def fetch(url, conditional=None): calls.append(url); raise news.NewsError("المصدر يمنع الوصول العام.")
    manager=news.NewsManager(store,fetch)
    identifier=asyncio.run(manager.add({"url":"https://reddit.com/r/science"}))
    assert manager.snapshot()["subscriptions"][0]["error"]
    manager.update({"subscription_id":identifier,"enabled":False})
    asyncio.run(manager.sync(force=True))
    assert len(calls)==1


def test_poll_retries_only_due_subscriptions(store,monkeypatch):
    calls=[]
    async def fetch(url, conditional=None): calls.append(url); raise news.NewsError("temporary failure")
    manager=news.NewsManager(store,fetch)
    identifier=asyncio.run(manager.add({"url":"https://publisher.example/feed","interval_minutes":15}))
    asyncio.run(manager.sync())
    assert len(calls)==1
    with store.db: store.db.execute("UPDATE news_subscriptions SET last_checked=? WHERE id=?",((datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat(),identifier))
    async def stop_sleep(seconds):
        assert seconds==60
        raise asyncio.CancelledError()
    monkeypatch.setattr(news.asyncio,"sleep",stop_sleep)
    with pytest.raises(asyncio.CancelledError): asyncio.run(manager.poll())
    assert len(calls)==2


def test_no_technical_or_secret_error_text_persisted(store):
    async def fetch(url, conditional=None): raise RuntimeError("secret internal header")
    manager=news.NewsManager(store,fetch)
    asyncio.run(manager.add({"url":"https://publisher.example/feed"}))
    assert "secret" not in manager.snapshot()["subscriptions"][0]["error"]


def test_add_without_network_and_context_read_preserves_unread(store):
    async def fetch(url, conditional=None): return result(url,ARTICLE if url.endswith('/article') else RSS,headers={"content-type":"text/html"} if url.endswith('/article') else None)
    manager=news.NewsManager(store,fetch)
    identifier=asyncio.run(manager.add({"url":"https://publisher.example/feed"},sync=False))
    assert manager.snapshot()["articles"]==[]
    asyncio.run(manager.sync(identifier))
    item=manager.snapshot()["articles"][0]
    manager.article(item["id"],mark_read=False)
    assert manager.snapshot()["subscriptions"][0]["unread_count"]==1


def test_response_size_limit_rejects_before_read(monkeypatch):
    monkeypatch.setattr(news,"resolve_public",lambda *a:["93.184.216.34"])
    class Response:
        status=200
        def getheaders(self): return [("Content-Length",str(news.MAX_BYTES+1))]
        def read1(self,*a): raise AssertionError("Must not read oversized body")
    class Connection:
        def __init__(self,*a): pass
        def request(self,*a,**kw): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(news,"PinnedHTTP",Connection)
    with pytest.raises(news.NewsError): news._fetch("https://publisher.example/feed")


def test_redirect_dns_rechecked_and_cookies_not_forwarded(monkeypatch):
    resolutions=[]; requests=[]
    def resolve(host, port):
        resolutions.append(host)
        if host=="blocked.example": raise news.NewsError("private resolution")
        return ["93.184.216.34"]
    monkeypatch.setattr(news,"resolve_public",resolve)
    class Response:
        status=302
        def getheaders(self): return [("Location","https://blocked.example/feed"),("Set-Cookie","secret=x")]
    class Connection:
        def __init__(self,*a): pass
        def request(self,*a,**kw): requests.append(kw["headers"])
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(news,"PinnedHTTP",Connection)
    with pytest.raises(news.NewsError): news._fetch("https://publisher.example/feed")
    assert resolutions==["publisher.example","blocked.example"]
    assert all("Cookie" not in headers and "Authorization" not in headers for headers in requests)


def test_podcast_without_article_link_keeps_description_without_fetching_audio(store):
    feed = b'<rss><channel><title>Podcast</title><item><title>Episode</title><guid isPermaLink="false">gid://episode/1</guid><description>Episode description only.</description><pubDate>Wed, 07 Oct 2026 10:00:00 GMT</pubDate><enclosure url="https://media.example/one.mp3" type="audio/mpeg"/></item></channel></rss>'
    calls=[]
    async def fetch(url, conditional=None):
        calls.append(url)
        assert url == 'https://publisher.example/podcast'
        return result(url,feed)
    manager=news.NewsManager(store,fetcher=fetch)
    async def run():
        identifier=await manager.add({'url':'https://publisher.example/podcast'})
        await manager.sync(identifier,force=True)
        rows=store.rows('SELECT * FROM news_articles')
        assert len(rows)==1
        assert rows[0]['body_status']=='media_summary'
        assert rows[0]['body_attempts']==0
        assert 'Episode description only.' in rows[0]['text']
        assert rows[0]['url']=='https://media.example/one.mp3'
        assert len(calls)==2
    asyncio.run(run())


def test_podcast_private_enclosure_not_imported():
    feed=b'<rss><channel><item><title>Episode</title><enclosure url="http://127.0.0.1/secret.mp3" type="audio/mpeg"/></item></channel></rss>'
    assert news.parse_feed(feed,'https://publisher.example/podcast')[1]==[]


def test_summary_preserves_structure_and_resolves_only_safe_links():
    content = '<h2>عنوان</h2><p><strong>مهم</strong> <a href="../evidence">الدليل</a> <a href="javascript:alert(1)">غير آمن</a><img src="https://tracking.example/pixel"/></p><ul><li>أولًا</li><li>ثانيًا</li></ul><script>do_not_preserve()</script>'
    markdown = news.summary_markdown(content, "https://publisher.example/articles/story")
    assert "## عنوان" in markdown
    assert "**مهم**" in markdown
    assert "[الدليل](https://publisher.example/evidence)" in markdown
    assert "- أولًا" in markdown and "- ثانيًا" in markdown
    assert "javascript" not in markdown and "tracking.example" not in markdown and "do_not_preserve" not in markdown
    assert "غير آمن" in markdown


def test_article_extraction_keeps_headings_bold_and_link_evidence():
    body = ('<html><body><article><h1>Article heading</h1><p>' + ('Details with <strong>important evidence</strong> and <a href="/proof">the original evidence</a>. ' * 20) + '</p><h2>Next section</h2><ul><li>First point</li><li>Second point</li></ul><p><a href="file:///etc/passwd">unsafe link</a></p></article></body></html>').encode()
    markdown = news.extract_markdown(body, "https://publisher.example/article")
    assert "# Article heading" in markdown and "## Next section" in markdown
    assert "**important evidence**" in markdown
    assert "[the original evidence](https://publisher.example/proof)" in markdown
    assert "- First point" in markdown
    assert "file:" not in markdown


def test_explicit_refresh_backfills_markdown_and_retains_full_text_on_failure(store):
    fail = False
    async def fetch(url, conditional=None):
        if url.endswith("/article"):
            if fail: raise news.NewsError("blocked")
            return result(url,ARTICLE,headers={"content-type":"text/html"})
        return result(url)
    manager = news.NewsManager(store,fetch)
    identifier = asyncio.run(manager.add({"url":"https://publisher.example/feed"}))
    article_id = manager.snapshot()["articles"][0]["id"]
    with store.db:
        store.db.execute("UPDATE news_articles SET text='old plain text',body_status='full' WHERE id=?",(article_id,))
    asyncio.run(manager.reader(article_id,force=True))
    updated = manager.article(article_id,mark_read=False)["text"]
    assert updated != "old plain text" and "A real headline" in updated
    fail = True
    asyncio.run(manager.reader(article_id,force=True))
    article = manager.article(article_id,mark_read=False)
    assert article["text"] == updated and article["body_status"] == "full"


def test_automatic_poll_does_not_refetch_already_full_articles(store):
    calls = []
    async def fetch(url, conditional=None):
        calls.append(url)
        return result(url,ARTICLE if url.endswith('/article') else RSS,headers={"content-type":"text/html"} if url.endswith('/article') else None)
    manager = news.NewsManager(store,fetch)
    identifier = asyncio.run(manager.add({"url":"https://publisher.example/feed"}))
    with store.db:
        store.db.execute("UPDATE news_subscriptions SET last_checked=NULL WHERE id=?",(identifier,))
    asyncio.run(manager.sync())
    asyncio.run(manager.sync(force=True))
    assert calls.count("https://publisher.example/article") == 1


def test_full_feed_content_is_saved_without_fetching_website(store):
    full='Actual public article evidence. '*20
    feed=('<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>Publisher</title><item><guid>one</guid><title>Article</title><link>https://publisher.example/article</link><description>Short excerpt</description><content:encoded><![CDATA[<p>'+full+'</p>]]></content:encoded></item></channel></rss>').encode()
    calls=[]
    async def fetch(url, conditional=None):
        calls.append(url)
        assert url.endswith('/feed')
        return result(url,feed)
    manager=news.NewsManager(store,fetch)
    asyncio.run(manager.add({'url':'https://publisher.example/feed'}))
    article=manager.article(manager.snapshot()['articles'][0]['id'],mark_read=False)
    assert article['body_status']=='full' and full.strip() in article['text']
    assert calls==['https://publisher.example/feed']


def test_body_backlog_drains_without_another_feed_refresh(store):
    async def fetch(url, conditional=None): return result(url, ARTICLE, headers={'content-type':'text/html'})
    manager = news.NewsManager(store, fetch)
    sub = asyncio.run(manager.add({'url':'https://publisher.example/feed'}, sync=False))
    with store.db:
        for i in range(25):
            key = 'backlog-' + str(i)
            store.db.execute("INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,discovered_at,summary) VALUES(?,?,?,?,?,?,?,?)",
                (key,store.workspace,sub,key,'Story','https://publisher.example/'+key,news.now(),'Excerpt'))
            manager.archive.register(key,sub,key,'https://publisher.example/'+key)
    asyncio.run(manager._fetch_bodies(None))
    assert store.one("SELECT count(*) AS n FROM news_articles WHERE body_status='full'")['n'] == 20
    asyncio.run(manager._fetch_bodies(None))
    assert store.one("SELECT count(*) AS n FROM news_articles WHERE body_status='full'")['n'] == 25


def test_body_retry_backoff_and_render_lease_survive_new_manager(store):
    calls = []
    async def fetch(url, conditional=None):
        calls.append(url)
        if url.endswith('/feed'): return result(url)
        raise news.NewsError('temporarily unavailable')
    manager = news.NewsManager(store, fetch)
    sub = asyncio.run(manager.add({'url':'https://publisher.example/feed'}))
    row = store.one('SELECT * FROM news_articles')
    assert row['body_attempts'] == 1
    asyncio.run(manager._fetch_bodies(None))
    assert len(calls) == 2
    with store.db:
        store.db.execute('UPDATE news_articles SET last_body_attempt=?', ((datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat(),))
    asyncio.run(manager._fetch_bodies(None))
    assert store.one('SELECT body_attempts FROM news_articles')['body_attempts'] == 2
    assert manager.next_public_capture()['article']['id'] == row['id']
    assert news.NewsManager(store, fetch).next_public_capture()['article'] is None
    with store.db: store.db.execute("UPDATE news_articles SET reader_json='{}'")
    manager.update({'subscription_id':sub,'enabled':False})
    assert manager.next_public_capture()['article'] is None
    asyncio.run(manager._fetch_bodies(None))
    assert len(calls) == 3


def test_source_description_is_publisher_metadata_not_first_article():
    from eis_engine.feed_parser import source_description
    assert source_description(b'<rss><channel><description>AI research and evaluations.</description><item><description>Unrelated story.</description></item></channel></rss>') == 'AI research and evaluations.'
    assert source_description(b'<feed xmlns="http://www.w3.org/2005/Atom"><subtitle>Research notes</subtitle></feed>') == 'Research notes'
    assert source_description(b'<html><head><meta name="description" content="Publisher topics"></head><body>Navigation</body></html>') == 'Publisher topics'
    assert source_description(RSS) == ''


def test_source_description_survives_reopening_store(store):
    feed = b'<rss><channel><title>Science</title><description>Science and AI.</description></channel></rss>'
    async def fetch(url, headers=None):
        return {'status':200, 'url':url, 'body':feed, 'headers':{}}
    manager = news.NewsManager(store, fetch)
    asyncio.run(manager.add({'url':'https://publisher.example/feed'}))
    assert manager.snapshot()['subscriptions'][0]['description'] == 'Science and AI.'
    assert news.NewsManager(store, fetch).snapshot()['subscriptions'][0]['description'] == 'Science and AI.'

def test_refresh_defaults_and_custom_interval_survive_restart(store):
    manager=news.NewsManager(store)
    identifier=asyncio.run(manager.add({'url':'https://publisher.example/feed'},sync=False))
    assert store.one('SELECT interval_minutes FROM news_subscriptions WHERE id=?',(identifier,))['interval_minutes']==5
    for minutes in (1,5,7,10080):
        manager.update({'subscription_id':identifier,'interval_minutes':minutes})
        assert store.one('SELECT interval_minutes FROM news_subscriptions WHERE id=?',(identifier,))['interval_minutes']==minutes
    for minutes in (0,-1,1.5,True,10081):
        with pytest.raises(news.Failure): manager.update({'subscription_id':identifier,'interval_minutes':minutes})
    restarted=news.NewsManager(store)
    assert store.one('SELECT interval_minutes FROM news_subscriptions WHERE id=?',(identifier,))['interval_minutes']==10080
