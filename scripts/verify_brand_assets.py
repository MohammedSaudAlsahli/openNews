# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow==11.3.0"]
# ///
"""Validate actual decoded assets and platform configuration. Run with uv run."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "branding"
NS = "{http://www.w3.org/2000/svg}"


def check_png(path, size, transparent=False, monochrome=None):
    with Image.open(path) as im:
        im.load()
        assert im.format == "PNG", path
        assert im.size == (size, size), (path, im.size, size)
        assert im.mode == "RGBA", (path, im.mode)
        alpha = im.getchannel("A")
        assert alpha.getextrema()[1] == 255, path
        if transparent:
            assert alpha.getpixel((0, 0)) == 0, path
            assert alpha.getextrema()[0] == 0, path
        if monochrome is not None:
            assert all((r, g, b) == (monochrome,) * 3 for r, g, b, a in im.getdata() if a), path
        return im.copy()


def check_ico(path, sizes, transparent=False):
    data = path.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data)
    assert (reserved, kind, count) == (0, 1, len(sizes)), path
    cursor = 6 + count * 16
    for i, size in enumerate(sizes):
        w, h, colors, reserved, planes, bits, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + i * 16)
        assert (w or 256, h or 256) == (size, size), path
        assert (planes, bits, offset, colors, reserved) == (1, 32, cursor, 0, 0), path
        im = check_png(BytesIO(data[offset:offset + length]), size, transparent)
        if "tray-" in path.name:
            value = 255 if "white" in path.name else 0
            assert all((r, g, b) == (value,) * 3 for r, g, b, a in im.getdata() if a), path
        cursor += length
    assert cursor == len(data), path
    with Image.open(path) as im:
        assert im.ico.sizes() == {(s, s) for s in sizes}, path


def components(im):
    alpha = im.getchannel("A")
    pixels = {(x, y) for y in range(im.height) for x in range(im.width) if alpha.getpixel((x, y)) >= 128}
    count = 0
    while pixels:
        count += 1
        todo = [pixels.pop()]
        while todo:
            x, y = todo.pop()
            for point in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if point in pixels:
                    pixels.remove(point)
                    todo.append(point)
    return count


def main():
    provenance = json.loads((BRAND / "source/generated-assets.json").read_text())
    for group in ("sources", "outputs"):
        for filename, digest in provenance[group].items():
            assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == digest, f"Regenerate stale brand assets: {filename}"
    master = ET.parse(BRAND / "source/openstudio.svg").getroot()
    geometry = {e.attrib["id"]: e.attrib["d"] for e in master.iter(f"{NS}path")}
    for path in BRAND.rglob("*.svg"):
        root = ET.parse(path).getroot()
        assert root.attrib.get("viewBox"), path
        assert not any(e.tag in {f"{NS}image", f"{NS}text", f"{NS}script", f"{NS}filter", f"{NS}linearGradient"} for e in root.iter()), path
        for node in root.iter():
            assert not any("href" in key for key in node.attrib), path
            if node.attrib.get("id") in geometry:
                assert node.attrib["d"] == geometry[node.attrib["id"]], path
    for size in (16, 18, 20, 22):
        for scale in (1, 2):
            image = check_png(BRAND / f"macos/menubar-{size}{'@2x' if scale == 2 else ''}.png", size * scale, True, 0)
            # The sparkle must remain separate and visible even at 16 px.
            assert components(image) == 2, (size, scale, components(image))
    for name in ("openstudio-app-1024.png", "openstudio-app-dark-1024.png"):
        image = check_png(BRAND / "macos" / name, 1024, True)
        # Ignore the subpixel antialiasing fringe when measuring tile padding.
        assert image.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox() == (100, 100, 924, 924), name
    catalog = ROOT / "macos/Assets.xcassets"
    app = json.loads((catalog / "AppIcon.appiconset/Contents.json").read_text())
    assert len(app["images"]) == 10
    for entry in app["images"]:
        points = int(entry["size"].split("x")[0])
        scale = int(entry["scale"][0])
        path = catalog / "AppIcon.appiconset" / entry["filename"]
        check_png(path, points * scale, True)
        assert path.read_bytes() == (BRAND / "macos/OpenStudio.iconset" / entry["filename"]).read_bytes()
    menu = json.loads((catalog / "MenuBarIcon.imageset/Contents.json").read_text())
    assert menu["properties"]["template-rendering-intent"] == "template"
    for entry in menu["images"]:
        path = catalog / "MenuBarIcon.imageset" / entry["filename"]
        check_png(path, 18 * int(entry["scale"][0]), True, 0)
        assert path.read_bytes() == (ROOT / "macos/Sources/OpenStudioApp/Resources/Brand" / entry["filename"]).read_bytes()
    icns = (BRAND / "macos/OpenStudio.icns").read_bytes()
    assert icns[:4] == b"icns" and struct.unpack_from(">I", icns, 4)[0] == len(icns)
    sizes = {"icp4": 16, "icp5": 32, "icp6": 64, "ic07": 128, "ic08": 256, "ic09": 512, "ic10": 1024, "ic11": 32, "ic12": 64, "ic13": 256, "ic14": 512}
    cursor = 8
    while cursor < len(icns):
        kind = icns[cursor:cursor+4].decode()
        length = struct.unpack_from(">I", icns, cursor+4)[0]
        check_png(BytesIO(icns[cursor+8:cursor+length]), sizes.pop(kind), True)
        cursor += length
    assert cursor == len(icns) and not sizes
    check_ico(BRAND / "windows/OpenStudio.ico", (16, 24, 32, 48, 64, 128, 256), True)
    for color in ("black", "white"):
        sizes = (16, 20, 24, 32, 40, 48, 64)
        check_ico(BRAND / f"windows/tray-{color}.ico", sizes, True)
        for size in sizes:
            check_png(BRAND / f"windows/tray-{color}-{size}.png", size, True, 0 if color == "black" else 255)
    check_ico(BRAND / "web/favicon.ico", (16, 32, 48))
    for size in (16, 32):
        check_png(BRAND / f"web/favicon-{size}x{size}.png", size)
    check_png(BRAND / "web/apple-touch-icon.png", 180)
    manifest = json.loads((BRAND / "web/site.webmanifest").read_text())
    for entry in manifest["icons"]:
        image = check_png(BRAND / "web" / entry["src"], int(entry["sizes"].split("x")[0]))
        assert image.getchannel("A").getextrema() == (255, 255), entry
        if entry["purpose"] == "maskable":
            paper = (245, 239, 231)
            for y in range(image.height):
                for x in range(image.width):
                    if image.getpixel((x, y))[:3] != paper:
                        assert (x + .5 - 256)**2 + (y + .5 - 256)**2 <= (512 * .4)**2, (x, y)
    # All links in the working preview must resolve, including the favicon/manifest.
    html = (BRAND / "web/index.html").read_text()
    for target in re.findall(r'(?:src|href|srcset)="([^"]+)"', html):
        assert (BRAND / "web" / target).is_file(), target
    for filename in re.findall(r'ICON "([^"]+)"', (BRAND / "windows/OpenStudioResources.rc").read_text()):
        assert (BRAND / "windows" / filename).is_file(), filename
    print("PASS: canonical vector paths, PNG sizes/alpha, separate small sparkle, ICNS/ICO frames, template catalog, Retina resources, web manifest and resource links")


if __name__ == "__main__":
    main()
