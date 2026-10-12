# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow==11.3.0", "resvg-py==0.2.6"]
# ///
"""Run: uv run scripts/generate_brand_assets.py. No runtime app dependencies.

All symbol/lettering geometry comes from branding/source/openstudio.svg.
The committed outputs also support builds without design tools installed.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
import resvg_py

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "branding"
CATALOG = ROOT / "macos/Assets.xcassets"
RESOURCES = ROOT / "macos/Sources/EISApp/Resources/Brand"
NS = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", NS[1:-1])
SOURCE = ET.parse(BRAND / "source/openstudio.svg").getroot()
INK, PEACH, PAPER = "#1B2024", "#E5BB9B", "#F5EFE7"
APP_SIZES = (16, 24, 32, 48, 64, 128, 256)
TRAY_SIZES = (16, 20, 24, 32, 40, 48, 64)
INFO = {"author": "xcode", "version": 1}


def save(path: Path, contents: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contents, str):
        path.write_text(contents, encoding="utf-8")
    else:
        path.write_bytes(contents)


def json_file(path: Path, value: object) -> None:
    save(path, json.dumps(value, indent=2) + "\n")


def svg(body: str, box: str, title: str = "OpenStudio") -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" role="img" aria-label="{title}">{body}</svg>\n'


def mark(ink: str = INK, ribbon: str | None = PEACH, sparkle: str | None = None) -> str:
    symbol = deepcopy(SOURCE.find(f"{NS}g[@id='symbol']"))
    for p in list(symbol):
        part = p.attrib["id"]
        if part == "ribbon" and ribbon is None:
            symbol.remove(p)
        else:
            p.set("fill", ribbon if part == "ribbon" else (sparkle or ink) if part == "sparkle" else ink)
    return ET.tostring(symbol, encoding="unicode")


def logo(dark: bool = False) -> str:
    ink = PAPER if dark else INK
    lettering = deepcopy(SOURCE.find(f"{NS}path[@id='wordmark']"))
    lettering.set("fill", ink)
    return svg(mark(ink, PEACH, PEACH) + ET.tostring(lettering, encoding="unicode"), SOURCE.attrib["viewBox"])


def icon(tile: bool = True, dark: bool = False, square: bool = False, maskable: bool = False, optical: bool = False) -> str:
    # 100 px transparent outer margin; 824 px continuous-curvature macOS tile.
    # Core mark is optically centered, including the sparkle, inside the tile.
    body = ""
    if tile:
        fill = INK if dark else PAPER
        if square:
            body = f'<path fill="{fill}" d="M0 0H1024V1024H0Z"/>'
        else:
            body = f'<path fill="{fill}" d="M308 100H716C861 100 924 163 924 308V716C924 861 861 924 716 924H308C163 924 100 861 100 716V308C100 163 163 100 308 100Z"/>'
    scale = 3.05 if maskable else 4.1 if optical else 3.18
    x, y = (1024 - 174 * scale) / 2, (1024 - 158 * scale) / 2
    body += f'<g transform="translate({x:.3f} {y:.3f}) scale({scale})">{mark(PAPER if dark else INK, None if dark else PEACH)}</g>'
    return svg(body, "0 0 1024 1024")


def small_mark(size: int, light: bool = False) -> str:
    # One ring + one sparkle; same contours as the master, no ribbon seam.
    # 1 px breathing room, centered vertically, with no container/effects.
    scale = (size - 2) / 174
    y = (size - 158 * scale) / 2
    return svg(f'<g transform="translate(1 {y:.6f}) scale({scale:.8f})">{mark("#FFFFFF" if light else "#000000", None)}</g>', f"0 0 {size} {size}")


def render(source: str, size: int) -> Image.Image:
    # Render at 4x then downsample for consistent antialiasing across platforms.
    data = resvg_py.svg_to_bytes(svg_string=source, width=size * 4, height=size * 4)
    return Image.open(BytesIO(data)).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def png(path: Path, source: str, size: int) -> Image.Image:
    im = render(source, size)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)
    return im


def ico(path: Path, images: dict[int, Image.Image]) -> None:
    # Each size is rendered independently, never expanded from a smaller frame.
    # PNG-compressed entries are supported by Windows Vista and later.
    payloads = []
    for im in images.values():
        buffer = BytesIO()
        im.save(buffer, format="PNG", optimize=True)
        payloads.append(buffer.getvalue())
    offset = 6 + 16 * len(images)
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    for size, payload in zip(images, payloads):
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(payload), offset)
        offset += len(payload)
    save(path, header + entries + b"".join(payloads))


def main() -> None:
    for dark, suffix in ((False, "light"), (True, "dark")):
        save(BRAND / f"web/openstudio-logo-{suffix}.svg", logo(dark))
        save(BRAND / f"web/openstudio-symbol-{suffix}.svg", svg(mark(PAPER if dark else INK, PEACH, PEACH), "0 0 174 158"))
    for dark, suffix in ((False, ""), (True, "-dark")):
        source = icon(dark=dark)
        save(BRAND / f"macos/openstudio-app{suffix}.svg", source)
        png(BRAND / f"macos/openstudio-app{suffix}-1024.png", source, 1024)
    json_file(CATALOG / "Contents.json", {"info": INFO})
    app_images = []
    iconset = BRAND / "macos/OpenStudio.iconset"
    for points in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            name = f"icon_{points}x{points}{'@2x' if scale == 2 else ''}.png"
            image = png(iconset / name, icon(optical=points <= 32), points * scale)
            destination = CATALOG / "AppIcon.appiconset" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination, optimize=True)
            app_images.append({"idiom": "mac", "size": f"{points}x{points}", "scale": f"{scale}x", "filename": name})
    json_file(CATALOG / "AppIcon.appiconset/Contents.json", {"images": app_images, "info": INFO})
    # Native ICNS container using PNG payloads, reproducible on any OS.
    icns_types = {"icp4": 16, "icp5": 32, "icp6": 64, "ic07": 128, "ic08": 256, "ic09": 512, "ic10": 1024, "ic11": 32, "ic12": 64, "ic13": 256, "ic14": 512}
    chunks = b""
    for kind, size in icns_types.items():
        payload = BytesIO()
        render(icon(optical=kind in {"icp4", "icp5", "icp6", "ic11", "ic12"}), size).save(payload, format="PNG", optimize=True)
        chunks += kind.encode("ascii") + struct.pack(">I", len(payload.getvalue()) + 8) + payload.getvalue()
    save(BRAND / "macos/OpenStudio.icns", b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)
    for size in (16, 18, 20, 22):
        source = small_mark(size)
        save(BRAND / f"macos/menubar-{size}.svg", source)
        for scale in (1, 2):
            name = f"menubar-{size}{'@2x' if scale == 2 else ''}.png"
            image = png(BRAND / "macos" / name, source, size * scale)
            if size == 18:
                resource_name = f"OpenStudioMenuBar{'@2x' if scale == 2 else ''}.png"
                for parent in (RESOURCES, CATALOG / "MenuBarIcon.imageset"):
                    parent.mkdir(parents=True, exist_ok=True)
                    image.save(parent / resource_name, optimize=True)
    json_file(CATALOG / "MenuBarIcon.imageset/Contents.json", {
        "images": [{"idiom": "mac", "scale": f"{s}x", "filename": f"OpenStudioMenuBar{'@2x' if s == 2 else ''}.png"} for s in (1, 2)],
        "info": INFO, "properties": {"template-rendering-intent": "template"},
    })
    ico(BRAND / "windows/OpenStudio.ico", {s: render(icon(optical=s <= 32), s) for s in APP_SIZES})
    for light, name in ((False, "black"), (True, "white")):
        save(BRAND / f"windows/tray-{name}.svg", small_mark(22, light))
        images = {s: png(BRAND / f"windows/tray-{name}-{s}.png", small_mark(s, light), s) for s in TRAY_SIZES}
        ico(BRAND / f"windows/tray-{name}.ico", images)
    # Adaptive favicon is monochrome for maximum clarity at 16 CSS pixels.
    adaptive = small_mark(16).replace('fill="#000000"', 'fill="currentColor"')
    adaptive = adaptive.replace('<g transform=', '<style>:root{color:#1B2024}@media(prefers-color-scheme:dark){:root{color:#F5EFE7}}</style><g transform=', 1)
    save(BRAND / "web/favicon.svg", adaptive)
    # Static fallback includes an opaque paper tile for contrast on either theme.
    favicon = icon(square=True)
    # Fill more of the small canvas; 1 px border, no peach seam at 16–32 px.
    small_favicon = svg(f'<path fill="{PAPER}" d="M0 0H20V20H0Z"/><g transform="translate(2 2.736) scale(.091954)">{mark(INK, None)}</g>', "0 0 20 20")
    ico(BRAND / "web/favicon.ico", {s: render(small_favicon, s) for s in (16, 32, 48)})
    for size in (16, 32):
        png(BRAND / f"web/favicon-{size}x{size}.png", small_favicon, size)
    png(BRAND / "web/apple-touch-icon.png", favicon, 180)
    for size in (192, 512):
        png(BRAND / f"web/icon-{size}.png", favicon, size)
    png(BRAND / "web/icon-maskable-512.png", icon(square=True, maskable=True), 512)
    json_file(BRAND / "web/site.webmanifest", {
        "name": "OpenStudio", "short_name": "OpenStudio", "id": "./", "start_url": "./", "scope": "./", "display": "standalone",
        "background_color": PAPER, "theme_color": PAPER,
        "icons": [{"src": f"icon-{s}.png", "sizes": f"{s}x{s}", "type": "image/png", "purpose": "any"} for s in (192, 512)] + [
            {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
    })
    preview()
    generated = set()
    for directory in (BRAND / "macos", BRAND / "windows", BRAND / "web", BRAND / "previews", CATALOG, RESOURCES):
        generated.update(p for p in directory.rglob("*") if p.is_file() and p.suffix in {".png", ".svg", ".ico", ".icns", ".json", ".webmanifest"})
    json_file(BRAND / "source/generated-assets.json", {
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (BRAND / "source/openstudio.svg", Path(__file__).resolve())},
        "outputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(generated)},
    })
    print("Generated OpenStudio SVG, PNG, ICO, ICNS, asset catalog and web manifest.")


def preview() -> None:
    sheet = Image.new("RGB", (1440, 960), "#F5F2EE")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=22)
    small = ImageFont.load_default(size=16)
    draw.text((48, 26), "OPENSTUDIO / PRODUCTION ASSETS", fill=INK, font=font)
    for dark, x in ((False, 32), (True, 736)):
        background = INK if dark else "#FFFFFF"
        draw.rounded_rectangle((x, 82, x + 672, 310), radius=20, fill=background)
        data = resvg_py.svg_to_bytes(svg_string=logo(dark), width=592)
        im = Image.open(BytesIO(data)).convert("RGBA")
        sheet.paste(im, (x + 40, 114), im)
    for dark, x in ((False, 28), (True, 374)):
        im = render(icon(dark=dark), 320)
        sheet.paste(im, (x, 334), im)
        draw.text((x + 52, 655), "macOS / " + ("dark alternate" if dark else "default"), fill=INK, font=small)
    draw.text((752, 348), "Menu bar / actual pixels + 3x inspection", fill=INK, font=font)
    for light, y in ((False, 400), (True, 524)):
        draw.rounded_rectangle((736, y - 8, 1408, y + 100), radius=12, fill=INK if light else "#FFFFFF")
        for i, size in enumerate((16, 18, 20, 22)):
            im = render(small_mark(size, light), size)
            x = 766 + i * 160
            sheet.paste(im, (x, y + 10), im)
            zoom = im.resize((size * 3, size * 3), Image.Resampling.NEAREST)
            sheet.paste(zoom, (x + 38, y + 2), zoom)
            draw.text((x, y + 74), f"{size} pt", font=small, fill=PAPER if light else INK)
    draw.text((48, 730), "Windows ICO / individually rendered frames", font=font, fill=INK)
    x = 48
    for size in APP_SIZES:
        im = render(icon(optical=size <= 32), size)
        display = im if size <= 128 else im.resize((128, 128), Image.Resampling.LANCZOS)
        sheet.paste(display, (x, 785), display)
        draw.text((x, 925), str(size), font=small, fill=INK)
        x += max(64, display.width + 24)
    sheet.save(BRAND / "previews/asset-board.png", optimize=True)


if __name__ == "__main__":
    main()
