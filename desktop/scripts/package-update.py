"""Build a signed Tauri update locally. Does not publish or touch the Sparkle feed.

Private key path stays outside the repository; only its public key is in config.
"""
import json, os, subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[2]
key = Path.home()/'.local/share/OpenStudio/release-signing/tauri-preview.key'
if not key.is_file(): raise SystemExit('The private Tauri release key is missing. Do not generate a replacement for an existing channel.')
config = json.loads((root/'desktop/src-tauri/tauri.conf.json').read_text())
if key.with_suffix('.key.pub').read_text().strip() != config['plugins']['updater']['pubkey']:
    raise SystemExit('Signing key does not match this application.')
environment = dict(os.environ, TAURI_SIGNING_PRIVATE_KEY=str(key), TAURI_SIGNING_PRIVATE_KEY_PASSWORD='')
subprocess.run(['npm','run','tauri','--','build','--bundles','app','--config',json.dumps({'bundle':{'createUpdaterArtifacts':True}})],cwd=root/'desktop',env=environment,check=True)
print('Signed local update created. Test in-place replacement before publishing the preview feed.')
