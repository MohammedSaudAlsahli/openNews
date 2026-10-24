"""Stage relocatable embedded CPython; dependency installation happens only at build time."""
import argparse, shutil, subprocess, sys
from pathlib import Path
p = argparse.ArgumentParser(); p.add_argument('app', type=Path, nargs='?'); args=p.parse_args()
root=Path(__file__).resolve().parents[2]
source = args.app/'Contents/Resources/python' if args.app else Path(sys.base_prefix)
if not (source/'bin/python3.12').exists(): raise SystemExit('Use uv-managed Python 3.12 to stage the runtime')
if not args.app and 'cpython-3.12' not in str(source): raise SystemExit('A relocatable uv-managed CPython 3.12 is required')
target=root/'desktop/src-tauri/runtime'; target.mkdir(parents=True,exist_ok=True)
# Generated staging only; never an installed application or user workspace.
if (target/'python').exists(): shutil.rmtree(target/'python')
shutil.copytree(source,target/'python',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
if not args.app:
    site=target/'python/lib/python3.12/site-packages'
    if site.exists(): shutil.rmtree(site)
    site.mkdir(parents=True)
    subprocess.run(['uv','pip','install','--target',str(site),'--require-hashes','-r',str(root/'build/requirements.lock')],check=True)
    for package in ('numpy','pandas'):
        for tests in sorted((site/package).rglob('tests'),key=lambda p:len(p.parts),reverse=True):
            if tests.is_dir(): shutil.rmtree(tests)
# Replace generated sources so removed files and FileProvider copies cannot linger.
if (target/'engine').exists(): shutil.rmtree(target/'engine')
shutil.copytree(root/'engine',target/'engine',ignore=shutil.ignore_patterns('.venv','__pycache__','tests','.pytest_cache','* 2.py'))
shutil.copy2(root/'LICENSE',target/'OPENNEWS-LICENSE.txt')
shutil.copy2(root/'THIRD_PARTY_NOTICES.md',target/'THIRD_PARTY_NOTICES.md')
print('Staged embedded CPython and current engine. No user data copied.')

subprocess.run(['/usr/bin/xcrun', 'swiftc', '-O', str(root/'desktop/native/SystemServices.swift'), '-o', str(target/'system-services')], check=True)

subprocess.run(['/usr/bin/xcrun', 'swiftc', '-O', '-parse-as-library', str(root/'desktop/native/PublicReader.swift'), '-o', str(target/'public-reader')], check=True)

# Seal embedded native binaries before the outer Tauri bundle is signed.
magic={b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xfe\xed\xfa\xcf'}
for file in sorted(target.rglob('*'),key=lambda p:len(p.parts),reverse=True):
    if file.is_file() and not file.is_symlink():
        with file.open('rb') as stream: native=stream.read(4) in magic
        if native: subprocess.run(['codesign','--force','--sign','-',str(file)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
