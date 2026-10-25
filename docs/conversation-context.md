# Conversation activity and context

SQLite message history is the source of truth for each conversation. Agno receives the application's conversation, workspace and job identifiers; the app does not enable a second history store or inject messages twice.

Each submitted job freezes its selected history, article references, instructions, preferences and model. Recent context is bounded, and truncated excerpts remain marked. `search_conversation_history` retrieves older saved excerpts only from that conversation, with pagination and an upper message boundary that prevents retries from seeing later turns. This is not cross-conversation memory or an automatically generated transcript summary.

The React interface shows actual execution events separately from answer text. Provider-supplied public reasoning summaries may appear when supported; missing summaries are not synthesized. Recorded activity persists with the result. Sources remain attributed beneath the response.

Jobs belong to the engine. Moving to another conversation detaches the foreground poll without cancelling the job; returning loads the saved result or resumes its active status. Request and conversation identifiers guard against stale completions replacing another thread. Composer drafts remain associated with their conversation. Quitting the application stops its local engine.

Conversation instructions and attachments remain separate from the current request. Unsaved changes, model-use consent and cancellation use the existing application controls. For user-facing behavior, see [conversations and news](chat-news.md), [instructions](editorial-instructions.md) and [Tauri QA](../desktop/qa/README.md).

Engine and interface fixtures cover session isolation, context bounds, frozen retries, persistence, activity rendering and navigation races. They do not establish live provider availability, response quality or latency.
