# Article explanations and daily news reports

Open Settings → News summaries → Summary instructions, or Daily report → View and edit instructions. The in-app editor shows the actual current text, supports saving and restoring defaults, and includes writing skills in its task selector. Unsaved edits must be saved or discarded before switching tasks. No external editor is required.

Storage remains local under `~/Library/Application Support/com.editorialintelligence.studio/default/instructions/`; existing edits are preserved. The allowlisted `instructions.get/save/reset` IPC endpoints read and atomically write the same documents used by generation.

- `article-summary.md`: shared by explicit article explanations and automatic background summaries. Defaults explain the main idea, context, evidence, significance and limitations in 250–450 words when justified by the article. Short articles need less; missing facts are never invented.
- `daily-report.md`: controls synthesis, source attribution and organization of daily reports.

Files are initialized from `engine/eis_engine/editorial_instructions.py`, loaded for each new request, and never overwritten on app update. Saved outputs remain unchanged when instructions are edited. General conversation style remains under Settings → Customize assistant (`personalization.py`); it is independent from these article/report tasks.

The selected language is enforced separately from the editable content instructions. A wrong-language response receives one bounded translation repair. If repair fails or the request budget is exhausted, a clear failure is shown; incorrect-language output is not cached. Cloud language repair consumes a request from the daily summary budget. Longer explanations require more model output than the former 100-word previews. Local model output is bounded to 2,000 tokens. Input is limited to 24,000 characters and explicitly flagged when truncated. Excerpts are not represented as a complete article.

## Daily report schedule

Settings → Daily report has an explicit on/off switch, hour/minute, time zone and Arabic/English language. It uses the selected news summary model. Enabling requests macOS notification permission; denied permission does not remove the saved report. The feature defaults off.

Scheduling is checked once a minute while the app/engine is running, including with the main window closed. It does not install a system daemon or wake a sleeping Mac. Returning after the selected time generates today's report; missed past days are not backfilled. One report per calendar date is saved in SQLite, with at most three attempts and a ten-minute retry delay. Turning it off cancels an in-progress report. Revoking model consent also cancels on the next schedule check.

Reports use already-fetched articles from enabled subscriptions, filtered by publication date (discovery date when absent) in the selected time zone. They include the newest 20 articles at most, with bounded excerpts and explicit available/included counts. This is a followed-source roundup, not comprehensive world-news coverage. Reports remain readable in this settings page; the latest 30 are listed. Notifications are sent only after a report is ready and are deduplicated on the device. Changing time/language does not create a second report for a date already completed.

## CI DMG verification

`scripts/dmg_verify.py` retries only the exact `Resource temporarily unavailable` failure up to three times, with 2/4-second pauses. Invalid checksums and other errors still fail immediately; persistent transient failures still fail CI. The release process never bypasses DMG verification.

## Conversation instructions

Settings → Customize assistant displays the actual baseline sections from `assistant_defaults.py`, with Markdown editing and the same preview renderer as articles. The general settings are frozen into each conversation job; editing a section replaces that section for new jobs. Old optional preferences are preserved and empty legacy fields inherit defaults. New explicit empty sections stay empty. Reset restores the canonical baseline. Empty Examples means no example was configured, not hidden examples. Agent and conversation preferences remain additional scoped overrides, with inherited general instructions shown separately. `{summary_language}` is resolved from the current message at execution. Article/report instructions remain separate. Output schema validation, available tools, consent, and provider-side policies are runtime constraints rather than editable style instructions.
