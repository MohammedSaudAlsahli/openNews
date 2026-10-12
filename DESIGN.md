---
name: Editorial Intelligence Studio
description: A native Arabic editorial workspace for conversation, writing, news and personal style.
colors:
  document-surface: Canvas
  document-text: CanvasText
  control-surface: ButtonFace
  control-text: ButtonText
  accent: AccentColor
typography:
  title:
    fontFamily: system-ui
    fontSize: 24px
    fontWeight: 600
  editor:
    fontFamily: system-ui
    fontSize: 18px
    fontWeight: 400
rounded:
  excerpt: 5px
  search: 6px
spacing:
  compact: 8px
  panel: 16px
  sheet: 24px
  canvas: 32px
---

# Design System: Editorial Intelligence Studio

## Overview

**Creative North Star: "The Writing Desk"**

Conversation and writing share one working window. News evidence, personal writing examples and explicitly approved style rules live in an adjacent accessory panel. The newer conversation-and-news request extends the writing-first redesign without restoring separate feature pages.

The interface uses native macOS controls, semantic surfaces, system typography, and SF Symbols. It is quiet and task-oriented: the authored document carries the hierarchy. Local writing and saving work without a configured model; optional model assistance has its own clearly bounded sheet.

**Key Characteristics:**

- Persistent conversation and document state with a hideable news/writing/style panel.
- Arabic-first layout with deliberate LTR treatment for technical fields and English drafts.
- System-owned appearance, control states, focus, and accent.
- Local saved versions and explicit review status.

## Colors

The frontmatter uses portable CSS system-color equivalents for the native semantic roles. The implementation is authoritative: `NSColor.textBackgroundColor` for the document, `controlBackgroundColor` for supplementary controls/panel, `windowBackgroundColor` for window/status surfaces, and SwiftUI `.primary`, `.secondary`, `.tertiary`, and system accent for content. CSS equivalents are documentation previews, not sampled RGB values or exact AppKit rendering.

Do not freeze the dark screenshot into a hard-coded palette. Appearance defaults to macOS and can be overridden for this app with System, Light, or Dark in Settings; it does not change system appearance. Secondary text is for supporting explanation; actionable errors include readable text and a symbol. The current code uses system red for error messages.

**The Semantic Surface Rule.** Choose an AppKit/SwiftUI role before introducing a custom color. Status must remain intelligible without hue.

## Typography

System typography supports native Arabic shaping and mixed-language content. The document title is semibold; editor text has extra line spacing (`8` points). Panel headers and form hierarchy use native title3/headline/body/callout/caption roles rather than a separate display font.

The title and editor tokens are the only fixed type sizes established by the workspace. Do not convert native relative text roles into invented fixed pixel values. Technical identifiers, URLs, secrets, and English documents have an intentional LTR environment.

## Layout

The default window is `1400 × 850` points, with a `900 × 640` minimum. At widths of at least `1180` points with references visible, or `860` with references hidden, conversation and the writing canvas appear side by side. The conversation takes between `360` and `420` points; the document expands. At narrower widths, a compact `المحادثة / المسودة` switch changes the visible main pane while preserving both states. The references panel occupies `320` points at the logical trailing edge (left in Arabic). Hiding it frees space for conversation and writing.

The main canvas uses the canvas spacing token. The panel uses the panel token and compact vertical rhythms. The bottom status strip is `36` points high and carries save state, word/character count, transient feedback, and activity. Native toolbar commands provide new draft, draft selection, save, export, and panel visibility. Draft selection opens a searchable popover rather than another page.

Review and earlier versions expand inside the document area, bounded to `220` points. Import and model-assisted generation use `620 × 650` sheets. Model setup uses the native Settings scene and Command–Comma.

**The Persistent Text Rule.** Browsing news, changing the supplementary panel, sending a conversation message or approving a style suggestion must not reset the working document. Conversation outputs open through the same dirty-state protection as other drafts.

## Elevation & Depth

The application is flat by default. Dividers and semantic surface differences establish regions. Native sheets, popovers, and window chrome supply their own elevation. There are no custom card shadows, decorative gradients, or nested dashboard panels.

## Shapes

Native buttons, segmented controls, text fields, and disclosures retain platform geometry. The few explicit rounded surfaces are the search field and quoted excerpt, using the frontmatter radii. Thin separators organize content; rounded cards are not the default container.

## Components

### Writing canvas

The main TextEditor uses the editor token, full authoritative draft text, and a visible placeholder for a new draft. Saving creates a version. Text/title editing is disabled during bounded busy operations to prevent late edits being discarded by asynchronous transitions. Unsaved transitions require explicit save or discard; closing/quitting protects dirty work.

### Toolbar and draft picker

