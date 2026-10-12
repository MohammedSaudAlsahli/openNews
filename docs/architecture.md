# Architecture — implementation 0.1.0

Date: 2026-10-11. PRD 1.0 remains the target specification, not a claim that every feature shipped.

## Implemented boundary

SwiftUI owns app lifecycle, windows, file panels, user consent and owner-only credential-file writes. One child CPython process owns editorial SQLite, Agno requests and job persistence. The client creates a private random temporary directory and passes its Unix socket path in argv. No credentials are passed in argv, process environment, protocol or database.

Each connection carries one UTF-8 JSON line with `schema_version=1` and UUID `request_id`. Maximum request/response size is 1 MiB. Invalid frames fail without provider exception contents. The directory is 0700 and socket is 0600. SQLite writes execute only on the engine event loop; network calls await asynchronously. A filesystem lock prevents a second engine opening the same workspace. The child watches parent death, and Swift terminates it on normal quit.

Jobs emit persisted `accepted/progress/completed/failed/cancelled` events. The current UI polls jobs once per second while any is running. Protocol `jobs.get(last_event_seq)` replays only later events. This is request/replay over the specified socket rather than server-push streaming; a later UI can add streaming without moving job truth out of SQLite.

`sources.add` normalizes HTTPS metadata URLs without fetching them. A canonical URL is a stable identity; otherwise SHA-256 of trimmed text deduplicates exact text. Updates at the same URL create immutable item versions. Unchanged imports do not create jobs automatically. Incremental analysis skips any completed analysis of the current version even if provider selection changes. Explicit rebuild permits a changed analysis configuration; identical signatures remain deduplicated. Signatures include the version identity to keep provenance distinct across sources with identical text.

Manual paste/file text becomes 2,000-code-point chunks with absolute source positions. Technique evidence is checked against an exact supplied chunk before transaction commit. Swift converts offsets using Unicode scalars, preserving Arabic combining marks. Deterministic local structure analysis emits only narrowly recognizable patterns; Agno is optional for deeper technique proposals.

DNA is approved explicitly. Each approval/retirement creates a frozen rules snapshot. Jobs pin input versions, profile configuration and DNA version at submission. Credentials are resolved at execution from the connection’s private JSON file, so key rotation does not modify the model or prompt snapshot. A job cancelled before execution is persisted as cancelled; unfinished prior-process jobs reopen as interrupted.

Agno runs with telemetry disabled, no tools, no filesystem, no persistent Agno memory, no automatic retries/fallback. Pydantic validates output. Source instructions cannot invoke shell/credential/network tools because none exist on the agent. Factual claims remain `needs_review` even if the model claims support. Referenced IDs must belong to selected input chunks. Editing creates a new draft version and invalidates previous evidence rather than reusing it on changed sentences.

## Pinned build

| Component | Observed version |
|---|---|
| Host | Apple Silicon, macOS 27.0 / 26A428 |
| Swift | 6.4 / swiftlang-6.4.0.34.1 |
| SDK | macOS 27.0 |
| Xcode present | 27.0 / 27A266a |
| Actual compiler selection | Command Line Tools; no global xcode-select change |
| Python | uv standalone CPython 3.12.13 |
| Agno | 3.1.2 |
| Pydantic | 2.14.0 |
| sqlite-vec | 0.1.9 |
| SQLite in bundle | 3.53.1 |
| OpenAI SDK | 3.28.0 |
| Anthropic SDK | 1.13.0 |

The full Xcode license was not accepted on the user's behalf. CLT can compile the application; the macOS 27 SwiftUI macro library is passed explicitly from the installed Xcode platform because this CLT install omits it. No unsigned plugin was downloaded. Runtime minimum is declared 14.0, but no claim of tested support below 27.0 is made.

## Deliberate milestone limits

One workspace directory is used by the UI; all business tables are workspace-scoped. FTS exists in the engine; UI currently filters titles and previews. sqlite-vec loading is proven, but embeddings/indexing are not implemented. Public RSS/Atom, website feed discovery and Reddit subreddit ingestion are implemented in a separate, opt-in news component; arbitrary source scraping and authenticated platform connectors are not. Persistent transaction checkpoints cover source analysis; interrupted model requests can incur another charge on explicit resume. Native schema decoding has tests; EIS-IPC still needs a full generated Swift model pipeline before a stable public contract release.

