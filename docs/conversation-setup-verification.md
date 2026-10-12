# Conversation navigation and first-run setup — 2026-10-12

## Changes

- Direct inspection of installed OpenWork informed the persistent session sidebar, explicit new-conversation state, centered composer, and always-visible Settings entry. This remains a native SwiftUI app.
- Command–N starts a conversation; Command–Shift–N starts a draft. History selection restores that conversation's unsent text during the running session. A new conversation clears prior output/draft context. Active jobs cannot be detached by starting another conversation.
- Three setup steps: interface language, existing/new provider and default writer model, then optional model-use permission. Provider selection can be skipped for local use. Setup does not require a paid inference test.
- Permission is initially off, persists only after a user choice, and can be revoked in Settings → Permissions and setup. It applies to user-requested chat, generation, model analysis, optional validation, and retries. Dispatch rechecks permission, including from already-open sheets. Revocation does not retroactively cancel a running request.
- Existing credentials are reused; authentication renewal remains provider-specific. No OS permission prompts or login items were invented. The setup guide explains existing menu-bar/background behavior.
- The observed failed conversation was `MODEL_RESPONSE_INVALID`, not a sign-out. The ChatGPT adapter advertised native structured output but did not transmit native schema parameters. This caused Agno to omit its JSON-schema prompt too. The adapter now declares its actual capabilities; Agno supplies the schema in the prompt and still validates the response. No raw response is silently converted into a supposedly valid result.

## Evidence

- `bash scripts/test.sh`: 253 Python tests and 27 Swift tests passed; brand asset verification passed.
- The schema regression test failed before the adapter change and passed afterward. It verifies the outbound schema contains nested ChatDraft fields and supported output formats.
- A live generic ChatGPT `gpt-5.6-sol` request returned a validated `ChatReply`: `الدردشة تعمل بنجاح.` No user news, writing samples, or conversation history was included in this probe. This verifies that tested route, not every provider or model.
- Packaged runtime smoke checks verify the embedded Python/SQLite/socket and four conversation output formats against a mock provider.
- Native UI walkthrough: English → Arabic setup, existing ChatGPT account/model retrieval without reauthentication, save writer assignment, finish with model permission off, direct route to Permissions settings, English/light main window, Arabic/dark main window, previous failed conversation with distinct failure explanation, Command–N, and restoration of unsent text on returning to history.
- Visual testing found and fixed a missing English Continue label and stale permission-notice localization after a live language switch. New localized components observe language changes.
- Permission persistence/revocation and blocking requests before transport are tested using isolated UserDefaults suites. The walkthrough did not grant persistent model-use permission on the user's behalf.

## Scope

This is a targeted setup/conversation regression pass, not a fresh claim that every application window, accessibility workflow, provider, or OS version has been accepted. The app is a development build with ad-hoc signing; distribution notarization is unchanged.
