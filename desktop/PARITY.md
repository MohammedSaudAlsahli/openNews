# Supported Tauri application — verification boundaries

Tauri is the official openNews application as of 0.3.0. SwiftUI is retained on `swift-legacy`. This is a standalone release; publication does not activate or replace either automatic-update feed.

| Surface | Current verification approach |
|---|---|
| Conversations and writing | Engine contracts, UI send/cancel/context/save flows, protected editors, synthetic model responses |
| Articles and sources | Reader/source fidelity and revision contracts, native populated reading/original-site flows |
| Models and skills | Shared inventory/capability and selection contracts; bounded text imports, provenance and native skill persistence |
| Background processing | Scheduling, cancellation and resource-pressure contracts; actual live model performance remains hardware-dependent |
| Native bridge | Embedded runtime restart/persistence, credential permissions and socket validation |
| Updates | Signed synthetic fixture proves signature rejection/replacement; actual automatic-update feed is not published |
| Packaging | CI builds the app, verifies signatures/arm64 and starts a relocated bundled engine with a temporary workspace |

[Interface verification](../docs/interface-redesign-2026.md) records the latest local observations. [Native QA instructions](qa/README.md) explain how to reproduce the opt-in isolated checks. Each release must pass CI for its exact commit. Tests do not establish every provider OAuth flow, clean-machine installation on every macOS version, real-model quality or Apple notarization.

The [October 18 migration ledger](../docs/legacy/tauri-acceptance-2026-10-18.md) is historical. It does not determine the supported release status or current feature coverage.