Schema v2 adds connection preferences, model catalog caches, and writer/analyst assignments without altering existing profile rows. Upgrading v1 creates an owner-only SQLite backup through the Backup API before a transactional migration. Unknown newer schemas are rejected.

The engine refreshes connected catalogs when due on startup and every minute checks a one-hour refresh interval; failed refreshes retry after five minutes and preserve the last successful list. Turning automatic refresh off preserves manual refresh. Discovery does not send editorial text. Swift resolves saved role preferences before displaying consent and sends the exact profile/model pair for each job. Analysis with no profile remains local. Job model snapshots remain immutable after assignment changes.

## Writing-workspace redesign

The native main window is a persistent editor plus SourcePanel, not a feature-page router. Settings is a native SwiftUI Settings scene. SourcePanel reads `sources.detail` for the complete current source version and its contextual techniques; snapshot previews must never be treated as authoritative editable text. `drafts.create` accepts the strict ManualDraft schema to create a local version with the current frozen DNA snapshot and explicit review warning, without a provider. `drafts.detail` remains authoritative for editing. Manual save, dirty-state transitions, and generated-job completion are separate: a generated result is identified through its submitted job ID and `jobs.get.result_json`, never by any newly appearing draft. Reimporting identical source text updates user-supplied metadata/rights without duplicating its immutable content version.


## Conversation, news and personal-style context (schema v3)

`news.py` owns `news_subscriptions` and `news_articles`. `conversation.py` owns conversations, paged messages, explicit source purposes and frozen news evidence attached to draft versions. Upgrades from existing v1/v2 stores create an owner-only pre-v3 backup before the transactional schema migration. Earlier provider tables and all 68 adapter entries remain intact.

`news.subscribe` persists an enabled subscription and queues background synchronization; it does not wait for every article before returning. A site URL can discover an advertised RSS/Atom link. Subreddit URLs normalize to Reddit's public `new/.rss` feed. Requests are GET-only, without browser sessions, cookies, account credentials or proxy inheritance. DNS answers are validated as public; TCP connects to a validated numeric address while TLS verifies the original hostname. Every redirect is validated again. Private/mixed DNS answers, dangerous XML declarations and oversized/decompression responses are rejected. Feed and article content remains untrusted data.

Conditional ETag/Last-Modified requests, URL/GUID deduplication, separate publication/discovery times, persistent unread state, per-subscription errors and retained prior items make refresh incremental. Full article extraction uses trafilatura. `body_status=full` means article text was extracted; `summary_only` means only the feed summary was retained, not that the article was read or its facts verified. `pending` means body retrieval has not finished. Retries and batches are bounded. The UI snapshot contains the 100 most recent articles; the underlying database is not truncated to that list.

`NewsManager.poll()` checks due subscriptions every minute while the embedded engine is running. The default subscription interval is one hour. Opening the app starts a due check; closing it cancels polling and active feed tasks. It is not an operating-system background subscription service. A source can refuse public access, including Reddit HTTP 403, without the app attempting a bypass.

`chat.send` freezes the selected profile/model, approved DNA version, bounded conversation history, optional current draft and selected evidence into a persistent job before awaiting a model. It allows only one active response per conversation and uses request idempotency. Resuming an older request after a newer message is rejected rather than mixing contexts. Detail responses page messages to stay inside the socket frame budget.

Without explicit article selection, news context is at most 12 deduplicated stored URLs with known publication timestamps in the selected window (seven days in the current native UI). Unknown or future dates do not establish weekly recency. Explicitly selected articles can be older. This query uses stored records, not only the 100 UI rows. Each supplied article is bounded to 10,000 characters. Up to six owned/licensed `purpose=style` examples (4,000 characters each), up to 30 approved rules and up to 16 prior messages provide context; this is prompt-time adaptation, not training or fine-tuning. News and personal style samples use separate tables/purposes and are not automatically promoted into DNA.

The conversation model has no browsing tools. It can discuss supplied evidence and propose independent X posts, a cohesive long YouTube script or individual TikTok scripts. These are textual artifacts. Output schemas and source IDs are validated; factual truth is not independently established by that validation. Draft artifacts are saved as separate editable drafts with frozen news excerpts and review warnings. They never silently replace the working document. Video duration is an estimate; no video rendering or publishing is performed. See `docs/chat-news.md` for the user-facing coverage boundary.
