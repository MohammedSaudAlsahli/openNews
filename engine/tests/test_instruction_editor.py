from types import SimpleNamespace
import pytest
from eis_engine.editorial_instructions import dispatch, load, DEFAULTS
from eis_engine.contracts import Failure


def test_editor_roundtrip_and_generation(tmp_path):
    store = SimpleNamespace(path=tmp_path / 'editorial.sqlite')
    current = dispatch(store, 'instructions.get', {'id': 'article-summary'})
    assert current['content'] == DEFAULTS['article-summary']
    custom = 'اشرح الخلفية والنتائج بالتفصيل مع الحفاظ على الأرقام.'
    dispatch(store, 'instructions.save', {'id':'article-summary', 'content':custom})
    assert load(store, 'article-summary') == custom
    assert dispatch(store, 'instructions.get', {'id':'article-summary'})['content'] == custom
    assert dispatch(store, 'instructions.reset', {'id':'article-summary'})['content'] == DEFAULTS['article-summary']


def test_daily_and_skill_preserve_existing(tmp_path):
    store = SimpleNamespace(path=tmp_path / 'editorial.sqlite')
    for key in ['daily-report', 'skill:linkedin']:
        dispatch(store, 'instructions.save', {'id':key, 'content':'My existing instructions'})
        assert dispatch(store, 'instructions.get', {'id':key})['content'] == 'My existing instructions'
    assert load(store, 'daily-report') == 'My existing instructions'
    assert (tmp_path/'instructions/skills/linkedin.md').read_text() == 'My existing instructions'


@pytest.mark.parametrize('payload', [{'id':'../../outside','content':'bad'}, {'id':'article-summary','content':''}, {'id':'skill:x','content':'x'*12001}, {'id':'article-summary','content':42}])
def test_editor_rejects_invalid_without_overwrite(tmp_path, payload):
    store = SimpleNamespace(path=tmp_path / 'editorial.sqlite')
    dispatch(store, 'instructions.save', {'id':'article-summary','content':'Keep this'})
    with pytest.raises(Failure): dispatch(store, 'instructions.save', payload)
    assert load(store, 'article-summary') == 'Keep this'
