#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
uv run scripts/verify_brand_assets.py
uv sync --project engine --frozen
engine/.venv/bin/python -m pytest engine/tests -q
FLAGS=()
SWIFTUI_PLUGIN=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/usr/lib/swift/host/plugins/libSwiftUIMacros.dylib
TEST_PLUGIN=/Library/Developer/CommandLineTools/usr/lib/swift/host/plugins/testing/libTestingMacros.dylib
for plugin in "$SWIFTUI_PLUGIN" "$TEST_PLUGIN"; do
    if [[ -f "$plugin" ]]; then FLAGS+=(-Xswiftc -load-plugin-library -Xswiftc "$plugin"); fi
done
FRAMEWORKS=/Library/Developer/CommandLineTools/Library/Developer/Frameworks
if [[ -d "$FRAMEWORKS/Testing.framework" ]]; then
    FLAGS+=(-Xswiftc -F -Xswiftc "$FRAMEWORKS" -Xlinker -F -Xlinker "$FRAMEWORKS" -Xlinker -rpath -Xlinker "$FRAMEWORKS")
fi
# Keep generated test bundles out of FileProvider-managed Documents.
SCRATCH="${EIS_TEST_BUILD_DIR:-/tmp/eis-native-tests}"
swift test --package-path macos --scratch-path "$SCRATCH" --build-system native --disable-xctest "${FLAGS[@]}"
