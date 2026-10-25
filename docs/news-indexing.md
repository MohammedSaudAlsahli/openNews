# Local news indexing and related stories

Settings → Your articles → Article search shows coverage, queued articles, current pause reason and segment details. Text search stays available without an embedding model. Indexing is independent of generated summaries.

SQLite queues new and changed content. Article text is split into bounded overlapping segments with the title attached. Vectors belong to a prepared model fingerprint; changing the content or model invalidates incompatible vectors without deleting the original articles. Progress survives restarts.

Ollama embedding calls are bounded and cancellable. The shared local runner manages model retention, foreground priority and cleanup. Quiet/balanced modes, battery policy and fresh thermal/memory signals determine when background work can proceed. New article arrival does not guarantee immediate completion while resource limits block work. These controls do not promise zero heat or constant throughput.

Related articles compare saved vectors within the current workspace and model space. They require suitable indexing coverage, exclude the current article and known duplicate records, and return semantic neighbors rather than a claim that two reports cover or corroborate the same event. This lookup does not run a model or mark articles read. Missing results remain explicit.

Engine contracts cover saved-vector retrieval without inference, bounded requests, cancellation cleanup, source invalidation, restart persistence and unrelated-result exclusion. UI contracts cover truthful coverage and pause states. See [architecture](architecture.en.md), [the archive](news-archive.md) and [TL;DR](tldr.en.md).
