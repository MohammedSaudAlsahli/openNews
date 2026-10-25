# Saved article archive

RSS is an ingestion source, not a retention policy. Entries disappearing from a feed do not delete their saved articles. Unsubscribing disables retrieval and preserves the source identity, articles, bookmarks, summaries and revisions. Re-adding the source can resume that subscription.

`NewsArchive` validates canonical URLs and removes known tracking parameters. Feed GUID aliases are scoped to a subscription. Origins record the same article appearing in multiple feeds; different publisher URLs remain separate articles. Existing duplicate identities remain available for saved citations while duplicate cards can be hidden.

Reader content changes create immutable revisions. Current text and historical snapshots are separate; metadata-only or layout-only changes do not need to create meaningful text revisions. Existing articles receive a baseline snapshot during migration. The React reader can display saved versions and their text differences; it does not claim a historical screenshot of the original website.

Content and evidence changes invalidate incompatible generated summaries and vectors. Stored coverage still distinguishes full text, partial text and feed excerpts. Ordinary retrieval failures preserve the last available content; unavailable pages are not invented.

Archive tests cover feed disappearance, unsubscribe/resubscribe, reopen, canonical identities, tracking links, cross-feed origins, content revisions and stable historical records. Reader/history UI tests and the [isolated native flow](../desktop/qa/README.md) cover presentation and persistence.

See [reading](article-reader.md), [local indexing](news-indexing.md) and [TL;DR](tldr.en.md).
