# Settings surface

The settings surface uses compact, task-oriented groups within the existing openNews design system. The production components and `desktop/src/settings.css` define the current behavior.

## Direction contract

THESIS: Preferences should read as a small, trustworthy Mac control panel. Local search is ready independently of explanations; the most useful action is choosing a model or pausing background work. Remove oversized headings, nested management cards and redundant processing copy.

OWN-WORLD: Existing platform sans in Arabic/English; neutral light/charcoal surfaces, one tonal grouped panel, hairline row separators,12–16px corner radii. Restrained system blue on active switches/progress and primary actions follows the user's DigUp reference. Preserve existing app/reader typography and source identity.

STORY: Choose a category, read what a preference does, change it confidently, and see actual saving/readiness. Processing shows complete versus pending coverage and a human reason for waiting. Unknown values stay unknown.

FIRST VIEWPORT: Five task categories with descriptions beside a centered preference column; a contextual two-item subnavigation retains all nine persisted destinations. Search matches translated preference labels and opens a direct result while retaining any unsaved child editor. Category title20–24px, group label13px, preference title14px and secondary12–13px. Rows align controls at the trailing edge; broad editors and model lists use full-width groups. Search, explanations and energy controls are close and distinct. Model coverage is an explicit disclosure; automatic protection and pause come before energy controls. Light/dark previews show the choice before applying it. Instruction scope and section use a compact form, with technical prompts behind a disclosure. Layout collapses to a compact category picker at narrow width.

FORM: Supplied DigUp reference selected by user; no additional concept election needed. Taste true-black-flat seed1994109306, retaining app palette/type and replacing dealt shell with compact labeled navigation because settings preserve nine destinations grouped into five user tasks. Blue control accent is a deliberate reference-led exception to the draw's neutral controls. Signature: one truthful local-processing panel with pause and coverage, separate from the heavier explanation task.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Verification contract

All existing settings remain findable and functional: appearance/language, accounts/models, privacy/updates/import, customization/instructions, writing skills, explanations, saved-article search, local models and daily report. Retain unsaved-change protection. Verify saving/failure/disabled states, model download/check/retry, and policy persistence. Inspect Arabic/English, light/dark,1440px and native narrow width; phone collapse is checked as a layout guard. Fixture screenshots are labeled fixtures and do not prove native IPC or real inference.

## October 24 simplification pass

The latest request prioritizes clarity and ease over more decoration. Preserve the incumbent visual world (Operate refinement; no new concept roll or comp round). Five rail destinations: General, AI models, Assistant & writing, Your articles, Daily report. Their two-item contextual navigation preserves appearance/privacy, local/accounts, instructions/skills and search/explanations. Existing deep links and persisted page IDs remain valid. Search is also available in the narrow layout; the destination picker changes to five task categories. Search hides rather than unmounts the current page so instruction drafts remain protected. No model, privacy, scheduling or inference defaults change in this design pass.

## Small-control refinement

The user supplied a crop showing the selected contextual tab as a sharp filled rectangle with text against its edges. This is a local defect in the incumbent system: the global `.selected` fill overrode the intended navigation treatment. Contextual navigation now uses `aria-current="page"` directly, with 12px inline padding, a 40px minimum target, consistent 13px/500 text and an inset underline. Selection stays stable without a persistent fill; pointer hover uses a rounded neutral surface, and keyboard focus has its own 2px inset outline. Wrapped labels remain available at narrow widths and zoom. Settings segmented controls use 13px labels, 34px minimum targets and the scoped control surface for selection. Preserve routes, draft guards, content and all other settings behavior. This Operate polish does not introduce a new world, comp round or seed.

## Shared Ollama library and in-place selection

The October 25 follow-up supplies native screenshots of hidden downloaded models, overlapping catalog rows and a doubled input focus ring. Preserve this Operate world while fixing the complete model-selection path. One shared inventory lists every local downloaded model with actual capabilities; task assignments for article search and explanations remain distinct. Changing task preserves the same mounted library, query, selection and list position. Known incompatible models cannot activate for the selected task. Unknown capabilities are tested by the existing backend activation path; a successful selection is never inferred from a button click alone. Catalog and inspection states remain independent, with late-result protection and bounded downloads.

Article search and local explanation settings embed this same picker instead of navigating away. Results use natural-height, non-shrinking rows in a bounded list; long descriptions wrap without overlapping. Selection opens adjacent details on wide layouts and stacked details below on narrow layouts, with focus handed to the selected model heading. Resource estimates disclose on demand. Composed search fields have one muted-blue focus ring around icon and input; their input is transparent without an extra border or ring. Primary button labels retain contrast in both themes. Existing model consent, verification, resource limits, local data and automatic-processing preferences retain their actual behavior. No new comp, identity, seed or decorative asset applies.
