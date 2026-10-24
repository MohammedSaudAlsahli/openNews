import asyncio
import base64
import json
import pytest
import httpx
from eis_engine.contracts import Failure
from eis_engine.storage import Store
from eis_engine import custom_skills, skill_discovery
from eis_engine.editorial_instructions import dispatch
from eis_engine.writing_skills import catalog, explicit, WritingSkills
from test_conversation import service, setup, finish

SKILL = {'id': 'newsletter', 'title': 'نشرة أسبوعية', 'description': 'حوّل المصادر إلى نشرة موثقة', 'content': 'Preserve sources. Write a useful newsletter.'}


def test_add_reload_edit_reset_remove_and_paths(tmp_path):
    store = Store(tmp_path)
    try:
        custom_skills.add(store, SKILL)
        row = next(r for r in catalog(store)['skills'] if r['id'] == 'newsletter')
        assert row['origin'] == 'custom' and row['format'] == 'auto'
        assert explicit('/newsletter draft', store) == 'newsletter'
        assert 'Preserve sources' in WritingSkills(store).load_editorial_skill('newsletter')
        dispatch(store, 'instructions.save', {'id': 'skill:newsletter', 'content': 'Edited'})
        assert 'Edited' in WritingSkills(store).load_editorial_skill('newsletter')
        assert dispatch(store, 'instructions.reset', {'id': 'skill:newsletter'})['content'] == SKILL['content']
        with pytest.raises(Failure): custom_skills.add(store, SKILL)
        for name in ['../escape', 'a/b', 'research', 'A Name', 'x'*41]:
            with pytest.raises(Failure): custom_skills.add(store, {**SKILL, 'id': name})
        with pytest.raises(Failure): custom_skills.add(store, {**SKILL, 'id': 'long-skill', 'content': 'x'*12001})
        with pytest.raises(Failure): custom_skills.remove(store, 'research')
        custom_skills.remove(store, 'newsletter')
        with pytest.raises(Failure): explicit('/newsletter draft', store)
    finally: store.close()


def test_corrupt_registry_is_not_replaced(tmp_path):
    store = Store(tmp_path)
    path = store.path.parent/'instructions/custom-skills.json';path.parent.mkdir(exist_ok=True);path.write_text('broken')
    with pytest.raises(Failure): custom_skills.add(store, SKILL)
    assert path.read_text() == 'broken';store.close()


def test_custom_command_uses_saved_instructions_and_keeps_auto_format(service):
    async def run():
        await service.dispatch('skills.add', SKILL)
        payload = await setup(service, message='/newsletter اكتب نشرة', format='auto')
        job = await finish(service, payload)
        assert job['state'] == 'completed'
        model_payload = service.factory.calls[0][2]
        assert model_payload['selected_skill']['skill_id'] == 'newsletter'
        assert model_payload['selected_skill']['instructions'] == SKILL['content']
        assert model_payload['format'] == 'auto'
    asyncio.run(run())


@pytest.mark.parametrize('url', ['http://github.com/a/b', 'https://localhost/a/b', 'https://github.com.evil/a/b', 'https://user@github.com/a/b', 'https://github.com/a/b/tree/main/%2e%2e/secret'])
def test_discovery_refuses_other_hosts_and_ambiguous_paths(url):
    with pytest.raises(Failure): skill_discovery.source_parts(url)


