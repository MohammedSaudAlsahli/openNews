# Reading and media — development stages

[العربية](reading-workspace.md)

Implemented on develop; this is not an official release announcement.

## Implemented

A reading hub offers catch-up, an estimated five-minute session, a queue, followed topic phrases, changed articles and saved quotations. It reuses saved summaries without model calls. Briefings cover the latest 500 articles; queued articles may be older.

Topic following matches phrases in titles/descriptions and orders results chronologically; it does not cluster events semantically. Source comparison shows literally different excerpts, not verified new facts or corrections.

Reading position and filters persist locally. Reader search covers article and summary text. Selection actions save a quote or prepare an unsent explanation, translation or question in chat. Quotes distinguish article text from AI summaries. Bookmark changes offer undo.

Inline image enlargement is removed. Known publisher images remain covers; absent covers show the source name rather than an invented news image. Article/RSS audio and video are preserved, and retrieved media associated with chat citations can be displayed.

## Media limits

Playback loads only on request, never automatically. Supported files up to 4 MiB load inline; the disk cache is bounded to 64 MiB. Larger files and embedded players open at the original source. Publisher scripts are not executed in the reader.

A media URL must already belong to an article or saved message citation in the workspace. Existing public transport validates destinations and redirects. Showing a video does not mean the assistant watched it: answers rely on retrieved text and metadata.

Responses expose the latest 40 quotations to keep IPC bounded; storage retains up to 500. Reopening an article does not regenerate its summary.

## Later stages

External cover discovery with provenance; semantic story grouping and evidence-backed source additions; resource-bounded streaming for longer clips; installed macOS playback and source-return acceptance checks before official promotion.
