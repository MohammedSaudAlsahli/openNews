# Agent 4 — Arabic, accessibility, and native input audit

Inspected existing App.swift and ContentView.swift on 2026-10-11. Findings below are implementation recommendations, not a claim that VoiceOver or keyboard QA has passed. Apple pages sometimes return a JavaScript-only body to direct fetch; source content was verified in indexed Apple Developer search results.

## Highest-impact replacements

- Remove the six-page taxonomy from navigation. Use a native selectable content list (sources and drafts) and a contextual work area. The same source should expose reading, technique suggestions, and approval without a page change. Keep style management in a sheet/inspector titled **أسلوبي** and connection management in settings.
- Replace fixed ink/paper RGB colors and `.preferredColorScheme(.light)` with semantic AppKit colors, standard SwiftUI foreground styles and native backgrounds. Current hard-coded dark green and white cards previously forced a light-only repair. Support the system appearance; inspect both appearances and Increased Contrast. [Apple Dark Mode](https://developer.apple.com/design/human-interface-guidelines/dark-mode)
- Use system text styles for navigation, labels, and status. Reserve a larger reading font for source/draft body, not slogans. Apple selects script-appropriate system typefaces; no downloaded Arabic font is needed. Avoid letter spacing/tracking on Arabic. [Apple Fonts](https://developer.apple.com/documentation/technologyoverviews/fonts)

## Arabic copy decisions (product recommendations)

| Existing | Replacement | Placement |
|---|---|---|
| Editorial DNA | أسلوبي | Sheet or inspector, not a top-level destination |
| تقنيات الكتابة | اقتراحات الأسلوب | Next to the selected source |
| اعتماد في DNA | أضف إلى أسلوبي | Beside the exact source excerpt |
| إيقاف قاعدة | إزالة من أسلوبي | Keep historical versions in backend |
| الاستوديو | مسودة جديدة | Primary task, not destination |
| رصد بنيوي محلي | اقتراح محلي | Small explanation: يكتشف بنية النص، ولا يقيّم معناه. |
| Agno | باستخدام نموذج الذكاء الاصطناعي | Keep library name in advanced details only |
| provider_key / model_id | خدمة الذكاء الاصطناعي / النموذج | Settings labels |
| needs_review | يحتاج مراجعة | Claim status |
| x_post, x_thread, youtube_long | منشور X، سلسلة X، نص فيديو YouTube | Friendly format labels |
| المحرك غير متصل | تعذّر تشغيل مساحة العمل | Error banner with إعادة المحاولة; technical detail disclosure |

Empty source state: **أضف نصًا تستلهم منه** / **الصق نصًا أو استورد ملفًا، ثم اختر ما يناسب أسلوبك.** / **إضافة مصدر**.
Empty draft state: **ابدأ مسودتك** / **اكتب الفكرة، واختر الشكل، ثم راجع النتيجة هنا.** / **مسودة جديدة**.
Generation consent remains explicit near its action: **أوافق على إرسال الفكرة والمصادر المحددة إلى [الخدمة]. قد تُحتسب تكلفة.** Do not imply local AI generation.

## RTL and mixed-script rules

Use semantic leading/trailing alignment and let native controls mirror. Retain RTL interface, but URLs, API keys, model identifiers and technical diagnostics should be LTR fields. Draft editor direction should follow selected writing language, not forcibly Arabic for English drafts. Preserve logical numbers with locale formatting; never manually reverse digits. SF Symbols provide directional variants: do not transform arbitrary images. [Apple RTL](https://developer.apple.com/design/human-interface-guidelines/right-to-left)

## Keyboard/focus checklist

- Restore a meaningful File > New command instead of the current empty `CommandGroup(replacing: .newItem)`; Cmd-N = new draft. Cmd-Shift-N can add a source. Cmd-, opens settings, Cmd-S saves current draft, Cmd-F focuses content search.
- Add `.keyboardShortcut(.cancelAction)` and `.defaultAction` to sheet Cancel/Save when unambiguous. Do not bind plain Return to generation inside a multiline editor.
- Add FocusState for initial source-title/topic focus and search. Preserve editor focus through background snapshot polling; avoid view identity changes on refresh.
- Use native List(selection:) so arrow navigation, selection state and focus visuals are native. Do not replace list rows with custom tap-only cards.
- Focus remains visible. Test keyboard-only add-source, select-source, approve-suggestion and edit/save draft. Follow standard shortcuts and enable Full Keyboard Access for a QA pass. [Apple Keyboards](https://developer.apple.com/design/human-interface-guidelines/keyboards/), [Focus and Selection](https://developer.apple.com/design/human-interface-guidelines/focus-and-selection/)

## Accessibility/layout checklist

- Give icon-only actions accessibilityLabel and help: إغلاق، إعدادات، إضافة مصدر، إظهار تفاصيل المسودة. Current notice-dismiss xmark has no purpose label.
- Label all TextEditors explicitly: نص المصدر / نص المسودة. Placeholder-only text fields should have persistent visual captions when context is ambiguous.
- Status combines words + symbol, never color alone. Busy states say جاري الحفظ / جاري التحليل when relevant.
- Source list rows should read title, type/status and excerpt in that order; avoid making the full complex workspace one combined VoiceOver element.
- Keep layout resizable. Replace a rigid large minimum and all fixed-size sheets with sensible minimum/ideal dimensions and scrollable content. At small width, collapse auxiliary context before squeezing text.
- Exact evidence remains selectable, source citation adjacent. Do not hide critical approval or consent behind tooltips.
- Test Arabic diacritics, long source titles, mixed Arabic/English/URLs, 200% content text zoom if offered, light/dark, increased contrast, and keyboard-only traversal. Do not claim Dynamic Type support solely because `.font(.body)` is present on macOS.
- [Apple accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility), [Apple VoiceOver criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/voiceover-evaluation-criteria), [Apple writing](https://developer.apple.com/design/human-interface-guidelines/writing)
