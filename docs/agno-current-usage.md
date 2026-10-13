# Agno: current integration audit

Verified against source and live ChatGPT-connected tool execution on 2026-10-13.

| Capability | Current behavior |
| --- | --- |
| Conversation replies | `Conversation.run` calls `Service.invoke_model`, which calls `ModelFactory.run` / `run_stream`. These instantiate `agno.agent.Agent` and call `agent.arun`. |
| Writing and AI style analysis | Also use `Service.invoke_model` and the same Agno agent path. Local structural analysis can run without a model. |
| ChatGPT sign-in | Uses the project's `ChatGPTResponses` subclass of Agno `OpenAIResponses`, still inside `Agent.arun`. Its adapter reads provider SSE output-text events. |
| Model adapters | Agno model registry supplies provider classes. The app manages credentials, discovery, availability and assignments. |
| Tools and browsing | Conversation agents receive RSS search/read and optional web search/read function tools. Web search uses Agno WebSearchTools/DDGS. ChatGPT tool calls/results are supported; non-conversation model tasks receive no tools. |
| RSS and article reading | `news.py` fetches and extracts subscribed feeds/articles itself. Conversation preparation sends a diverse sample (up to 12 articles, 1,800 characters each); tools search the full saved library and read up to 16,000 characters from a source. |
| Writing style | Examples and approved rules are prompt context, not fine-tuning. |
| Memory and persistence | Application-owned SQLite tables and conversation history. No Agno memory manager configured. |
| Embeddings / RAG | `sqlite-vec` extension is loaded when available, but no embedding model, vector index/population, or Agno Knowledge retrieval is configured. Existing source search uses SQLite FTS5. |
| AgentOS / teams / workflows | Not configured. App-defined named agents map to model assignments and instructions; they are not an AgentOS deployment or an Agno Team. |
| Reasoning display | No reasoning agent/tools are configured, and the UI does not consume provider reasoning events. Generic streaming handles content, completion and errors. The compact activity line shows actual RSS/web queries and the source being read. Final references appear beneath the reply; private reasoning is not exposed. |

Agno supports additional streaming event types when configured: [Running Agents](https://docs.agno.com/agents/running-agents). Those capabilities are different from what this app currently enables.

Before adding embeddings later, choose a local/cloud embedder, chunking/version strategy, index migration and deletion behavior, hybrid retrieval/reranking, and citation mapping. Embeddings remain unconfigured.
