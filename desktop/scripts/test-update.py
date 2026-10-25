"""Exercise the real pinned updater between two complete app bundles in /tmp.

No user workspace is opened and /Applications is read-only. Seed synthetic data
with the old packaged engine, update its copy, then reopen the new packaged engine.
Run native Cargo tests first so matching test-enabled crates are available.
"""
import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--prepared', type=Path, required=True)
parser.add_argument('--old-app', type=Path, default=Path('/Applications/openNews.app'))
parser.add_argument('--public', action='store_true', help='Check and download the public feed instead of using local archive bytes')
args = parser.parse_args()
prepared = args.prepared.resolve()
manifest = json.loads((prepared / 'tauri-preview.json').read_text())
version = manifest['version']
old_info = plistlib.loads((args.old_app / 'Contents/Info.plist').read_bytes())
old_version = old_info['CFBundleShortVersionString']
assert old_version != version, 'Two distinct app versions are required'
archive = prepared / f'openNews-{version}-macOS-arm64.app.tar.gz'
assert archive.is_file()
# Reuse pinned app dependencies; compile the standalone harness without walking
# or rebuilding the very large Tauri resource tree in a FileProvider checkout.
deps = ROOT / 'desktop/src-tauri/target/debug/deps'
choices = []
for fingerprint in deps.parent.glob('.fingerprint/tauri-*/lib-tauri.json'):
    if '"test"' in json.loads(fingerprint.read_text())['features']:
        library = deps / f'lib{fingerprint.parent.name}.rlib'
        if library.is_file():
            choices.append(library)
assert choices, 'Run the native Cargo tests before compiling the updater harness'
libs = {'tauri': max(choices, key=lambda p: p.stat().st_mtime)}
for name in ('tauri_plugin_updater', 'serde_json'):
    libs[name] = max(deps.glob(f'lib{name}-*.rlib'), key=lambda p: p.stat().st_mtime)
binary = ROOT / 'build/updater-upgrade-qa'
command = ['rustc', '--edition=2021', str(ROOT / 'desktop/qa/updater-upgrade.rs'), '-L', f'dependency={deps}', '-o', str(binary)]
for name, library in libs.items():
    command.extend(['--extern', f'{name}={library}'])
subprocess.run(command, check=True)

