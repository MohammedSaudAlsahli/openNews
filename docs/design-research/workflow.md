# Workflow audit — analyst 3 of 5

This is an implementation-grounded audit of PRD.md, ContentView.swift, StudioModel.swift, IPC.swift, service.py and contracts.py. No application files changed. The PRD's original eight-page navigation is superseded by the user's explicit full simplification request; functional truth and consent contracts remain.

## Main recommendation

Use one writing workbench, with a compact item sidebar (sections: المسودات، المصادر), one selection-dependent content surface, and optional contextual review inspector. Delete overview, metrics, slogan, separate techniques page, separate DNA page, and full-page settings. Make أسلوبي a sheet or inspector section; put provider setup behind standard Settings and direct actionable links from blocked generation. Sources are selectable documents, not giant cards. Drafts are selectable documents, not generation-form appendices. The toolbar contains new draft, add source, optional review/inspector and settings. Show background work in a compact status area with expansion, not a navigation destination.

A source opens its preview and extracted technique suggestions together. Its primary action is تحليل النص locally. Each suggestion includes its exact excerpt and إضافة إلى أسلوبي, so source → technique → approved rule occurs without leaving context. Allow editing the statement before approval (already supported). Once a rule is added, offer اكتب بهذه القواعد to focus the writing composer. New writing shows brief + format first; references, language/video length and model options are secondary sections. Open an existing draft directly in the central editor; review evidence and versions in a collapsible inspector.

## Contracts to retain

| User action | Actual contract | Required UI behavior |
|---|---|---|
| Add text/file | sources.add; title1–300, text1–120000; author≤200, optional HTTPS URI≤2000; rights owned/licensed/unknown | Primary fields title/text; metadata in disclosure; rights retained; import is local only. Close only after successful save. |
| Local analysis | analysis.run(item_ids,idempotency_key), no profile | No cloud consent needed. It only detects opening question, numbered steps, separate paragraphs. Explain no matches as a valid outcome. |
| AI analysis | analysis.run(...profile_id,consent:true) | Explicit cost/data approval; unknown rights cannot be sent. Reanalysis mode issue below. |
| Style approval | dna.approve(technique_id, optional statement3–1500) | Explicit approval only; display precise quoted evidence; no auto-selection of all suggestions. |
| Remove style rule | dna.retire(rule_id) | Label إزالة من أسلوبي / تعطيل القاعدة; this changes future writing only; earlier frozen versions survive. |
| Generate | drafts.generate(topic3–2000,format,language,profile_id,dna_version_id,source_ids≤12,consent,idempotency_key) | Explain missing style rule/profile inline with direct remedy. Video requires10–7200 seconds. Never silently check consent. |
| Reference selection | owned/licensed sources only for cloud; aggregate≤45000 chars | Prevent selecting unknown-rights sources with explanation; max12; backend remains authoritative for full text length. |
| Edit draft | drafts.detail gives full text; drafts.save max60000 creates immutable new version | Never edit preview; save must preserve dirty text on failure and protect navigation from silent discard. Saving invalidates old evidence. |
| Export | drafts.export returns Markdown, unapproved warning | Export saved version only. If dirty, offer save then export or clearly export last saved; never imply approval/publication. |
| Jobs | jobs.cancel/get/resume; persisted queue | Show running/failure in context. Resume cloud work requires explicit cost consent. Cancellation not error. |
| Providers | providers.save returns keychain_ref, then native Keychain.save | Config secrets must remain native Keychain only. Connection test separate explicit paid action. Current Keychain limitation must remain visible near relevant actions/settings. |

## High-priority traps during redesign

1. Snapshot Source.text is only first1200 characters, Draft.text only1600. Label source excerpt as preview unless adding full detail read. Never put preview in an editable full document. drafts.detail is authoritative.
2. Technique snapshot has sourceTitle and canonicalUri but no source ID. Matching titles is unsafe for duplicate names; add i.id AS item_id to backend SELECT and corresponding TechniqueCard field, or keep global suggestions clearly global. Old versions also remain as evidence, so distinguish current source version if filtering.
3. Any completed analysis on a version causes incremental analysis to skip, even changing local to AI. An AI analysis option after local must request mode explicit_rebuild. Same signature is still skipped. Do not promise new results when no new run occurs.
4. Source snapshot is limited200, techniques50, drafts100; local title/preview filter is not a full-library search. Label accurately or use library.search (returns chunks; currently lacks stable source item IDs too).
5. Async submission success only means queued. Do not show “اكتمل التحليل” at submit time. Polling refreshes active jobs once/sec. After completion inspect new suggestions/draft; no-match is possible.
6. perform catches errors and returns Void; stale model.error can prevent sheet dismissal despite successful mutation. Clear error at new action or use throwing call + explicit success. Do not navigate on assumed success.
7. A draft editor must key reload by draft.id. A generic onAppear can show previous draft if selection changes. Do not let snapshot refresh overwrite dirty text. If fetching fails keep editor unavailable, not an empty editor with save active.
8. Deleted credential leaves provider profile; profile existence does not prove connection. Current provider readiness is SDK constructor availability, not tested credentials. Keep names accurate.
9. Existing provider rotation shares one String across profile rows. Use per-profile state/sheet to avoid accidentally applying another profile's secret.
10. Successful style removal changes technique to suggested again; allow re-approval, do not assume approved forever.
11. Snapshot jobs expose type/state/error but no related document ID. For truly contextual jobs, capture returned job ID on submit or extend result identity. A global compact job popover is safer than false association.
12. Swift String.count counts graphemes, Python len counts code points. Limits shown by client are approximate; preserve backend validation. Evidence offsets correctly use UnicodeScalars and must remain that way.

## Arabic labels and action copy

| Existing | Recommended |
|---|---|
| Editorial DNA | أسلوبي |
| تقنيات الكتابة | اقتراحات من هذا النص |
| تحليل Agno | تحليل بالذكاء الاصطناعي… |
| اعتمد قاعدة في DNA | أضف إلى أسلوبي |
| ولّد المسودة | أنشئ مسودة |
| فتح المحرر والأدلة | Open by row selection; optional راجع الأدلة inspector |
| محرك محلي متصل | Hidden when healthy; جارٍ فتح مساحة العمل while starting |
| Settings verbose technology copy | النموذج المستخدم للكتابة; technical details in disclosure |
| No style rules | أضف قاعدة واحدة لأسلوبك قبل إنشاء المسودة. Action اختر من المصادر |
| Unknown rights reference | حدّد ملكية النص أو ترخيصه قبل إرساله. |
| No extracted techniques | لم نجد اقتراحات بنيوية في هذا النص. يمكنك تجربة نص آخر. |
| Export | تصدير Markdown… (draft warning stays in exported file) |

## Acceptance walkthrough

Launch opens useful writing/source context without dashboard. Import a uniquely titled owned sample; remain on selected source and run local analysis. See exact technique excerpt in same context, edit/approve rule, then remove/reapprove through أسلوبي. Start a draft brief; missing provider is actionable and consent never preselected. Existing drafts open full authoritative text; edits survive inspector toggles and need save/discard on navigation. Toggle review inspector, inspect prior versions, export saved version. Cancel/resume local job and ensure statuses remain readable without raw API enum names. Settings still supports all ready adapters via searchable advanced selection rather than a68-item first-run list. Validate Arabic mixed English URLs with LTR fields only.
