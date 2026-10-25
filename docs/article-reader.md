# Article reader

The supported reader is the React/Tauri interface in `desktop/src/pages.tsx`, with Markdown rendering, code blocks and source previews shared with the rest of the app.

- Articles retain their original URL, publisher, available text and coverage status. A feed excerpt is not presented as a complete article.
- Reader mode and the original publisher website are separate surfaces. Publisher pages use a separate native webview; their scripts do not execute in the application renderer.
- Saved TL;DR appears before the article, with the actual generating model and recorded time when available. Opening a saved result does not request inference. Explicit regeneration keeps the previous result until a replacement succeeds. See [TL;DR](tldr.en.md).
- Article links and summary citations support deliberate-hover and keyboard previews. They reuse saved source text first and disclose unavailable pages. Previews do not run a model or execute social embeds.
- Paragraph direction follows content; code remains left-to-right. Headings, lists, quotes, tables and preserved source formatting use the shared [Markdown renderer](markdown-rendering.md).
- Bookmarks, read state and saved article revisions persist in the local archive. Source removal does not delete saved articles. See [archive behavior](news-archive.md).
- Images and icons use bounded caches and constrained public fetching. Login-only and blocked pages may remain unavailable.

For source discovery and subscription controls, see [the source library](source-library.md). For isolated reader, history and original-webview verification, follow [native QA](../desktop/qa/README.md). Tests and saved source text do not establish that a publisher's claims are true.
