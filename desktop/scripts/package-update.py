"""Prepare a signed updater artifact from an existing verified GitHub release.

No application rebuild, private-key export, upload or feed publication occurs here.
Publish only after test-update.py passes with this exact archive/signature pair.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import tarfile
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[2]
REPO = 'MohammedSaudAlsahli/openNews'
config = json.loads((ROOT / 'desktop/src-tauri/tauri.conf.json').read_text())
parser = argparse.ArgumentParser()
parser.add_argument('--version', default=config['version'])
parser.add_argument('--output', type=Path)
args = parser.parse_args()
assert re.fullmatch(r'\d+\.\d+\.\d+', args.version)
version = args.version
tag = f'v{version}'
output = (args.output or ROOT / f'build/updater/{tag}').resolve()
assert not list(output.glob('*.app.tar.gz')), 'Existing signed artifacts must not be overwritten'
key = Path.home() / '.local/share/OpenStudio/release-signing/tauri-preview.key'
assert key.is_file(), 'Existing release key missing; do not generate a replacement'
assert key.stat().st_mode & 0o077 == 0, 'Private release key must be owner-only'
assert key.with_suffix('.key.pub').read_text().strip() == config['plugins']['updater']['pubkey'], 'Release public key mismatch'

def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPO}/{path}'], text=True))

release = api(f'releases/tags/{tag}')
assert not release['draft'] and not release['prerelease']
output.mkdir(parents=True, exist_ok=True)
source_info = re.search(r'<!-- opennews-build-info\n(.*?)\n-->', release['body'], re.S)
assert source_info, 'Release is missing its CI build provenance'
metadata = json.loads(source_info.group(1))
assert metadata['version'] == version and metadata['architecture'] == 'arm64'
run_id = metadata['ci_run'].rsplit('/', 1)[-1]
assert run_id.isdigit()
run = api(f'actions/runs/{run_id}')
assert run['conclusion'] == 'success' and run['head_sha'] == metadata['commit']
assert run['status'] == 'completed' and run['head_repository']['full_name'] == REPO
assert metadata['ci_run'] == f'https://github.com/{REPO}/actions/runs/{run_id}'
assert run['path'] == '.github/workflows/ci.yml' and run['event'] == 'push' and run['head_branch'] == 'main'
ref = api(f'git/ref/tags/{tag}')['object']
assert ref['type'] == 'tag'
assert api(f'git/tags/{ref["sha"]}')['object']['sha'] == metadata['commit']
dmg_name = f'openNews-{version}-macOS-arm64.dmg'
source_asset = next(asset for asset in release['assets'] if asset['name'] == dmg_name)
assert source_asset['state'] == 'uploaded'
assert re.fullmatch(r'sha256:[a-f0-9]{64}', source_asset['digest'])
subprocess.run(['gh', 'release', 'download', tag, '--repo', REPO, '--dir', str(output), '--skip-existing', '--pattern', dmg_name], check=True)
with (output / dmg_name).open('rb') as stream:
    source_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
assert 'sha256:' + source_digest == source_asset['digest'], 'Published DMG checksum mismatch'
subprocess.run(['hdiutil', 'verify', str(output / dmg_name)], check=True)
archive = output / f'openNews-{version}-macOS-arm64.app.tar.gz'
# Keep extracted bundles outside FileProvider-managed Documents; Finder metadata
# there can invalidate an otherwise unchanged Apple code signature.
if (output / 'extracted').exists():
    shutil.rmtree(output / 'extracted')  # obsolete generated staging only
with tempfile.TemporaryDirectory(prefix='opennews-update-stage-', dir='/tmp') as staging:
    stage = Path(staging)
    mount = stage / 'mounted'
    subprocess.run(['hdiutil', 'attach', str(output / dmg_name), '-mountpoint', str(mount), '-nobrowse', '-noautoopen', '-readonly'], check=True, stdout=subprocess.DEVNULL)
    try:
        subprocess.run(['ditto', str(mount / 'openNews.app'), str(stage / 'openNews.app')], check=True)
    finally:
        subprocess.run(['hdiutil', 'detach', str(mount)], check=True, stdout=subprocess.DEVNULL)
    app = stage / 'openNews.app'
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    assert info['CFBundleShortVersionString'] == version
    assert info['CFBundleIdentifier'] == config['identifier']
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    subprocess.run(['lipo', str(app / 'Contents/MacOS' / info['CFBundleExecutable']), '-verify_arch', 'arm64'], check=True)
    with tarfile.open(archive, 'w:gz', compresslevel=6, dereference=False) as bundle:
        bundle.add(app, arcname='openNews.app')
# Pass the key path only. Never print or copy private signing material.
signed = subprocess.run(['npm', '--prefix', str(ROOT / 'desktop'), 'run', 'tauri', '--', 'signer', 'sign', '--private-key-path', str(key), '--password', '', '--app-version', version, str(archive)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
assert signed.returncode == 0, 'Could not sign with the existing release key'
signature = archive.with_suffix(archive.suffix + '.sig')
assert signature.is_file()
manifest = {'version': version, 'pub_date': release['published_at'], 'notes': 'تحديث openNews الرسمي مع إبقاء المقالات والحسابات والنماذج.\n\nOfficial openNews update; articles, accounts and downloaded models are retained.', 'platforms': {'darwin-aarch64': {'url': f'https://github.com/{REPO}/releases/download/{tag}/{archive.name}', 'signature': signature.read_text().strip()}}}
(output / 'tauri-preview.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
with (output / 'updater-SHA256SUMS').open('w') as checks:
    for path in (archive, signature):
        with path.open('rb') as stream:
            checks.write(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {path.name}\n')
(output / 'update-build-info.json').write_text(json.dumps({'version': version, 'source_commit': metadata['commit'], 'source_ci_run': metadata['ci_run'], 'source_dmg_sha256': source_digest, 'archive': archive.name, 'signed_version_required': True, 'prepared_at': datetime.now(timezone.utc).isoformat()}, indent=2) + '\n')
print(f'Prepared signed {version} updater from successful CI artifact. Test before uploading or publishing the manifest.')
