<div dir="rtl">

# openNews

**أخبارك ومصادرك ومساعد الكتابة، في مساحة واحدة على جهاز Mac.**

[English](README.en.md) · [دليل الاستخدام](docs/SETUP.md) · [التوثيق](docs/README.md) · [تحميل آخر إصدار](https://github.com/MohammedSaudAlsahli/openNews/releases/latest)

[![الفحوصات والبناء](https://github.com/MohammedSaudAlsahli/openNews/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MohammedSaudAlsahli/openNews/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/MohammedSaudAlsahli/openNews)](https://github.com/MohammedSaudAlsahli/openNews/releases/latest)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

openNews تطبيق macOS لجمع الأخبار وقراءتها ومناقشتها وتحويل الأفكار إلى مسودات قابلة للتحرير. واجهته عربية وإنجليزية، ويدعم النماذج المحلية عبر Ollama والحسابات السحابية عند اختيارها.

**نسخة Tauri هي النسخة الرسمية الوحيدة المدعومة من openNews، و`main` هو فرعها الأساسي.** واجهة React، وجسر Rust، ومحرك Python مضمّن مع SQLite. لا تحتاج إلى تثبيت Python أو Node لاستخدام النسخة الجاهزة. واجهة SwiftUI السابقة محفوظة للأرشيف فقط في [swift-legacy](https://github.com/MohammedSaudAlsahli/openNews/tree/swift-legacy)، ولا تُنشر كتطبيق أساسي موازٍ.

## ما الذي يمكنك فعله؟

- **اقرأ من مصادرك:** RSS وAtom وReddit وروابط المواقع العامة، مع أرشيف وقارئ داخلي وسجل نسخ المقال.
- **ناقش واكتب:** محادثات مرتبطة بالأخبار، مراجع عبر `@`، أوامر مهارات عبر `/`، ومسودات تحفظ نسخها.
- **ابحث في المحفوظات:** بحث نصي، وبحث دلالي اختياري بنموذج embedding محلي.
- **أدر نماذجك من مكان واحد:** مكتبة Ollama موحّدة تعرض المحمّل وقدراته؛ اختر نموذج البحث ونموذج الشرح كلًا حسب وظيفته.
- **خصّص مساعدك:** تعليمات وأمثلة كتابة ومهارات قابلة للتحرير، واكتشاف مهارات من skills.sh ومعاينة تعليماتها من GitHub قبل إضافتها.
- **تحكّم في الخلفية:** إعدادات للأداء والبطارية والجدولة، وحالات واضحة للتنزيل والفهرسة والتقارير اليومية.

استيراد المهارات يضيف تعليمات نصية فقط؛ لا يثبّت سكربتات أو ينفّذ ملفاتها. البحث الدلالي والشرح وظيفتان مختلفتان، حتى لو كان مزوّدهما Ollama نفسه.

## التثبيت

1. حمّل `openNews-<version>-macOS-arm64.zip` من [الإصدارات الرسمية](https://github.com/MohammedSaudAlsahli/openNews/releases/latest).
2. فك الضغط، وانقل **openNews.app** إلى **Applications**، ثم افتحه.
3. أضف مصدرًا وابدأ القراءة. ربط حساب أو تنزيل نموذج خطوة اختيارية.

التوزيع الحالي لأجهزة **Apple Silicon**؛ الحد الأدنى المعلن **macOS 14**. الحزمة موقّعة محليًا بتوقيع ad-hoc، وليست موثّقة لدى Apple؛ راجع [دليل التثبيت](docs/SETUP.md) إذا منعها Gatekeeper. لا يتوفر بناء Intel أو Windows أو Linux ضمن هذا الإصدار.

## بياناتك واتصالاتك

تُحفظ المقالات والمحادثات والمسودات في مساحة محلية. استخدام حساب سحابي يرسل السياق اللازم إلى مزوّده؛ وجلب الأخبار والأدلة وتنزيل النماذج يحتاج الإنترنت. «محلي» لا يعني أن كل ميزات التطبيق بلا اتصال. التفاصيل في [الخصوصية](docs/privacy.md).

يحافظ التطبيق على معرّف البيانات `com.editorialintelligence.studio.preview` للتوافق مع التثبيت السابق؛ كلمة `preview` في المسار اسم تقني قديم، وليست حالة الإصدار. لا تحذف مساحة البيانات أثناء التحديث.

## للمطورين

المتطلبات: macOS، أدوات Xcode Command Line Tools، Node.js 22، Rust stable، وuv مع CPython 3.12.13.

</div>

```sh
git clone https://github.com/MohammedSaudAlsahli/openNews.git
cd openNews
bash scripts/test.sh
bash scripts/build_app.sh
cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml
```

<div dir="rtl">

ناتج البناء: `desktop/src-tauri/target/release/bundle/macos/openNews.app`. لإطلاق وضع التطوير بعد تجهيز المحرك: `npm --prefix desktop run tauri -- dev`.

راجع [دليل المساهمة](CONTRIBUTING.md)، [المعمارية](docs/architecture.md)، و[إجراءات الإصدار](docs/RELEASING.md). الاعتمادات مقفلة في npm وCargo وuv؛ تبني CI الحزمة وتختبر المحرك والواجهة والجسر الأصلي.

## حدود واضحة

المخرجات الآلية تحتاج مراجعتك؛ وجود رابط لا يثبت صحة الادعاء. لا ينشر التطبيق المحتوى نيابة عنك. قد تمنع بعض المواقع القراءة العامة. سرعة النماذج والذاكرة والحرارة تعتمد على الجهاز وحجم المحتوى؛ لا توجد دعوى «بلا حرارة» أو قياسات أداء عامة. التحديث الموقّع متاح من إعدادات التطبيق: تحقّق من وجود تحديث ثم اختر التثبيت وإعادة التشغيل. يبقى التنزيل اليدوي من GitHub Releases متاحًا.

## المشاركة والرخصة

[بلاغ مشكلة](https://github.com/MohammedSaudAlsahli/openNews/issues/new/choose) · [طلب ميزة](https://github.com/MohammedSaudAlsahli/openNews/issues/new/choose) · [الإبلاغ الأمني الخاص](SECURITY.md) · [سجل التغييرات](CHANGELOG.md)

شفرة المشروع تحت [MIT](LICENSE). تراخيص الاعتمادات والنماذج والمحتوى الخارجي مستقلة؛ راجع [إشعارات الأطراف الثالثة](THIRD_PARTY_NOTICES.md). تسمح MIT بالاستخدام التجاري والتوزيع والبيع مع الاحتفاظ بالإشعارات المطلوبة.

</div>
