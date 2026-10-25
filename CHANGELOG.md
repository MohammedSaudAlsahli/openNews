# سجل التغييرات / Changelog

## 0.3.2 — 2026-10-25

إعادة التلخيص حسب الطلب بالمودل المختار مع حفظ النتيجة السابقة حتى نجاح البديل، وإظهار المودل الذي أنشأ الملخص ووقت حفظه، ومعاينة روابط المقالات والمصادر والمنشورات عند المرور بالمؤشر أو التركيز بلوحة المفاتيح، دون تشغيل مودل. إعادة استخدام المحتوى المحفوظ مع إظهار تعذّر القراءة بوضوح. [التفاصيل / Details](docs/releases/v0.3.2.md).

On-demand regeneration preserves the previous result until success. Show the original summary model and creation time, plus reader link previews on hover or keyboard focus. Previews reuse saved evidence without inference and disclose unavailable sources.

## 0.3.1 — 2026-10-25

الملخص / TL;DR ظاهر مباشرة في القارئ، وتجهيز خلفي للمقالات والروابط المباشرة، واقتباسات مطابقة للمصدر، واستئناف للمقالات الطويلة وحماية موارد الجهاز. إصلاح تزامن اختبار التركيز في مكتبة المهارات. [التفاصيل / Details](docs/releases/v0.3.1.md).

Visible TL;DR, bounded linked-source preparation, verified quotation text, resumable long-article notes and resource-aware local inference. Fix the skill-library focus test race.

## 0.3.0 — 2026-10-25

**Tauri هو التطبيق المعتمد / Tauri is the official application.**

إعادة تنظيم الواجهة والإعدادات، مكتبة Ollama موحّدة، مهارات قابلة للاكتشاف والاستيراد النصي، تحسين الاستدلال المحلي والقارئ وتنسيق النص، وتوثيق عربي وإنجليزي ورخصة MIT. [ملاحظات الإصدار كاملة / Full release notes](docs/releases/v0.3.0.md).

## سجل Swift السابق / Previous Swift releases

### 0.2.3 — 2026-10-18

Automatic article recovery, editable instructions, writing skills and indexing visibility. See [release notes](docs/releases/v0.2.3.md).

### 0.2.2 — 2026-10-18

Improved article covers, image caching, source management and public blog-page subscriptions. See [release notes](docs/releases/v0.2.2.md).

### 0.2.1 — 2026-10-15 (Experimental)

Smaller bundle with optional Ollama embeddings; complete RSS.mobi discovery and followed-source fixes; clearer settings, live activity and bilingual public summaries. Consistent article-summary language and lighter text rendering. Full notes: docs/releases/v0.2.1.md.

### 0.2.0 — 2026-10-14 (Experimental)

Guided first-run news workflow, paginated on-demand article loading, signed Sparkle
updates, persistent news memory, optional local summaries, and quieter background
inference. Improved native conversation and article reading. macOS 14+ Apple Silicon.
Not Apple-notarized. Full notes: docs/releases/v0.2.0.md.
