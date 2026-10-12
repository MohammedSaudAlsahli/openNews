# Independent acceptance review — analyst 5 of 5

User-confirmed primary task: **writing and reviewing content, with sources alongside it**. This supersedes research proposals that would replace the central editor with a source document. Review the actual build against the following checklist; these are acceptance targets, not claims of passed verification.

## Structure and first-use clarity

- Launch directly into a writing brief or the selected draft. No dashboard, metrics, slogan, or six-feature navigation.
- Writing remains visible while sources and style are browsed. Source inspection must not replace the primary writing canvas.
- Draft selection is a clearly labeled toolbar menu, with a discoverable new-draft action; Settings is separate and reachable by standard shortcut.
- Every disabled primary action has a concise nearby reason and an actionable remedy. Model setup and style approval do not require a hunt.
- The side panel can be hidden for focus and reopened from a labeled toolbar command. Important actions remain accessible when hidden.

## Source and style loop

- Import locally, select the new source, analyze, see its exact evidence, and explicitly approve a suggestion without changing primary destination.
- Preview text is labeled accurately; a truncated source preview is never represented as the complete source.
- Suggestions correlate by stable source ID, not title, including duplicate titles.
- Unknown-rights sources cannot become cloud reference selections. Consent is explicit, unselected by default, and tied to the requested action.
- Empty analysis results, queued/running states, cancellation, and actionable failure are distinguishable.
- Style removal affects future writing, preserves prior draft versions, and allows later reapproval.

## Authoring integrity

- Open drafts via authoritative `drafts.detail`; never edit the snapshot's truncated preview.
- Changing selected draft, creating a new draft, or closing an editor protects unsaved text. Inspector toggles never discard it.
- A failed load cannot present a blank editable document with an enabled Save action.
- Save creates a version and invalidates obsolete review evidence. Export uses saved content, with an explicit save-first route if dirty.
- Claims remain unverified until genuinely verified; the visual redesign does not imply factual approval.
- Completion follows job result, not merely queued submission. A generated document appears in the same writing space.

## Native layout, Arabic, accessibility

- System semantic colors work in light and dark appearance. No forced light-only workaround remains without a demonstrated reason.
- Arabic reads naturally right-to-left; model IDs, URLs, credentials and code-like values use deliberate LTR contexts.
- Controls retain visible labels; icon-only toolbar actions have accessible labels/tooltips. Selection and error states use more than color.
- Keyboard focus reaches main controls, standard shortcuts work, and minimum window size avoids clipped primary actions.
- Text density favors the document. Secondary diagnostics and provider catalogs do not dominate the writing flow.

## Verification boundary

Inspect source for state/data protection, run existing tests and compile, then visually inspect the compiled app and exercise import → local analysis → approve style beside the writer. Mocked or unavailable cloud generation must not be reported as live acceptance. Existing Keychain failure, unsigned development distribution, and missing full-PRD capabilities remain truthful constraints.

## Source basis

- Apple [Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars): use a compact supplementary panel that can be hidden; our writing-first placement is the user's product decision.
- Apple [Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars): stable frequent commands with native menu/keyboard access.
- Apple [Panels](https://developer.apple.com/design/human-interface-guidelines/panels): contextual supplementary detail supports the selected work.
- Apple [Managing windows](https://developer.apple.com/design/human-interface-guidelines/managing-windows): preserve user work through document/window changes.

Direct HIG open returned JavaScript shells for sidebar/toolbar; research requires indexed Apple text where available, not fabricated visual observations. Mobbin collection screenshots were not available publicly; see `mobbin.md` for verified accessible material.

## Pending final review

Awaiting rebuilt sources and rendered screenshots from root. DESIGN.md and the component sidecar will describe the final implementation, not proposed tokens.

## Source review — first rebuilt implementation

The new architecture meets the primary structural request: the document remains present while the sources/style panel changes, local drafting is possible without model setup, and Settings uses the native scene.

Concrete findings sent to root for correction:

1. **P1 — edits during asynchronous save/load may be discarded.** ContentView's title and editor remained editable while save/load awaited IPC. Save-then-switch could capture old text and later replace newer keystrokes with the next draft. Disable editing during the bounded operation or preserve a revision token.
2. **P2 — generated draft watcher treats any new draft as its result.** A manual save during model work can consume the watcher, preventing the actual generated document from opening. Track the submitted job/result, and clear pending state on failed submission.
3. **P2 — analysis-sheet errors are routed behind the sheet.** AnalyzeSourceSheet sets global model.error but does not show a local error. Keep the failure visible within the submitting surface and lock controls while submitting.
4. **P2 — checkmark icon suggests factual approval.** Claim rows use text.badge.checkmark even when verdict is needs_review. Use a neutral/review-needed symbol and an explicit Arabic verdict.
5. **P3 — draft picker toolbar lacks a menu command.** Add a standard open-drafts command/shortcut to mirror the toolbar.

This is a code review, not a screenshot or runtime acceptance claim. Final review pending.

## Final independent review — 2026-10-11

Reviewed the rebuilt running app from `/Volumes/Editorial Intelligence Studio/Editorial Intelligence Studio.app` using one read-only native AX inspection and one screenshot. No controls were clicked by this reviewer. The observed state was a saved synthetic Arabic draft with source detail and a style suggestion beside it, in the current system dark appearance.

**Verdict: PASS for the requested structural redesign and observed readability, with bounded verification.** The writing canvas dominates; the source panel remains adjacent; the Arabic title/body read right-to-left; local save state and counts are visible; source analysis/evidence/explicit style approval are available in context. The previous dashboard and six-page hierarchy are absent. The redundant segmented-selector label observed during this direct review was removed in root's final batch.

All five earlier source findings have a corresponding correction in the updated implementation: busy-state edit lock, submitted-job tracking and ready affordance, local analysis-sheet error, neutral claims status, and Command–O draft picker command. No additional blocking issue found in this review.

Root separately reports functional verification of Arabic local save, contextual style approval, dirty-state save-then-continue, Command–O reopening full text, and Markdown export. Those are root's test results, not independently replayed by this read-only reviewer. This pass does not establish minimum-window usability, screen-reader completion, every keyboard/appearance state, or live provider acceptance.

Final design files are `DESIGN.md` and `.impeccable/design.json` in the project. Native semantic color roles are authoritative; HTML/CSS previews are explicitly portable approximations. No decorative raster assets or stock imagery were introduced.


## Final build confirmation and bounded verdict

Root reports the final DMG compiled and verified, with saved Arabic text surviving restart; source context beside the editor; dirty Save-then-continue; Command–O reopening; and actual Markdown export. Root also inspected light and dark Settings/editor states. The app-only System/Light/Dark setting works and was restored to System. Settings label duplication was removed and the default service displays OpenAI. This is root QA evidence, distinct from this reviewer's earlier direct dark screenshot and code review. No further UI actions or broad audit were performed for this confirmation.

**Final verdict: PASS with one minor known visual detail.** The empty new-title placeholder remains physically left-aligned despite modifiers; saved Arabic titles and Arabic body text are correctly right-aligned. This does not block the requested single-workspace writing/source flow and is not claimed fixed. The five concrete code findings are corrected. The verdict covers the redesigned workflow and the stated tested states, not minimum-window usability, screen-reader completion, live model calls, or complete PRD delivery.
