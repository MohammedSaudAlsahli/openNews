# Local news memory

The RSS library remains the persistent evidence store. Agno's `search_saved_articles` now uses hybrid retrieval; external research remains a separate tool and is used when RSS does not answer the request or the user explicitly asks for web search.

## Storage and retrieval

- Explicit RSS `content:encoded` / Atom content is preserved, including when a short description precedes it. Full cached articles survive both automatic and manual feed refresh. Explicit reader refresh can still retrieve corrections.
- SQLite FTS5 indexes overlapping passages across the entire saved text. Keyword search works during setup and offline, with fallback for newly ingested articles.
- Optional local semantic search uses Google's `google/embeddinggemma-2`, pinned revision `914f7f89142e33e77833254d9c9b90c3cef7303b`. Only text encoders load, on two CPU threads in a worker, using float32. Query/document task prefixes follow Google's model card. Embeddings are normalized to 256 dimensions and stored in SQLite alongside the original passages; sqlite-vec computes cosine distance. This is exact vector search over date-filtered rows, not an approximate ANN index.
- Model weights download once to the workspace models cache; the published checkpoint download is approximately 1.49 GB even though unused vision/audio encoders are not loaded. No article text is sent to Google or Hugging Face. Model download requires connectivity; subsequent inference is local.
- Reciprocal rank fusion combines lexical and semantic candidates. Publication-date constraints and workspace/RSS scope apply to both paths. Duplicate URLs collapse at retrieval. Results contain original article IDs, passages, source names and URLs, preserving citations. Semantic similarity is a retrieval hint, not evidence that two events are causally related.
- SQL triggers immediately invalidate stale passages when article content or metadata changes; deleted articles remove their vectors and FTS entries. Encoder revision changes discard incompatible vectors. Indexing processes small batches and yields between them. Pending chat jobs take priority. If semantic setup fails or indexing owns the encoder, keyword search remains available.

## Prepared summaries

The user-selected news model generates brief source-grounded summaries through the existing Agno route. Only complete articles enter the queue. Summaries preserve uncertainty, names and dates; very long articles send a bounded 12,000-character excerpt marked as truncated. Original articles remain available for detailed follow-up.

Settings expose a daily request limit (default 20, range 1–200). Requests are reserved durably before dispatch, so cancellation, retries, failures and restarts count toward the limit. It resets at midnight UTC. This bounds request count and input size, not an exact monetary amount. Model-provider pricing still applies. Disabling preparation cancels the active summary request. User conversations interrupt background generation.

The cache identity includes article text/title/URL/date/completeness, language, provider profile and selected model. Identical evidence already summarized through the same configuration can be reused without another request. Changing an article invalidates the displayed cached summary immediately. All eligible saved history is considered; no newest-300 cutoff remains.

Native SwiftUI controls live in `NewsMemorySettings.swift`; indexing and summary services remain separate modules. There is no inferred knowledge graph in this release.

## Validation — 2026-10-14

- 312 Python and 40 Swift tests passed after packaging dependencies were finalized.
- The relocated bundled runtime passed SQLite/vec/provider smoke checks and four Agno conversation formats against a controlled model endpoint, including streaming, persisted messages, drafts and citations.
- The actual pinned Google model passed four cross-language retrieval cases (Arabic queries over English stories and English over Arabic), exact date exclusion, and vector reuse. The bundled-runtime run used `HF_HUB_OFFLINE=1` and the cached official weights. Warm retrieval on five synthetic stories took 53–61 ms; this is a small fixture, not a large-library performance claim. Initial offline setup/indexing took 16.7 seconds and process peak memory was about 2 GB.
- Native News memory settings were inspected in Arabic RTL and English LTR. Local indexing was enabled and observed progressing on the user's saved library. Prepared summaries reached the 20-request daily cap and stopped; the remaining backlog is intentionally deferred.
- The model processor currently requires Pillow and torchvision even for text-only encoding; these are included in the locked application runtime.


## Queue visibility and cache audit — 2026-10-14

