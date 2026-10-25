"""Publish an existing immutable tag using its successful main-branch CI artifact."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--tag', required=True)
parser.add_argument('--run-id', required=True)
args = parser.parse_args()
assert re.fullmatch(r'v\d+\.\d+\.\d+', args.tag), 'Official release tag required'
assert re.fullmatch(r'\d+', args.run_id), 'Numeric CI run ID required'
repo = os.environ.get('GITHUB_REPOSITORY', 'MohammedSaudAlsahli/openNews')
assert repo == 'MohammedSaudAlsahli/openNews', 'Publication is limited to the official repository'

def output(*command):
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()

version = json.loads((ROOT / 'desktop/package.json').read_text())['version']
assert args.tag == f'v{version}'
assert output('git', 'cat-file', '-t', args.tag) == 'tag', 'Annotated release tag required'
commit = output('git', 'rev-parse', f'{args.tag}^{{commit}}')
assert output('git', 'rev-parse', 'HEAD') == commit, 'Check out the tagged source first'
run = json.loads(output('gh', 'api', f'repos/{repo}/actions/runs/{args.run_id}'))
assert run['conclusion'] == 'success' and run['status'] == 'completed'
assert run['head_sha'] == commit and run['head_branch'] == 'main' and run['event'] == 'push'
assert run['path'] == '.github/workflows/ci.yml'
assert run['head_repository']['full_name'] == repo
remote_tag = output('git', 'ls-remote', 'origin', f'refs/tags/{args.tag}^{{}}').split()[0]
assert remote_tag == commit, 'Published tag does not match the tested source'
notes = ROOT / 'docs/releases' / f'{args.tag}.md'
assert notes.is_file()
with tempfile.TemporaryDirectory(prefix='opennews-publish-') as temporary:
    directory = Path(temporary)
    subprocess.run(['gh', 'run', 'download', args.run_id, '--repo', repo, '--name', 'openNews-macOS-arm64', '--dir', str(directory)], check=True)
    dmg_name = f'openNews-{version}-macOS-arm64.dmg'
    expected = {f'openNews-{version}-macOS-arm64.zip', dmg_name, 'build-info.json', 'SHA256SUMS'}
    assert {p.name for p in directory.iterdir()} == expected, 'Unexpected release artifact contents'
    sums = (directory / 'SHA256SUMS').read_text().splitlines()
    assert len(sums) == len(expected) - 1
    checked = set()
    for line in sums:
        digest, name = line.split('  ', 1)
        assert name in expected - {'SHA256SUMS'} and name not in checked
        assert re.fullmatch('[a-f0-9]{64}', digest)
        with (directory / name).open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest, f'Checksum mismatch: {name}'
        checked.add(name)
    metadata = json.loads((directory / 'build-info.json').read_text())
    assert metadata['version'] == version and metadata['commit'] == commit and metadata['architecture'] == 'arm64'
    assert metadata['ci_run'] == run['html_url']
    # CI keeps intermediate ZIP/build metadata. Users see the installer and its
    # checksum; updater assets are appended only after the signed upgrade test.
    checksum = directory / f'openNews-{version}-SHA256SUMS.txt'
    with (directory / dmg_name).open('rb') as stream:
        checksum.write_text(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {dmg_name}\n')
    release_notes = directory / 'release-notes.md'
    download_url = f'https://github.com/{repo}/releases/download/{args.tag}/{dmg_name}'
    note_text = re.sub(r'\]\(\.\./([^\s)]+)\)', rf'](https://github.com/{repo}/blob/{args.tag}/docs/\1)', notes.read_text())
    release_notes.write_text(
        f'**[تحميل openNews لأجهزة Mac — DMG]({download_url})** · **[Download for Mac — DMG]({download_url})**\n\n'
        'افتح الملف واسحب openNews إلى Applications. بقية ملفات التحديث يستخدمها التطبيق تلقائيًا.\n\n'
        'Open the image and drag openNews to Applications. Update files are used automatically by the app.\n\n'
        + note_text + f'\n\n[CI / مصدر البناء]({run["html_url"]})\n\n'
        + '<!-- opennews-build-info\n' + json.dumps(metadata, indent=2) + '\n-->\n'
    )
    published = {dmg_name, checksum.name}
    # No --clobber: an existing release/tag must be inspected, never silently replaced.
    subprocess.run(['gh', 'release', 'create', args.tag, '--repo', repo, '--verify-tag', '--latest', '--title', f'openNews {version}', '--notes-file', str(release_notes), *(str(directory / name) for name in sorted(published))], check=True)
    release = json.loads(output('gh', 'release', 'view', args.tag, '--repo', repo, '--json', 'url,isDraft,isPrerelease,assets'))
    assert not release['isDraft'] and not release['isPrerelease']
    assert {asset['name'] for asset in release['assets']} == published
    print(release['url'])
