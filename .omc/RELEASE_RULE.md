# Release Rules
<!-- last-analyzed: 2026-10-25 -->

## Version Sources
Primary: desktop/package.json. Match desktop/package-lock.json (root and packages[""]), desktop/src-tauri/tauri.conf.json, Cargo.toml and the application package in Cargo.lock. Stable version: 0.3.1. The Python package version is independent. VERSION, BUILD_VERSION and appcast.xml are historical Swift artifacts.

## Release Trigger
Push main, require successful ci.yml for that exact SHA, push an annotated vVERSION tag, then manually dispatch release.yml with tag and successful CI run ID. User authorized publishing the current Tauri work as the official application, not a prerelease. Never replace published tags/assets.

## Test Gate
bash scripts/test.sh; bash scripts/build_app.sh; cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml; relocated bundle smoke/signature validation. No bypass flags.

## Registry / Distribution
GitHub Releases: official macOS Apple Silicon ZIP, SHA256SUMS, build-info.json. CI builds; release.yml publishes only the successful main/push artifact at the tagged SHA. Ad-hoc signed, not Apple-notarized. No registry package publishing. Prepare a signed updater locally from that exact CI artifact with the existing owner key, test with test-update.py, append assets to the release, then promote updates/tauri-preview.json. Assets must precede the feed.

## Release Notes Strategy
Arabic-first README/docs with English counterparts. CHANGELOG.md and bilingual docs/releases/vVERSION.md. Clearly disclose architecture/signing and upgrade behavior.

## CI Workflow Files
.github/workflows/ci.yml and .github/workflows/release.yml. See docs/RELEASING.md.

## First-Time Setup Gaps
Apple Developer ID/notarization is not provisioned. The Tauri signed channel is active; a real 0.3.0-preview.1 to 0.3.0 upgrade is tested. Future promotions require the same two-version and public-download checks. Private keys stay outside source/CI. Never use scripts/publish_release.py or modify Sparkle appcast for Tauri.
