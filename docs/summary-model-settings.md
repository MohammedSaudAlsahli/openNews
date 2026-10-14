# Summary model settings

## Native settings extension

The dedicated **Summaries & Models** (التلخيص والنماذج) section extends the existing
macOS Settings window. It uses the existing sidebar, native segmented control,
search field, list selection, version menu, disclosure and progress controls.
Automatic-summary language, pause/resume, active model and queue status stay above
the model browser. The detail pane prioritizes download size, preliminary device fit
and one primary action; memory estimates, publisher information and quality limits
are disclosed below it. Suggested entries are candidates to try, not quality-ranked
recommendations. The Downloaded view reflects the app-owned model store, including
when its runtime is stopped.

This is an ordinary extension of the incumbent native design. It introduces no new
palette, typography system, card vocabulary or design tokens. `DESIGN.md` and
`.impeccable/design.json` are preserved. The settings implementation already exposes
optional theme palettes that are not fully represented by the older native-only
design narrative; this task does not reconcile that pre-existing documentation drift.

## Setup and activation contract

1. Browse suggestions or search the live Ollama catalogue, loading more results as
   needed. Select a model and one of the versions discovered from its public tags page.
2. Inspect registry download size and device capacity. Required free disk includes
   undownloaded weights, three times the runtime archive size when needed, and a
   2 GB reserve. Estimated inference memory is 1.25 times weight size plus 1 GB;
   estimates above 80% of physical RAM block setup. These are conservative heuristics.
3. With model-use permission enabled, choose Download & Use. The app reuses a managed
   or existing Ollama executable when available. Otherwise it downloads the official
   macOS release, checks the published SHA-256 digest and extracts it into app storage.
4. Start the app-owned loopback service on port 11435, download and verify the model's
   presence, check local completion capability, then run an Agno `ArticleSummary`
   schema smoke request. Only successful completion selects the model and enables
   automatic summaries. Cancellation and failures leave the proposed model inactive.

The runtime preparation, weight download and test have visible progress/status and
a cancellation action. Model information comes from public catalogue HTML, so upstream
markup changes can affect discovery; the page exposes errors and retry. Local inference
uses no cloud fallback. The connected route remains available and retains its daily
request limit. Downloading another model does not by itself establish its quality.

## Implementation references

- `macos/Sources/OpenStudioApp/ModelSettingsView.swift`: dedicated settings destination.
- `macos/Sources/OpenStudioApp/LocalSummaryModels.swift`: discovery, detail, summary controls and setup states.
- `engine/eis_engine/model_library.py`: paged catalogue and version discovery.
- `engine/eis_engine/model_capacity.py`: disk/RAM preflight.
- `engine/eis_engine/local_runtime.py`: official runtime acquisition and checksum verification.
- `engine/eis_engine/local_summary.py`: app-owned models, setup, capability checks and Agno inference.

## Validation boundary — 2026-10-14

The implementation run reports 353 Python tests and 51 Swift tests passing. The
actual official Ollama 0.40.4 runtime was downloaded, checksum-verified and unpacked.
An isolated live test downloaded `gemma3:270m` (approximately 291 MB), returned the
Agno JSON summary schema and completed local activation. This used an English smoke
prompt; it is not an Arabic quality test or an English summary-quality benchmark.
The user's existing connected/cloud summary assignment was left unchanged.

Final Arabic and English native recaptures were verified. The visual verdict was
ship for the three reviewed fixes: copy fit/sidebar layout, search enabled from
Suggested with a switch to Library, and unique version tags. No regressions were
observed within those fixes; this was not a whole-surface audit. Native checks also
confirmed that Gemma 4 `31b-it-bf16` showed Needs more memory with Download & Use
disabled, while `e2b-it-qat` showed a 4.34 GB download, preliminary fit and an enabled
download action. Final bundled build, signature and DMG checks passed. These checks
do not establish comprehensive accessibility or performance/quality results for
larger models or libraries.
