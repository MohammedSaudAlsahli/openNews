# openNews architecture

[العربية](architecture.md) · [Documentation](README.en.md)

Tauri is the supported app. The former architecture remains on [archive/swift-legacy](https://github.com/MohammedSaudAlsahli/openNews/tree/archive/swift-legacy).

```text
React / TypeScript → Tauri / Rust → Unix socket → Python / Agno → SQLite
                           ↓                          ↓
                    macOS helpers              Ollama / chosen providers
```

- `desktop/src` owns rendering, navigation and transient state: Arabic/English, reading, conversations and settings. The browser does not read credential files directly.
- `desktop/src-tauri/src` owns engine lifecycle, allowed IPC commands, native dialogs, external URLs, diagnostics and updates. External reading webviews are separate from the application UI.
- `desktop/native` provides small Swift services for macOS/WebKit, not the legacy SwiftUI app.
- `engine/eis_engine` owns news, conversations, drafts, instructions, skills, models and jobs. It is authoritative for persisted state.
- SQLite stores local content versions and job state. Downloaded model weights are separate.

Rust starts bundled Python in isolated mode with a restricted environment and uses a private Unix socket. A workspace lock prevents competing engines. Messages use request IDs, a schema version and size limits. Quitting terminates the engine; closing the window leaves the tray app running.

Embedding and explanation workloads share local inference scheduling and performance limits. Power, thermal and memory-pressure signals can defer background work. Downloaded inventory is separate from model assignments: embedding for search, generation for explanations. Not every model supports both.

Articles, skills and HTML are untrusted data. Fetching constrains public addresses and redirects; rendering sanitizes HTML. Skill import never executes repositories. A selected cloud provider receives the context required for its request.

Verification comprises engine pytest tests, frontend Vitest tests, and Rust tests for IPC, persistence and a synthetic signed update. [Native QA](../desktop/qa/README.md) exercises real UI flows in a separate workspace. These gates do not establish performance on all hardware or a complete security audit.

## Compatibility names

The current app retains `com.editorialintelligence.studio.preview`, the internal `eis_engine` Python package, and historical executable/signing-key paths. These are active runtime and compatibility references, not additional former applications. Cosmetic renaming can disconnect data or updates. `engine/eis_engine/contracts.py` is the source of IPC contracts; unused generated JSON snapshots are not tracked.
