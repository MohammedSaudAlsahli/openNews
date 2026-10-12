# Apple HIG review — analyst 1

Reviewed 2026-10-11. Evidence: current `ContentView.swift` and directly indexed Apple Developer documentation. Canonical HIG pages sometimes returned a JavaScript shell; Apple-domain search results supplied the page body. No third-party HIG mirror was relied upon.

## Diagnosis

The six-item `Page` enum treats a sequence of work (source → suggestion → chosen style → draft) as unrelated destinations. The overview consumes the first screen with a slogan, three statistics, repeated navigation, and technical status. The writing screen mixes setup, draft creation, and a second list of drafts; editing then opens a modal sheet. Essential recovery sends people elsewhere: source import points to the library, generation points to overview for progress, and missing style rules point to a technical “DNA” destination.

## Five implementable recommendations

1. **Make content the navigation.** Replace six feature pages with one two-column workspace: a compact, hideable navigator containing Sources and Drafts; the selected document occupies the main area. Default to the most recent draft, or a simple “New draft / Add source” empty state. A source detail shows its text and analysis together. “Writing style” becomes an on-demand supplementary view rather than a required navigation stop. This is our product-specific inference from Apple’s guidance: sidebars expose peer content areas; they consume considerable space and should be hideable. Avoid filling one with process stages. [Apple: Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars)

2. **Use the native window toolbar for stable commands.** Show “New draft”, “Add source”, and the contextual inspector toggle. Put save/export with the selected draft and provide matching menu commands and keyboard shortcuts. Remove the fabricated in-content header, redundant branding block, metric cards, and slogan. Toolbar commands should reflect frequent tasks, remain intelligible, and avoid overcrowding; Apple also expects menu equivalents on macOS. Keep at most a few coherent command groups. [Apple: Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars)

3. **Keep review beside the object being reviewed.** Analysis completion should reveal the technique immediately below/beside its source, with excerpt and “Use in writing style”. Editing a draft should happen in the main workspace, with optional evidence/style inspector. Do not make the author navigate away to locate a job or interpret its output. Show progress beside the action that created it. Apple describes inspectors as selection-dependent supplementary information and explicitly permits a split-view pane. This application of that pattern preserves the writer’s context. [Apple: Panels](https://developer.apple.com/design/human-interface-guidelines/panels)

4. **Disclose advanced choices only when needed.** The default composition surface needs topic, format, and one clear next action. Put language, video duration, references, and advanced model options in labeled disclosure sections; duration appears only for video. Keep consent visible immediately before an external request. Source import defaults to title/text/rights, with author/URL under optional details. Apple recommends keeping essential controls visible while concealing detailed options until relevant. Model settings belong in the macOS Settings window, with a direct “Set up a model” action when required. [Apple: Disclosure controls](https://developer.apple.com/design/human-interface-guidelines/disclosure-controls), [Apple: Settings integration](https://developer.apple.com/documentation/foundation/adding-a-settings-interface-to-your-app)

5. **Restore system readability and ordinary Arabic.** Replace `Editorial DNA` with `أسلوب الكتابة`, `تحليل Agno` with `تحليل بالنموذج`, and raw verdicts with Arabic review statuses. Add persistent labels to fields and accessible names to icon-only controls. Replace hard-coded paper/ink combinations and forced light appearance with semantic system surfaces/text, then check both appearances and increased contrast. Status needs text/symbols as well as color. Apple favors familiar, accessible interactions and adaptive system colors; its writing guidance recommends plain language, clear verbs, and direct recovery links. [Apple: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility), [Apple: Writing](https://developer.apple.com/design/human-interface-guidelines/writing)

## Acceptance checks

- A first-time user can add a source, analyze it, and approve a style suggestion without switching primary destinations.
- Creating/choosing a draft keeps its editor visible; evidence can be shown or hidden without closing the draft.
- Toolbar and menu actions work by keyboard. Hiding the navigator never removes access to essential commands.
- Source rights and explicit external-request consent remain real gates. Simplification must not imply cloud generation is verified while the Keychain integration remains blocked.
- The primary workspace contains no runtime names, UUIDs, adapter catalog, future-feature inventory, or statistics unrelated to the selected work.
