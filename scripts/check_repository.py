"""Validate public entry documentation and synchronized Tauri version sources."""
import json
import base64
from datetime import datetime
from pathlib import Path
import re
import subprocess
import tomllib
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

def read_json(name):
    return json.loads((ROOT / name).read_text())

version = read_json('desktop/package.json')['version']
assert re.fullmatch(r'\d+\.\d+\.\d+', version), 'Official app versions must be stable semver'
lock = read_json('desktop/package-lock.json')
assert version == lock['version'] == lock['packages']['']['version']
assert version == read_json('desktop/src-tauri/tauri.conf.json')['version']
cargo = tomllib.loads((ROOT / 'desktop/src-tauri/Cargo.toml').read_text())
assert version == cargo['package']['version']
packages = tomllib.loads((ROOT / 'desktop/src-tauri/Cargo.lock').read_text())['package']
assert [p['version'] for p in packages if p['name'] == cargo['package']['name']] == [version]
feed_path = ROOT / 'updates/tauri-preview.json'
if feed_path.exists():
    feed = json.loads(feed_path.read_text())
    assert re.fullmatch(r'\d+\.\d+\.\d+', feed['version'])
    assert tuple(map(int, feed['version'].split('.'))) <= tuple(map(int, version.split('.')))
    datetime.fromisoformat(feed['pub_date'].replace('Z', '+00:00'))
    platform = feed['platforms']['darwin-aarch64']
    expected_url = f"https://github.com/MohammedSaudAlsahli/openNews/releases/download/v{feed['version']}/openNews-{feed['version']}-macOS-arm64.app.tar.gz"
    assert platform['url'] == expected_url, 'Unexpected signed-update destination'
    envelope = base64.b64decode(platform['signature'], validate=True).decode()
    assert 'trusted comment:' in envelope and '/Users/' not in envelope
entries = [ROOT / name for name in subprocess.check_output(
    ['git', 'ls-files', '-z', '--', '*.md'], cwd=ROOT, text=True
).split('\0') if name]
assert (ROOT / 'docs/releases' / f'v{version}.md') in entries
assert (ROOT / 'LICENSE').read_text().startswith('MIT License\n')
for path in entries:
    content = path.read_text()
    assert '/Users/' not in content, f'Personal path in {path.relative_to(ROOT)}'
    for target in re.findall(r'\]\(([^\s)]+)\)', content):
        if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            continue
        destination = unquote(target.split('#', 1)[0])
        assert (path.parent / destination).exists(), f'Broken local link: {path.relative_to(ROOT)} → {target}'
print(f'Repository documentation and Tauri version {version}: passed')