def test_preview_pins_revision_and_never_fetches_scripts(monkeypatch):
    paths=[]
    text='---\nname: article-guide\ndescription: Write useful articles.\nlicense: MIT\n---\n# Guide\nPreserve facts.'
    def transport(request):
        paths.append(request.url.path)
        path=request.url.path
        if path.endswith('/repos/a/b'): return httpx.Response(200,json={'default_branch':'main','license':{'spdx_id':'MIT'}})
        if '/commits/' in path: return httpx.Response(200,json={'sha':'c'*40})
        if '/git/trees/' in path: return httpx.Response(200,json={'tree':[{'path':'skills/article-guide/SKILL.md','type':'blob','sha':'b'*40,'size':len(text)},{'path':'skills/article-guide/scripts/run.sh','type':'blob','sha':'d'*40}]})
        if '/git/blobs/' in path: return httpx.Response(200,json={'content':base64.b64encode(text.encode()).decode()})
        raise AssertionError(path)
    original=httpx.AsyncClient
    monkeypatch.setattr(skill_discovery.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(transport),**kwargs))
    result=asyncio.run(skill_discovery.preview('https://skills.sh/a/b/article-guide'))
    assert result['source_url']=='https://github.com/a/b/blob/'+('c'*40)+'/skills/article-guide/SKILL.md'
    assert result['content']=='# Guide\nPreserve facts.' and result['supporting_files'] is True
    assert not any('run.sh' in path for path in paths)


def test_search_filters_unusable_directory_results(monkeypatch):
    original=httpx.AsyncClient
    data={'skills':[{'source':'a/b','name':'article-guide'},{'source':'../../bad','name':'bad'}]}
    monkeypatch.setattr(skill_discovery.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=data)),**kwargs))
    result=asyncio.run(skill_discovery.search('article writing'))
    assert len(result['skills'])==1 and result['source']=='skills.sh'


def test_redirects_stay_on_the_directory_or_github_api(monkeypatch):
    calls=[]
    def transport(request):
        calls.append(str(request.url))
        if len(calls)==1: return httpx.Response(301,headers={'location':'https://api.github.com/repositories/123'})
        return httpx.Response(200,json={'name':'ok'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            assert await skill_discovery.fetch_json(client,'https://api.github.com/repos/a/b')=={'name':'ok'}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(302,headers={'location':'http://127.0.0.1/private'}))) as client:
            with pytest.raises(Failure): await skill_discovery.fetch_json(client,'https://api.github.com/repos/a/b')
    asyncio.run(run());assert len(calls)==2


def test_assistant_can_discover_but_does_not_install(tmp_path, monkeypatch):
    store=Store(tmp_path)
    async def search(query): return {'skills':[{'id':'a/b/guide','source_url':'https://skills.sh/a/b/guide'}], 'query':query}
    monkeypatch.setattr(skill_discovery,'search',search)
    async def run():
        result=json.loads(await WritingSkills(store).find_writing_skills('article writing'))
        assert result['skills'] and 'not installed' in result['scope']
        assert custom_skills.read(store)=={}
    asyncio.run(run());store.close()


def test_assistant_discovery_requires_web_research(service):
    from test_conversation import FakeChatModel
    async def run():
        class ToolModel(FakeChatModel):
            supports_tools=True
            async def run(self,profile,instructions,payload,schema,tools=None,on_turn=None):
                names={tool.__name__ for tool in tools}
                assert 'find_writing_skills' not in names and 'inspect_writing_skill' not in names
                return self.reply
        service.factory=ToolModel()
        job=await finish(service,await setup(service,research_web=False,message='ابحث عن مهارات للكتابة'))
        assert job['state']=='completed'
    asyncio.run(run())


def test_direct_file_preview_does_not_enumerate_a_large_repository(monkeypatch):
    paths=[]
    def transport(request):
        paths.append(request.url.path)
        if request.url.path.endswith('/repos/a/b'): return httpx.Response(200,json={'default_branch':'main'})
        if '/commits/' in request.url.path: return httpx.Response(200,json={'sha':'c'*40})
        if '/contents/' in request.url.path: return httpx.Response(200,json={'type':'file','encoding':'base64','sha':'b'*40,'content':base64.b64encode(b'---\nname: guide\ndescription: Write clearly\n---\n# Guide\nRead references/style.md').decode(),'size':100})
        raise AssertionError('Direct file preview must not request a tree')
    original=httpx.AsyncClient
    monkeypatch.setattr(skill_discovery.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(transport),**kwargs))
    result=asyncio.run(skill_discovery.preview('https://github.com/a/b/blob/main/skills/guide/SKILL.md?plain=1#L1'))
    assert result['supporting_files'] is True and result['id']=='guide'
    assert len(paths)==3
