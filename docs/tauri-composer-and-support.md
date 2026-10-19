# Sources, composer and diagnostics

The composer has a floating slash command menu with descriptions, arrow-key navigation,
Enter selection and Escape dismissal. `@` searches local news by title/text with an
optional bookmarks filter; selection attaches the saved article ID (maximum 12).
The plus button retains article-link import and per-conversation instructions.
Context options are presented in a floating panel without shifting the send controls.

Text attachment support: TXT, Markdown, CSV and JSON; three files, 48 KB input size,
10,000 characters per file. The combined message and file text must fit the engine's
12,000-character message contract. No silent truncation. File contents are sent only
with the message, using the existing provider consent gate, and retained in that
conversation as message text. PDF, images and office documents are not supported by
this attachment path. Unsent file selections remain in memory per conversation.

Source descriptions come from the curated catalog or publisher RSS channel / Atom
subtitle / HTML metadata. Existing subscriptions gain publisher metadata on refresh;
missing descriptions are disclosed rather than invented. Connection failures appear
separately. Drafts are local editable post/script documents, not published posts.

Shortcuts: Cmd/Ctrl+, settings; Cmd/Ctrl+N new chat; Cmd/Ctrl+Shift+B sidebar;
Shift+Enter newline. Help & diagnostics lists these shortcuts.

Diagnostics use bounded JSONL files in Tauri's app_log_dir, rotated at 256 KiB with one
previous file. Only timestamp, operation and error code are recorded. Payloads, raw
error messages, account details and article contents are excluded. The export includes
app version, OS/architecture and the latest 150 events. GitHub opens an unsubmitted
issue template; reports are attached manually after review. This is a local technical
log, not a native crash dump or remote telemetry service.

Validation: 25 frontend tests, 37 news tests; Tauri release build. Installed-app checks
covered slash keyboard selection, Arabic @ search and attachment, Cmd+, navigation,
source metadata after refresh, Context layout and diagnostic export.
