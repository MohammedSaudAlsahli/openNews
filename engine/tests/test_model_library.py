import asyncio
from types import SimpleNamespace
from eis_engine.model_library import ModelLibrary, parse_search, parse_variants
from eis_engine import model_capacity

def test_catalog_pagination_and_capabilities():
    result=parse_search('<li><a href="/library/example"><h2>Example</h2><p>Small model</p><span>tools</span></a></li><li hx-trigger="revealed" hx-get="/search?page=2"></li>')
    assert result['has_more']
    assert result['models'][0]['id']=='example'
    assert result['models'][0]['capabilities']==['tools']

def test_variants_keep_sizes_deduplicate_and_mark_cloud():
    result=parse_variants('<a href="/library/example:2b">2b 1.5GB</a><a href="/library/example:2b">2b</a><a href="/library/example:cloud">cloud</a>','example')
    assert result['variants']==[{'id':'example:2b','size':1500000000,'cloud':False},{'id':'example:cloud','size':None,'cloud':True}]

def test_paged_fetch_uses_library_fragment_header(monkeypatch):
    import httpx
    calls=[]
    async def get(self,url,**kwargs):
        calls.append(kwargs)
        return httpx.Response(200,text='<li></li>',request=httpx.Request('GET',url))
    monkeypatch.setattr(httpx.AsyncClient,'get',get)
    asyncio.run(ModelLibrary().search('',2))
    assert calls[0]['headers']=={'HX-Request':'true'}
    assert calls[0]['params']=={'page':2}

def test_capacity_distinguishes_disk_and_memory(tmp_path,monkeypatch):
    gb=10**9
    monkeypatch.setattr(model_capacity,'physical_memory',lambda:8*gb)
    monkeypatch.setattr(model_capacity.shutil,'disk_usage',lambda path:SimpleNamespace(free=3*gb))
    assert model_capacity.capacity(tmp_path,2*gb)['fit']=='disk'
    monkeypatch.setattr(model_capacity.shutil,'disk_usage',lambda path:SimpleNamespace(free=100*gb))
    assert model_capacity.capacity(tmp_path,6*gb)['fit']=='memory'
    plan=model_capacity.capacity(tmp_path,2*gb,runtime_size=200000000)
    assert plan['can_download'] and plan['required_disk']==4600000000
    assert model_capacity.capacity(tmp_path,2*gb,installed=True)['required_disk']==2*gb
