import asyncio
import math
import httpx
import pytest
from eis_engine.news_embeddings import LocalNewsEmbeddings
from eis_engine.contracts import Failure
from test_news_digest import service


def test_agno_adapter_validates_identity_normalizes_and_releases(monkeypatch):
    from agno.knowledge.embedder.ollama import OllamaEmbedder
    from ollama import Client
    requests=[]
    def embed(self, **kwargs):
        requests.append(kwargs)
        return {'embeddings':[[3.,4.]]}
    monkeypatch.setattr(Client,'embed',embed)
    monkeypatch.setattr(httpx.Client,'get',lambda *a,**k:httpx.Response(200,json={'models':[{'name':'embeddinggemma-2:270m','digest':'abc'}]},request=httpx.Request('GET','http://local')))
    encoder=LocalNewsEmbeddings(dimensions=2,digest='abc')
    assert encoder.encode(['العربية English'],query=True)==[[.6,.8]]
    assert requests[0]['keep_alive']==0
    assert requests[0]['dimensions']==2
    assert requests[0]['input']=='task: search result | query: العربية English'
    encoder.digest='changed'
    with pytest.raises(RuntimeError,match='changed'): encoder.encode(['x'])
    assert len(requests)==1
    encoder.close()
    with pytest.raises(RuntimeError,match='closed'): encoder.encode(['x'])


def test_unprepared_model_never_downloads_or_infers():
    with pytest.raises(RuntimeError,match='prepare'): LocalNewsEmbeddings().encode(['hello'])


def test_switch_model_invalidates_only_vectors_and_preserves_summary_settings(service):
    async def run():
        k=service.news.knowledge
        while k.index_next(): pass
        before=service.news_digest.settings()
        count=k.db.execute('SELECT count(*) FROM news_search_chunks').fetchone()[0]
        with k.db: k.db.execute("UPDATE news_search_chunks SET vector=x'00000000',model='old'")
        await k.select_model('custom:small',512,'sha')
        assert k.status()['enabled']
        assert k.status()['model']=='custom:small'
        assert k.db.execute('SELECT count(*) FROM news_search_chunks WHERE vector IS NULL').fetchone()[0]==count
        assert service.news_digest.settings()==before
        from eis_engine.news_knowledge import NewsKnowledge
        reopened=NewsKnowledge(service.news)
        assert reopened.embedder.dimensions==512 and reopened.embedder.digest=='sha'
        assert (await reopened.search('story')) is not None
    asyncio.run(run())


def test_non_embedding_model_rejected_before_inference(service,monkeypatch):
    calls=[]
    async def post(self,url,**kwargs):
        calls.append(url)
        return httpx.Response(200,json={'capabilities':['completion','thinking']},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    before=service.news.knowledge.status()['model']
    with pytest.raises(Failure): asyncio.run(service.news_digest.local.prepare_embedding('chat:small'))
    assert len(calls)==1 and calls[0].endswith('/api/show')
    assert service.news.knowledge.status()['model']==before


def test_registry_size_selects_apple_mlx_manifest_and_verifies_hash(monkeypatch):
    import hashlib,json
    from eis_engine.local_summary import registry_size
    from eis_engine import local_summary
    monkeypatch.setattr(local_summary.platform,'system',lambda:'Darwin')
    monkeypatch.setattr(local_summary.platform,'machine',lambda:'arm64')
    body=json.dumps({'layers':[{'size':378000000}],'config':{'size':123}}).encode()
    digest='sha256:'+hashlib.sha256(body).hexdigest()
    async def handler(request):
        if '/manifests/' in str(request.url):
            return httpx.Response(200,json={'manifests':[{'runner':'llamacpp','digest':'sha256:'+'0'*64},{'runner':'mlx','digest':digest}]})
        assert str(request.url).endswith(digest)
        return httpx.Response(200,content=body)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await registry_size(client,'library/embeddinggemma-2','270m')==378000123
    asyncio.run(run())


def test_installed_model_preflight_works_offline(service,monkeypatch):
    local=service.news_digest.local
    local.installed={'custom:small':300000000}
    async def offline(*a,**k): raise AssertionError('Installed model should not need the registry')
    async def metadata(): return 0
    monkeypatch.setattr(httpx.AsyncClient,'get',offline)
    monkeypatch.setattr(local.runner,'metadata',metadata)
    result=asyncio.run(local.inspect('custom:small'))
    assert result['size']==300000000 and result['can_download']


def test_multiple_chunks_share_one_short_model_residency(monkeypatch):
    from ollama import Client
    requests = []
    def embed(self, **kwargs):
        requests.append(kwargs)
        return {'embeddings':[[3.,4.]]}
    monkeypatch.setattr(Client,'embed',embed)
    monkeypatch.setattr(httpx.Client,'get',lambda *a,**k:httpx.Response(200,json={'models':[{'name':'embeddinggemma-2:270m','digest':'abc'}]},request=httpx.Request('GET','http://local')))
    encoder=LocalNewsEmbeddings(dimensions=2,digest='abc')
    assert len(encoder.encode(['one','two','three','four'])) == 4
    assert [r['keep_alive'] for r in requests] == ['5s','5s','5s',0]
