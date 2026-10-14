# Conversation activity, sessions and context

Each conversation uses its existing persistent SQLite message history as the source of truth. Agno receives the application's conversation ID as `session_id`, workspace ID as `user_id`, and job ID as `run_id`. We do not enable a second Agno history store or inject the same messages twice.

Before enqueueing a request, the app freezes its history, sources, preferences, model and highest historical message row. Recent history is limited to 16 messages and 32,000 UTF-8 bytes. This is a history budget, not a token count or a guarantee that every provider's total context window fits. Oversized excerpts are explicitly marked truncated. The current request and attached working draft remain separate.

`search_conversation_history` is an Agno tool over the current conversation only. It can retrieve older exact excerpts and their saved citations, even after restarting. Pagination and a frozen upper message boundary prevent retries from seeing newer turns. Source pages still need to be read to verify facts. Full transcripts are retained; no automatic generated session summary or cross-conversation memory is claimed.

The native SwiftUI disclosure presents real execution events (context preparation, history search, RSS search, web search and reading) and provider-supplied reasoning content separately from the answer. Source lists remain beneath the answer. Public OpenAI reasoning summaries are requested for known reasoning model families on Responses adapters. Provider/model support varies; no private internal trace is exposed or synthesized. Recorded steps and summaries are bounded and persisted in job events, then restored with the completed answer. Old messages without activity records remain compatible.

Validation uses fake providers and SSE fixtures. It covers session isolation, frozen retries, context bounds, history retrieval after reopening SQLite, durable activity and separation of reasoning from answer text. Live provider availability and latency remain dependent on the selected account/model.

References: [Agno sessions](https://docs.agno.com/sessions/overview), [context engineering](https://docs.agno.com/context/agent/overview), [reasoning events](https://docs.agno.com/reference/reasoning/reasoning).

Live verification on the connected `gpt-6-sol` ChatGPT route completed two short requests. The second called the history-search tool and correctly recovered the first question; its recorded activity and two-message context were visible in the native disclosure. This provider did not return a reasoning summary for these short requests. The SSE summary path is covered by fixtures, not claimed as live-confirmed.

## Background navigation

Running jobs belong to the engine, not the visible SwiftUI conversation. Once submission is acknowledged, selecting another thread or opening a new one detaches only the foreground progress poll; it does not cancel the job. Returning loads the persisted reply or resumes polling its active job. The sidebar reports active jobs independently of the selected thread. Unsent composer text is retained per conversation during navigation.

Navigation is briefly disabled during submission acknowledgement to avoid assigning a newly created conversation to the wrong editor. Completion fetches are guarded by conversation and job IDs; delayed replies cannot replace a different thread. A completion poll retries when navigation temporarily defers delivery. This covers moving between conversations, articles, drafts and other apps while OpenStudio remains running; quitting OpenStudio still stops its local engine.

Completed runs use a subdued “Worked for …” SwiftUI disclosure with minutes/hours and a trailing indicator. The active run retains its actual current operation. Tests cover draft restoration, active-thread navigation, delayed completion races, polling during navigation, and background job completion without modifying another thread.

## Composer and reading rhythm

The conversation and composer share a 680pt maximum reading column. The native editor grows from a compact single-line height to a capped 160pt scroll area using measured text layout, including wrapped text and window resizing. Focus has a subtle accent outline; an over-limit message uses an error outline and its existing explanatory text. Enter, Shift–Enter and input-method composition retain their existing behavior.

New conversations offer compact native prompt buttons with a vertical fallback for narrow layouts. References enables archive search without a fixed seven-day scope; explicit article and draft attachments stay visible. During an active reply the composer permits preparing the next message and explains background continuation. Focus/submit feedback and execution disclosure use brief transitions, disabled by the macOS Reduce Motion preference. Streaming prose itself is not animated.

Validation: 320 Python and 51 Swift tests passed after the reading-direction/editor changes. Native macOS inspection covered the empty state, long Arabic input reaching the scroll cap, shrinking after deletion, mixed Arabic/English paragraphs, and persisted Arabic reply lists with citations. Test composer text was removed without sending it. A final focus-state reset clears the editor outline when switching conversations. This pass did not re-test every theme or minimum-window configuration.


## Archive scope and activity audit — 2026-10-14

The composer no longer sends `days: 7`. Legacy explicit `days` remains supported up to 100 years; omission is unbounded. Common Arabic/English relative periods resolve before initial evidence selection (two days, numbered days, prior calendar week/month, current month/quarter). Last week uses ISO Monday–Sunday and resolved dates are supplied to the model. Other dates remain the agent's responsibility using dated archive tools. The initial 12-item sample is explicitly labeled as a sample, never complete archive coverage. Archive tools already search saved history outside the sample. Identical saved searches within one run reuse their results.

Execution groups repeated searches/reads under compact disclosures, omits empty context statistics, and separates public reasoning summaries across model turns and Responses summary parts. The compatibility renderer also separates joined bold headings in older records. It does not invent reasoning. The sidebar Activity popover summarizes completed tasks and retains actionable active/failed tasks. Redundant toolbar Settings and reference-panel Discover Sources controls were removed. Settings editors mount on first visit and retain edits thereafter.

Validation: 330 Python and 51 Swift tests pass. A live current-quarter RSS request resolved October 1–14, 2026, made one archive search, returned two linked stories, and completed in 21 seconds. This is one live observation, not a general latency guarantee. Existing public summaries were visually checked after expanding a saved reply.
