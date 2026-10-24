> Historical migration observations. See [current acceptance](../../desktop/PARITY.md).

# Native → Tauri acceptance ledger

The approved calm Tauri visual design is retained. This is a functional migration
preview, not permission to replace the native release or its Sparkle channel.
Updated 2026-10-18. Evidence below distinguishes automated contracts from live UI.

| Workflow | Implemented / acceptance evidence |
|---|---|
| Conversations | Existing Agno engine, account/model/agent selection, attachments, per-chat instructions, persisted draft text, slash skills, live public activity, collapse/reopen. Imported ChatGPT account returned `جاهز` in a live Arabic test. |
| Articles | Source/unread/bookmark filters, pagination, full-text retry and refresh, related stories, explanation, history/diff, original link. macOS system HTTP transport recovered the reported WordPress article; UTF-8 regression covered; site banners and Gravatar identities excluded, old reader caches upgraded on opening. |
| Images | Viewport-triggered fetch, local cache, consistent cover dimensions and failed-image fallback. Two component tests. Imported 415 cached image files. |
| Sources | RSS directory search/filter/pagination, follow/unfollow, custom feed/link/subreddit flows use the existing engine. Not every external publisher is guaranteed accessible. |
| Accounts | Provider catalog, credential entry with owner-only atomic storage, browser OAuth, connection checks, model refresh and role assignment. Existing four connections imported; only ChatGPT exercised live. |
| Local models | Library/installed/capability/variant selection, capacity preflight, download/cancel/progress, activation. Shared Ollama models reused. New multi-GB downloads were not repeated during migration QA. |
| Instructions | Actual default/general/agent/conversation and summary/report instructions editable inside Markdown write/preview views. Save and preference-preservation contracts tested. |
| Writing | References, analysis, style approval/retirement, custom agents, draft creation/edit/history/export. |
| Background | Engine scheduler plus real macOS thermal/low-power state, daily report checks and notification delivery with persisted deduplication. Notification appearance still depends on macOS permission. |
| Reader helper | Cookie-free nonpersistent WKWebView public-page recovery in a separate short-lived helper; no credential/login/CAPTCHA bypass. |
| Menu bar | Background engine survives closing windows. Tray offers a compact searchable article reader, daily reports, workspace and Quit. |
| Appearance | Light/dark and Arabic/English with RTL; core Arabic UI visually checked. Provider/model names and upstream error messages can remain untranslated. |
| Import | Original must be closed. APFS clone, SQLite integrity checks, path rebasing, backup/restore, background work paused in copy. Live import: 2303 articles, 24 conversations, 17 drafts, 4 connections, 415 images; original retained. Four isolated migration tests. |
| Updates | Separate signed Tauri channel, check/download/progress/install/restart. Real updater library tested against a signed fixture: tampering rejected, one bundle replaced, outside workspace retained. Channel not published; a full released-app upgrade and download measurement remain release gates. |

## Required before a replacement release

- Publish the preview update feed only after a real two-version app upgrade test;
  measure bytes, verify imported data survives and prevent duplicate installed apps.
  Signed archive support does **not** prove incremental/delta updates.
- Run the expanded macOS CI (engine/native contracts, frontend, Rust and Tauri bundle).
- Complete clean-machine and long-session QA, notification permission/delivery,
  additional provider OAuth, model download and offline recovery smoke tests.
- Retain the native application until those gates pass. Do not point Sparkle at a
  Tauri artifact or merge the two workspace directories.

## Local test run, 2026-10-18

- `scripts/test.sh`: brand-asset checks, 417 engine tests (final reader regression rerun) and 54 native Swift tests passed.
- `npm --prefix desktop test`: 11 React tests passed.
- `cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml`: 4 passed,
  including embedded-engine restart persistence, credential permissions and the
  signed-update installation fixture.
- TypeScript production build passed. macOS release bundle and signed updater
  artifact built locally. These results are not a claim that remote CI ran.

## Reader parity follow-up, 2026-10-18

- Full article cards now open through a stretched native button, including images
  and whitespace. The bookmark remains a separate button above the hit target.
  Verified by clicking an image in the running macOS bundle.
- Explanations are expanded before the article body, with local generation feedback
  and visibility-aware polling for newly completed background explanations. Preview
  reads include valid cached explanations without changing read state.
- Disabled automatic explanations are now explicitly disclosed in the article list,
  with an opt-in enable action. Migration's paused setting is not silently overridden.
- Restored article discussion attachments, persistent reading font size, date filters,
  filter reset and an original-source action for complete articles as well as excerpts.
- App chrome is not text-selectable; article/message prose and editors remain selectable.
- 14 frontend tests and 23 conversation/preview engine tests passed. The earlier
  migration commit 9d69a02 passed both GitHub workflow runs; these follow-up changes
  have not yet run remotely.
- Local Tauri installation is distinct from publishing a replacement release. The
  original Swift bundle and workspace remain available for rollback. Original-site
  browsing currently opens the external browser rather than an embedded website tab;
  image enlargement and native Share menu parity still need implementation. The
  update/clean-machine gates above remain open.
