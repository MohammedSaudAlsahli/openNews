# Sign in with ChatGPT

The OpenAI connection flow offers an API key or browser sign-in. Browser sign-in uses OpenAI's documented dynamic registration for locally hosted applications, with this application's own name and persistent host identifier. It does not read OpenWork/Codex credentials or use shared client IDs or private inference endpoints.

The engine binds an ephemeral loopback-only callback, validates PKCE, state, nonce, issuer, signed identity, audience, and granted scopes, and atomically stores credentials in the workspace's private `.providers` directory. Credentials and tokens never cross the app's IPC interface. The UI polls only a bounded attempt identifier and status. Closing the flow cancels pending sign-in; attempts expire after ten minutes. Reauthorization preserves the saved account identity.

Models come from the signed-in account's official model endpoint. The custom Agno Responses adapter consumes the required streaming response with `store=false`, rejects failed or incomplete streams, and retains the existing structured-output validation. Model tools are not enabled for this connection. The UI offers reauthentication if the session expires.

Mocked tests cover the callback socket, JWT signature and claim failures, permission denial, refresh rotation, account mismatch, symlink-safe storage, shutdown, model discovery, and execution through the real Agno factory. Official OpenID discovery metadata was checked live. On 12 October 2026, a generic connection request using the user's already signed-in ChatGPT account and GPT-6-Sol completed through the real Agno factory with validated structured output. This exposed and verified the fix for empty terminal output arrays described in `model-selection-and-chatgpt-fix-2026-10-12.md`. Availability for other accounts and models remains unverified.

Official sources:
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
