import fcntl
import importlib.util
from pathlib import Path
import sqlite3
import pytest
spec=importlib.util.spec_from_file_location('workspace_transfer',Path(__file__).parents[1]/'workspace_transfer.py')
transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer)

def workspace(path):
    path.mkdir(); db=sqlite3.connect(path/'editorial.sqlite')
    for name in ('news_articles','conversations','provider_profiles','drafts'):
        db.execute('CREATE TABLE '+name+'(id TEXT)');db.execute('INSERT INTO '+name+" VALUES('preserved')")
    db.commit();db.close();return path

def test_copy_preserves_original_and_backs_up_destination(tmp_path):
    source=workspace(tmp_path/'source'); destination=workspace(tmp_path/'preview')
    (source/'reader-images').mkdir();(source/'reader-images'/'cover.image').write_bytes(b'cached')
    result=transfer.transfer(source,destination)
    assert result['counts']['news_articles']==1
    assert (destination/'reader-images'/'cover.image').read_bytes()==b'cached'
    assert (source/'editorial.sqlite').exists()
    assert (Path(result['backup'])/'editorial.sqlite').exists()

def test_active_source_and_external_links_are_rejected(tmp_path):
    source=workspace(tmp_path/'source')
    with (source/'engine.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(ValueError,match='Quit'):transfer.transfer(source,tmp_path/'preview')
    (source/'outside').symlink_to(tmp_path/'elsewhere')
    with pytest.raises(ValueError,match='outside'):transfer.transfer(source,tmp_path/'preview')

def test_restore_keeps_both_workspaces_recoverable(tmp_path):
    source=workspace(tmp_path/'source');destination=workspace(tmp_path/'preview')
    (destination/'preview-marker').write_text('old preview')
    transfer.transfer(source,destination)
    assert not (destination/'preview-marker').exists()
    result=transfer.restore(destination)
    assert (destination/'preview-marker').read_text()=='old preview'
    assert Path(result['backup']).is_dir()

def test_absolute_internal_links_are_rebased_to_copy(tmp_path):
    source=workspace(tmp_path/'source');destination=tmp_path/'preview'
    (source/'asset').write_text('original')
    (source/'link').symlink_to(source/'asset')
    transfer.transfer(source,destination)
    assert (destination/'link').resolve()==destination/'asset'
    (destination/'link').write_text('preview')
    assert (source/'asset').read_text()=='original'
