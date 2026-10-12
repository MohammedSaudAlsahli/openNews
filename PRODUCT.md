# Product
<!-- impeccable:product-schema 1 -->

## Platform
Native macOS (SwiftUI), not web or iOS.

## Users and purpose
An Arabic-speaking individual writer discusses ideas and subscribed news, then develops original, editable content using examples of their own writing. The user requested a complete UI simplification, followed by persistent editorial conversation, automatic public-news subscriptions, and a clear separation between news evidence and personal style examples.

## Stack and constraints
SwiftUI, embedded Python/Agno, local SQLite, versioned source/draft records, Unix socket IPC. Preserve exact evidence, explicit style-rule approval, and consent before sending conversation, drafts, news or style samples to a model. Snapshot text is a preview; detail endpoints provide authoritative text. This is a development build with ad-hoc signing, not a notarized public release. Credentials use owner-only local JSON files at the user's request; historical Keychain findings do not describe the current path.

## Current scope
- Persistent editorial conversation with optional current-draft context, selected news or a bounded recent-news window, and separately saved proposed drafts.
- RSS/Atom subscriptions, feed discovery from website links, and public Reddit subreddit feeds. Automatic polling runs only while the app is open; reopening checks subscriptions that are due. Linked articles are fetched where public access and extraction succeed; feed summaries remain clearly distinguished when full text is unavailable.
- Manual owned/licensed writing samples, contextual style adaptation, local structural analysis, optional model analysis, and explicitly approved or retired style rules. This is not model training or fine-tuning.
- Independent X posts, one cohesive long YouTube script, or individual short TikTok scripts from conversation. These are text artifacts, not produced videos or published posts.
- Local manual drafts, immutable saved versions, evidence review and Markdown export. Local writing does not require a model.
- All 68 pinned Agno adapters remain represented, with per-connection dynamic model catalogs and separate writer/analyst choices. Adapter availability does not prove live account access or model capabilities.

## Principles
- Keep discussion, writing, and relevant sources in one working window.
- Use contextual controls and adaptive panels, not separate pages for each pipeline stage.
- Separate news evidence, reference material, and personal writing style.
- Preserve dirty writing; generated proposals never silently replace it.
- Use plain Arabic, native macOS controls and keyboard equivalents.
- State coverage and retrieval limits. Citations identify supplied evidence, not independently verified truth.

## Coverage limits
The recent-news default is the last seven days by known publication timestamp, not discovery time or an invented event date. At most 12 articles enter a request; explicit selection can include older articles. The news list exposes the 100 most recent stored articles, while automatic context selection queries stored publication dates independently. Missing dates, inaccessible bodies and limited context must not be described as complete weekly coverage. Full fact-checking, audiovisual production, publishing, series/storyboards, Skills execution and embeddings remain outside the implemented feature set.

## Evidence
PRD.md remains the broader target specification. Current behavior is defined by native views and the source, news, conversation, provider and draft IPC contracts. See docs/chat-news.md, docs/provider-discovery-coverage.md and the historical validation record in docs/acceptance.md. This document does not assert a newly packaged build or a successful live model call.

## شريط القوائم والخلفية
إغلاق نافذة التحرير يخفيها مع الاحتفاظ بالمسودة والنقاش، ويستمر التطبيق في متابعة الأخبار. قارئ شريط القوائم يعرض الأخبار ويتيح قراءتها سريعًا والبحث والتصفية والعودة لمساحة التحرير. الإنهاء الصريح يوقف المحرك، ولا يوجد تشغيل تلقائي عند تسجيل الدخول أو استيقاظ للجهاز من السكون.
