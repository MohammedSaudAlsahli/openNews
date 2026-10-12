# Packaging and release gates

`scripts/build_app.sh` freezes Python dependencies from `engine/uv.lock`, generates JSON schemas/provider catalog, compiles SwiftUI, copies a relocatable uv-managed CPython distribution into the `.app`, installs hash-checked runtime wheels at build time, copies only engine sources, and signs every concrete Mach-O from the inside out before signing the bundle. `codesign --deep` is used only for verification.

The runtime runs with `-I -B`; a fixed bootstrap adds only the bundled engine path. No working-directory imports, user site-packages, inherited provider keys or runtime package installation. The build includes the wheel `dist-info` license files and a dependency inventory; a standards-compliant SBOM remains a release gate.

The bundled smoke test copies the app into a new temporary directory and runs health, SQLite/vec, import, local analysis, evidence and explicit DNA approval through the real socket. It verifies private modes and clean shutdown. This proves relocation on this host; it does **not** prove clean-machine installation, all supported macOS versions, notarization, Intel, or live AI.

`EIS_SIGN_IDENTITY` defaults to `-` for ad-hoc local testing. A real Developer ID identity enables hardened runtime/timestamp flags for nested code and app. No valid code-signing identities were available during this implementation. Ad-hoc builds are not notarized and must not be described as public releases. Do not disable Gatekeeper globally to test.

For a release, after all acceptance gates pass:

```bash
EIS_SIGN_IDENTITY='Developer ID Application: Your Name (TEAMID)' \
EIS_NOTARY_PROFILE='your-existing-keychain-profile' \
bash scripts/notarize.sh
```

The script signs, submits the zip to notarytool, staples, validates, checks Gatekeeper, then creates/signs/notarizes/staples the DMG. This release script has not been exercised with a real certificate. Notary failure must stop publication. Run `spctl`, notarization-ticket validation, fresh-user launch, offline launch, quit/orphan tests and a full source→draft→export journey on a separate supported Mac before declaring AC-01/AC-17 complete.

The minimum deployment target is provisionally macOS 14.0; actual validated host was macOS 27.0 / Apple Silicon only. SwiftUI is compiled via Swift Package Manager instead of a checked-in Xcode project. The installed full Xcode requires the user to accept its license; it was not accepted automatically. CLT compilation and platform macro plugins support this local build. Tests use Swift Testing, avoiding the absent CLT XCTest framework.

FileProvider can attach FinderInfo to generated `.xctest` bundles in Documents. Use a dedicated temporary scratch build directory for tests if automatic code signing rejects such metadata; do not modify user documents or global system policy as a workaround.

The same host also attached FinderInfo to a delivered `.app` directory and rejected its signature check. The final pipeline signs and tests the app in a private `/tmp` staging directory, then creates and verifies `dist/Editorial Intelligence Studio-development.dmg`. The filesystem inside that image preserves the signed bundle independently of Documents metadata. The default deliverable is the DMG; no unverified loose app is shipped. A release invocation can request a non-FileProvider app staging directory through `EIS_APP_OUTPUT_DIR` for notarization. This does not replace clean-machine Gatekeeper testing.
