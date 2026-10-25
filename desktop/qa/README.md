# Isolated interface verification

The HTML fixtures use the production React components with mock IPC. Run the
frontend dev server and open `qa/index.html` or `qa/formatting.html`. Parameters:
`lang=ar|en`, `theme=dark|light`; `links=1&preview=1` opens the reader and focuses a source preview; `first=1` on the workspace fixture shows first-run
setup. Fixtures never import into the production entry or read the user's data.
`long=1` supplies long account/model/assistant names; `models=retry` fails the
first model-list request so the local retry and retained selection can be checked.
`settings=<tab>` opens a settings section after mounting (for example,
`settings=local-models` or `settings=daily`). `download=downloading`
supplies an active model-download state and `reports=1` supplies a saved report.
`links=1` also includes a synthetic revision comparison with retained context and separated hunks. Expand Article history, show/hide unchanged lines, switch to Saved article, and collapse/reopen navigation to inspect focus restoration. These are fixture data, not actual downloads, provider requests or saved user reports.

## Packaged native checks

Build a separate QA bundle from `desktop/`:

```sh
npm run tauri -- build --debug --config "$PWD/qa/tauri.conf.json"
open --env OPENNEWS_NATIVE_QA=1 -n -a "$PWD/src-tauri/target/debug/bundle/macos/openNews Dev QA.app"
```

Quit any existing **QA** process before rebuilding or opening another QA bundle.
Do not quit or replace `/Applications/openNews.app`. The QA identifier uses its
own application-data directory and does not share the installed workspace.

The QA config disables WebKit background suspension only for the isolated test
window. The opt-in debug child browser receives the same scheduling policy, so
covering the test window with Codex does not suspend the runner mid-flow. Release
builds retain their normal energy-saving policy. Visibility-aware status polling
can still pause; its first read must complete independently of visibility.
The opt-in runner also falls back to timers for hidden animation frames so native
browser geometry is measured when the test window is occluded. No such override
is included in the production page.

`native-flow.js` is included only in debug builds. It runs only when the bundle
identifier is exactly `com.opennews.ui-qa` and `OPENNEWS_NATIVE_QA=1` is explicitly
present. It clicks the real interface, checks Cmd+, settings editing, source
discovery, draft saving, protected navigation, daily schedule saving/restoration,
legacy-import confirmation cancellation, activity and sidebar controls. It
restores the instruction field and disabled report schedule it edits, and leaves
clearly named QA drafts in that isolated workspace. It never confirms a workspace
import, sends a model request, installs an update or submits an issue report.

`LOCAL_PROCESSING_POLICY` changes quiet/balanced and pause through the real
controls, verifies the persisted engine response, then restores both preferences.
The final `SETTINGS_LOCAL_MODELS_RENDERED` leaves model settings visible for a
native screenshot. Browser fixtures also accept `local=loading|failed` to inspect
truthful unknown coverage without invoking any model.

`DRAFT_PREVIEW_EXPORT` previews the saved text and exports Markdown through the
actual UI/Rust command. `DRAFT_EXPORTED_<uuid>` identifies the exact generated file
`~/Downloads/openNews-<uuid>.md`; inspect and remove that one QA artifact afterward.
`CONVERSATION_CONTEXT` creates a named QA conversation, checks protected closing
and saved conversation instructions, and restores its original settings in `finally`.

When QA already has a subscribed feed, `SOURCE_INTERVAL` opens its action menu
with the keyboard, saves a different interval, reads the actual saved value, and
restores the original in `finally`. Closing the interval control must return
focus to that source's menu. `ARTICLE_LIBRARY_NAV` verifies that selecting Articles
in the sidebar returns from the reader to the library before reopening the story.

Check `~/Library/Logs/com.opennews.ui-qa/diagnostics.jsonl` for `ui.qa` checkpoints.
Only a final `PASSED` after the current launch proves that run completed; earlier
or partial checkpoints do not. Inspect native screenshots separately for visual
quality, original-site behavior and OS window interactions.

`native-smoke.py --pid <QA app PID>` tests the actual packaged engine via the
QA process's private socket. It validates the workspace path before any request,
reads/saves/restores instructions, creates a conversation and draft versions,
and checks snapshots and processing status. It cannot substitute for UI tests.

Optionally append `--feed https://blog.rust-lang.org/feed.xml` to subscribe to a
public feed in QA, wait for an article, verify full text/history/bookmarking, and
report content length and request timings. This reads public web content and
does not run a model. Restart the native runner after this check to exercise
the populated reader and embedded original website. The debug hook observes the
original webview's page-load completion; the runner leaves that site visible for
native screenshot review. An empty-library run explicitly logs that condition
and does not prove populated-reader or original-site behavior.

With a populated library, the runner also opens the article report, verifies that
its preview contains article context, and exports it through the actual Rust
command. `REPORT_SAVED_<uuid>` identifies the exact generated file in Downloads:
`openNews-diagnostics-<uuid>.txt`. Review that file and remove only this QA export
after verification; never clean Downloads by a broad filename pattern.

## Real signed update upgrade

Prepare a CI-built release with `desktop/scripts/package-update.py`. After the native Cargo tests compile matching test-enabled crates, run `engine/.venv/bin/python desktop/scripts/test-update.py --prepared build/updater/vVERSION`. The standalone Rust harness reuses those crates without rebuilding the large Tauri resource tree. It clones the old app to `/tmp`, starts its packaged engine with synthetic data and a temporary HOME, rejects tampering and signed-version mismatch, installs the new bundle, and reopens its engine to verify persisted articles, conversations, drafts, instructions and external credential/model sentinels. No user workspace or live model is used.

After publication, add `--public` to check the configured endpoint and download/verify the live artifact; it also verifies that the current version does not offer itself again. Validation JSON files contain shareable synthetic-check outcomes. Extracted bundles stay outside FileProvider-managed Documents so Finder metadata cannot invalidate their signatures.
