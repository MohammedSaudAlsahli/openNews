# Provider connections and live model catalogs

The provider menu is generated from all 68 canonical adapter keys in Agno 3.1.2. Every adapter's SDK is included in the locked build. An adapter importing successfully does not prove account entitlement, endpoint availability, structured output support, or live inference.

## Using the app

Add a provider in Settings, give the connection an optional name, and supply its credentials/configuration. Multiple connections to the same provider are independent. Expand a saved connection to search its model dropdown, refresh immediately, change its default model, or enable/disable automatic refresh. There is no manual model-ID field. Writer and analyst each have a separate saved connection/model choice; every writing or analysis request can override that choice before explicit consent.

Credentials are native-written JSON files at `~/Library/Application Support/com.editorialintelligence.studio/default/.providers/<connection-id>.json`. The folder is 0700 and files 0600. Settings can edit/reveal each file. API keys and cloud credential fields are not sent over IPC or persisted in SQLite. Existing `.claude` and `.codex` files are untouched. This deliberately replaces the previous Keychain path at the user's request; old Keychain keys must be re-entered.

## Automatic updates

The engine checks refresh eligibility on startup and every minute while running. Successful catalogs refresh hourly. Failed attempts retry after five minutes and retain the last good catalog. Manual refresh bypasses the schedule. Opening a dropdown reads the current cache; visible selectors check for updates every minute. No model is downloaded or inference invoked by discovery.

Sources are provider model APIs, official published catalogs where an API does not list models, and the configured server for local/OpenAI-compatible adapters. Pagination stays on the intended provider; credentials are never forwarded to arbitrary next-page origins. Error messages are redacted. OpenAI lists the account's models; Google and Cohere use their model listing APIs; Anthropic supports paginated model listing. Azure lists actual deployments through ARM and requires resource identifiers plus a management token separately from its inference key. AWS and Vertex need cloud credentials and region/project configuration. Ollama combines installed server models with its official public library; models needing installation remain disabled. Public catalog entries can be selected, but access must still be tested with the user's account.

Each provider has a discovery strategy in `engine/eis_engine/model_catalog.py`. The generic OpenAI-compatible path depends on the configured server implementing `/models`; a server that does not expose it reports a discovery error rather than offering fabricated or stale hardcoded IDs. Published catalogs are not proof of account-level availability. This build has not made paid or authenticated inference calls across 68 adapters.

## Verification boundary

Tests cover adapter imports/construction, credential file isolation and permissions, authenticated request routing with synthetic secrets, pagination, cache preservation after failure, independent role assignments, model-selection snapshots, workspace isolation, and v1 database migration. Public catalog smoke checks do not establish inference support. Exact current checks are in `validation-results.json`.

Official references: [Agno provider index](https://docs.agno.com/models/providers/model-index), [OpenAI model listing](https://platform.openai.com/docs/api-reference/models/list), [Google model listing](https://ai.google.dev/api/models), [Ollama installed models](https://docs.ollama.com/api/tags), [Ollama published library](https://ollama.com/library), [AWS model information](https://docs.aws.amazon.com/bedrock/latest/userguide/models-get-info.html).
