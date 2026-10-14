# Release Rules
<!-- last-analyzed: 2026-10-14 -->

## Version Sources
VERSION (marketing version), BUILD_VERSION (monotonically increasing Sparkle version),
engine/pyproject.toml, engine/eis_engine/__init__.py, engine/eis_engine/service_commands.py;
refresh engine/uv.lock with uv lock. Package Info.plist derives from VERSION/BUILD_VERSION.

## Release Trigger
Local scripts/publish_release.sh after tests, build, source commit and green CI.
GitHub prerelease v0.2.0 is explicitly authorized. Future releases require an explicit
publish request. Existing CI runs tests and bundle smoke tests on push/pull requests.

## Test Gate
bash scripts/test.sh; bash scripts/build_app.sh. No bypass flags.

## Distribution
Public GitHub Releases, macOS 14+ Apple Silicon DMG. Ad-hoc Apple signature:
not notarized, experimental. Sparkle 2.10.0 EdDSA signatures protect updates.
Private key stays in login Keychain account com.editorialintelligence.studio.
Only release-config.json's public key belongs in Git. Never replace the signing key.

## Release Notes
CHANGELOG.md and docs/releases/vVERSION.md; user-visible changes and honest limitations.

## CI Workflow
.github/workflows/ci.yml. Publishing is local because no private signing key is in CI.

## First-Time Setup Gaps
No Apple Developer ID/notarization. First installation requires user trust of the
experimental distribution. Automatic update checks work after installing v0.2.0.
