# Application packaging

[العربية](packaging.md) · [Release process](RELEASING.en.md)

`bash scripts/build_app.sh` generates the provider catalog, exports locked Python dependencies, stages relocatable CPython and its dependencies, compiles small macOS services, and builds Tauri. End users need no development tools or external Python.

Embedded native binaries are signed inside-out with ad-hoc signatures. CI verifies the bundle signature and starts the relocated bundled engine in a temporary directory, then creates a drag-to-Applications DMG from that same application. The final read-only mounted image must contain identical application bytes, modes and symlinks, with a valid signature. Intermediate ZIP/build metadata stays in CI; test reports are not user download assets. User databases, keys and model weights are excluded.

Output: `desktop/src-tauri/target/release/bundle/macos/openNews.app`. The current distribution builds on an Apple Silicon macOS runner. The declared minimum is 14.0; no supported Intel build is published.

Ad-hoc signing is not Apple Developer ID signing or notarization. Release notes disclose that limitation without classifying the official release as a preview. Apple signing/notarization needs separate provisioning. The supported build and release path is Tauri-only; former application tooling remains on `swift-legacy`.
