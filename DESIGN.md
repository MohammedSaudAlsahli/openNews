---
name: openNews
description: A calm Arabic and English conversation and reading workspace with compact Mac preferences.
colors:
  app-accent: "#303331"
  app-accent-hover: "#454945"
  paper: "#fff"
  surface: "#f5f5f4"
  sidebar: "#f8f8f7"
  field: "#fff"
  text: "#252525"
  muted: "#686866"
  line: "#e5e5e3"
  hover: "#eeeeec"
  success: "#28734b"
  warning: "#966321"
  danger: "#ac3e35"
  focus: "#717e75"
  dark-app-accent: "#e4e6e1"
  dark-app-accent-hover: "#fff"
  dark-paper: "#212121"
  dark-surface: "#2c2c2c"
  dark-sidebar: "#191919"
  dark-field: "#272727"
  dark-text: "#ededed"
  dark-muted: "#b2b2ae"
  dark-line: "#3b3b39"
  dark-hover: "#333331"
  dark-success: "#91cba5"
  dark-warning: "#e2ba83"
  dark-danger: "#e89f97"
  dark-focus: "#aab5ac"
  settings-primary: "#0068cf"
  settings-primary-hover: "#005ebc"
  settings-selection: "#0879e6"
  settings-focus: "#276cae"
  settings-surface: "#f3f3f5"
  settings-control: "#fff"
  dark-settings-primary: "#0068cf"
  dark-settings-primary-hover: "#005ebc"
  dark-settings-selection: "#0a84ff"
  dark-settings-focus: "#8bb9e8"
  dark-settings-surface: "#2c2c2e"
  dark-settings-control: "#3a3a3c"
  skill-primary: "#0068cf"
  skill-primary-hover: "#005ebc"
typography:
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "27px"
    fontWeight: 620
    lineHeight: 1.35
    letterSpacing: "-0.025em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "14px"
  settings-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0"
  settings-navigation-title:
    fontSize: "20px"
    fontWeight: 600
    letterSpacing: "0"
  settings-label:
    fontSize: "14px"
    fontWeight: 500
  settings-description:
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
  settings-metadata:
    fontSize: "12px"
  settings-group-label:
    fontSize: "13px"
    fontWeight: 500
  settings-model-title:
    fontSize: "13px"
    fontWeight: 550
    lineHeight: 1.6
rounded:
  control: "7px"
  button: "8px"
  editor: "10px"
  settings-panel: "12px"
  popup: "13px"
  dialog: "16px"
  category-chip: "18px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.app-accent}"
    textColor: "{colors.paper}"
    rounded: "{rounded.button}"
    padding: "9px 14px"
  button-primary-hover:
    backgroundColor: "{colors.app-accent-hover}"
  settings-button-primary:
    backgroundColor: "{colors.settings-primary}"
    textColor: "#fff"
    rounded: "{rounded.control}"
    padding: "6px 13px"
  settings-button-primary-hover:
    backgroundColor: "{colors.settings-primary-hover}"
  skill-button-primary:
    backgroundColor: "{colors.skill-primary}"
    textColor: "#fff"
    rounded: "{rounded.control}"
    padding: "6px 13px"
  skill-button-primary-hover:
    backgroundColor: "{colors.skill-primary-hover}"
  settings-button-secondary:
    backgroundColor: "{colors.settings-control}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "6px 12px"
  settings-input:
    backgroundColor: "{colors.settings-control}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "6px 9px"
  settings-panel:
    backgroundColor: "{colors.settings-surface}"
    rounded: "{rounded.settings-panel}"
    padding: "0 16px"
  settings-model-result:
    textColor: "{colors.text}"
    typography: "{typography.settings-model-title}"
    rounded: "6px"
    padding: "12px"
  settings-navigation:
    rounded: "9px"
    padding: "12px 10px"
    height: "64px"
  settings-subnavigation:
    textColor: "{colors.muted}"
    typography: "{typography.settings-group-label}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  settings-segment:
    padding: "7px 12px"
    rounded: "5px"
  settings-segment-selected:
    backgroundColor: "{colors.settings-control}"
  settings-switch:
    backgroundColor: "{colors.muted}"
    width: "34px"
    height: "21px"
  category-chip:
    textColor: "{colors.muted}"
    rounded: "{rounded.category-chip}"
    padding: "6px 11px"
---
# Design System: openNews

## Overview

**Creative North Star: "A quiet working canvas"**

A calm conversation and reading workspace. The user explicitly requested ChatGPT-like conversation patterns and authorized replacing every interface element. Use established product controls: a labelled sidebar, neutral selection, a single conversation column, an autosizing composer, keyboard-operable popovers, and task-oriented settings. Article covers and source provenance give this product its identity.

