# Provider connection status

Connection health is independent of model selection, catalog availability, and stored account labels. SQLite schema v5 adds private per-profile status timestamps, with a migration backup for existing workspaces. No tokens are stored in this table or returned over IPC.

- `connected`: authenticated ChatGPT account request, OAuth completion, or successful model inference.
- `configured`: credentials saved; account/model response not verified. Public model discovery does not turn this green or renew an earlier verification timestamp.
- `unverified`: successful verification is older than ten minutes.
- `needs_login`: local credentials absent/invalid or provider rejects authentication.
- `disconnected`: explicitly disconnected locally; all subsequent model and catalog requests blocked.
- `network_error`, `service_error`, `restricted`, `limited`, `check_failed`: distinct recovery states, preserving credentials and last success.

The native list and detail view show readable status labels and symbols, not color alone. Details include last-check and last-success timestamps, Check now, reconnection and confirmation before Disconnect. An unavailable engine overrides cached green status. ChatGPT health is checked every five minutes while running (even with catalog auto-update disabled). Other providers update on catalog refresh or model requests. Provider-side revocation is detected on a subsequent check, not through an instantaneous push notification.

Disconnect removes local secrets, retains nonsecret OAuth registration metadata for same-account sign-in, cancels pending reauthorization, clears cached models and prevents stale in-flight catalog/inference results from restoring connected status. It does not revoke authorization on the provider website. Credential edits reset verification. Chat, analysis and drafting share the same health-aware model invocation path.

OAuth success/failure pages are static HTML with Arabic/English direction, no external resources, no reflected query parameters or account data, no-store caching, and restrictive CSP. Transient failures during token renewal preserve credentials; invalid-grant/authentication failures request reauthorization.

Recovery reference: [OpenAI errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery).

Tests cover token renewal failures, network recovery, permission/usage errors, missing/changed credentials, stale verification, disconnect/restart, cancellation, stale in-flight requests, public catalogs, and bilingual callback pages. Real account checks are separate from mocked protocol tests.
