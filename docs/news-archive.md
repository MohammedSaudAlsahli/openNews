# Permanent RSS archive

RSS is an ingestion source, not the retention policy. Missing feed entries are never deleted. Unsubscribing sets `removed_at` and disables polling; the source identity, articles, bookmarks, summaries and revisions remain available. Re-adding the source resumes the same subscription.

`NewsArchive` assigns article identities using validated canonical URLs with known tracking parameters removed. GUID aliases are scoped to a subscription. Origins record the same article appearing in multiple feeds. Distinct publisher URLs remain distinct articles; semantic related-story grouping is deferred. Existing duplicate records retain their IDs for old chat citations, but duplicate cards are hidden and bookmark/read flags are preserved on the primary record.

Before the first archive migration, SQLite's backup API creates a complete committed database backup under the workspace `backups` directory. Migration does not delete articles or chat messages. Existing saved articles become baseline revisions; the application cannot reconstruct edits that happened before it saved the article.

Revisions store compressed, content-addressed JSON snapshots. Unchanged snapshots are not repeated; reverting to earlier content reuses its compressed blob but creates a new revision event. Current text stays readable in SQLite for existing search and reader code. Full-article teaser changes and reader layout/refresh metadata do not create revisions. Text, title, publication date, URL and completeness changes do. Revision comparison shows additions/deletions against the preceding saved revision, with the first revision compared against an empty baseline.

Full feed content updates are saved directly. Previously fetched website articles are rechecked when their RSS title or teaser changes. Ordinary unchanged-feed refreshes use cached full content. Changes on a website that RSS does not signal are not continuously crawled. Original ingestion size/safety limits still apply; inaccessible or partial articles retain their actual completeness status.

Summary cache identities include the evidence content and metadata so a new article revision does not reuse an old summary. Image data is not stored per revision. Reader images use the existing 100 MiB disk cache with access-time refresh; site icons remain bounded separately. Historical comparison is textual, not a pixel-perfect historical website capture.

## Validation

- Tests cover feed disappearance, unsubscribe/resubscribe, restart, duplicate cross-feed URLs and tracking links, distinct publisher coverage, changed article text, layout-only changes, immutable prior content and diff output.
- Migration is checked on a temporary SQLite backup of the real workspace before the live app is upgraded; row counts, foreign keys, integrity and repeat startup are checked.
- Reader history and unsubscribe controls use SwiftUI, with Arabic and English labels.

### Acceptance check (2026-10-14)

315 Python tests and 40 Swift tests passed. Migrating a copy of the real database preserved 703 articles, 5 subscriptions and 20 chat messages; integrity, foreign keys and repeat startup passed. The live upgrade created a backup and retained 703 articles with 703 baseline revisions. Packaged-runtime and Agno mock conversation checks passed.

History uses a separate SwiftUI comparison component: removed paragraphs have a red gutter, minus sign and tinted background; additions use green and a plus sign. Unchanged surrounding paragraphs remain neutral. Internal unified-diff headers are replaced by localized section names. The initial saved copy is neutral. The real history sheet was checked in Arabic and English, and the comparison component was visually tested with paired Arabic/English changed-text fixtures without modifying the user's articles.

### Native reading polish

The revision sheet now identifies the article, uses a native saved-version Picker, and gives the comparison the full reading width instead of an mostly empty sidebar. A single footer Close action and a brief history explanation remain. Loading, empty and retryable error states are explicit. Initial snapshots have no diff gutter; changed snapshots retain neutral context and restrained red/green marks. Paragraph direction follows its content independently of interface direction. Arabic/dark and English/light were visually checked using the actual SwiftUI views with isolated fixture data; the application data was not edited for the design test. The 315 Python and 40 Swift tests passed.