Conversation, source management, writing and settings use Operate mode. The article reader uses Read mode. Current React/Tauri code is authoritative; the former implementation is archived on the swift-legacy branch. Updated Taste app-screen guidance, Impeccable 4.7 and restrained motion principles informed this redesign.

The approved DigUp-inspired change is limited to settings: compact category navigation, tonal preference groups, restrained blue controls and truthful processing status. It retains the shared platform family, Arabic/English behavior and light/charcoal app surfaces. The implementation in desktop/src/settings.css and the settings components is authoritative for this exception; docs/settings-surface.md records the surface contract.

**Key Characteristics:**

- A calm conversation and focused reading workspace.
- Neutral app actions and selection, with a blue control accent confined to settings.
- Compact, grouped preferences with visible saving and readiness.
- Source provenance and bilingual content direction.

## Colors

The interface tokens live in desktop/src/style.css and apply to light/dark themes. Shared names: --paper, --surface, --sidebar, --field, --text, --muted, --line, --hover, --accent, --accent-hover, --success, --warning, --danger, --focus. The accent is neutral; color explains success, warning or failure. Syntax tokens keep their own semantic colors.

Light: white canvas, near-white sidebar, soft neutral secondary surface, dark charcoal text. Dark: charcoal canvas, deeper sidebar, one-step lighter controls, readable off-white text. No decorative gradients or glass.

### Primary

The shared app accent is charcoal in light mode and pale neutral in dark mode. Settings retain a local system-blue selection accent for active switches, model selection strokes, contextual underlines and progress fills. Primary actions use the deeper Settings Primary and Settings Primary Hover roles in both themes so white labels remain readable. Writing-skill actions share this treatment; their existing scoped token names remain valid. This does not authorize blue category navigation or whole-app accent replacement.

Settings Focus is a separate muted-blue role, lighter in the dark theme. It identifies keyboard focus without changing the selection accent, primary fill, caret or text-selection color.

### Neutral

Paper, secondary surface, sidebar, fields, text, muted text, dividers and hover colors retain the shared theme tokens. Settings add a slightly cool grouped surface and a distinct control surface in each theme. Settings primary action text remains white in both themes.

### Semantic feedback

Success, warning and danger retain their shared meanings. A ready processing icon uses success color; waiting and failure also use text or icons so meaning survives without color. Syntax tokens keep their established semantic colors.

**The Settings Scope Rule.** Blue primary and progress controls belong inside settings; the conversation, reader and app shell retain their neutral accent.

## Typography

One platform text family supports Arabic and English. UI text is 13–15px, metadata 11–12px, page titles 24–30px. Reading is adjustable from 14 to 24px with a comfortable measure and 1.8 line height. Code is the only primary monospace use. Use sentence case and plain labels; avoid marketing copy above working content.

Settings use a compact exception to the page-title range: the navigation title is 20px and the category title is 22px, becoming 20px at the narrow breakpoint. Titles have weight 600 and zero tracking; category headings use line-height 1.4. Preference labels are 14px/500, descriptions 13px/400 with 1.6 line-height, group labels 13px/500 and metadata/status/counts 12px. Descriptive heading copy uses 1.65 line-height and a 67ch maximum; row descriptions use a 58ch maximum. Model identifiers and counts keep tabular numerals where provided, with identifiers isolated using bdi. Technical instruction editors retain the implemented 14px/1.8 monospace editor treatment.

**The Compact Preferences Rule.** Settings titles and metadata follow the settings type roles; do not promote them into the reader or conversation hierarchy.

## Layout

Spacing follows 8/16/24/32px groups. Main canvas has 24–56px side gutters. Sidebar is 224–248px. Conversation text and composer share an 816px outer measure; reader has an 824px outer measure. Library grid uses 24px gaps, three columns on wide desktop and two at smaller native widths. Source discovery uses two columns, then one.

### App shell

A 40px drag area reserves the physical leading 96px for macOS window controls independent of text direction. Avoid a duplicate title/status banner. Sidebar holds new conversation, Articles, Sources, Saved drafts, thread search and history, then activity/settings/help. Collapse/reveal is available from the window header and keyboard shortcut.

### Settings

Settings form a two-column grid with a 214px task-category rail and flexible content. At viewport widths of 1150px or less the rail becomes 194px and content side padding becomes 22px. The preference pane stays centered at a maximum of 800px. Content padding is 28px at the top, clamp(20px, 3.5vw, 48px) at the sides and 60px at the bottom. The rail and content scroll independently at desktop widths.

