# Interface verification — October 2026

The supported Tauri interface covers conversations, articles, reader/history, sources, drafts, settings, skills and local model management. Arabic/English, RTL/LTR, light/dark, keyboard focus and native minimum width are part of the design contract. See [DESIGN.md](../DESIGN.md), [settings](settings-surface.md) and [skills](skills-surface.md).

## Repeatable checks

- `bash scripts/test.sh`: engine contracts, UI behavior, TypeScript and production assets.
- `bash scripts/build_app.sh` then `cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml`: native bridge, persisted engine state and synthetic signed-update verification.
- [Developer fixtures](../desktop/qa/README.md): synthetic IPC for visual and keyboard checks, separate from the production entry.
- The opt-in native runner uses only `com.opennews.ui-qa`. It exercises settings save/restore, source controls, draft editing/export, protected navigation, article/history/original-site and sidebar interactions. It does not send live model requests or import an actual user's workspace.

## Observed before release preparation

Frontend: 389 tests passed; engine: 514 tests passed. The final isolated native run completed 31 checkpoints with `PASSED`. Native QA and these counts are observations from the October 25 local validation; current CI is authoritative for each published commit. Browser review included Arabic/English, both themes and widths of 1440, 860 and 390 pixels. The 390px fixture is a layout stress test, not a mobile application claim.

These checks do not establish real-model answer quality, performance/heat on every Mac, clean-machine Gatekeeper acceptance, Apple notarization or a real two-version automatic upgrade. Local screenshots, personal data and session logs are deliberately excluded from Git.
