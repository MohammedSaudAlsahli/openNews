# سياسة الأمان / Security policy

## العربية

تتلقى أحدث نسخة Tauri منشورة على `main` إصلاحات الأمان. نسخ Swift والإصدارات الأقدم غير مدعومة بإصلاحات مستقلة. لا يعني مرور CI أو وجود هذه السياسة خلو المشروع من الثغرات أو حصوله على تدقيق أمني شامل.

**للثغرات استخدم [الإبلاغ الخاص على GitHub](https://github.com/MohammedSaudAlsahli/openNews/security/advisories/new)**؛ لا تنشر الاستغلال أو المفاتيح أو بيانات المستخدم في Issue عام. اذكر الإصدار والنظام وخطوات إعادة إنتاج صغيرة والأثر المتوقع، مستخدمًا بيانات اصطناعية. إن لم تتوفر القناة الخاصة، افتح بلاغًا عامًا بعنوان «طلب قناة تواصل أمني» دون تفاصيل حساسة. لا يوجد موعد استجابة مضمون.

حدود مهمة: جسر Tauri↔Python، فحص الروابط العامة والتحويلات، بيانات الاعتماد، استيراد المهارات، HTML/Markdown غير الموثوق، وتحديثات التطبيق. النص القادم من خبر أو مهارة بيانات غير موثوقة ولا يمنح صلاحية تنفيذ سكربتات. شارك أقل قدر لازم من التشخيص.

## English

Security fixes target the latest published Tauri release on `main`. Swift and older releases do not receive independent fixes. Passing CI or having this policy does not establish a comprehensive security audit or absence of vulnerabilities.

**Use [GitHub private vulnerability reporting](https://github.com/MohammedSaudAlsahli/openNews/security/advisories/new)** for vulnerabilities. Never disclose exploits, credentials or user data in public issues. Include version, platform, a minimal synthetic reproduction and expected impact. If private reporting is unavailable, open a public issue requesting a security contact without sensitive details. No response-time guarantee is offered.

Relevant boundaries include Tauri↔Python IPC, public URL/redirect validation, credentials, skill imports, untrusted HTML/Markdown and application updates. News and skill text is untrusted data and does not authorize script execution. Share only necessary diagnostics.

## تحديثات الاعتمادات / Dependency updates

تُوجّه طلبات Dependabot إلى `develop` وتُدمج آليًا فقط بعد نجاح الفحوصات المطلوبة، ثم تُحذف فروعها. التحديث الذي يفشل لا يُفرض على التطبيق. `main` محمي ويتلقى الترقية من `develop`؛ النشر الرسمي يحتاج إجراء الإصدار والتحقق من الحزمة والتوقيع.

تنبيه GLib `GHSA-wrw7-89jp-8q8g` في قفل Cargo يخص مسار GTK/Linux، ولا يدخل في شجرة بناء macOS المدعومة. لا ندّعي إصلاح GLib على Linux؛ يلزم معالجته قبل دعم تلك المنصة.

Dependabot PRs are routed to `develop` and auto-merged only after required checks pass, then their branches are removed. Failed updates are not forced through. Protected `main` accepts promotion from `develop`; official publication still requires release/package/signature validation.

The Cargo-lock GLib advisory `GHSA-wrw7-89jp-8q8g` affects the GTK/Linux dependency graph, absent from the supported macOS build graph. This is not a Linux GLib fix; address it before supporting that platform.