Manual summaries now populate the shared digest cache, including legacy explicit-cache hits. Background preparation drains eligible work with a one-second yield after progress and a ten-second idle wait; user model jobs retain priority. Status exposes disabled, missing model, quota reached, waiting for model/articles, retry, queued, preparing, and ready states. Settings show the selected summary model, ready/backlog counts, request usage and the reason for waiting. The existing daily limit is not silently increased.

The live workspace had 17 valid summaries and had used all 20 daily requests (requests include cancelled/failed attempts). Opening “Is 'Attention' the Essence of Intelligence?” displayed its pre-existing Arabic summary immediately without requesting generation. The updated native settings displayed the daily-limit reason and 714 eligible pending articles. Regression tests verify manual-summary reuse after recreating the digest service. No additional paid generation was forced past the user's limit.

## User-selected local summaries

Settings → Summaries & Models (التلخيص والنماذج) is the dedicated native page for
automatic summaries. News memory links to it. Suggested, Library and Downloaded
views share a searchable list and model detail pane. Library search is live and
paged; available versions come from Ollama's public catalogue HTML. No manual tag
entry or separate Ollama installation is required. Catalogue access and new
downloads need connectivity; downloaded models remain listed from app-owned
manifests even while the local runtime is stopped.

Choose a version and select **Download & Use** (or **Use this model** for an existing
download). The app checks capacity, prepares the runtime, downloads weights when
needed, and tests an actual Agno structured summary before selecting the local model
and enabling automatic summaries. The existing model-use permission must be enabled.
Progress, cancellation and actionable errors are shown in the same page; failed or
cancelled preparation does not activate the proposed model. Automatic summaries can
subsequently be paused with the switch. The connected-model route remains available
through the page's options menu.

The runtime uses app-owned model storage and a separate loopback service on
`127.0.0.1:11435`. It reuses an available Ollama executable, otherwise downloads the
official macOS release into app-owned storage and verifies its published SHA-256
before unpacking. Runtime and weights are downloaded on demand, not bundled into the
app. Capacity checks reserve 2 GB of disk space plus room for runtime extraction;
the conservative RAM estimate is a preflight check, not a speed or quality guarantee.
Cloud and embedding-only models cannot be activated for local summaries.

Generation uses Agno's Ollama adapter with no cloud fallback. One request runs at a
time with foreground work taking priority. Local requests do not consume the cloud
daily budget. Cache identities include model, language, and article fingerprint.
Article cards show summarized, summarizing, pending, retrying, or missing-full-text
states, refreshed in batches without resetting the article list. Download size,
estimated memory and actual startup validation are separate signals. Arabic and
English summary quality has **not been benchmarked in OpenStudio**.

See [Summary model settings](summary-model-settings.md) for implementation and
validation boundaries.

### Quiet local summaries

Local automatic summaries use one article per batch, followed by a rest of at least
60 seconds or four times the inference duration, whichever is longer. Native macOS
thermal status and Low Power Mode are reported every five seconds. Any non-nominal
thermal state, Low Power Mode, or missing/stale device signal blocks new local work;
thermal/power changes cancel active automatic summaries. Cloud summaries retain
existing daily limits. Local weights are released after completion, failure, or
cancellation; CPU inference is limited to two threads (this is not a GPU power cap).
The settings page exposes resting, cooling, power-saving, and waiting states.

Idle overhead: semantic-index polling no longer calculates full archive statistics
every second. Idle checks back off to ten seconds. Summary counts reuse results
until database changes, without caching entire article bodies. The references
panel relies on the central snapshot monitor instead of duplicating polling.

EmbeddingGemma also runs in an isolated local worker that exits after 30 seconds
without requests. This releases both tensor-runtime memory and model weights;
subsequent searches restart it on demand and may have cold-start latency. Automatic
embedding batches share the quiet budget/model lock with summaries, so the two
models do not infer concurrently in background. Thermal/power signals terminate
automatic embedding work. User-requested searches still run immediately. Stored
vectors remain in SQLite and are never deleted by idle cleanup.
