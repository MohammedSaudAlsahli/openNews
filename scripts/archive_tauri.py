"""Validate a relocated release bundle, then archive only CI-built application bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import socket
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=ROOT / 'build/release')
parser.add_argument('--app', type=Path, default=ROOT / 'desktop/src-tauri/target/release/bundle/macos/openNews.app')
args = parser.parse_args()
version = json.loads((ROOT / 'desktop/package.json').read_text())['version']
source = args.app.resolve()
assert os.uname().machine == 'arm64', 'This distribution requires an arm64 build host'
info = plistlib.loads((source / 'Contents/Info.plist').read_bytes())
assert info['CFBundleShortVersionString'] == version
assert info['CFBundleIdentifier'] == 'com.editorialintelligence.studio.preview'
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(source)], check=True)
# Relocate and exercise the packaged runtime; never open a user's workspace.
with tempfile.TemporaryDirectory(prefix='opennews-release-', dir='/tmp') as temporary:
    temp = Path(temporary)
    app = temp / 'openNews.app'
    subprocess.run(['ditto', str(source), str(app)], check=True)
    runtime = app / 'Contents/Resources/runtime'
    assert (runtime / 'OPENNEWS-LICENSE.txt').is_file()
    assert not list((runtime / 'engine').rglob('* 2.py')), 'Duplicate source copy in bundle'
    subprocess.run(['lipo', str(app / 'Contents/MacOS' / info['CFBundleExecutable']), '-verify_arch', 'arm64'], check=True)
    address = temp / 'engine.sock'
    environment = {'HOME': str(temp), 'PATH': '/usr/bin:/bin', 'LANG': 'en_US.UTF-8', 'AGNO_TELEMETRY': 'false'}
    process = subprocess.Popen([str(runtime / 'python/bin/python3.12'), '-I', '-B', str(runtime / 'engine/bootstrap.py'), '--workspace', str(temp / 'workspace'), '--socket', str(address)], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 30
        while not address.exists():
            assert process.poll() is None, 'Relocated engine exited before readiness'
            assert time.monotonic() < deadline, 'Relocated engine startup timed out'
            time.sleep(.1)
        request_id = str(uuid.uuid4())
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
            stream.settimeout(30)
            stream.connect(str(address))
            stream.sendall((json.dumps({'schema_version': 1, 'request_id': request_id, 'command': 'runtime.health', 'payload': {}}) + '\n').encode())
            result = json.loads(stream.makefile('rb').readline(1024 * 1024))
        assert result['request_id'] == request_id and result['event'] == 'completed'
        assert result['result']['schema_version'] == 1 and isinstance(result['result']['sqlite_vec'], str)
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise AssertionError('Relocated engine failed to stop cleanly')
    assert process.returncode == 0, 'Relocated engine did not exit cleanly'

output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
archive = output / f'openNews-{version}-macOS-arm64.zip'
assert not archive.exists(), 'Refusing to overwrite a release archive'
subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(source), str(archive)], check=True)
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
run_url = None
if os.environ.get('GITHUB_RUN_ID'):
    run_url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
metadata = output / 'build-info.json'
metadata.write_text(json.dumps({'version': version, 'commit': sha, 'ci_run': run_url, 'platform': 'macOS', 'architecture': 'arm64', 'declared_minimum_macos': '14.0', 'signing': 'ad-hoc', 'apple_notarized': False, 'automatic_update_feed_published': False}, indent=2) + '\n')
with (output / 'SHA256SUMS').open('w') as sums:
    for path in (archive, metadata):
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        sums.write(f'{digest}  {path.name}\n')
print(f'Relocated packaged engine, architecture and signature passed; archive: {archive.name}')
