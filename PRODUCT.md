# openNews

## Platform

web — a React interface inside Tauri on macOS. Python/Agno and SQLite run locally as an embedded engine. The paused Swift implementation is retained on the swift-legacy branch; documents about its native views are historical.

## Users and purpose

Arabic- and English-speaking readers follow news sources, read original articles, discuss evidence with an assistant, and create editable writing. The app should feel as direct as a good chat application, with a separate, focused reading experience.

## Product objects

- Sources: publisher sites, RSS/Atom, supported public Reddit communities and website discovery. Following is an explicit action; discovery itself never subscribes.
- Articles: saved originals, source URL, publication date, reading state, bookmarks, cached reader text and images, immutable revisions and optional explanations.
- Conversations: persisted threads, per-thread composer text, selected articles/files, model/assistant choice, optional saved-news retrieval and web research, progress, citations and generated draft artifacts.
- Drafts: editable local documents with saved versions, preview, copying and Markdown export. The app does not publish them.
- Models: provider connections and readiness, local Ollama generation and embedding models, on-device download/activation. App-observed request counts are not provider quota or billing data.
- Preferences: general/agent/conversation instructions, task instructions, writing references and guides, news processing, daily reports, appearance/language, diagnostics and updates.

## Invariants

- Preserve text while moving between surfaces. Unsaved editors must offer save, discard and keep editing.
- Preserve real sources and coverage. Feed excerpts are not full articles; inaccessible pages do not become invented content.
- Model-use permission and explicit user action gate requests. Credentials never enter conversation or diagnostics.
- Reports and automatic work run while the app is running; sleep/quit can defer them. Poll intervals are user-controlled.
- Original websites use a separate native webview within the reading surface. Publisher scripts do not execute in the application Markdown renderer.
- Arabic and English interface direction, mixed-content paragraphs, code, links and keyboard shortcuts remain usable in both themes.

## Current redesign

The 2026 Tauri redesign is the sole official, supported application. Swift is an archived implementation, with no parallel supported app releases. See desktop/qa/README.md and CONTRIBUTING.md for verification workflows and boundaries. A successful build alone does not prove all workflows or provider calls work. Browser QA fixtures are developer-only and do not ship with the production entry.
