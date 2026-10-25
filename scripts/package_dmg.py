# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["ds-store==1.3.2", "pillow==12.3.0"]
# ///
"""Package an existing signed app, without rebuilding it or requiring Finder/GUI."""
import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile

from ds_store import DSStore
from mac_alias import Alias
from PIL import Image, ImageDraw, ImageFont

from dmg_verify import verify


def tree_digest(root):
    """Include paths, executable modes, symlink destinations and file bytes."""
    digest = hashlib.sha256()
    for item in sorted(root.rglob('*')):
        digest.update(str(item.relative_to(root)).encode() + b'\0')
        digest.update(str(item.lstat().st_mode & 0o777).encode() + b'\0')
        if item.is_symlink():
            digest.update(os.readlink(item).encode())
        elif item.is_file():
            with item.open('rb') as stream:
                digest.update(hashlib.file_digest(stream, 'sha256').digest())
    return digest.hexdigest()


def run(*command):
    return subprocess.run(command, check=True, stdout=subprocess.PIPE)


def attach(image, mount, readonly=False):
    arguments = ['hdiutil', 'attach', str(image), '-mountpoint', str(mount), '-nobrowse', '-noautoopen', '-plist']
    if readonly:
        arguments.append('-readonly')
    run(*arguments)


def background(destination):
    # Retina-size, quiet native installer artwork; no fetched assets or fonts.
    canvas = Image.new('RGB', (1280, 760), '#f6f5f1')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 40)
    small = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 26)
    draw.text((640, 92), 'Drag openNews to Applications', font=font, fill='#282824', anchor='mm')
    draw.text((640, 650), 'openNews  ·  macOS', font=small, fill='#6d6d66', anchor='mm')
    draw.line([(565, 360), (715, 360)], fill='#96988d', width=5)
    draw.line([(691, 337), (715, 360), (691, 383)], fill='#96988d', width=5, joint='curve')
    canvas.save(destination, dpi=(144, 144))


def package(app, output):
    app = app.resolve()
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    version = info['CFBundleShortVersionString']
    assert info['CFBundleIdentifier'] == 'com.editorialintelligence.studio.preview'
    assert app.name == 'openNews.app'
    assert not output.exists(), 'Refusing to replace an existing DMG'
    run('codesign', '--verify', '--deep', '--strict', str(app))
    run('lipo', str(app / 'Contents/MacOS' / info['CFBundleExecutable']), '-verify_arch', 'arm64')
    original = tree_digest(app)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='opennews-dmg-', suffix='.noindex', dir='/tmp') as temporary:
        stage = Path(temporary)
        contents = stage / 'contents'
        contents.mkdir()
        run('ditto', str(app), str(contents / app.name))
        (contents / 'Applications').symlink_to('/Applications')
        (contents / '.metadata_never_index').touch()
        (contents / '.background').mkdir()
        background(contents / '.background/install.png')
        writable = stage / 'installer.dmg'
        run('hdiutil', 'create', '-srcfolder', str(contents), '-volname', f'openNews {version}', '-fs', 'HFS+', '-format', 'UDRW', str(writable))
        mount = stage / 'mounted'
        attach(writable, mount)
        try:
            with DSStore.open(str(mount / '.DS_Store'), 'w+') as store:
                store['.']['bwsp'] = {
                    'ShowToolbar': False, 'ShowStatusBar': False, 'ShowTabView': False,
                    'ShowPathbar': False, 'ShowSidebar': False,
                    'WindowBounds': '{{180, 160}, {640, 500}}',
                    'ContainerShowSidebar': False, 'PreviewPaneVisibility': False, 'SidebarWidth': 180,
                }
                store['.']['icvp'] = {
                    'viewOptionsVersion': 1, 'backgroundType': 2,
                    'backgroundColorRed': 1.0, 'backgroundColorGreen': 1.0, 'backgroundColorBlue': 1.0,
                    'backgroundImageAlias': Alias.for_file(str(mount / '.background/install.png')).to_bytes(),
                    'iconSize': 112.0, 'textSize': 14.0, 'labelOnBottom': True,
                    'gridSpacing': 100.0, 'gridOffsetX': 0.0, 'gridOffsetY': 0.0,
                    'scrollPositionX': 0.0, 'scrollPositionY': 0.0,
                    'arrangeBy': 'none', 'showIconPreview': True, 'showItemInfo': False,
                }
                store['.']['vSrn'] = ('long', 1)
                store['.']['icvl'] = ('type', b'icnv')
                store[app.name]['Iloc'] = (160, 180)
                store['Applications']['Iloc'] = (480, 180)
        finally:
            run('hdiutil', 'detach', str(mount))
        # Build to a temporary filename; expose only a completely validated image.
        finished = stage / 'finished.dmg'
        run('hdiutil', 'convert', str(writable), '-format', 'UDZO', '-imagekey', 'zlib-level=9', '-o', str(finished))
        verify(finished)
        attach(finished, mount, readonly=True)
        try:
            assert (mount / 'Applications').is_symlink()
            assert os.readlink(mount / 'Applications') == '/Applications'
            assert tree_digest(mount / app.name) == original, 'DMG changed application bytes or modes'
            run('codesign', '--verify', '--deep', '--strict', str(mount / app.name))
            with DSStore.open(str(mount / '.DS_Store'), 'r') as store:
                assert store[app.name]['Iloc'] == (160, 180)
                assert store['Applications']['Iloc'] == (480, 180)
        finally:
            run('hdiutil', 'detach', str(mount))
        # The output may be on a different filesystem.
        with finished.open('rb') as source, output.open('xb') as target:
            shutil.copyfileobj(source, target)
    print(f'{output.name}: verified signed {version} app, identical tree {original}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    package(args.app, args.output.resolve())
