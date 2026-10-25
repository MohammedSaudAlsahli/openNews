# Summary, report and assistant instructions

Settings exposes the actual editable instructions used by the assistant, article TL;DR and daily reports. Save and reset act on those documents, and protected navigation handles unsaved changes. No external editor is required.

Instruction files live under the active workspace's `instructions/` directory; see [workspace location](SETUP.en.md). Existing edits are preserved across application updates. The allowlisted `instructions.get/save/reset` commands read and atomically write the same documents generation uses.

- `article-summary.md` controls source-grounded article summaries. Output language, source coverage, quotation checks and inference limits remain runtime constraints. See [TL;DR](tldr.en.md) for background preparation, caching and regeneration.
- `daily-report.md` controls synthesis and attribution in daily reports. Scheduling, saved report identities and notification permissions remain separate from the writing instructions.
- Assistant sections come from `assistant_defaults.py`. Saved general instructions combine with explicit agent and conversation overrides; article/report instructions remain separate. Saving instructions affects new requests, not already saved answers.

## Daily report

The feature has an explicit on/off switch, local time, time zone and output language. It runs while the engine is active, using available followed-source articles and bounded context. Sleep or quitting can defer work; no system daemon is installed. Saved reports remain available in settings. Notifications are requested through macOS and sent after completion when permitted.

One saved report per scheduled date prevents duplicate output. Source coverage remains explicit; a followed-source roundup is not comprehensive world-news coverage. Model consent, cancellation and resource limits still apply.

## Verification

Engine contracts and isolated interface checks cover instruction persistence/reset, protected editing, saved schedules, summary caching and date-based report identities. See [contributing](../CONTRIBUTING.en.md) and [native QA](../desktop/qa/README.md).
