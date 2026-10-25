# سجل التغييرات / Changelog

## 0.3.3 — 2026-10-25

فصل النسخة اليومية عن **openNews Dev** باسم ومعرّف ومساحة بيانات مستقلة، وتعطيل قناة التحديث الرسمي في التطوير. مسار `develop` → `main`، وفروع تحديثات مؤقتة تُدمج بعد الاختبار وتُحذف تلقائيًا. تحديث Pillow وfilelock وLiteLLM وcertifi لمعالجة التنبيهات الأمنية الحالية، وتنظيف المستودع والهوية القديمة وتجهيز DMG رسمي واضح. [التفاصيل / Details](docs/releases/v0.3.3.md).

Isolate development identity, data and updates; test dependency updates on develop, automatically delete merged branches and promote official releases through main. Update Pillow/filelock/LiteLLM/certifi, remove obsolete Swift-era files and deliver a clean official DMG.

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

إصدارات 0.2.x وأدواتها تخص التطبيق السابق؛ راجع [الإصدارات السابقة](https://github.com/MohammedSaudAlsahli/openNews/releases) أو [وسم الأرشيف](https://github.com/MohammedSaudAlsahli/openNews/tree/archive/swift-legacy).

The 0.2.x releases belong to the former application. Their notes and source remain available in [GitHub Releases](https://github.com/MohammedSaudAlsahli/openNews/releases) and [archive/swift-legacy](https://github.com/MohammedSaudAlsahli/openNews/tree/archive/swift-legacy).
