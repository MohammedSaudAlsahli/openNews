import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
staging=tempfile.TemporaryDirectory(prefix='eis-package-',dir='/tmp')
app=Path(staging.name)/'Editorial Intelligence Studio.app'
resources=app/'Contents/Resources'
(app/'Contents/MacOS').mkdir(parents=True)
resources.mkdir()
shutil.copy2(sys.argv[1],app/'Contents/MacOS/EditorialIntelligenceStudio')
# SwiftPM localization resources must travel with the standalone executable.
localization_bundle = Path(sys.argv[1]).parent / 'EditorialIntelligenceStudio_EISApp.bundle'
if not localization_bundle.is_dir():
    raise RuntimeError('Missing SwiftPM localization resource bundle')
shutil.copytree(localization_bundle, resources / localization_bundle.name)
base=Path(sys.base_prefix)
if 'cpython-3.12' not in str(base):
    raise SystemExit('Build requires relocatable uv-managed CPython 3.12, not system/Homebrew Python')
shutil.copytree(base,resources/'python',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
site=resources/'python/lib/python3.12/site-packages'
if site.exists():
    shutil.rmtree(site)
site.mkdir(parents=True)
subprocess.run(['uv','pip','install','--target',str(site),'--require-hashes','-r',str(ROOT/'build/requirements.lock')],check=True)
shutil.copytree(ROOT/'engine/eis_engine',resources/'engine/eis_engine',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copy2(ROOT/'engine/bootstrap.py',resources/'engine/bootstrap.py')
shutil.copy2(ROOT/'engine/uv.lock',resources/'uv.lock')
shutil.copy2(ROOT/'build/requirements.lock',resources/'requirements.lock')
with (app/'Contents/Info.plist').open('wb') as f:
    plistlib.dump(dict(CFBundleIdentifier='com.editorialintelligence.studio',CFBundleExecutable='EditorialIntelligenceStudio',
                      CFBundleName='Editorial Intelligence Studio',CFBundleDisplayName='Editorial Intelligence Studio',
                      CFBundleShortVersionString='0.1.0',CFBundleVersion='1',CFBundlePackageType='APPL',
                      LSMinimumSystemVersion='14.0',NSHighResolutionCapable=True,
                      CFBundleDevelopmentRegion='ar',CFBundleLocalizations=['ar','en'],NSPrincipalClass='NSApplication'),f)
sbom=[]
for dist in importlib.metadata.distributions(path=[str(site)]):
    sbom.append({'name':dist.metadata['Name'],'version':dist.version,
                 'license':dist.metadata.get('License-Expression') or dist.metadata.get('License','See bundled dist-info license files')})
(resources/'dependency-inventory.json').write_text(json.dumps({'format':'dependency-inventory-v1','python':sys.version,'packages':sorted(sbom,key=lambda x:x['name'])},indent=2))
# Sign concrete Mach-O files from the inside out, never codesign --deep as a repair.
magic={b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xfe\xed\xfa\xcf'}
identity=os.environ.get('EIS_SIGN_IDENTITY','-')
# Finder/FileProvider decoration is not bundle content. Never clear quarantine
# or other security attributes; remove only forbidden signing metadata.
for attribute in ('com.apple.FinderInfo','com.apple.ResourceFork'):
    subprocess.run(['xattr','-dr',attribute,str(app)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for file in sorted(app.rglob('*'),key=lambda p:len(p.parts),reverse=True):
    if file.is_file() and not file.is_symlink():
        with file.open('rb') as f:
            macho=f.read(4) in magic
        if macho:
            command=['codesign','--force','--sign',identity]
            if identity!='-':
                command+=['--options','runtime','--timestamp']
            subprocess.run(command+[str(file)],check=True,stdout=subprocess.DEVNULL)
command=['codesign','--force','--sign',identity]
if identity!='-':
    command+=['--options','runtime','--timestamp']
subprocess.run(command+[str(app)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict','--verbose=2',str(app)],check=True)
subprocess.run([sys.executable,str(ROOT/'scripts/smoke_bundle.py'),str(app)],check=True)
subprocess.run([sys.executable,str(ROOT/'scripts/smoke_conversation.py'),str(app)],check=True)
manifest={str(p.relative_to(app)):hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*') if p.is_file() and not p.is_symlink()}
(ROOT/'build/bundle-sha256.json').write_text(json.dumps(manifest,indent=2))
if os.environ.get('EIS_APP_OUTPUT_DIR'):
    destination=Path(os.environ['EIS_APP_OUTPUT_DIR'])/app.name
    shutil.copytree(app,destination,symlinks=True,copy_function=shutil.copy)
    subprocess.run(['codesign','--verify','--deep','--strict',str(destination)],check=True)
image=ROOT/'dist/Editorial Intelligence Studio-development.dmg'
subprocess.run(['hdiutil','create','-volname','Editorial Intelligence Studio','-srcfolder',str(Path(staging.name)),'-ov','-format','UDZO',str(image)],check=True)
subprocess.run(['hdiutil','verify',str(image)],check=True)
print(image)
staging.cleanup()
