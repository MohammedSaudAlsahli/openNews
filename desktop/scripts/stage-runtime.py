"""Reuse the verified embedded CPython runtime; no Nuitka or runtime pip install."""
import argparse, shutil, subprocess
from pathlib import Path
p = argparse.ArgumentParser(); p.add_argument('app', type=Path); args=p.parse_args()
root=Path(__file__).resolve().parents[2]
source=args.app/'Contents/Resources/python'
if not (source/'bin/python3.12').exists(): raise SystemExit('Expected an existing OpenStudio .app with embedded Python')
target=root/'desktop/src-tauri/runtime'; target.mkdir(parents=True,exist_ok=True)
# Generated bundle staging only; never the installed app or a user workspace.
if (target/'python').exists(): shutil.rmtree(target/'python')
shutil.copytree(source,target/'python',symlinks=True)
shutil.copytree(root/'engine',target/'engine',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.venv','__pycache__','tests','.pytest_cache'))
print('Staged existing embedded CPython and current engine. No user data copied.')

subprocess.run(['/usr/bin/xcrun', 'swiftc', '-O', str(root/'desktop/native/SystemServices.swift'), '-o', str(target/'system-services')], check=True)

subprocess.run(['/usr/bin/xcrun', 'swiftc', '-O', '-parse-as-library', str(root/'desktop/native/PublicReader.swift'), '-o', str(target/'public-reader')], check=True)