At viewport widths of 760px or less, settings become one scrolling column. Search remains available above a labeled native category picker with five task options; the desktop destination list and local-storage note are hidden. Navigation padding is 18px 16px 10px; content padding is 18px 16px 40px. Preference rows reduce their gap from 24px to 16px. The model catalog uses one list; selecting a model adds an adjacent inspector above 1200px and stacks the inspector below the list at 1200px or less. At 1150px or less, model role values wrap below the label rather than compressing the copy.

Group headings and sections use a 28px separation. Grouped rows use 16px vertical padding, a 60px minimum height and trailing controls. Wide editors and model lists use the full group width. Logical margins, borders and text alignment preserve RTL layout.

## Elevation & Depth

Settings groups, notices, segmented selectors and coverage displays are flat, separated by tonal surfaces and hairline row dividers. Coverage is part of its parent group rather than another nested card. Shared floating controls and dialogs retain their existing elevation; flat settings do not remove the app's popup hierarchy.

The shared floating panel and composer picker use 0 10px 30px #0000001a; conversation options use 0 10px 30px #00000014; the shared dialog uses 0 18px 60px #0003. Shared controls use a 2px shared focus outline with a 3px offset. Settings standalone controls retain that width and offset using the muted-blue Settings Focus role; contextual navigation keeps its inset offset. Composed settings search fields own one 2px outline with a 2px offset around the whole field, while the child input has no outline. Caret and text selection retain the local selection accent.

**The Group Before Card Rule.** Related preferences share one tonal panel with row dividers; an embedded status display does not acquire a second card surface.

## Shapes

Settings grouped panels use 12px corners and 16px horizontal padding. Fields and primary/connection actions use 7px corners; the settings search uses 8px; editors and resumable downloads use 10px. The compact switch is a 34px by 21px pill with a 17px white thumb that travels 13px; its travel reverses in RTL. Shared popovers and dialogs retain 13px and 16px corners. Source category chips keep their established 18px pill corners.

## Components

### Buttons and fields

Settings primary actions use blue and white, a 32px minimum height and 6px 13px padding. Secondary connection actions use the control surface, shared text and 6px 12px padding; pause/resume uses a 30px minimum height and 6px corners. Disabled settings buttons, inputs and selects use 0.6 opacity and the default cursor. Fields use a 1px shared divider stroke, control surface, 7px corners and 6px 9px padding with a 32px minimum height; labeled field inputs/selects use a 36px minimum height. Settings focus remains visible through its dedicated muted-blue role.

Theme choices show miniature light/dark workspace previews inside tonal choices with a selected accent stroke and no added shadow. Each choice is at most 164px wide and fits half the available row; the preview is 80px high. Settings destination rows keep neutral selection, 13px/550 labels, 12px descriptions, a 64px minimum height, 9px corners and 12px 10px padding. Settings category search is a 34px-high tonal field with the composed-field focus treatment. The narrow layout retains search and a labeled native category select.

Contextual navigation keeps stable 13px/500 text and 1.5 line-height across states, 9px 12px padding and a 40px minimum target. The current page is identified by aria-current and a 2px accent underline inset 12px from each reading edge; it does not acquire the shared selected fill. The wrapping navigation row uses a hairline baseline, 5px bottom padding and 4px 6px gaps. Its underline sits 6px below the button, on the baseline. Pointer hover supplies a neutral surface within 7px corners; active press uses the preference surface. Keyboard focus has its own 2px outline with a -2px inset offset. Wrapped labels retain the same padding and type.

Segmented selectors keep a tonal container with 3px padding, a 3px gap and 8px corners. Their buttons use 13px text, 1.5 line-height, 7px 12px padding, a 34px minimum target and 5px corners. Selected buttons use the scoped preference-control surface without a shadow in both themes; this scoped selection takes precedence over the shared selected fill. Contextual navigation and segmented selection remain distinct treatments.

Composed search fields in settings use one focus boundary around the icon and input. Their child input is transparent, borderless and square-cornered, with no shadow or independent outline, 13px text, a 36px minimum height and 7px vertical padding. The compact category-search input remains constrained by its 34px parent. Icon actions have a 34px width and minimum height, 7px padding and 6px corners. Standalone fields keep their own visible focus.

### Local models and processing

One grouped assignment surface presents article search and article explanations as distinct roles above one permanently mounted Ollama library. Role buttons use aria-pressed and aria-controls to change the assignment target and focus the library heading; they do not open separate inventories. Downloaded is the initial library view, alongside Suggested and Ollama library. Actual capabilities and current use appear in the downloaded rows. Changing the target preserves the query, selected model and list position. Known incompatible task choices stay unavailable; unknown compatibility is checked during activation.

