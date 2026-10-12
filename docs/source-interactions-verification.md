# Source discovery and conversation feedback

- Customization has one Cancel action plus Save; removed the duplicate header close action. Escape and dirty-state protection remain.
- Discover sources is visible in the primary sidebar and the News panel. Its existing YAML-backed catalog supports categories, search, language filtering and Following only. Follow starts the existing subscription workflow; saved/paused/error states are explicit. Add a link opens the existing RSS/Reddit form directly in the catalog. File editing remains under Manage source catalog.
- Conversation reference links show a native NSPopover containing the source title, domain, date, saved excerpt and original-source link. Hover waits 300 ms; clicking also opens the preview for keyboard/accessibility use. Non-citation links retain browser behavior. Preview content is local and is labelled as a stored excerpt, not a frozen transcript of what the model read.
- `news.preview` reuses the workspace-scoped local article reader with mark_read=False. Preview does not fetch a website, call a model or mark the article read. Summaries remain available when full text is absent.
- Assistant activity uses existing chat.progress stages and frozen attached-source metadata. It distinguishes waiting, receiving text and validating. No inferred chain of thought, fake browsing or new Agno behavior is introduced.
- Regression tests cover citation glyph hit testing in Arabic and English (including rejecting blank-space hits), and read-only, workspace-isolated source preview.

## Verification — 2026-10-12

- `bash scripts/test.sh`: 267 Python tests and 32 Swift tests passed (299 total); brand asset verification passed.
- `bash scripts/build_app.sh`: final development DMG built, strict code-signature verification and disk-image verification passed.
- Relocated bundled runtime smoke passed. Bundled conversation smoke made four actual Agno calls against the mock transport, covered discussion/X/YouTube/TikTok, emitted 19 stream previews, persisted eight messages and created three separate drafts. No paid provider request was needed for this validation.
- Native UI checked in Arabic and English: Discover sources, categories, Following only (the four existing subscriptions), Add a link and Cancel, customization with one Cancel action, and an existing Arabic conversation's source preview.
- Source preview checked in light and dark appearance. Its saved article excerpt has a fixed readable scroll area; title, domain, date and original-source link remain visible. RTL/LTR hover hit testing is covered by the native TextKit test; clicking was checked in the running app.
- The user's English/dark appearance was restored after QA. Existing subscriptions, conversations and customization were preserved.
- New request activity is checked against existing progress-stage contracts and build/tests; this pass did not send a new live model request.
- No changes to the Agno provider, conversation engine or authentication implementation. See `agno-current-usage.md` for enabled and absent capabilities.
