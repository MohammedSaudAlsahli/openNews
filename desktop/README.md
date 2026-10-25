# openNews desktop

React/TypeScript + Tauri 2 with the existing embedded CPython/Agno engine. The
approved reading-room interface supports light/dark themes and Arabic/English.
See [architecture](../docs/architecture.en.md), [isolated QA](qa/README.md) and [release gates](../docs/RELEASING.en.md).

## Build and test

Requires macOS 14+, Node 22+, Rust stable, uv and Xcode command-line tools.
The build stages a relocatable CPython runtime directly; no SwiftUI app is needed.
Models and user data are not bundled.

```sh
bash scripts/test.sh
bash scripts/build_app.sh
cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml
```

## Data and background work

`com.editorialintelligence.studio.preview` has its own Application Support workspace.
Settings → Privacy & updates imports a copy of the original workspace only when
its engine is closed. The current Tauri workspace is backed up and can be restored from
the same page. Original articles/accounts remain untouched. Shared Ollama models
are reused. Explanations, semantic indexing and daily reports are paused in the
imported copy; enable them in their settings when ready to use this app.

Closing the window leaves the tray and engine active. Quit stops the engine.
The tray's Read articles command opens a compact reader. Public-page capture uses
a temporary nonpersistent WebKit helper; it cannot recover private/paywalled pages.

## Signed updates

Tauri is the official application. Its signed update channel is separate from legacy Sparkle and is published at `updates/tauri-preview.json`. The historical filename and key remain for installed-client compatibility.
`engine/.venv/bin/python desktop/scripts/package-update.py` prepares a signed archive from the verified CI-built GitHub release using
an owner-only key outside the repository. It never publishes an update. Back up
that release key securely; losing it prevents updates to this signed channel.
No private key belongs in the repository, application, logs or CI artifact.

A signed-fixture integration test verifies rejection of tampering and replacement
of one bundle while preserving outside data. The real 0.3.0-preview.1 to 0.3.0 upgrade is checked with both packaged engines, synthetic persisted article/conversation/draft/instruction data and external credential/model sentinels. `desktop/scripts/test-update.py` also rejects signature tampering and signed-version mismatch. No incremental/delta-download claim is made.