Model results form one bounded scrolling list with a maximum height of min(440px, 48vh), 4px inset padding, a hairline border and 9px corners. Rows have natural height, do not shrink, and retain a 72px minimum with 12px padding and 6px corners. Names use 13px/550 with 1.6 line-height; descriptions and capability metadata use 12px. Long names and descriptions wrap. Selection has a tonal surface and an inset 1px accent stroke. Selecting a row focuses its inspector heading; the list stays mounted.

Above 1200px, the selected inspector sits beside the list in minmax(0, 1fr) / minmax(240px, 0.9fr) columns with an 18px gap and a hairline separator. At 1200px or less it stacks below with an 18px top inset and horizontal separator. An exact downloaded tag does not repeat a redundant one-option size selector. Storage and memory estimates live behind a named disclosure and do not promise speed or quality. Article search and local explanation settings embed the same picker in place, preserving the current page. Downloading, checking, retry, cancellation and activation feedback stay attached to the actual operation.

Processing keeps article search and explanations separate. Automatic protection and pause/resume appear before performance and battery preferences. Detailed search/explanation coverage lives behind an initially closed, named disclosure. Expanded coverage uses a compact status line, a 5px progress bar when the completed and pending counts are both known and total is positive, and 12px inline counts with tabular numerals. A waiting state names the reason; background controls show saving or saved feedback and expose pause/resume beside the current reason. Loading uses a labeled, static skeleton with aria-busy; an initial verification failure displays an unavailable message. Unknown, negative and non-finite counts render as an em dash. Missing counts never become an invented zero, ratio or progress total. Model download size, rate and remaining time appear only when supported by available data.

### Conversation

Model choice belongs in the conversation toolbar. User messages use a neutral rounded bubble; assistant content is open on the canvas. Source citations expand into actionable references; draft artifacts link to drafts. Copy feedback is visible. The scroll position follows the latest response only while the reader is already near the bottom; a jump button appears otherwise.

The composer autosizes up to 200px. Its plus menu contains files, saved articles and mentions. A separate tools menu explains saved-news retrieval and web research. Slash commands and news mentions appear above the composer. Menus escape overflow containers through portals and support Escape, focus restoration and keyboard navigation.

Execution details use a compact disclosure, closed initially. The current task and a short elapsed time occupy one line; expanded public summaries and tool steps stay grouped in a bounded, keyboard-scrollable region. Controls follow the interface language; each content fragment keeps its own reading direction. Failure and cancellation must not look like successful completion. Copy feedback belongs to the exact response or draft that was copied, expires, and cannot transfer to another message.

### News and sources

Every article card has a fixed cover/placeholder frame and one full-card open target, with a separate bookmark target. Source/title/excerpt/publication time form a clear hierarchy. Reader cover and publisher mark have separate, compact roles; inline editorial images stay in the article. Reading/original website, discussion, type size and reporting remain available without a crowded toolbar.

Discovery renders local suggestions before remote results. Category chips, search and followed state make the directory useful immediately. Stale responses cannot replace newer searches. Subscription secondary actions live in a menu; status names both readiness and failure.

Source identity stays aligned with its icon and hostname across languages; isolate the name's reading direction without moving the whole heading to the opposite edge. A successful write remains successful if a subsequent list refresh fails. Pending actions lock their exact control, errors stay beside that operation, and interval settings acknowledge saving and return focus to the source menu on close. Selecting Articles in the sidebar returns to the library and keeps its filters. Explanation/history disclosures share one keyboard/focus/chevron treatment; related articles identify their source and publication time.

### Drafts and settings

Drafts use searchable rows, format labels and previews. The editor separates writing, preview, history, copying, export and save state. Unsaved changes block destructive navigation and a failed save must retain text and the navigation decision.

Settings expose five task categories: General, AI models, Assistant & writing, Your articles, and Daily report. Contextual related-page navigation preserves all nine persisted page IDs and deep links. Category search matches English and translated preference names as well as task labels, showing named page results with their category. Searching hides the current page without unmounting its editor; result navigation retains the existing unsaved-change decision. Local Ollama models share one inventory for explanation/search assignments, with the same picker embedded in article settings. Processing displays actual completed/pending counts and an honest status. Instruction scope and section use a two-column compact form that stacks at the narrow breakpoint. System and developer prompts appear in the section menu only after the user expands technical options; inline copy explains the result. Provider options remain accessible, with explanatory copy.

### Writing skill library

