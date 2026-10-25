# TL;DR

When automatic summaries are enabled and a model is assigned, new and older articles enter a persistent background queue, newest first. Saved results appear at the start of the reader without a disclosure or another inference request. An existing backlog takes time, and charging/resource conditions may defer preparation. Arrival does not mean generation has already finished.

The summary leads with the takeaway, then organizes events or ideas, evidence, positions actually present, implications and uncertainty. Social posts remain attributed claims, not independent verification.

Up to six direct editorial links are fetched through the existing DNS-pinned public transport, without cookies, account credentials, browser automation or recursive crawling. Successful and failed page results are cached for 24 hours, with at most 500 pages per workspace. Login-protected tweets, paywalls and dynamic pages may be unavailable. Linked evidence is limited to 24,000 characters per page; source status and incomplete coverage remain visible.

Long articles are processed in 4,500-character sections. Completed notes are persisted for resumption after cancellation or resource pressure, then combined into the final summary. If the combined notes exceed the context allowance, the reader discloses limited coverage. Comprehensiveness cannot imply access to blocked content or unlimited processing.

Direct quotations must match retrieved source text exactly and fit a total of 25 words per source. Citation URLs come from retrieved evidence rather than model-provided destinations. Interpretation can still be wrong, particularly for conflicting or sensitive news.

Local work shares one inference lease with search, disables extended thinking, limits output, rests between long-article sections, and respects fresh memory/thermal signals, battery policy and manual pause. These controls reduce sustained load; they cannot guarantee zero heat or embedding-like generation speed.

[العربية](tldr.md)

## Persistence, model provenance and link previews

Summaries are stored in SQLite with their generating model ID. The reader shows that original model and the recorded creation time, without invoking inference when opening the article, including after an app restart. Article, assigned-model or output-language changes can invalidate a result and queue a replacement. Older results without reliable creation metadata do not receive invented timestamps.

Pause over a link in reading mode, or focus it with the keyboard, to see the source card. Down Arrow focuses Open original; Escape dismisses it. Moving into the card keeps it open. It displays an available source excerpt, not a newly generated summary, and does not run inference, publisher scripts or X embeds. Clicking the original link still opens it.

Previews prefer a saved article, then reuse the shared 24-hour source cache or perform a bounded public fetch. Unavailable results are cached too, and only one page fetch runs at a time. The interface retains at most 80 preview responses for five minutes each. Requests must refer to links in the selected article; hovering neither imports an article nor marks one read. Blocked or sign-in-only posts disclose their unavailable state. Cards are not injected into the separate original-website view.

Regenerate summary starts a fresh request using the currently assigned summary model and bypasses previous generated summary/section-note results. The old summary remains visible and persisted until a validated replacement succeeds, including after connection or generation failures. Explicit work takes priority after safely stopping background preparation; duplicate manual requests are rejected, and thermal, memory and battery limits remain in force. Regeneration still reuses unexpired source-page text rather than automatically fetching it again.
