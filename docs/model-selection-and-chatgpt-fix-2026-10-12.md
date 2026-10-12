# Model selection and ChatGPT response fix — 12 October 2026

## Reported problems

The separate “Search models” field filtered a dropdown on the next row without making that relationship clear. The ChatGPT connection displayed MODEL_UNSUPPORTED after the user had already signed in and loaded an account-specific model catalog.

## Diagnosis and fix

A small live request using the saved ChatGPT connection and GPT-6-Sol authenticated and completed successfully. The response stream delivered its text in a `response.output_item.done` event, followed by `response.completed` with an explicitly empty `output` array. The previous adapter read only the terminal response object and lost the finalized text. The subsequent schema validation produced the misleading generic MODEL_UNSUPPORTED message.

The adapter now retains finalized output items by output index and uses them when the successful terminal response has no output. It preserves final annotations and refusals, does not concatenate duplicate text, and still rejects failed, incomplete, or interrupted streams. Receiving text alone is never treated as completion. No OAuth scopes, account permissions, stored credentials, or billing paths were changed.

Known subscription, permission, request-format, network and temporary-service failures now produce separate recovery messages. A structured-output validation failure says the account is connected but the response format was invalid, instead of directing the user to check an API key they do not use. Raw provider response bodies and credentials are not returned to the interface.

The connection form now has one Model chooser. It opens a selectable list with a checkmark for the current model. Search appears inside the list only for catalogs larger than eight models; small lists show their choices directly. Search checks both display names and IDs and does not keep unrelated selected models in filtered results. This shared control is used by connection settings, agents and the conversation model selector.

## Verification

- Live pre-fix reproduction: GPT-6-Sol completed the stream, but the adapter returned no content.
- Observed event sequence: finalized message with output text, then completed response with an empty output array.
- Live post-fix execution through the real Agno ModelFactory and GeneratedDraft schema: `Connection OK`, structured output validated.
- Requests used generic connection-test text, not user articles, writing samples, or conversation history.
- 243 Python tests and 21 Swift tests passed. The OAuth/adapter subset has 32 tests, including empty/full terminal outputs, duplicate finalized events, incomplete streams, safe recovery messages, and full Agno schema validation with an empty terminal output.

## Packaged-app check

The rebuilt DMG passed both bundled-runtime smoke checks, local code-sign verification and disk-image verification. In the running app, the existing ChatGPT/GPT-6-Sol connection test displayed **Model test succeeded**. The seven-model ChatGPT chooser had no search field; the larger OpenRouter chooser filtered Gemini rows immediately and displayed a clear no-results state for an unmatched query. The new chooser was opened in both English and Arabic; English/Dark preferences were restored. No provider credential, saved model choice, or connection name was changed during this check.

## References

- [OpenAI models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [OpenAI errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)
- [OpenAI preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
