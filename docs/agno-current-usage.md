# Agno: current integration audit

Verified against the application source on 2026-10-12. This change does not alter the Agno adapter, model settings, prompts, or model call path.

| Capability | Current behavior |
| --- | --- |
| Conversation replies | `Conversation.run` calls `Service.invoke_model`, which calls `ModelFactory.run` / `run_stream`. These instantiate `agno.agent.Agent` and call `agent.arun`. |
| Writing and AI style analysis | Also use `Service.invoke_model` and the same Agno agent path. Local structural analysis can run without a model. |
| ChatGPT sign-in | Uses the project's `ChatGPTResponses` subclass of Agno `OpenAIResponses`, still inside `Agent.arun`. Its adapter reads provider SSE output-text events. |
| Model adapters | Agno model registry supplies provider classes. The app manages credentials, discovery, availability and assignments. |
| Tools and browsing | Agent configuration currently explicitly uses `tools=[]`, `search_knowledge=False`. No agent browser or web search is available. |
| RSS and article reading | `news.py` fetches and extracts subscribed feeds/articles itself. Conversation preparation sends selected local evidence to Agno (up to 12 news articles, at most 10,000 characters per article). |
| Writing style | Examples and approved rules are prompt context, not fine-tuning. |
| Memory and persistence | Application-owned SQLite tables and conversation history. No Agno memory manager configured. |
| Embeddings / RAG | `sqlite-vec` extension is loaded when available, but no embedding model, vector index/population, or Agno Knowledge retrieval is configured. Existing source search uses SQLite FTS5. |
| AgentOS / teams / workflows | Not configured. App-defined named agents map to model assignments and instructions; they are not an AgentOS deployment or an Agno Team. |
| Reasoning display | No reasoning agent/tools are configured, and the UI does not consume provider reasoning events. Generic streaming handles content, completion and errors. The activity panel shows existing application stages and the exact citation list attached to the current request; it does not invent thoughts or tool runs. |

Agno supports additional streaming event types when configured: [Running Agents](https://docs.agno.com/agents/running-agents). Those capabilities are different from what this app currently enables.

Before adding embeddings later, choose a local/cloud embedder, chunking/version strategy, index migration and deletion behavior, hybrid retrieval/reranking, and citation mapping. None are enabled by this UI change.
