"""Exercise publication gates without network access or a real release mutation."""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest


def publish_fixture(tmp_path, monkeypatch, fault=None):
    root = tmp_path / 'repo'
    (root / 'scripts').mkdir(parents=True)
    (root / 'desktop').mkdir()
    (root / 'docs/releases').mkdir(parents=True)
    script = root / 'scripts/publish_tauri_release.py'
    shutil.copyfile(Path(__file__).parents[2] / 'scripts/publish_tauri_release.py', script)
    (root / 'desktop/package.json').write_text('{"version":"1.2.3"}')
    (root / 'docs/releases/v1.2.3.md').write_text('ملاحظات الإصدار\nEnglish notes\n')
    commit = 'a' * 40
    repo = 'MohammedSaudAlsahli/openNews'
    run = {'conclusion': 'success', 'status': 'completed', 'head_sha': commit,
           'head_branch': 'main', 'event': 'push', 'path': '.github/workflows/ci.yml',
           'head_repository': {'full_name': repo}, 'html_url': f'https://github.com/{repo}/actions/runs/123'}
    published = {'openNews-1.2.3-macOS-arm64.dmg', 'openNews-1.2.3-SHA256SUMS.txt'}
    captured = []

    def output(command, **kwargs):
        if command[:2] == ('git', 'cat-file'):
            return 'tag'
        if command[:2] == ('git', 'rev-parse'):
            return commit
        if command[:2] == ('git', 'ls-remote'):
            return commit + '\trefs/tags/v1.2.3^{}'
        if command[:2] == ('gh', 'api'):
            return json.dumps(run)
        if command[:3] == ('gh', 'release', 'view'):
            return json.dumps({'url': 'https://example.org/release', 'isDraft': False,
                               'isPrerelease': False, 'assets': [{'name': name} for name in published]})
        raise AssertionError(command)

    def execute(command, **kwargs):
        if command[:3] == ['gh', 'run', 'download']:
            destination = Path(command[command.index('--dir') + 1])
            metadata = {'version': '1.2.3', 'architecture': 'arm64',
                        'commit': 'b' * 40 if fault == 'provenance' else commit, 'ci_run': run['html_url']}
            files = {'openNews-1.2.3-macOS-arm64.zip': b'CI ZIP',
                     'openNews-1.2.3-macOS-arm64.dmg': b'CI DMG',
                     'build-info.json': json.dumps(metadata).encode()}
            sums = []
            for name, data in files.items():
                (destination / name).write_bytes(data)
                sums.append(f'{hashlib.sha256(data).hexdigest()}  {name}')
            (destination / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
            if fault == 'checksum':
                (destination / 'openNews-1.2.3-macOS-arm64.dmg').write_bytes(b'tampered')
            if fault == 'missing':
                (destination / 'openNews-1.2.3-macOS-arm64.dmg').unlink()
        elif command[:3] == ['gh', 'release', 'create']:
            notes = Path(command[command.index('--notes-file') + 1]).read_text()
            assets = {Path(item).name for item in command if Path(item).is_file()}
            assets.discard('release-notes.md')
            captured.append((notes, assets))
        else:
            raise AssertionError(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, 'check_output', output)
    monkeypatch.setattr(subprocess, 'run', execute)
    monkeypatch.setattr(sys, 'argv', [str(script), '--tag', 'v1.2.3', '--run-id', '123'])
    monkeypatch.setenv('GITHUB_REPOSITORY', repo)
    return script, captured, published


def test_release_publishes_installer_without_intermediate_or_reports(tmp_path, monkeypatch):
    script, captured, expected = publish_fixture(tmp_path, monkeypatch)
    runpy.run_path(str(script), run_name='__main__')
    notes, assets = captured[0]
    assert assets == expected
    assert 'تحميل openNews' in notes and 'Download for Mac' in notes
    assert '<!-- opennews-build-info\n' in notes and '"commit": "' + 'a' * 40 in notes


@pytest.mark.parametrize('fault', ['checksum', 'missing', 'provenance'])
def test_release_rejects_unverified_installer_before_publication(tmp_path, monkeypatch, fault):
    script, captured, _ = publish_fixture(tmp_path, monkeypatch, fault)
    with pytest.raises(AssertionError):
        runpy.run_path(str(script), run_name='__main__')
    assert captured == []
