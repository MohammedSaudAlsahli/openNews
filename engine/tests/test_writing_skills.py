import asyncio
import json
import pytest
from eis_engine.writing_skills import WritingSkills, explicit, catalog
from eis_engine.storage import Store
from eis_engine.contracts import Failure, ChatReply
from test_conversation import service, setup, finish


def test_commands_only_apply_at_start():
    assert explicit('/linkedin اكتب عن تجربتي') == 'linkedin'
    assert explicit('/X draft a post') == 'x'
    for message in ['https://x.com/example', 'اشرح /youtube', '"/x"', 'ما هو لينكدإن؟', '/tmp/file']:
        assert explicit(message) is None
    with pytest.raises(Failure): explicit('/typo text')


def test_lazy_guides_are_editable_bounded_and_traversal_safe(tmp_path):
    store=Store(tmp_path); events=[]
    skills=WritingSkills(store, lambda *args: events.append(args))
    root=store.path.parent/'instructions'/'skills'
    assert not root.exists()
    assert 'error' in json.loads(skills.load_editorial_skill('../secrets'))
    assert not root.exists()
    first=skills.load_editorial_skill('linkedin')
    assert len(list(root.glob('*.md')))==1
    assert skills.load_editorial_skill('linkedin')==first and len(events)==1
    (root/'linkedin.md').write_text('My voice preference')
    assert 'My voice preference' in WritingSkills(store).load_editorial_skill('linkedin')
    skills.load_editorial_skill('x');skills.load_editorial_skill('hooks')
    assert 'error' in json.loads(skills.load_editorial_skill('plan'))
    store.close()


def test_explicit_skill_overrides_old_mode_and_saves_linkedin(service):
    async def run():
        payload=await setup(service,message='/linkedin اكتب عن التعلم المستمر',format='tiktok',include_news=True)
        service.factory.reply=ChatReply(message='مسودة مقترحة',drafts=[{'title':'التعلم','text':'أخصص وقتًا للتعلم.','format':'linkedin','evidence_basis':'original'}])
        job=await finish(service,payload)
        assert job['state']=='completed'
        _, instructions, data=service.factory.calls[0]
        assert data['format']=='linkedin' and data['selected_skill']['skill_id']=='linkedin'
        assert 'Infer the requested task' in instructions
        assert service.store.one('SELECT format FROM drafts')['format']=='linkedin'
    asyncio.run(run())


def test_auto_has_catalog_without_eager_loading_or_keyword_routing(service):
    async def run():
        payload=await setup(service,message='ما الفرق بين يوتيوب ولينكدإن؟')
        job=await finish(service,payload)
        assert job['state']=='completed'
        data=service.factory.calls[0][2]
        assert data['format']=='auto' and 'selected_skill' not in data
        assert len(data['editorial_skills'])==len(catalog()['skills'])
        assert service.store.rows('SELECT id FROM drafts')==[]
        assert not (service.store.path.parent/'instructions'/'skills').exists()
    asyncio.run(run())


def test_unknown_slash_never_creates_job(service):
    async def run():
        payload=await setup(service,message='/unknown hello')
        with pytest.raises(Failure): await service.dispatch('chat.send',payload)
        assert not service.store.rows("SELECT id FROM jobs WHERE type='chat.send'")
    asyncio.run(run())
