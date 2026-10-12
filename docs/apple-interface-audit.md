# مراجعة واجهة macOS والعربية — 2026-10-12

هذه مراجعة تطبيقية للأجزاء الحالية من التطبيق، وليست شهادة اعتماد من Apple أو ادعاء تغطية كل إرشاداتها.

## المراجع الرسمية

- [صمّم بالعربي — جلسة Apple العربية](https://developer.apple.com/videos/play/wwdc2022/110441/)
- [Design for Arabic — النسخة الإنجليزية](https://developer.apple.com/videos/play/wwdc2022/10034/)
- [Right to left — Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/right-to-left)
- [Get it right (to left)](https://developer.apple.com/videos/play/wwdc2022/10107/)
- [Designing for macOS](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos)
- [Keyboards](https://developer.apple.com/design/human-interface-guidelines/keyboards)

## التطبيق

| القاعدة | التنفيذ |
|---|---|
| ترتيب منطقي قابل للعكس | اتجاه البيئة حسب لغة الواجهة، ومحاذاة leading/trailing؛ حقول الروابط والمسارات والمفاتيح وحدها LTR وتبقى تسمياتها باتجاه الواجهة. |
| فصل اتجاه المحتوى عن اتجاه الواجهة | النص القصير يتبع الواجهة؛ الفقرة الطويلة تتبع لغتها عند عرضها. القوائم والعناوين متسقة مع الواجهة والكود LTR. يستخدم المحرر NSTextView واتجاه Unicode الطبيعي لكل فقرة. |
| احترام اللغة والمنطقة | تنسيق الأعداد والتواريخ عبر Foundation مع الاحتفاظ بمنطقة المستخدم والتقويم ونظام الساعات. عزل بيانات العرض المختلطة لا يغير النص المخزن. |
| أدوات macOS | SwiftUI وAppKit، TabView وForm وList وPicker وLabeledContent، ألوان النظام وخطوطه وSF Symbols؛ لا WebView في قارئ النصوص أو المحرر. |
| لوحة المفاتيح والوصول | التراجع الأصلي للمحرر، تسميات للأزرار الأيقونية، تغيير تسمية المحرر فور تبديل اللغة، وتجنب حجز اختصار ⌘J القياسي. |
| الروابط والقراءة | عناوين وقوائم واقتباسات وكود وروابط بلون النظام وتسطير؛ روابط HTTP/HTTPS فقط. الاقتباسات المستخدمة كدليل تبقى حرفية. |

## حدود التحقق

اختبارات منطق Markdown واتجاه الفقرات والمحاذاة والتواريخ والأرقام وتطابق موارد اللغتين، مع فحص فعلي للحزمة في العربية والإنجليزية. هذه الجولة لا تشمل تدقيق VoiceOver شاملًا أو اعتماد App Store. تفاصيل الاختبارات والقيود الأخرى في acceptance.md.
