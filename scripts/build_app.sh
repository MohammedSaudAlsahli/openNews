#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p build dist
uv sync --project engine --frozen
PYTHONPATH="$ROOT/engine" engine/.venv/bin/python scripts/generate_catalog.py
uv export --project engine --frozen --no-dev --no-emit-project --format requirements-txt --output-file build/requirements.lock >/dev/null
# SwiftUI in the macOS 27 SDK uses a macro plugin not shipped by this CLT installation.
# Use the installed platform plugin explicitly without changing xcode-select globally.
SCRATCH="${EIS_RELEASE_BUILD_DIR:-/tmp/eis-native-release}"
PLUGIN=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/usr/lib/swift/host/plugins/libSwiftUIMacros.dylib
if [[ -f "$PLUGIN" ]]; then
    swift build --package-path macos --scratch-path "$SCRATCH" -c release -Xswiftc -load-plugin-library -Xswiftc "$PLUGIN"
    BIN="$(swift build --package-path macos --scratch-path "$SCRATCH" -c release --show-bin-path -Xswiftc -load-plugin-library -Xswiftc "$PLUGIN")"
else
    swift build --package-path macos --scratch-path "$SCRATCH" -c release
    BIN="$(swift build --package-path macos --scratch-path "$SCRATCH" -c release --show-bin-path)"
fi
engine/.venv/bin/python scripts/package_app.py "$BIN/OpenStudio"