Use native labeled actions with accessible names, tooltips, and menu equivalents. New draft, open drafts, save, export, and references visibility have keyboard routes. The saved-draft picker contains a title search and compact title/preview rows. The preview is never used as editable full text.

### References panel

Three segments, `الأخبار`, `كتاباتي` and `أسلوبي`, change only the supplementary panel. News subscriptions and article selection remain distinct from imported writing samples and approved style rules. Source rows select a full-detail view with a route back to the list. Source text is disclosed, evidence remains read-only, and local analysis and optional model analysis are separate actions. Style approval requires the explicit `أضف إلى أسلوبي` action. Editing rule wording is secondary disclosure.

### Editorial conversation

The composer prioritizes the request, a compact output choice (`نقاش`, independent X posts, long YouTube script, TikTok script), optional news/current-draft context, and explicit model-use consent. Model choice and duration are supporting controls. Messages persist, older history can be loaded, an in-flight response can be stopped, and proposals appear as separately saved artifacts with an explicit open action. Opening a proposal does not silently replace unsaved writing.

### News and writing samples

The news panel exposes subscribe, refresh, pause/resume, article selection and retrieval status. Full text and feed summary are visibly distinct. Display missing publication dates honestly; a saved/discovered timestamp must not imply recent publication. The UI lists 100 recent stored articles and selects no more than 12 for a request. The default recent-news context is seven days, not a promise of comprehensive weekly coverage.

The writing import form asks whether a text is a personal style example or a content reference. Owned/licensed style examples guide vocabulary, rhythm and structure within model context; they are not training data or automatic facts about current news. A permanent rule still needs explicit approval in `أسلوبي`.

### Review and activity

Claims use neutral review-needed symbols and readable status, never a success checkmark for an unverified fact. Version history is disclosed beneath the current review. Activity is a compact popover; failed model work has a retry consent step. A completed generated draft is associated with its submitted job and offers a ready-to-open action when dirty writing must be preserved.

### Sheets and settings

Import prioritizes title, source text, purpose and rights; saving a personal-style sample stays unavailable until ownership or licensing is selected; author/URL are optional details. Generation prioritizes the brief and format, with references and explicit sending/cost consent. Native settings contain model configuration, secure credential controls, and connection-test consent. Credentials now use owner-only local files under the connection settings workflow. Historical Keychain limitations must not be presented as a current-path failure. Adapter and catalog availability are not live account validation.

## Do's and Don'ts

- Do keep writing visible while the user inspects sources and style.
- Do use semantic native colors and system control behavior.
- Do provide a direct remedy beside a blocked action.
- Do preserve dirty text and use full detail endpoints for editing.
- Do describe unverified claims and model readiness honestly.
- Don't restore a dashboard or separate pages for pipeline stages.
- Don't use decorative metrics, oversized slogans, or repeated cards.
- Don't make model setup a prerequisite for local writing.
- Don't make a checkmark imply a claim has been verified.
- Don't copy a screenshot palette into fixed colors.

Research basis: [Apple Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars), [Apple Settings](https://developer.apple.com/design/human-interface-guidelines/settings), [Apple Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars), [Mobbin Sidebar UI](https://mobbin.com/glossary/sidebar). Product-specific composition follows the user's writing-first choice; no authenticated Mobbin screen collection was available.

Historical redesign verification boundary (before the conversation/news extension): the independent reviewer directly inspected one native AX/screenshot of the dark-appearance saved-draft/source-detail state, and reviewed state preservation, job association, and source evidence in code. Root separately verified the final compiled DMG, Arabic saved text after restart, source context, dirty save-then-continue, Command–O, actual Markdown export, and light/dark editor and Settings appearance. The app-only appearance option was restored to System. These root checks were not independently replayed by the reviewer. Minimum-window usability, screen-reader completion, live provider acceptance, and the complete PRD remain outside this verdict.

Known minor visual detail: the empty new-title placeholder begins at the physical left despite alignment modifiers. Saved Arabic titles and Arabic editor content are correctly right-aligned. This placeholder detail is not reported as fixed.

Current conversation/news implementation has been documented from source. This document does not claim a new packaged-build acceptance, new visual walkthrough, final test count or live-model acceptance for that extension. Its current release evidence belongs in docs/acceptance.md and validation-results.json after verification.

## Menu bar reader

A native SwiftUI MenuBarExtra with window style provides a420×580pt reader. A newspaper symbol opens a searchable recent-news list, source filter and unread toggle. Selecting a story loads cached article text and marks it read, with explicit summary/podcast-description labels. Closing the editor hides its existing window, retaining unsaved text and chat state. Reopening focuses that same window; explicit Quit retains the dirty-work warning and stops the engine. Background snapshot refresh continues independent of visible views. This does not install a login item or wake a sleeping Mac. Apple reference: https://developer.apple.com/documentation/swiftui/windowmenubarextrastyle