with tempfile.TemporaryDirectory(prefix='opennews-update-qa-', dir='/tmp') as temporary:
    temp = Path(temporary)
    app = temp / 'openNews.app'
    subprocess.run(['ditto', str(args.old_app), str(app)], check=True)
    workspace = temp / 'workspace'
    home = temp / 'home';home.mkdir(mode=0o700)

    @contextmanager
    def engine():
        address = temp / 'engine.sock'
        runtime = app / 'Contents/Resources/runtime'
        process = subprocess.Popen([str(runtime / 'python/bin/python3.12'), '-I', '-B', str(runtime / 'engine/bootstrap.py'), '--workspace', str(workspace), '--socket', str(address)], env={'HOME': str(home), 'PATH': '/usr/bin:/bin', 'LANG': 'en_US.UTF-8', 'AGNO_TELEMETRY': 'false'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 30
            while not address.exists():
                assert process.poll() is None, 'Packaged engine stopped before readiness'
                assert time.monotonic() < deadline, 'Packaged engine readiness timeout'
                time.sleep(.1)
            def call(command, payload=None):
                identifier = str(uuid.uuid4())
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
                    stream.settimeout(30);stream.connect(str(address))
                    stream.sendall((json.dumps({'schema_version': 1, 'request_id': identifier, 'command': command, 'payload': payload or {}}) + '\n').encode())
                    response = json.loads(stream.makefile('rb').readline(1024 * 1024))
                assert response['request_id'] == identifier and response['event'] != 'failed', command
                return response['result']
            call('runtime.health')
            yield call
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
                raise AssertionError('Packaged engine failed to shut down cleanly')
            assert process.returncode == 0

    with engine() as call:
        chat = call('chat.create', {'title': 'Updater QA · محفوظة'})
        draft = call('drafts.create', {'topic': 'Updater QA', 'format': 'linkedin', 'language': 'ar', 'text': 'مسودة محفوظة قبل التحديث.'})
        call('drafts.save', {'draft_id': draft['draft_id'], 'text': 'نسخة ثانية محفوظة قبل التحديث.'})
        settings = call('assistant.get', {'scope': 'general'})['settings']
        call('assistant.save', {'scope': 'general', 'settings': {**settings, 'style': 'Updater QA preserved writing style.'}})
    # Seed one synthetic archived article while the packaged engine is stopped.
    # The subscription stays disabled, so this check does not fetch publisher data.
    sys.path.insert(0, str(ROOT / 'engine'))
    from eis_engine.storage import Store, now
    from eis_engine.news import NewsManager
    store = Store(workspace)
    manager = NewsManager(store)
    subscription = asyncio.run(manager.add({'url': 'https://publisher.example/feed'}, sync=False))
    article_id = str(uuid.uuid4())
    article_text = 'Synthetic archived article preserved across an app update. ' * 8
    with store.db:
        store.db.execute('UPDATE news_subscriptions SET enabled=0 WHERE id=?', (subscription,))
        store.db.execute('INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,discovered_at,summary,text,body_status) VALUES(?,?,?,?,?,?,?,?,?,?)', (article_id, store.workspace, subscription, article_id, 'Updater QA archived article', 'https://publisher.example/update-qa', now(), 'Synthetic article summary.', article_text, 'full'))
        manager.archive.register(article_id, subscription, article_id, 'https://publisher.example/update-qa')
    store.close()
    # Synthetic external credential/model sentinels, never real account material.
    credentials = workspace / '.providers/qa-sentinel.json'
    credentials.parent.mkdir(exist_ok=True)
    credentials.write_text('{"qa_only":true,"token":"synthetic-not-a-real-secret"}')
    model = home / '.ollama/models/qa-sentinel'
    model.parent.mkdir(parents=True);model.write_bytes(b'SYNTHETIC MODEL SENTINEL; NOT MODEL WEIGHTS')
    preserved = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (credentials, model)}
    action = 'download' if args.public else str(archive)
    result = subprocess.check_output([str(binary), str(ROOT / 'desktop/src-tauri/tauri.conf.json'), str(prepared / 'tauri-preview.json'), str(app), old_version, action], text=True)
    print(result.strip())
    new_info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    assert new_info['CFBundleShortVersionString'] == version
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    assert len(list(temp.glob('*.app'))) == 1
    with engine() as call:
        article = call('news.preview', {'article_id': article_id})
        assert article['title'] == 'Updater QA archived article' and article_text.strip() in article['text']
        assert call('chat.detail', {'conversation_id': chat['conversation_id']})['title'] == 'Updater QA · محفوظة'
        detail = call('drafts.detail', {'draft_id': draft['draft_id']})
        assert len(detail['versions']) == 2
        assert call('assistant.get', {'scope': 'general'})['settings']['style'] == 'Updater QA preserved writing style.'
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in preserved.items())
    if args.public:
        # Equal installed/current versions must report no update.
        subprocess.run([str(binary), str(ROOT / 'desktop/src-tauri/tauri.conf.json'), str(prepared / 'tauri-preview.json'), str(app), version, 'current'], check=True)

record = {'from_version': old_version, 'to_version': version, 'signed_bundle_install': 'passed', 'tamper_rejected': True, 'signed_version_mismatch_rejected': True, 'old_and_new_packaged_engines': 'passed', 'article_preserved': True, 'conversation_preserved': True, 'draft_versions_preserved': True, 'instructions_preserved': True, 'synthetic_credentials_and_model_preserved': True, 'single_app_after_update': True, 'public_feed_and_download_verified': args.public}
(prepared / ('update-public-validation.json' if args.public else 'update-validation.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
