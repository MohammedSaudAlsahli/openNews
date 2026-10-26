# Accounts and connection methods

[العربية](accounts.md)

Open **Settings → AI models → Accounts & models → Add account**, search by provider name and choose a connection method. Adapters are grouped under recognizable provider names. Published model availability is not proof of account entitlement.

- **OpenAI:** browser sign-in with an eligible ChatGPT plan, or an API key with separate API billing.
- **Gemini:** a Google AI Studio API key, or Google Cloud OAuth for Vertex AI. Cloud OAuth does not consume a personal Gemini subscription.
- **Claude:** a Claude Console API key. The app does not advertise unsupported Pro/Max subscription sign-in. Supported cloud integrations retain their platform names.
- **Ollama:** a local server; address configuration lives in advanced options.

## Google Cloud OAuth setup

Enable billing and Vertex AI on a Google Cloud project. Grant the signing-in user permission to use Vertex AI. Configure the consent screen in Google Auth Platform and create a **Desktop app** OAuth client. Add test users during testing; public distribution may require Google's scope review.

Enter the project ID, region, client ID and client secret, then choose **Sign in with Google**. The browser requests the `cloud-platform` scope using PKCE and a temporary loopback callback. Choose a Vertex AI region supported by your project/model; the default is `us-central1`.

Registration and session credentials remain in the workspace's private local credential store, outside conversations and diagnostics. Tokens refresh when needed. Disconnect removes access/refresh tokens but retains client registration for reconnection; deleting the account removes its local credential. Local disconnect is not remote revocation; revoke access separately from Google account settings if desired.

After signing in, check the connection and refresh models. OAuth success alone does not verify project billing or model entitlement. Gemini requests use Agno's Gemini adapter, and ChatGPT retains the existing Agno integration.

Google support is implemented and tested with a simulated provider and real local callback. Live verification requires a configured OAuth project; this document does not claim a live account test.

References: [Google OAuth](https://ai.google.dev/gemini-api/docs/oauth), [Agno Gemini](https://docs.agno.com/models/providers/native/google/overview), [Sign in with ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).