Named guides and their purpose lead the library; slash commands and included/custom provenance are secondary metadata. A guide name uses the settings label role, its purpose the settings description role and its command/provenance the settings metadata role. Library rows share one tonal group with 12px corners, 16px horizontal and vertical row padding, hairline dividers and a 20px gap. Discovery reuses these grouped rows with a separate, named preview action. Library/discovery selectors and topic controls use 13px text. Search is a full-width tonal field with a 36px input minimum height and visible focus on the containing field.

Detail and import review replace the list rather than layering another management card. Review places original repository/source and actual support limits before editable name, command and purpose; main instruction text is behind a named disclosure. The source strip uses hairlines instead of another filled card. Imports explicitly describe a local copy of the main instructions and any missing supporting files/tools; do not imply those dependencies are installed. The character count and addition state stay beside the final action. Existing editors preserve their save/reset and unsaved-navigation behavior.

At 1150px or less, headings/actions can wrap and the extra provenance label hides while the command remains visible. At 760px or less, rows wrap with a 12px gap, metadata aligns to the reading edge and the addition footer wraps. Shared forms stack according to the incumbent narrow layout. Names and user-written content determine their own direction; commands stay LTR and repository names are isolated. Chevrons and recommendation arrows mirror in RTL.

Opening detail or review moves keyboard focus to its programmatically focusable heading. Opening link import focuses its URL field; Back restores the originating library row or discovery preview action, falling back to Add from a link. Successful addition focuses the new detail heading; removal focuses the library heading. Input edits do not trigger these handoffs. Success and failure remain visible in the operation. Try in a conversation and assistant recommendations prepare an unsent composer draft through the existing guarded navigation.

### Interaction and accessibility

Buttons have clear names, visible focus and consistent target sizes. Status never relies on color alone. Radix primitives handle popup focus/dismiss behavior. Standard inputs and real labels remain. Frequent/keyboard actions have immediate feedback; hover color transitions are about 140ms. Reduced-motion mode disables optional transitions. Mixed-language paragraphs determine their own direction; code always reads LTR.

Settings switch thumbs and disclosure chevrons use 120ms ease transitions; shared button background/color transitions use 140ms cubic-bezier(0.2, 0.7, 0.3, 1). Reduced-motion mode removes transitions and animations, including busy indicators. This build introduces no raster assets.

## Do's and Don'ts

### Do:
- **Do** keep the settings blue accent scoped to settings and use neutral category selection.
- **Do** use compact title, label, description and metadata roles for preferences.
- **Do** group related rows in one tonal panel with trailing controls and logical RTL spacing.
- **Do** preserve unknown processing counts, labeled loading, unavailable states and operation-specific feedback.
- **Do** keep settings search available in the narrow layout and preserve editor drafts while showing results.
- **Do** place detailed coverage and technical instructions behind named, keyboard-operable disclosures.
- **Do** preserve all app, conversation, source, reader and draft behavior described above.

### Don't:
- **Don't** replace the neutral whole-app accent with settings blue.
- **Don't** put nested management cards around inline coverage and status.
- **Don't** present unknown counts as zero or show an unsupported progress ratio.
- **Don't** remove unsaved-change protection, keyboard focus or source provenance during visual work.
- **Don't** add decorative gradients or glass to the established app surfaces.

### Verification

Use the developer-only desktop/qa fixture for repeatable visual and keyboard inspection, plus real Tauri/runtime checks for native window controls and embedded websites. Verify both themes, both interface languages, native minimum width and wide desktop. New behavior needs regression tests for stale results, navigation/data protection and keyboard sending. Follow the isolated verification instructions in desktop/qa/README.md.

### Reader source previews and summary provenance

TL;DR identifies the stored generating model and recorded creation time in a wrapping 12px metadata row; an absent historical model or timestamp is never replaced with the current selection. Reader links and summary citations share a text-only floating preview using the existing paper/text/muted/focus tokens, 13px popup radius and floating-panel elevation. Titles are 16px/600, excerpts 14px/1.7, source/status metadata 12px. The card is 360px wide, clamped to viewport space, and supports both directions and themes. It opens after 320ms of pointer intent or on keyboard focus; a 180ms exit grace allows moving into it. Down Arrow focuses Open original; Escape dismisses and returns focus. Loading/unavailable states remain explicit. No decorative media, inference or remote embeds are added to this interaction.

A compact Regenerate summary action sits at the trailing edge of the TL;DR heading. Its in-place progress leaves the previous summary and provenance visible; failure retains that result with retry available. Resource-blocked states explain the disabled action in adjacent status text. Only an explicit click starts regeneration.
