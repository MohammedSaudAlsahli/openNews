# openNews

تطبيق macOS لقراءة الأخبار ومناقشتها وصناعة المحتوى، بواجهة **Tauri + React** ومحرك **Python + Agno + SQLite** مضمّن.

**`main` هو فرع التطوير الأساسي لنسخة Tauri.** توقّف تطوير واجهة SwiftUI، وحُفظت نسختها الكاملة وتاريخها في [swift-legacy](https://github.com/MohammedSaudAlsahli/openStudio/tree/swift-legacy). ملفات Swift الصغيرة داخل `desktop/native` هي خدمات macOS يستعملها Tauri وليست التطبيق القديم.

## المميزات الحالية

- RSS وAtom وReddit ومواقع بلا RSS، مع قارئ داخلي وصور محفوظة وشرح المقالات.
- تحديث افتراضي كل 5 دقائق، وقائمة لاختيار الفترة من دقيقة إلى يوم، وأوقات نشر نسبية.
- محادثات وأوامر `/` وإرفاق أخبار عبر `@` وملفات نصية، ومسودات قابلة للتحرير.
- تعليمات قابلة للتعديل داخل التطبيق، نماذج محلية أو سحابية، بحث نصي ودلالي وتقارير يومية.
- بلاغ GitHub قابل للمراجعة يتضمن تفاصيل الخبر ووقت التحميل عند اختياره، وتنبيه بعد إغلاق غير متوقع.

## التطوير والبناء

المتطلبات: macOS، أدوات Xcode Command Line Tools، Rust، Node.js 22، وuv مع CPython 3.12.13.

```sh
bash scripts/test.sh
bash scripts/build_app.sh
cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml
```

ناتج البناء: `desktop/src-tauri/target/release/bundle/macos/openNews.app`.
يُجهّز البناء Python واعتماداته المقفلة مباشرة؛ لا يحتاج إلى بناء تطبيق SwiftUI أو تثبيت Python لدى المستخدم.

للتطوير بعد تجهيز المحرك:

```sh
npm --prefix desktop run tauri -- dev
```

## البيانات والإصدارات

معرّف نسخة Tauri باقٍ `com.editorialintelligence.studio.preview` للتوافق مع بيانات المستخدمين الحاليين؛ الاسم الظاهر هو **openNews**. تبقى البيانات في:

`~/Library/Application Support/com.editorialintelligence.studio.preview/default/`

لم يتغير مسار بيانات نسخة Swift السابقة. يمكن استيراد بياناتها من داخل التطبيق. لا تنسخ ملفات الاعتماد إلى مستودع GitHub.

إصدارات Swift المنشورة سابقًا وملف Sparkle التاريخي لا تعني أن إصدار Tauri جديدًا قد نُشر. رفع الشفرة إلى `main` منفصل عن إصدار تحديث موقّع؛ قناة Tauri لا تُحدّث إلا بعد بناء الحزمة واختبارها. التطبيق الحالي تجريبي وغير موثّق لدى Apple.

[البلاغات والقراءة والتحديث](docs/opennews-reporting.md) · [المحادثة والمرفقات](docs/tauri-composer-and-support.md). بقية مستندات Swift التاريخية مرجع للميزات السابقة؛ تعليمات بنائها موجودة في فرع `swift-legacy`.
