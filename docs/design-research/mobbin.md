# Analyst 2 — Mobbin and native writing references

Research date: 2026-10-11. Scope: live primary-source research and current ContentView.swift inspection; no app code changes.

## Verified sources and transferable patterns

- [Mobbin — Sidebar UI](https://mobbin.com/glossary/sidebar): distinguishes navigation drawers from contextual drawers used for filtering or page-specific information/actions. Its guidance is largely mobile/web; translate principles to native macOS instead of copying hamburger navigation. **Apply:** keep sources and drafts as content objects; analysis details belong beside the selected source, not in another global destination.
- [Mobbin — Segmented Control UI](https://mobbin.com/glossary/segmented-control): a small set of mutually exclusive options with immediate switching suits a segmented control. **Apply:** a compact “المسودات / المصادر” selector above the library list; do not replace six pages with six tabs.
- [Apple Notes — View your notes](https://support.apple.com/en-au/guide/notes/apd8b73d28be/mac): sidebar, note list and selected note content stay in one window; single-click selects content, and search locates notes. **Apply:** selecting an item updates the main canvas while preserving the library context. Avoid separate “open editor” modal as the ordinary editing path.
- [iA Writer — Navigate](https://ia.net/writer/support/library/navigation): file selection opens a document in the same window; filtering and quick search support retrieval. **Apply:** searchable compact rows with title and short preview, stable selection, same-window editing.
- [iA Writer — Settings](https://ia.net/writer/support/basics/settings?tab=settings-mac): settings use the app menu and ⌘,; window/toolbar options support a focused experience. **Apply:** provider setup is a preferences sheet with a visible setup route when needed, not a peer page to writing.
- [Ulysses — Sheets & Groups](https://help.ulysses.app/567894-sheets-groups): authored sheets and supporting material coexist in the library, with material excluded from final export. **Apply:** distinguish source/reference material from authored drafts; source text remains read-only and export pertains to the selected draft.

Access limitation: [Mobbin public app discovery](https://mobbin.com/discover/apps/web) returned login/join chrome through the web reader. No authenticated screen collections or complete product flows were viewed. The recommendations above cite accessible Mobbin glossary content, not imagined screenshots.

## Problems in inspected implementation

1. Six `Page` destinations force users to understand internal pipeline stages: library → techniques → DNA → studio. The user is trying to write, not operate a processing pipeline.
2. Overview spends first-screen space on a slogan, three large counts, status and future capabilities. None edits a document.
3. Every source/draft is a large card in a scrolling page, reducing scan density; draft editing is another sheet.
4. Global “أضف مصدرًا” stays the only prominent action even on the writing screen.
5. Provider catalog, engine internals and development limitations compete with writing. Cost/consent must stay explicit at the actual paid action, while diagnostic details belong in settings.

## Concrete replacement proposal

One working window, two content collections, contextual detail:

- Narrow native library pane: new draft action, “المسودات / المصادر” segmented filter, search, compact selectable rows. Add source sits with the source collection.
- Main canvas opens directly to a draft or a quiet start state “ماذا تريد أن تكتب؟”. New draft setup uses topic and format first; language/duration appear only as relevant. The generated draft becomes the editor in this same canvas.
- Selected source shows readable source text and an adjacent/below “أساليب مقترحة” section. Analyze, review exact excerpt and approve “أضف إلى أسلوبي” happen without changing global destination.
- Toolbar “أسلوبي” opens approved rules; “الإعدادات” or ⌘, opens providers. Active task progress appears near its action; history is secondary.
- Reading/editing uses the majority of width. Neutral native background, system typography, one accent, thin separators. Remove dashboard metrics, oversized slogan and repeated card borders.
- If sources and rules are generation prerequisites, the empty state offers precise direct actions to add a source/review styles. Never hide a blocked generation reason behind a disabled button.

## Review criteria

From launch, user can identify the next writing action without learning “DNA” or “Agno”. Import→inspect→approve occurs with one persistent source context. Selecting a draft opens editable text directly. Settings are accessible without consuming a primary navigation destination. Preserve explicit external-call consent, read-only source evidence, draft versioning and unapproved export warning.
