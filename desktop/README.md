# OpenStudio Tauri preview

Separate macOS preview: React/TypeScript interface, Tauri 2 window and Rust bridge,
with the existing embedded CPython + Agno engine. Not a replacement release yet.

## Build

Requires Node 22+, Rust stable and macOS command-line tools. Use the existing app's
verified Python runtime; no Nuitka, runtime pip installs, models or user databases.

```sh
npm --prefix desktop ci
python3 desktop/scripts/stage-runtime.py /path/to/OpenStudio.app
npm --prefix desktop test
cargo test --manifest-path desktop/src-tauri/Cargo.toml
cd desktop
npm run tauri -- dev
npm run tauri -- build --bundles app
```

## Implemented

- Quiet light/dark themes, persisted preference and reduced-motion support.
- Conversations, per-chat drafts, task routing and slash suggestions; engine jobs
  continue across navigation. Public activity updates live and collapses on completion.
- RSS subscriptions, directory, follow/unfollow, paginated articles, reader, bookmarks,
  related articles, cached images, draft editing and local Ollama connections.
- Actual assistant instructions visible in a Markdown editor with preview.
- Daily schedule settings and background/indexing/explanation status.
- Lazy page modules; bounded JSON IPC, cache-constrained images, HTTP/S links only.

Bundle ID `com.editorialintelligence.studio.preview` uses its own Application Support
workspace. Closing the window keeps the engine running; quitting stops it. No changes
to the installed native application or its data.

## Verified

Five React tests cover live activity updates, auto collapse/reopen, language isolation,
RTL/inert HTML, aggregator excerpts and viewport-triggered image loading. Two Rust tests run the real embedded engine,
checking persistence across restart, validation and instruction defaults. Manual UI
checks covered dark/light settings, visible instructions, subscribing to Hacker News,
and reading a fetched article. Optimized app builds successfully.

## Required before replacing the native app

- Complete provider connections, secure credential storage and browser sign-in.
- Model downloads/selection, power/thermal budgets, editable model/report instructions.
- Daily execution/notifications, tray reader, onboarding and Arabic UI localization.
- Rendered public-page recovery equivalent to the native cookie-free capture.
- Existing workspace migration with backup/rollback and cache/model preservation;
  never run two engines against one workspace.
- Signed updater, no duplicate installed apps, and a measured real upgrade. Tauri's
  documented updater uses a signed app archive; smaller/delta updates are unverified.
- Real-provider Arabic/English end-to-end tests, long chats, offline recovery,
  accessibility, performance and clean-machine packaging.

This preview has manual builds and cannot import production data. It does not use
or change the native Sparkle feed. Native v0.2.3 remains the working application.
