"""Publish a tested preview and its signed Sparkle feed. Run from a clean main branch.
The signing key stays in the macOS login Keychain; only the public key is committed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

def run(*args, **kw):
    return subprocess.run(args, check=True, **kw)

def output(*args):
    return subprocess.check_output(args, text=True).strip()

version = (ROOT/'VERSION').read_text().strip()
if not re.fullmatch(r'\d+\.\d+\.\d+', version): raise SystemExit('Invalid VERSION')
tag = 'v'+version
if output('git','branch','--show-current') != 'main': raise SystemExit('Publish from main')
if output('git','status','--porcelain'): raise SystemExit('Commit reviewed source changes first')
run('git','fetch','origin','main')
commit = output('git','rev-parse','HEAD')
if commit != output('git','rev-parse','origin/main'): raise SystemExit('Push main before publishing')
if subprocess.run(['git','rev-parse','--verify',f'refs/tags/{tag}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0:
    raise SystemExit('Tag already exists; never overwrite an issued update')
notes = ROOT/f'docs/releases/{tag}.md'
if not notes.is_file(): raise SystemExit('Write release notes first')
run('bash','scripts/test.sh')
run('bash','scripts/build_app.sh')
config = json.loads((ROOT/'release-config.json').read_text())
repo = config['repository']
asset = ROOT/f'dist/OpenStudio-{version}-macOS-arm64.dmg'
sparkle = ROOT/'macos/.build/artifacts/sparkle/Sparkle/bin'
if not sparkle.is_dir():
    run('swift','package','--package-path','macos','resolve')
public_key = output(str(sparkle/'generate_keys'),'--account',config['keychain_account'],'-p')
if public_key != config['public_key']: raise SystemExit('Signing key does not match the installed application')
with tempfile.TemporaryDirectory(prefix='openstudio-release-') as directory:
    stage = Path(directory)
    shutil.copy2(asset,stage/asset.name)
    checksum = stage/'SHA256SUMS.txt'
    checksum.write_text(hashlib.file_digest(asset.open('rb'),'sha256').hexdigest()+'  '+asset.name+'\n')
    run(str(sparkle/'generate_appcast'),'--account',config['keychain_account'],
        '--download-url-prefix',f'https://github.com/{repo}/releases/download/{tag}/',
        '--maximum-deltas','0',str(stage))
    feed = stage/'appcast.xml'
    if not feed.is_file(): raise SystemExit('No signed appcast generated')
    run('git','tag','-a',tag,'-m',f'OpenStudio {version} experimental preview')
    run('git','push','origin',tag)
    run('gh','release','create',tag,str(asset),str(checksum),str(feed),'--repo',repo,
        '--verify-tag','--draft','--prerelease','--title',f'OpenStudio {version} — Experimental preview','--notes-file',str(notes))
    run('gh','release','edit',tag,'--repo',repo,'--draft=false')
    # Publish the feed last, so clients never see a download that is not available yet.
    shutil.copy2(feed,ROOT/'appcast.xml')
    run('git','add','appcast.xml')
    run('git','commit','-m',f'Publish signed update feed for {tag}')
    run('git','push','origin','main')
print(f'https://github.com/{repo}/releases/tag/{tag}')
