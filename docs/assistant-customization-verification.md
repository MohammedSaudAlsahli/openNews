# Assistant customization and conversation streaming

Verified on 12 October 2026. Native SwiftUI/AppKit frontend with the existing Agno engine; no web UI replacement.

## Behavior

- Settings → Customize assistant: general preferences shared by conversations, the writer, and the analyst.
- Agents → selected agent → Customize assistant: built-in writer/analyst and saved custom agents get individual preferences. Custom agents retain their original working instructions too.
- Conversation header → Customize assistant: settings apply only to that conversation. Opening it on a new chat creates an empty local conversation so the preferences have a stable owner.
- Six optional fields: role, working instructions, style, background knowledge, examples, and output format. Advanced System/Developer fields are mapped to the provider's supported instruction channel. The normal composer supplies user requests; assistant replies and tool results are not editable instruction roles.
- Preferences combine general → agent → conversation. The editor shows inherited general instructions and explains the selected-agent layer. More specific preferences guide style conflicts. The application's evidence and structured-output contract remains enforced.
- References added as text in the knowledge field do not create RSS subscriptions or grant browsing tools. This field is background information; subscribed news and writing samples continue through their existing controls.
- Local schema v6 adds workspace-scoped preferences with an owner-only pre-migration SQLite backup. No credentials or provider tables are rewritten. Each job captures its preferences before execution; retry keeps that snapshot.

## Response presentation

ChatGPT's existing official response stream forwards text deltas while retaining the terminal-event validation. Other Agno adapters use async streaming. A bounded JSON decoder exposes only the top-level message, never structured JSON, reasoning fields, or unfinished draft objects. Polling returns the current preview and actual waiting/generating/validation stage. This is not simulated typing or invented search activity.

Final messages/drafts are saved only after successful schema, source-ID, and format checks. Failure/cancellation removes the transient preview and preserves the user request. Provider authentication/rate-limit/service errors retain their connection-health classification. No automatic second model request is made as a streaming fallback.

UUID citation tokens resolve against the message's frozen evidence to safe, numbered HTTP(S) links. Unknown references cannot create links. Existing stored text is preserved. The transcript uses clearer user bubbles, a centered reading column, 16-point reply text and readable spacing.

Paragraph language is detected with Apple's on-device NaturalLanguage framework, then given an explicit TextKit paragraph direction and alignment. This handles Arabic paragraphs beginning with Latin product names. Original characters and evidence offsets remain unchanged. Language/appearance settings use segmented native controls to avoid the observed duplicate RTL picker arrows. The reading sheet no longer repeats its title inside the body.

## Verification

- `bash scripts/test.sh`: 266 Python tests and 31 Swift Testing tests pass. Coverage includes per-scope ownership, persistence/reset, frozen retry preferences, incremental Unicode JSON decoding, real Agno streamed chunks, cancellation/failure without partial saves, provider error classification, migration backup, glyph geometry and citation link safety.
- `scripts/smoke_conversation.py`: isolated local HTTP SSE model with the actual Agno adapter and Unix-socket IPC. All four content formats complete; intermediate previews observed; eight messages and three separate drafts saved; exported sources preserved. Also passes using the embedded runtime from the built app.
- Live ChatGPT probe with synthetic input only, no personal context: gpt-5.6-sol, 171 deltas; first readable preview at 14.46 seconds; completion at 20.48 seconds; preview exactly matched the validated final message. This is a single observed timing, not a latency guarantee. Other providers were not tested against paid live accounts in this change.
- Native UI: Arabic/dark and English/light customization, advanced options, per-conversation save/reopen, built-in writer/analyst entry points, restored original language/appearance, original saved conversation rendering and numbered references. Temporary preference content was removed after the save/reopen test.
- Release packaging: embedded-runtime smoke checks, ad-hoc signature verification and DMG checksum verification. Developer ID signing/notarization is still outside this development build.

## References

- [Apple: Right to left](https://developer.apple.com/design/human-interface-guidelines/right-to-left)
- [Apple: NSTextAlignment.natural](https://developer.apple.com/documentation/appkit/nstextalignment/natural)
- [Agno: Running agents](https://docs.agno.com/agents/running-agents)
- [Agno: Agent API](https://docs.agno.com/reference/agents/agent)
