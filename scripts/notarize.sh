#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
: "${EIS_SIGN_IDENTITY:?Set a Developer ID Application identity before release}"
: "${EIS_NOTARY_PROFILE:?Set an existing notarytool keychain profile}"
if [[ "$EIS_SIGN_IDENTITY" == "-" ]]; then
    echo 'Ad-hoc signatures cannot be used for distribution.' >&2
    exit 1
fi
RELEASE_STAGE="$(mktemp -d /tmp/eis-release.XXXXXX)"
trap 'rm -rf "$RELEASE_STAGE"' EXIT
EIS_APP_OUTPUT_DIR="$RELEASE_STAGE" bash scripts/build_app.sh
APP="$RELEASE_STAGE/Editorial Intelligence Studio.app"
codesign --verify --deep --strict "$APP"
ditto -c -k --keepParent "$APP" build/notarization.zip
xcrun notarytool submit build/notarization.zip --keychain-profile "$EIS_NOTARY_PROFILE" --wait
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
spctl --assess --type execute --verbose=2 "$APP"
hdiutil create -volname 'Editorial Intelligence Studio' -srcfolder "$APP" -ov -format UDZO 'dist/Editorial Intelligence Studio.dmg'
codesign --sign "$EIS_SIGN_IDENTITY" --timestamp 'dist/Editorial Intelligence Studio.dmg'
xcrun notarytool submit 'dist/Editorial Intelligence Studio.dmg' --keychain-profile "$EIS_NOTARY_PROFILE" --wait
xcrun stapler staple 'dist/Editorial Intelligence Studio.dmg'
xcrun stapler validate 'dist/Editorial Intelligence Studio.dmg'
