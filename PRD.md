# وثيقة متطلبات المنتج — OpenStudio

**الإصدار:** 1.0  
**التاريخ:** 11 أكتوبر 2026  
**الحالة:** مواصفات تنفيذية لـ Codex  
**المنصة:** تطبيق macOS أصلي لمستخدم واحد، مع تصميم بيانات يقبل تعدد مساحات العمل مستقبلًا.

## 1. الملخص والقرار المعماري

OpenStudio استوديو شخصي للبحث والتخطيط والكتابة. يحلل أمثلة مصرّحًا بالوصول إليها من صناع المحتوى، يستخلص منها **تقنيات تحريرية عامة**، ويكوّن مع المستخدم هوية كتابة أصلية تسمى **Editorial DNA**. يستورد مواد مرجعية، وينتج محتوى مناسبًا لـ X وLinkedIn وفيديو YouTube الطويل وShorts وReels وTikTok، مع إدارة السلاسل والأدلة والتعديلات.

التطبيق واجهته **SwiftUI**، ويشغّل **Python مضمّنًا داخل حزمة `.app`** لتنسيق Agents وWorkflows باستخدام **Agno**. تبقى SQLite المصدر الدائم للحقيقة، ويستخدم `sqlite-vec` للبحث الدلالي عند توفر تضمين مناسب. **Jev اختياري** لقرارات التصنيف والترتيب والتقييم المحددة مسبقًا؛ تعطل Jev أو عدم توافره لا يعطل الوظائف الأساسية. **AgentOS / Agno OS** خيار لتنفيذ المحرك المحلي إذا أثبت اختبار مبكر أنه يبسّط التشغيل والرصد؛ لا يُشترط تثبيت خدمة أو Docker أو Terminal لدى المستخدم النهائي.

> **تعريف Local-first:** الملفات، قاعدة البيانات، الفهارس، وسجل القرارات تبقى على جهاز المستخدم. إرسال نص إلى مزود نموذج أو Jev أو منصة مصدر هو اتصال خارجي صريح وفق إعدادات المستخدم؛ لذا لا تعني Local-first أن توليد الذكاء الاصطناعي يعمل دون إنترنت دائمًا.

## 2. الأهداف، المقاييس، وحدود النطاق

### أهداف المنتج

1. تحويل المصادر والأمثلة إلى معرفة تحريرية قابلة للمراجعة مع إسناد واضح.
2. إنتاج مسودات أصلية تتبع تفضيلات المستخدم والمنصة بدل تقليد صانع بعينه.
3. توفير سير عمل تراكمي لا يعيد تحليل العنصر نفسه بلا تغيير أو طلب صريح.
4. إظهار سبب كل ادعاء مهم في المحتوى وحالة التحقق منه.
5. توفير تجربة إعداد مزود نموذج بسيطة، واختيار أي مزود **يدعمه Agno رسميًا في الإصدار المثبّت** ضمن قدرات النموذج الفعلية.
6. تسليم تطبيق Mac مستقل وقابل للتثبيت والتحديث والنسخ الاحتياطي.

### مؤشرات نجاح أولية، وليست ضمانات أداء نموذج

| المؤشر | معيار إطلاق MVP |
|---|---|
| تشغيل التطبيق | يفتح على Mac نظيف ضمن إصدارات macOS المدعومة دون Python/Docker/Terminal مثبتة |
| منع إعادة التحليل | استيراد المصدر نفسه مرتين دون تغيير ينتج صفر مهام تحليل جديدة |
| قابلية التتبع | 100% من التقنيات المحفوظة تربط إلى مثال أو ملاحظة مستخدم؛ 100% من الادعاءات المعروضة تربط إلى حالة دليل |
| التدخل البشري | لا تصبح قاعدة Editorial DNA دائمة من تعديل منفرد أو دون موافقة المستخدم |
| المرونة | انقطاع مزود النموذج أو Jev لا يفسد قاعدة البيانات؛ يمكن استئناف المهمة أو إعادة محاولتها |
| المزودون | اجتياز اختبارات التعاقد على OpenAI وAnthropic، واختبار تهيئة لكل مزود رسمي معلن مدعوم في سجل الإصدار |

### خارج النطاق في MVP

النشر المباشر على الشبكات، تجريف صفحات خلف تسجيل الدخول، تجاوز حدود أو سياسات API، توليد صور/فيديو/صوت نهائي، التعاون متعدد المستخدمين، التدريب أو الضبط الدقيق على نصوص صناع المحتوى، مزامنة سحابية تلقائية، وقياس أداء منشورات لا يملك المستخدم إذنًا للوصول إلى تحليلاتها.

## 3. المستخدم وسيناريوهات الاستخدام

المستخدم صانع محتوى عربي أو إنجليزي يعمل منفردًا. يحتاج إلى معرفة لماذا تنجح تقنية ما، ثم توظيفها بأسلوبه في خبر أو فكرة أو سلسلة. الاستخدامات الأساسية: إضافة أمثلة صناع محتوى، استيراد ملف أو RSS، البحث في المكتبة، بناء DNA، توليد مسودة، فحص ادعاءاتها، تحريرها، اعتمادها، وتسجيل نتائجها بعد النشر إن توفرت.

ينبغي دعم العربية من اليمين إلى اليسار في الإدخال والعرض والتصدير، مع عدم كسر النص المختلط بالأرقام والروابط والإنجليزية. لغة الواجهة الأولى العربية؛ يمكن إضافة الإنجليزية لاحقًا دون تغيير نموذج البيانات.

## 4. تجربة المستخدم ومساراتها

### بنية الواجهة

شريط جانبي: **نظرة عامة، صناع المحتوى، المكتبة، Editorial DNA، الاستوديو، السلاسل، المراجعة، الإعدادات**. تعرض كل شاشة حالة فارغة، وتقدم المهمة، والأخطاء القابلة للإصلاح. لا يبدأ تحليل أو اتصال خارجي مخفي.

### UX-01 — الإعداد الأول

1. شاشة ترحيب تشرح التخزين المحلي والاتصالات الخارجية والتكلفة المحتملة للمزود.
2. اختيار مساحة عمل أولى ولغة المحتوى الافتراضية.
3. اختيار مزود Agno من دليل المزودين المثبّت؛ تظهر حقول الاعتماد المطلوبة له فقط. إذا كان مفتاح API يكفي، تكون الخطوة الوحيدة إدخال المفتاح واختيار النموذج الافتراضي أو قبول نموذج موصى به ومتحقق منه.
4. اختبار اتصال صغير بعد موافقة المستخدم، مع رسالة واضحة إذا كان المفتاح غير صالح، أو النموذج غير متاح، أو القدرة المطلوبة غير مدعومة.
5. اختيار سياسة إرسال البيانات: كل مهمة على حدة أو سماح محفوظ لكل نوع مصدر؛ لا يرسل ملف مستورد تلقائيًا قبل الاختيار.
6. فتح مساحة العمل مع مثال تجريبي محلي اختياري.

### UX-02 — إضافة صانع وتحليل تراكمي

إضافة الاسم والمنصة ورابط الملف الشخصي أو ملف/نص يملكه المستخدم. تعرض الواجهة **وسيلة الجلب وصلاحيتها** قبل البدء. يختار المستخدم نطاقًا زمنيًا أو كمية عناصر. تظهر العناصر الجديدة والمتغيرة والمتخطاة. بعد التحليل تُعرض «بطاقات تقنية» فيها التعريف، متى تصلح، مثال قصير، المصدر، الثقة، وتعارضات محتملة. لا تُضاف التقنية إلى DNA تلقائيًا. عند غياب إذن API تعرض الواجهة بديل استيراد يدوي أو ملف مصدّر بطريقة مشروعة، ولا تعد بقراءة الحساب كاملًا.

### UX-03 — بناء Editorial DNA

تعرض الصفحة قواعد مثل الافتتاحيات والإيقاع والعمق والنبرة والمحظورات، مع أصل كل قاعدة: اختيار صريح، عدة تعديلات، أو اقتراح من تحليل. يمكن قبول/تعديل/رفض كل اقتراح. يحفظ كل تغيير كنسخة قابلة للاسترجاع. يمكن معاينة تأثير نسختين على موضوع تجريبي.

### UX-04 — إنتاج المحتوى

يختار المستخدم فكرة أو مصادر، المنصة والصيغة، اللغة، الجمهور، المدة/الطول، مستوى التوثيق، ونسخة DNA. تعرض الواجهة مخططًا مختصرًا قبل الكتابة عند المحتوى الطويل. بعد التوليد تظهر المسودة بجانب لوحة أدلة وتقييم جودة؛ يمكن تعديلها وتصديرها نصًا/Markdown. لا تصدر المسودة «جاهزة للنشر» إذا بقي ادعاء عالي الأثر بلا دليل أو عليه تعارض.

### UX-05 — السلسلة والـ Storyboard

ينشئ المستخدم Series Bible: الفرضية، الجمهور، قوس السرد، المصطلحات، المصادر، قائمة الحلقات، حقائق ثابتة، وأسئلة مفتوحة. عند كتابة حلقة يظهر ملخص الحلقات المعتمدة، تحذيرات Continuity، وCoverage. تنتج لوحة Storyboard صفوفًا زمنية مرتبطة بمقاطع السكربت: التعليق، الوصف البصري، النص على الشاشة، الأصل المطلوب، وحالة توفره. تعديلات الحلقات المعتمدة لا تُطبّق تلقائيًا على باقي السلسلة.

### UX-06 — التعلم من التعديل

بعد تحرير المسودة يعرض التطبيق فرقًا مرئيًا بين الأصل والنسخة المعدلة، ويسأل إن كان التعديل تفضيلًا دائمًا أو خاصًا بهذا النص. يستخرج المرشحات بعد تكرار نمط التعديل، ويعرض الأمثلة المؤيدة والمعارضة قبل تحديث DNA. يمكن التراجع عن أي قاعدة.

### UX-07 — غرفة الأخبار وفريق التحرير

يلصق المستخدم رابط خبر أو منشور Reddit/4chan، أو يستورد نصًا يملك حق استخدامه، ويختار «تحقق واكتب ملخصًا». تظهر شاشة تقدم الفريق: استخراج الادعاءات → البحث عن المصدر الأول → البحث عن تأكيد مستقل → فحص التاريخ والسياق → مراجعة الصور → تحرير الملخص. الناتج **بطاقة خبر** فيها: حالة التحقق، أهم النقاط بلغة عامة، ما تأكد وما لم يتأكد، روابط الأدلة، تاريخ آخر فحص، وروابط صور مرشحة. يستطيع المستخدم فتح كل دليل وتعديل الملخص واختيار صورة قبل التصدير. الخبر غير المؤكد يعرض صياغة منسوبة مثل «تداول مستخدمون ادعاءً…» ولا يُصاغ كحقيقة. لا تعني نتيجة «لا توجد تغطية في رويترز» أن الخبر كاذب.

### UX-08 — إنشاء Skills واستيرادها وربطها بفرق مخصصة

في «مكتبة Skills» يستطيع المستخدم (أ) إنشاء Skill داخل التطبيق، أو (ب) سحب مجلد Skill/ملف `SKILL.md`/حزمة ZIP، أو (ج) لصق رابط ملف أو مجلد داخل GitHub أو مستودع Git عام، أو (د) لصق صفحة Skill من دليل مثل skillsmp.com أو skills.sh. يستخرج التطبيق رابط المصدر الأصلي إن أمكن، ثم يعرض **معاينة قبل الإضافة**: الاسم، الوصف، الناشر/المستودع، الإصدار أو commit، الملفات المرافقة، السكربتات، الأدوات/الخدمات المطلوبة، وحالة التوافق مع Agno ومحرك التطبيق. يختار المستخدم «أضف»، ثم يربط Skill بوكيل أو فريق ويجربها على مثال. لمهارة مرتبطة بمستودع يظهر مفتاح واحد «حدّث تلقائيًا» مفعّل افتراضيًا؛ تظهر النسخة النشطة وتاريخ آخر فحص وزر «الرجوع إلى نسخة سابقة». لا تتطلب متابعة التحديثات Terminal أو Git مثبتًا. في «الفرق» يختار قائدًا وأعضاء من Agents الجاهزين، يحدد مهمة كل عضو وترتيب المراجعات وحدود التكلفة، ثم يجرب الفريق قبل تفعيله. رابط skills.md قد يمثل Skill مستضافة تُشغّل عن بُعد، لذلك تعرض الواجهة هذا الفرق قبل الربط ولا توهم المستخدم بأنها أُضيفت كملف محلي.

## 5. المتطلبات الوظيفية

### FR-01 — المصادر وصناع المحتوى

- موصلات منفصلة لـ X وLinkedIn وYouTube خلف واجهة `SourceConnector`، مع `capabilities()` يبيّن: metadata، نص، transcript، metrics، incremental cursor، ومصدر الصلاحية.
- الجلب الآلي فقط عبر واجهات رسمية وبصلاحيات صريحة للحساب أو البيانات العامة المتاحة حسب شروط المنصة. لا يُستخدم تسجيل دخول آلي أو تجاوز جدار دخول أو استخراج captions بطرق غير مصرح بها.
- بدائل ثابتة: لصق نص مع رابط أصلي، استيراد CSV/JSON/Markdown/TXT، أو ملف تصدير رسمي يقدمه المستخدم. تسجل طريقة الحصول على كل عنصر وحالة الإذن.
- الاحتفاظ بالنص الأصلي فقط بالقدر الذي تسمح به رخصته وإعداد المستخدم؛ يمكن الاحتفاظ بملخص وتقنيات وروابط بدل نسخة كاملة.
- مفاتيح العنصر: `(platform, external_id)` إذا توفر، وإلا URL معيارية أو بصمة محتوى مع تاريخ النشر. تحديثات العناصر تنشئ `content_version` جديدة ولا تمحو الأصل بلا سياسة احتفاظ.

### FR-02 — التحليل التراكمي والتقنيات

- خط أنابيب: جلب → توحيد → إزالة تكرار → مقارنة البصمة → تحليل جديد/متغير → استخراج تقنية → ربط دليل → دمج مرشح → مراجعة مستخدم.
- `analysis_signature = SHA256(content_hash + extractor_version + prompt_version + model_profile + schema_version)`. إذا تطابقت، تتخطى المهمة. تغيير النموذج أو القالب لا يعيد المعالجة تلقائيًا؛ يوفر إعادة تحليل مقصودة بنطاق محدد.
- تعريف التقنية مستقل عن صياغة المثال: نوع الافتتاحية، بنية الحجة، بناء التوتر، الانتقال، الإيقاع، النهاية، أو استراتيجية المنصة. لا تخزن «اكتب تمامًا مثل فلان» كتعليمات.
- الدمج يستخدم تشابهًا نصيًا/دلاليًا ثم حكمًا مفسرًا؛ التشابه لا يعني تطابقًا تلقائيًا. عند الشك تبقى بطاقتان أو تُعرض مراجعة.

### FR-03 — Editorial Brain وDNA

- أربع طبقات واضحة: `Creator Intelligence` (تقنيات مع نسبتها)، `Editorial DNA` (قواعد المستخدم المعتمدة)، `Content Memory` (نسخ المسودات والقرارات)، `Performance Intelligence` (مؤشرات أدخلها المستخدم أو استوردها بإذن).
- لا تستخدم تقنيات صانع واحد وحدها لتوليد هوية المستخدم. يجمع المحرك قواعد المستخدم الصريحة والأمثلة المعتمدة مع تقنيات عامة من عدة مصادر، ويمنع عبارات أو مقاطع متطابقة طويلًا عبر فحص تشابه قبل التصدير.
- كل قاعدة DNA تحمل حالة `suggested|approved|rejected|retired`، وتاريخًا، وأدلة، ونسخة. الاقتراح ليس قاعدة تشغيلية حتى الاعتماد.
- التعلم من تعديلات المستخدم يعتمد حدًا قابلًا للضبط (الافتراضي ثلاث وقائع مستقلة) أو موافقة صريحة على قاعدة بعد واقعة واحدة. لا يعيد التدريب الآلي على نص خاص دون إذن الإرسال.

### FR-04 — المكتبة والبحث

- استيراد RSS، URLs أخبار ومقالات يختارها المستخدم، وTXT/Markdown/PDF/EPUB للكتب المرخّص لها. يخزن عنوان المصدر والمؤلف والتاريخ والرابط والرخصة/الملكية وتاريخ الجلب.
- RSS عبر ETag/Last-Modified حين يتوفر، وإزالة تكرار canonical URL والبصمة. الصور والمرفقات لا تُنزّل افتراضيًا.
- استخلاص النص مع رقم الصفحة أو موضع المقطع. فشل الاستخلاص أو المحتوى المصور يظهر كحالة «يحتاج نصًا/إذنًا»؛ OCR مرحلة لاحقة.
- البحث النصي عبر FTS5، والدلالي عبر `sqlite-vec` إن هيئ نموذج embedding. لكل فهرس `embedding_model_id` و`dimension`؛ تغيير النموذج ينشئ فهرسًا/إعادة فهرسة صريحة ولا يخلط أبعادًا مختلفة. يعمل البحث النصي عند تعطل التضمين.
- جدول كيانات وعلاقات بسيط في V3 لبناء Content Graph، مع إحالة كل علاقة إلى مقاطع المصدر وعدم اعتبار استنتاج النموذج حقيقة.

### FR-05 — الاستوديو والصيغ

| الصيغة | المخرجات المطلوبة |
|---|---|
| X منشور | نص أساسي وبديلان، عدد أحرف محسوب، ومواضع روابط/وسوم اختيارية |
| X سلسلة | ترتيب منشورات وترابط بينها وافتتاح وخاتمة؛ حدود الطول قابلة للتكوين حسب الحساب/المنصة |
| LinkedIn | افتتاحية، متن بفقرات، خاتمة/دعوة للفعل، بدائل نبرة |
| YouTube long-form | عنوان عمل، فرضية، مخطط فصول، سكربت بمقاطع، مدة تقديرية، Evidence Map |
| Shorts / Reels / TikTok | خطاف، سكربت زمني قصير، نص على الشاشة، إيقاع وانتقالات، Storyboard أولي |

كل صيغة تستخدم `FormatSpec` قابلة لتحديث قيودها. لا تُثبّت حدود المنصات في تعليمات النموذج فقط. يعرض التطبيق تقدير المدة بناء على معدل كلام قابل للتعديل، لا يعد بطول فيديو دقيق.

### FR-06 — البحث، التحقق، والأصالة

- كل ادعاء قابل للتحقق يمثّل `Claim` بحالة: `supported|contradicted|insufficient|opinion|needs_review`، ويرتبط بمقطع مصدر وتاريخ الاطلاع ونوعه. الاستشهاد ليس دليلًا ما لم يدعم الجملة المحددة.
- فصل الوقائع عن الرأي والاستنتاج؛ تضارب مصدرين يظهر للمستخدم ولا يحسمه النموذج بصمت. الأخبار المتغيرة زمنيًا تتطلب إبراز تاريخها.
- `Fact Checking` مراجع مساعد، وليس ضمانًا للصحة. الادعاءات عالية الأثر (أرقام مالية، اتهامات، صحة، قانون) تتطلب موافقة بشرية قبل وسم المسودة جاهزة.
- فحص أصالة يقارن الناتج بالمصادر والأمثلة المخزنة لاكتشاف نسخ متصل أو شبه تطابق؛ يعرض المقطع ويطلب إعادة صياغة أو اقتباسًا منسوبًا. لا يدعي كشف الانتحال الشامل للإنترنت.

### FR-07 — السلاسل، الاستمرارية، والقصص المصورة

- `Series Bible` ونسخ الحلقات المعتمدة مرجعان منفصلان. قبل توليد حلقة تُسترجع الحقائق الثابتة، الوعد التحريري، ما قيل سابقًا، والأسئلة المؤجلة.
- `Continuity Check` ينتج تحذيرات عن تكرار غير مبرر أو تناقض أو فجوة مصطلح، مع إحالة للحلقة السابقة. لا يعدل حلقة معتمدة آليًا.
- `Storyboard` نصي منظم بزمن بداية/نهاية وتسلسل غير متداخل، مرتبط بمعرّف مقطع السكربت؛ لا يعد بتوليد وسائط في MVP/V2.

### FR-08 — التقييم وفرص المحتوى

- تقييم المسودة بمقاييس محددة: وضوح الفكرة، ملاءمة المنصة، الاتساق مع DNA، جودة الخطاف، اكتمال الأدلة، والأصالة. يعرض أسبابًا قابلة للمراجعة؛ درجات النموذج ليست تنبؤًا بمشاهدات أو نجاح.
- في V3: اقتراح فرص من RSS بعد تجميع الأحداث المتشابهة ومقارنة المكتبة وDNA. لا تُنشأ مسودة تلقائيًا ولا يُنشر شيء دون طلب المستخدم.
- في V3: استيراد تحليلات محتوى المستخدم بإذن المنصة أو يدويًا، مع فصل الارتباط الإحصائي عن السببية.

### FR-09 — Skills وفرق التحرير القابلة للتكوين

- يدعم المحرك Agno `Skills` لوكيل منفرد أو قائد `Team`؛ لا ترث أعضاء الفريق مهارة القائد تلقائيًا، بل تُربط المهارة صراحة بمن يحتاجها. توفر القوالب الأولية: «التحقق من خبر»، «فحص المصادر الأصلية»، «فحص صورة ومصدرها»، «كتابة ملخص للجمهور»، و«مراجعة الحقوق والاعتماد».
- يقبل الاستيراد من: مجلد محلي، `SKILL.md` منفرد، ZIP، رابط raw/مجلد/مستودع GitHub، ومستودع Git عام يحدد المستخدم فيه مسار Skill. يتعرف على `SKILL.md` والملفات النسبية داخل `references/` و`scripts/` وأي ملفات مساعدة معلنة. صفحة دليل SkillsMP أو skills.sh تُحل إلى مصدرها القابل للفحص عندما توفر رابط Git الأصلي؛ عند فشل الحل يطلب رابط Git/الملف مباشرة، ولا يعتمد على scraping هش كشرط عمل أساسي.
- يحفظ الأصل `source_url`, `repo_url`, `subpath`, `commit_sha` أو checksum، والرخصة إن وجدت، ونسخة محلية غير قابلة للتعديل. تنشأ نسخة منفصلة عند تخصيص Skill كي لا تضيع إمكانية المقارنة بالمصدر. لمصدر Git يتابع التطبيق `release` مستقرًا إذا كان المسار مرتبطًا بإصدار، أو الفرع المحدد عند الاستيراد؛ يسجل commit الفعلي لكل نسخة. يفحص التحديثات عند فتح التطبيق وبحد أقصى دوري معقول (الافتراضي كل 24 ساعة)، ويحترم `ETag`/حدود المعدل وأخطاء الشبكة. تنزيل نسخة جديدة يتم في staging مع تحقق بنية وملفات وتوافق وتجربة تحميل، ثم تبديل ذري عند عدم وجود Job يستخدم النسخة القديمة. تحديث النصوص/المراجع الذي لا يزيد الصلاحيات يفعّل تلقائيًا بعد اجتياز الفحص؛ إضافة سكربت/أداة/اعتماد/مضيف شبكة أو تغييرها يبقى «بانتظار مراجعتك» ولا يُفعّل بصمت. يحتفظ التطبيق بآخر ثلاث نسخ ناجحة على الأقل ويتيح استعادة أي منها بنقرة واحدة، مع خيار إيقاف التحديث التلقائي لكل Skill. يمنع تكرار الاسم من مصدرين مختلفين بلا اسم عرض أو معرّف مميز.
- يفحص المستورد وفق مواصفة `SKILL.md` المدعومة ويجرب تحميله بـ Agno `LocalSkills` مع تحقق مفعّل؛ تكون الحالة `ready`, `needs_tool`, `needs_dependency`, `remote_only`, أو `invalid`. لا يجعل نجاح تحميل النص وحده Skill صالحة للعمل إذا كانت تطلب أداة غير موجودة. يستورد الملفات المرجعية والسكربتات ضمن الحزمة، لكن تشغيل السكربت يتطلب إذنًا منفصلًا، قائمة أدوات محددة، وحدود ملفات/شبكة/وقت؛ إذا تعذرت هذه البيئة يظهر القيد بوضوح.
- `skills.md` خدمة Skills مستضافة عبر CLI/MCP بحساب وتشغيل خارجي؛ تُعامل كـ **نوع تكامل مستقل** يحتاج تسجيل دخول المستخدم وموافقته على إرسال البيانات والتكلفة لكل تشغيل. إذا قدمت الصفحة `SKILL.md` قابلًا للتنزيل، يمكن استيراد التعليمات محليًا، لكن هذا لا يضمن تشغيل مهامها المستضافة محليًا. لا يثبت التطبيق CLI عالميًا أو يسجل MCP في برامج أخرى دون فعل صريح من المستخدم.
- قوالب فرق: `NewsVerificationTeam`، `EditorialReviewTeam`، `VisualResearchTeam`. يمكن للمستخدم نسخ القالب، تغيير أدوار الأعضاء، ربط Skills، واختيار مزود/نموذج لكل عضو ضمن قدراته، ثم حفظ نسخة الفريق واختبارها. لا يسمح تعديل فريق منشور بتغيير نتيجة Job جارٍ؛ يحفظ كل Job `team_version_id`.
- يبقى ترتيب التحقق الإلزامي داخل Workflow حتميًا؛ لا يقرر قائد الفريق إسقاط فحص المصدر أو الحقوق عند صياغة خبر للعامة. المراجعات المستقلة تجمع أدلتها ثم يصدر قرار تحريري واحد، مع إمكانية التوقف عند نقص الأدلة.

### FR-10 — حزمة خبر موثقة وملخص عام

- المدخل رابط أو نص/ملف مصرح به من Reddit أو 4chan أو أي مصدر. يعامل المنشور الأول **إشارة للبحث** لا دليلًا كافيًا. يستخرج الفريق ادعاءات ذرية: من؟ ماذا؟ أين؟ متى؟ أرقام؟ صور؟ ثم يبحث عن المصدر الأصلي (بيان رسمي، وثيقة، شاهد مباشر موثق) وتأكيدات مستقلة مع سجل استعلامات وروابط وتواريخ.
- البحث في رويترز أو غيرها يتم عبر صفحات عامة أو وصول مرخّص يملكه المستخدم، وبطريقة تحترم الشروط؛ وجود تقرير مطابق يعد دليلًا بحسب مضمونه وتاريخه، وعدم وجوده ليس نفيًا. نتائج محرك البحث هي مسارات إلى الأدلة وليست أدلة بحد ذاتها. لا يعتبر اقتباس عدة مواقع لنفس المنشور «مصادر مستقلة».
- يميز قرار الخبر: `verified`, `partially_verified`, `unverified`, `contradicted`, `outdated`. يبين لكل ادعاء المصدر الأول، التأكيد المستقل، التعارض، وما يحتاج متابعة. لا يرفع الفريق الحالة إلى `verified` بتصويت Agents أو ثقة نموذج وحدها.
- ينتج `PublicNewsSummary`: عنوان محايد، خلاصة من جملتين، 3–5 نقاط رئيسية، سياق ضروري، حالة التحقق، وقت التحديث، وروابط الأدلة. كل نقطة واقعية ترتبط بمعرّفات Claims موثقة. عند نقص التحقق يجب أن تظهر نسبة الادعاء ومعلومة النقص في النص القابل للنشر، أو يمنع وسمه «جاهزًا للنشر».
- تحفظ بطاقة الخبر رابط النص الأول وتاريخ نشره ونسخة/مقتطفًا مسموحًا بها، وتربط الاقتباسات الحرفية بموضعها. يقارن المراجع الملخص بالنصوص الأصلية لتجنب قلب المعنى أو نقل جملة خارج سياقها، ويمنع نسخ فقرات طويلة من مصدر خبري في ملخص المستخدم.
- يحفظ نسخة عربية/إنجليزية عند الطلب ونسخًا ملائمة لـ X/LinkedIn ونص تعليق فيديو قصير دون حذف تحفظات التحقق. يراجع المستخدم الملخص ويعتمده قبل التصدير؛ إعادة فحص الخبر تحدث نسخة جديدة مع سجل ما تغير.

### FR-11 — البحث البصري وحقوق استخدام الصور

- يبحث `VisualResearchTeam` في Unsplash وShutterstock ومصادر صور إضافية مرخصة أو في محرك بحث كروابط اكتشاف فقط. كل بطاقة صورة تعرض: صورة معاينة مأذونًا بها، المصور/الناشر، الرابط الأصلي، التاريخ إن توفر، نوع الاستخدام (`صورة من الحدث` أو `صورة توضيحية`)، حالة الترخيص، شروط النسبة، وحالة التنزيل/الشراء.
- للصورة التي تُقدَّم على أنها **من الحدث نفسه**: يتحقق الفريق من المصدر الأول وتاريخ/مكان التصوير ووصف الناشر، ويفحص احتمال إعادة استخدام صورة قديمة أو مقتطعة. عند عدم القدرة على الإثبات تُصنف «توضيحية» ولا تُرفق كدليل على الحدث. البحث العكسي/البيانات الوصفية وسائل مساعدة وليست حكمًا نهائيًا.
- صور Unsplash تُعرض وتُختار وفق متطلبات API الحالية، بما فيها النسبة وسلوك روابط الصور/تتبع التنزيل. Shutterstock يتطلب اشتراك API وترخيصًا مناسبًا قبل استخدام الأصل داخل الفيديو؛ المعاينة أو نتيجة البحث لا تمنح حق الاستخدام. نتائج صور محرك البحث لا تُنزّل أو تُصدّر تلقائيًا لأنها لا تثبت الترخيص.
- يضيف Storyboard `asset_id` لكل مشهد، مع تعليق بصري وبديل عند غياب أصل مرخص. يمنع تصدير «قائمة أصول جاهزة للاستخدام» إذا بقي ترخيص الصورة `unknown` أو `preview_only`؛ يستطيع المستخدم إرفاق رخصته الخاصة ومراجعتها.

## 6. دعم مزودي Agno وJev وAgentOS

### 6.1 سجل المزودين وإعدادهم

المطلوب هو دعم **كل موصل نموذج رسمي في نسخة Agno المقفلة للمشروع**، لا قائمة ثابتة مخفية في SwiftUI ولا الاكتفاء بإظهار اسم الموصل. عند البناء تُستخرج مفاتيح المزودين الرسمية والمعلومات المعتمدة إلى `provider_catalog.json` بإصدار واضح؛ يحتفظ محرك Python بمصنع `ModelFactory` يربط المفتاح بمهايئ Agno الرسمي وحزمة الاعتمادات اللازمة. يتيح UI البحث عن جميع المزودين في السجل ويعرض متطلبات كل واحد وحالة جاهزيته. يجب أن يصبح كل مزود صالحًا للتشغيل بعد توفير اعتماداته ومتطلباته الرسمية؛ أي خلل معروف في مهايئ Agno نفسه يُعرض كقيد محدد بالإصدار مع اختبار فاشل موثق، ولا يُسوّق على أنه يعمل. تحديث Agno يتبعه تحديث السجل واختبارات التوافق قبل الإطلاق. لا يعني «مدعوم رسميًا» أن كل نماذج المزود تدعم الأدوات أو المخرجات المنظمة أو الصور؛ التوافق يُقاس لكل `(adapter, endpoint, model_id)`.

**مسار إدخال مفتاح فقط:** OpenAI وAnthropic وأي مزود تكفيه قيمة مفتاح مع endpoint افتراضي ونموذج معروف؛ يضبط التطبيق الباقي داخليًا. المزودون الذين يحتاجون region أو project أو deployment أو base URL أو OAuth أو خادم محلي يعرضون الحقول الضرورية بدل وعد مضلل بمفتاح وحده. لا يُجمع مفتاح مشترك لكل المزودين. اختيار نموذج مخصص مسموح مع فحص قدرة وتشغيل تجريبي.

يُستخدم `ProviderProfile` لكل مهمة: مزود/نموذج للكتابة، وآخر اختياري للتضمين، وثالث للتقييم. لا يفترض النظام أن نموذج الكتابة يقدم embeddings. عند غياب قدرة `structured_output` يستخدم استخراج JSON مع تحقق Pydantic وإعادة محاولة محدودة، ثم يطلب مراجعة. عند غياب `tool_calling` يتحول إلى Workflow بخطوات Python، أو يوضح عدم دعم المهمة. لا يغير المزود على المستخدم بصمت إذا فشل؛ يعرض الاختيار والتكلفة المحتملة قبل fallback خارجي.

### 6.2 Jev

واجهته خلف `DecisionProvider` وتستخدم فقط في `choice/score/classification/ranking` ذات الخيارات المحددة. يفضل قواعد محلية حاسمة للقرارات البسيطة. عند عدم توفر Jev أو مفتاحه أو الشبكة، يستخدم المسار البديل المحلي أو نموذج Agno المهيأ مع تحقق، ويسجل القرار ومصدره. لا يستخدم Jev لكتابة نص طويل أو إثبات صحة معلومة. إعداد Jev منفصل واختياري.

### 6.3 AgentOS / Agno OS

ينفذ Codex تجربة قصيرة في بداية MVP لمقارنة تشغيل Workflows مباشرة داخل subprocess مقابل AgentOS محلي. يُعتمد AgentOS فقط إذا وفر إدارة جلسات/مهام أو بث تقدم ملموسًا من دون زيادة متطلبات المستخدم أو تعريض API محلي غير موثق. في حالة اعتماده: يبدأه التطبيق ويوقفه مع دورة حياته، يرتبط بـ loopback فقط أو socket محلي حيث أمكن، يستخدم رمز جلسة عشوائيًا، وتُعطل واجهات docs/control plane الخارجية في نسخة الإنتاج ما لم تكن ضرورية. تبقى SQLite التحريرية خارج مخزن جلسات AgentOS ووراء Repository خاص بالتطبيق. إذا لم ينجح اختبار التغليف والأمان، تستخدم Workflows المضمّنة مع بروتوكول IPC أدناه. القرار يوثق في ADR-001 قبل إكمال MVP.

### 6.4 بوابة استيراد Skills

الاستيراد مسؤولية التطبيق، ثم ينسخ Skill المقبولة إلى مجلد مساحة العمل ويحمّلها Agno عبر `Skills(loaders=[LocalSkills(path)])`. توثيق Agno الحالي يذكر `LocalSkills` كوسيلة التحميل المتاحة من نظام الملفات، ويدعم إعادة التحميل والتحقق؛ لذلك لا يفترض المشروع وجود تحميل Git أو Marketplace أصلي داخل Agno. [توثيق Agno لتحميل Skills](https://docs.agno.com/skills/loading-skills). تفصل `SkillSourceResolver` بين الروابط الأربعة: ملف مباشر، مستودع/مسار Git، صفحة دليل تشير إلى مصدر Git، وخدمة Skills مستضافة. لا يُنسخ مشروع Git كامل إلى موضع التنفيذ إلا بعد تحديد مجلد Skill، والتحقق من الحدود والبصمات والملفات المسموحة. ينشئ التطبيق `CompatibilityReport` يبين ما يمكن تشغيله، وما يحتاج أداة/اعتمادًا/خدمة خارجية، وما لا يمكن تشغيله. إضافة Skill لا تمنحها أدوات تلقائيًا؛ الصلاحيات تأتي من سياسة التطبيق وربط المستخدم.

## 7. المعمارية وتشغيل التطبيق

```text
SwiftUI Views ↔ App State / Use Cases
                     │
          IPC Client + Job Controller
                     │ JSON Lines / Unix domain socket
                     ▼
      Python Runtime (bundled, child process)
      ├─ API/command dispatcher + Pydantic
      ├─ Agno workflows + model/provider factory
      ├─ Source connectors + Jev decision adapter
      ├─ Editorial/research services
      └─ SQLite repositories + FTS5 + sqlite-vec
                     │
      Application Support/<bundle-id>/<workspace-id>/
```

قرار التنفيذ الافتراضي: عملية Python فرعية واحدة يطلقها تطبيق Swift، عبر Unix domain socket داخل مجلد خاص بالمستخدم. لا يستقبل اتصالات من الشبكة. يحتفظ Swift بمسؤولية النوافذ، اختيار الملفات، Keychain، التنبيهات، وإدارة عمر العملية. Python مسؤول عن تحليل البيانات والتنسيق والوصول إلى SQLite. اتصال كتابة واحد أو طابور كتابة لتجنب تعارضات SQLite؛ القراءات المعزولة ممكنة مع WAL. إعادة تشغيل المحرك لا تفقد المهام لأن حالات jobs محفوظة.

## 8. نموذج البيانات والتخزين

كل جدول أعمال يحمل `workspace_id` حتى لو كان هناك مستخدم واحد. المفاتيح UUID، التواريخ UTC بصيغة ISO-8601، مع `created_at/updated_at` وقيود FK وفهارس. الملفات الكبيرة تحفظ في مخزن ملفات منظم وتخزن مسارات نسبية وبصمات في SQLite. `source_uri` ليس أمرًا للتنفيذ.

| الجدول | أهم الحقول والقيود | الغرض |
|---|---|---|
| `workspaces` | `id, name, default_language, privacy_policy` | مساحة العمل |
| `provider_profiles` | `id, provider_key, model_id, role, config_json, keychain_ref, status` | إعدادات بلا أسرار في DB |
| `creators` | `id, platform, external_ref, display_name, access_mode` | صناع المحتوى؛ UNIQUE على المنصة والمرجع |
| `sources` | `id, kind, canonical_uri, title, author, published_at, rights_status, access_method, etag, cursor` | أصل المستند أو القناة |
| `source_items` | `id, source_id, external_id, canonical_uri, content_hash, current_version_id` | عنصر قابل للتحديث؛ مفتاح فريد مناسب للمصدر |
| `item_versions` | `id, item_id, version_no, text_path, text_hash, fetched_at, provenance_json` | نسخ المحتوى |
| `chunks` | `id, item_version_id, ordinal, location_json, text, token_count` | مقاطع مع موضع |
| `analysis_runs` | `id, item_version_id, signature UNIQUE, status, extractor_version, model_profile_id, error_code` | تحليل تراكمي |
| `techniques` | `id, category, normalized_name, description, applicability, status` | أنماط عامة |
| `technique_evidence` | `technique_id, chunk_id, excerpt_start, excerpt_end, rationale` | أصل التقنية |
| `dna_rules` / `dna_versions` | `rule_id, version_id, statement, priority, status, evidence_json, approved_at` | الهوية ونسخها |
| `drafts` / `draft_versions` | `format, language, status, dna_version_id, text, parent_version_id` | الذاكرة التحريرية |
| `claims` / `claim_evidence` | `draft_version_id, span, claim_type, verdict, chunk_id, support_note` | خريطة الأدلة |
| `series` / `episodes` | `bible_json, episode_order, status, approved_version_id` | السلاسل |
| `storyboard_beats` | `episode_id, script_span, start_ms, end_ms, visual, overlay, asset_status` | المشاهد |
| `feedback_events` / `rule_candidates` | `before_version_id, after_version_id, edit_type, candidate_status` | التعلم من التحرير |
| `jobs` / `job_events` | `type, state, progress, idempotency_key, retry_count, error_code` | التعافي والتقدم |
| `entities` / `relationships` | `label, relation_type, evidence_chunk_id, confidence` | Content Graph في V3 |
| `metric_snapshots` | `draft_id, platform, metric_name, value, observed_at, access_method` | نتائج النشر المصرّح بها |
| `skills` / `skill_versions` / `skill_update_events` | `name, instructions_path, allowed_tool_ids, status, version_no, trust_level, source_kind, source_url, repo_url, subpath, commit_sha, content_sha256, license_id, compatibility_json, auto_update, track_ref, last_checked_at, etag, applied_at, update_result` | مهارات منشأة/مستوردة وسجل التحديث والرجوع |
| `teams` / `team_versions` / `team_members` | `mode, leader_id, member_id, role, skill_version_ids, model_profile_id` | تكوين فرق التحرير بنسخ ثابتة |
| `news_cases` / `news_claims` / `verification_sources` | `origin_uri, origin_platform, status, checked_at, independence_group, claim_id, evidence_span` | ملف تحقق خبر ومصادره |
| `public_summaries` | `news_case_id, version_no, headline, lead, bullets_json, caveats, approved_at` | ملخص قابل للنشر بنسخ |
| `media_assets` / `asset_licenses` | `provider, provider_asset_id, preview_uri, origin_uri, creator, event_relation, license_status, attribution, receipt_path` | صور وحقوقها وموضع استخدامها |

فهرس FTS5 على `chunks.text` مع ضبط tokenizer للعربية والإنجليزية واختبار استرجاع؛ لا يفترض أن stemming العربي مضمون. جدول `vec0` منفصل لكل إعداد embedding متوافق أو تصميم مكافئ مثبت، مع جدول ربط `chunk_id ↔ rowid`. تدير migrations نسخة schema مع نسخ احتياطي قبل ترقية مؤثرة، واختبار فتح قاعدة قديمة واسترجاعها. `sqlite-vec` ما زال قبل v1، لذا تُقفل نسخته ويُختبر تحميل الامتداد داخل التطبيق الموقّع.

## 9. عقد IPC وأخطاء التشغيل

البروتوكول `EIS-IPC/1` رسائل JSON Lines UTF-8 مع `request_id` UUID و`schema_version=1`. الحد الأقصى لحجم الرسالة 1 MiB؛ الملفات والنصوص الكبيرة تمر عبر `asset_id` لمسار داخل مساحة العمل يُفحص ولا يقبل مسارًا اعتباطيًا. كل طلب يرجع `accepted` سريعًا إذا بدأ Job ثم تبث أحداث `progress/completed/failed`. يحفظ العميل `last_event_seq` ليستعيد الأحداث بعد إعادة اتصال.

| الأمر | المدخل المختصر | المخرج |
|---|---|---|
| `runtime.health` | — | نسخة المحرك، schema، قدرات |
| `providers.catalog` | — | المزودون الرسميون المثبتون ومتطلبات الإعداد |
| `providers.validate` | `provider_profile_id` | صحة الإعداد والقدرات المكتشفة |
| `sources.add` | نوع/رابط/ملف/إذن | `source_id` |
| `sources.sync` | `source_id, scope, idempotency_key` | `job_id` |
| `analysis.run` | `item_ids, mode=incremental|explicit_rebuild` | `job_id` |
| `dna.propose` / `dna.approve` | الأدلة أو `candidate_id` | نسخة DNA |
| `library.search` | query، فلاتر، طريقة | نتائج مع المصدر والموضع |
| `drafts.generate` | `GenerationRequest` | `job_id` ثم `DraftResult` |
| `drafts.fact_check` | `draft_version_id` | Evidence Map |
| `series.plan` / `series.episode.generate` | `series_id` وسياق | خطة/Job |
| `storyboard.generate` | `draft_version_id` | beats |
| `feedback.record` | نسختان وتقييم مستخدم | مرشح قاعدة |
| `jobs.cancel` / `jobs.resume` | `job_id` | حالة محفوظة |
| `workspace.export` / `workspace.import` | نطاق ومسار اختاره Swift | Job وملف احتياطي |
| `skills.create` / `skills.test` / `skills.publish` | `SkillSpec` ونسخة مثال | مهارة محفوظة/نتيجة تجربة |
| `skills.resolve` / `skills.import` | `SkillImportRequest` من ملف/مجلد/ZIP/URL | معاينة مصدر و`CompatibilityReport` ثم نسخة محلية بعد اختيار المستخدم |
| `skills.check_update` / `skills.apply_update` / `skills.rollback` | `skill_id, version_id` | فحص المصدر، تحديث آلي أو معتمد، أو استعادة نسخة محددة |
| `teams.create` / `teams.test` / `teams.publish` | `TeamSpec` | نسخة فريق ثابتة |
| `news.verify` / `news.summarize` | رابط/مصدر أو `news_case_id` | Job ثم `NewsVerificationResult` / `PublicNewsSummary` |
| `media.search` / `media.attach` | بحث وقيود ترخيص / `asset_id, script_span_id` | صور مرشحة وسجل حقوق |

مثال طلب/حدث، لا يمثل API خارجيًا:

```json
{"schema_version":1,"request_id":"0a656c56-9010-4df4-9a77-490cbba0e8fe","command":"drafts.generate","payload":{"workspace_id":"b21860c0-7736-4f66-b4da-5e5b5398d1d9","format":"youtube_long","topic":"موضوع تجريبي","source_ids":[],"language":"ar","provider_profile_id":"cf7c7bc8-2bf0-4441-b367-2c16542465b1","dna_version_id":"a716fa2a-cf7d-4b93-8cf6-22a1c74654fa"}}
{"schema_version":1,"request_id":"0a656c56-9010-4df4-9a77-490cbba0e8fe","event":"accepted","job_id":"a2aef61a-ddac-45e4-a8ae-19aa87bb7e67"}
```

أخطاء معيارية: `AUTH_REQUIRED`, `PERMISSION_DENIED`, `RATE_LIMITED` (مع `retry_after` إن توفر), `MODEL_UNSUPPORTED`, `VALIDATION_ERROR`, `SOURCE_UNAVAILABLE`, `RIGHTS_RESTRICTED`, `NETWORK_OFFLINE`, `ENGINE_CRASHED`, `DB_MIGRATION_FAILED`. لا يضم الخطأ مفتاح API أو النص الخاص كاملًا. الإلغاء تعاوني ويحفظ ما اكتمل، والاستئناف لا يكرر عناصر تمت كتابتها بنجاح.

## 10. عقود Pydantic المرجعية

الشفرة التالية **عقد أولي**؛ تُشتق منه JSON Schema وتختبر Swift decoding. يمكن توسيع الحقول دون كسر `schema_version=1`، أما تغيير المعنى فيحتاج نسخة بروتوكول جديدة.

```python
from enum import StrEnum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Format(StrEnum):
    X_POST = "x_post"
    X_THREAD = "x_thread"
    LINKEDIN = "linkedin"
    YOUTUBE_LONG = "youtube_long"
    SHORTS = "shorts"
    REELS = "reels"
    TIKTOK = "tiktok"

class ProviderProfile(StrictModel):
    id: UUID
    provider_key: str
    model_id: str
    role: Literal["writer", "embedding", "evaluator"]
    keychain_ref: str | None = None  # مرجع فقط؛ السر في Keychain
    endpoint: HttpUrl | None = None
    region: str | None = None
    capabilities: set[str] = Field(default_factory=set)

class SourceProvenance(StrictModel):
    source_id: UUID
    item_id: UUID
    item_version_id: UUID
    access_method: Literal["official_api", "user_file", "user_paste", "rss", "licensed_url"]
    canonical_url: HttpUrl | None = None
    rights_status: Literal["owned", "licensed", "public_metadata", "unknown"]
    retrieved_at: str

class TechniqueCandidate(StrictModel):
    category: str
    name: str
    description: str
    applicability: list[str]
    evidence_chunk_ids: list[UUID] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    originality_risk: Literal["low", "review", "high"]

class GenerationRequest(StrictModel):
    workspace_id: UUID
    format: Format
    topic: str = Field(min_length=3, max_length=2000)
    source_ids: list[UUID] = Field(default_factory=list)
    language: Literal["ar", "en"]
    provider_profile_id: UUID
    dna_version_id: UUID
    target_seconds: int | None = Field(default=None, ge=10, le=7200)
    audience: str | None = None
    evidence_level: Literal["standard", "strict"] = "standard"

class ClaimEvidence(StrictModel):
    claim_text: str
    claim_type: Literal["fact", "interpretation", "opinion"]
    verdict: Literal["supported", "contradicted", "insufficient", "opinion", "needs_review"]
    source_chunk_ids: list[UUID] = Field(default_factory=list)
    rationale: str

class StoryboardBeat(StrictModel):
    script_span_id: UUID
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    voiceover: str
    visual: str
    on_screen_text: str | None = None
    asset_status: Literal["idea", "available", "needs_asset"]

class DraftResult(StrictModel):
    draft_version_id: UUID
    format: Format
    text: str
    claims: list[ClaimEvidence]
    warnings: list[str]
    ready_for_review: bool

class SkillSpec(StrictModel):
    name: str = Field(min_length=3, max_length=100)
    purpose: str
    instructions: str
    allowed_tool_ids: list[str] = Field(default_factory=list)
    output_schema_id: str | None = None

class SkillImportRequest(StrictModel):
    source_kind: Literal["local_file", "local_directory", "zip", "git", "raw_url", "directory_page", "hosted_service"]
    source_ref: str  # ملف اختاره Swift أو رابط أدخله المستخدم
    repo_subpath: str | None = None
    revision: str | None = None  # commit/tag عند توفره
    auto_update: bool = True  # يطبق فقط على مصدر ذي مرجع قابل للمتابعة

class SkillCompatibilityReport(StrictModel):
    skill_name: str
    resolved_source_url: str | None = None
    content_sha256: str
    status: Literal["ready", "needs_tool", "needs_dependency", "remote_only", "invalid"]
    required_tools: list[str] = Field(default_factory=list)
    required_dependencies: list[str] = Field(default_factory=list)
    script_paths: list[str] = Field(default_factory=list)
    requested_network_hosts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class TeamMemberSpec(StrictModel):
    agent_id: str
    role: str
    skill_version_ids: list[UUID] = Field(default_factory=list)
    model_profile_id: UUID

class TeamSpec(StrictModel):
    name: str
    mode: Literal["coordinate", "route", "broadcast", "tasks"]
    members: list[TeamMemberSpec] = Field(min_length=1)
    max_model_calls: int = Field(ge=1, le=100)

class NewsClaim(StrictModel):
    text: str
    verdict: Literal["verified", "partially_verified", "unverified", "contradicted", "outdated"]
    evidence_ids: list[UUID] = Field(default_factory=list)
    independence_groups: list[str] = Field(default_factory=list)
    caveat: str | None = None

class PublicNewsSummary(StrictModel):
    news_case_id: UUID
    headline: str
    lead: str
    bullets: list[str] = Field(min_length=3, max_length=5)
    claim_ids_by_bullet: list[list[UUID]]
    context: str | None = None
    verification_status: Literal["verified", "partially_verified", "unverified", "contradicted", "outdated"]
    caveats: list[str] = Field(default_factory=list)
    last_checked_at: str
    ready_for_publication: bool

class NewsVerificationResult(StrictModel):
    news_case_id: UUID
    claims: list[NewsClaim]
    status: Literal["verified", "partially_verified", "unverified", "contradicted", "outdated"]
    primary_source_ids: list[UUID] = Field(default_factory=list)
    independent_source_ids: list[UUID] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    checked_at: str

class MediaCandidate(StrictModel):
    provider: str
    provider_asset_id: str
    origin_url: HttpUrl
    creator: str | None = None
    event_relation: Literal["event_photo", "illustrative", "unknown"]
    license_status: Literal["licensed", "attribution_required", "preview_only", "unknown"]
    attribution: str | None = None
```

يضاف تحقق عابر للحقول: نهاية beat بعد بدايته، عدم تداخل المقاطع، إلزام `target_seconds` للفيديو القصير/الطويل، وإلزام دليل أو `needs_review` لكل ادعاء واقعي. يجب مساواة طول `claim_ids_by_bullet` بعدد `bullets`، وأن يعود كل claim إلى الملف نفسه، وأن يحتوي الملخص غير المؤكد على تحفظ ظاهر. لا تُستخدم قيمة `confidence` وحدها لقبول حقيقة أو تقنية.

## 11. Workflows وAgents

كل Workflow محدد المدخلات والمخرجات، idempotency، والآثار الجانبية. يستخدم Agno لتنسيق الخطوات ذات القيمة، وتبقى عمليات الملفات وSQL وقيود القبول في كود حتمي. أوصاف Agents لا تمنحها صلاحية إنترنت أو قاعدة بيانات عامة؛ تحصل على أدوات مقيدة بالنطاق.

| Workflow | الخطوات | نقطة موافقة المستخدم |
|---|---|---|
| `CreatorIngest` | إذن/جلب → Normalize → Dedup → Chunk → Extract → Evidence → Merge proposals | قبل الجلب الخارجي، وقبل اعتماد قاعدة DNA |
| `LibraryIngest` | اختيار ملف/Feed → حقوق → استخراج → Metadata → Chunk → FTS/Embedding | قبل إرسال نص إلى مزود خارجي |
| `GenerateContent` | Brief → Retrieval → Outline → Narrative choice → Draft → Claims → Review → Originality | قبل تصدير «جاهز للنشر» عند التحذيرات |
| `SeriesPlan` | موضوع → خريطة مصادر → Bible → حلقات → تغطية | اعتماد Bible وخطة الحلقات |
| `EpisodeDraft` | Bible/Continuity → Outline → Draft → Fact Check → Storyboard | اعتماد الحلقة وتثبيتها |
| `FeedbackLearn` | Diff → تصنيف تعديل → تجميع وقائع → اقتراح DNA | قبول/رفض قاعدة جديدة |
| `OpportunityScan` (V3) | RSS → Dedup/Event clusters → Relevance → Ideas مع أدلة | اختيار فكرة للتنفيذ |
| `NewsVerification` | إشارة أولية → تفكيك ادعاءات → بحث عن المصدر الأول → بحث مستقل → تحقق زمني/بصري → قرار مدعوم → ملخص عام | قبل وسم الخبر جاهزًا وقبل تصدير الملخص |
| `VisualAssetSearch` | استخراج احتياج المشهد → بحث مرخص → فحص صلة الصورة بالحدث → مراجعة الحقوق → إلحاق Storyboard | قبل شراء/تنزيل أو اعتماد الصورة |

وكلاء Agno المقترحون: `SourceAnalyst`, `TechniqueExtractor`, `Researcher`, `NarrativePlanner`, `Writer`, `FactReviewer`, `ContinuityReviewer`, `EditorialEvaluator`. ليست هناك حاجة لثماني مكالمات نموذج لكل طلب؛ يدمج Codex الخطوات عندما يقل وقت الانتظار والتكلفة مع الحفاظ على عقود المخرجات. دور Jev اختياري عند قرار محدد قابل للتقييم. تسجل نسخة التعليمات والنموذج والتكلفة التقريبية ومدة التنفيذ لكل run دون حفظ سلسلة تفكير خاصة.

لفريق الأخبار يضاف `ClaimExtractor` و`PrimarySourceResearcher` و`IndependentCorroborator` و`ImageProvenanceReviewer` و`RightsReviewer` و`PublicSummaryEditor`. الفريق في Agno يوزع الأدوار، أما Workflow فيفرض بوابات التحقق والتصدير. لا يكفي اتفاق عدة Agents مدعومة بالنموذج نفسه لإثبات خبر؛ الاستقلالية تخص **المصادر الخارجية**. ترتبط Skills المتخصصة بالأعضاء المعنيين، وتسجل نسخها المستخدمة في كل نتيجة. [Skills الفرق في Agno](https://docs.agno.com/skills/team-skills)، [طرق تنسيق الفرق](https://docs.agno.com/teams/delegation)، [Workflows](https://docs.agno.com/workflows/overview).

## 12. الأمن والخصوصية والحقوق

- مفاتيح API وOAuth tokens في macOS Keychain؛ SQLite تحتفظ بمراجع فقط. لا تظهر الأسرار في السجلات أو IPC أو ملفات التصدير. تدوير/حذف المفاتيح من الإعدادات.
- ملفات مساحة العمل ضمن `Application Support` بصلاحيات المستخدم، وقاعدة البيانات بنسخ احتياطي مشفر اختياريًا بكلمة مرور يختارها المستخدم. لا تُرفع نسخ احتياطية تلقائيًا.
- الاتصال بمزود خارجي يتطلب إظهار نوع البيانات المُرسلة والمزود. تحترم إعدادات الامتناع عن إرسال الكتب/النصوص الخاصة، مع تنقيح المقاطع غير اللازمة قبل الطلب.
- التحقق من URLs لحماية `SSRF`: `https` حيث يلزم، منع شبكات خاصة/محلية في الاستيراد عبر URL، حد حجم/مهلة، وحد تحويلات. ملفات PDF/EPUB تعامل كمدخلات غير موثوقة وتخضع لحد حجم وفك ضغط.
- النص المستورد غير موثوق كتعليمات؛ يفصل عن system/developer prompts ولا يستطيع استدعاء أدوات أو تغيير سياسات التطبيق. لا تنفذ شيفرة أو روابط من داخل المصدر.
- حذف مصدر يتيح حذف النص، المقاطع، embeddings، وعلاقاته، مع قرار منفصل بشأن بقاء التقنيات المشتقة المجهولة المصدر؛ لا يُترك دليل يتيم. تصدير البيانات وحذف مساحة العمل من UI.
- سياسات API وحقوق النشر لكل منصة تُراجع عند التنفيذ وعند تحديث الموصل؛ لا يُبنى الاعتماد على scraping أو حسابات بديلة أو تجاوز rate limits. يحفظ مصدر ووقت وطريقة الحصول على كل مثال.
- بيانات التحليلات مقتصرة على حسابات المستخدم أو ملفات يملك حق استيرادها. لا تُرسل بيانات تشخيصية خارجية إلا بموافقة صريحة.
- Reddit و4chan مصادر إشارة عالية المخاطر للتضليل وليسا دليلين كافيين للنشر. يمنع استخدام بيانات Reddit لتدريب نموذج أو تحويلها إلى ذاكرة تعليمية دائمة دون ترخيص مناسب، وتطبق شروط API والاستبقاء والحذف؛ عند غياب الحق المناسب تُستخدم روابط/ملخصات أدلة مأذون بها بدل استيراد النص إلى مزود نموذج. لا يظهر ادعاء مجهول المصدر كحقيقة عن شخص دون تحقق ومراجعة بشرية.
- Skill من صنع المستخدم لا يستطيع توسيع صلاحيات الأدوات أو قراءة Keychain أو تنفيذ سكربتات بمجرد كتابة تعليمات. يحدد `allowed_tool_ids` وميزانية اتصال/تكلفة لكل فريق، وتعرض أي عملية شراء أصل بصري للمستخدم قبل إتمامها.
- استيراد Skills من Git/ZIP يطبق حدود حجم وعدد ملفات، منع path traversal والروابط الرمزية التي تخرج من الحزمة، رفض الملفات التنفيذية غير المعلنة، وتثبيت commit أو checksum. تعالج مراجع Skill وتعليماتها كمحتوى غير موثوق قبل إتاحتها للوكلاء. يقتصر تشغيل السكربتات المصرح بها على عملية معزولة دون وصول افتراضي إلى مفاتيح المستخدم أو قاعدة البيانات أو الشبكة؛ يعتمد Codex آلية عزل قابلة للاختبار على macOS قبل تفعيل هذا المسار.
- يحدث التطبيق Skills من المصدر المسجل فقط عبر HTTPS/بصمة commit مع حدود حجم ووقت؛ لا تتبع روابط تنزيل عشوائية داخل `SKILL.md`. فشل الفحص أو انقطاع الشبكة يترك النسخة الحالية فعالة. الرجوع نسخة محلية لا يتطلب الشبكة، ويمنع تطبيق التحديث نفسه مجددًا تلقائيًا حتى يظهر إصدار أحدث أو يختار المستخدم إعادة المحاولة.

## 13. حدود التكامل والمخاطر

| الخطر | القرار التنفيذي |
|---|---|
| تغير أسعار/حصص/صلاحيات X | موصل بقدرات مكتشفة، backoff واحترام 429، استيراد يدوي واضح؛ لا يعتمد MVP على حصول ترخيص مدفوع |
| تقييد قراءة منشورات LinkedIn | قراءة الأعضاء قد تتطلب موافقة خاصة؛ دعم حساب المستخدم أو المؤسسة المصرح بها والملفات التي يقدمها المستخدم، مع تعطيل الجلب غير المتاح |
| YouTube captions | بيانات الفيديو العامة لا تعني حق تنزيل captions لغير المالك؛ الاعتماد على نص يقدمه المستخدم أو نص مرخص عندما لا تتوفر الصلاحية |
| اختلاف مزودي Agno | catalog مبني من النسخة المثبتة + اختبارات تهيئة وقدرات؛ مسار fallback معلن لا تبديل خفي |
| Jev وصول مبكر/خدمة سحابية | feature flag، client مع timeout، fallback، ولا تبعية للإطلاق |
| `sqlite-vec` قبل v1 | pin للنسخة، اختبار extension داخل حزمة موقعة، migrations واختبار إعادة فهرسة |
| اختلاف جودة اللغة العربية | مجموعة تقييم عربية، مراجعة بشرية، توضيح حدود التحقق الدلالي والبحث |
| هلوسة المصادر أو تقليد نصوص | Evidence Map، عرض المقتطف الأصلي، فحص تشابه، منع اعتماد غير موثق |
| توقيع Python والامتدادات | build مبكر على جهاز نظيف ثم توقيع كل binary/extension داخل bundle قبل notarization |
| Reddit و4chan | قراءة عبر وصول مشروع فقط؛ محتوى المستخدمين قد يختفي أو يتغير، وتمنع شروط Reddit استخدامات AI غير المصرح بها؛ لا اعتماد خبري على منشور منفرد |
| Reuters ومحركات البحث | نتيجة البحث أو غيابها لا تثبت أو تنفي الخبر؛ حفظ روابط التقرير/الوثيقة الفعلية، واستخدام المحتوى المرخص وفق حق الوصول |
| Unsplash/Shutterstock | شروط عرض/نسبة/تنزيل أو شراء تختلف؛ فصل معاينة الصورة عن حق إدراجها في الفيديو وحفظ إثبات الترخيص |
| فرق وSkills مخصصة | تعليمات الطرف الثالث قد تحاول تجاوز بوابات التحقق أو استدعاء أدوات؛ الصلاحيات تفرض برمجيًا لا بالنص |
| أدلة Skills وخدماتها | SkillsMP وskills.sh فهارس وروابط لمصادر مختلفة؛ skills.md يوفر تشغيلًا مستضافًا؛ لا يفترض تساوي الاستيراد المحلي والتشغيل البعيد أو توافق أي Skill مع أدوات التطبيق |

الوثائق الرسمية الحالية التي يراجعها Codex قبل تكامل كل موصل: [مزودو Agno](https://docs.agno.com/models/providers/model-index)، [توافق النماذج](https://docs.agno.com/models/compatibility)، [تحميل Skills](https://docs.agno.com/skills/loading-skills)، [Skills الفرق](https://docs.agno.com/skills/team-skills)، [Workflows](https://docs.agno.com/workflows/overview)، [AgentOS Studio](https://docs.agno.com/agent-os/studio/introduction)، [X API](https://docs.x.com/x-api)، [LinkedIn Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api)، [YouTube captions.download](https://developers.google.com/youtube/v3/docs/captions/download)، [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms)، [4chan API](https://github.com/4chan/4chan-API)، [Unsplash API](https://unsplash.com/documentation)، [Shutterstock API](https://api-reference.shutterstock.com/)، [Reuters Connect licensing](https://www.reutersconnect.com/transactional-license-terms/)، [sqlite-vec](https://github.com/asg017/sqlite-vec)، [Jev API](https://api.typesafe.ai/redoc)، و[توثيق Apple للتوقيع والتوثيق](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution). ولأن أدلة Skills ليست موصلًا واحدًا، يراجع كذلك [SkillsMP](https://skillsmp.com/)، [skills.sh](https://skills.sh/)، و[skills.md](https://skills.md/) عند تنفيذ محلل الروابط. هذه الروابط مرجعية؛ تُثبت الإصدارات والمتطلبات الفعلية في ADR وسجل تبعيات المشروع وقت التنفيذ.

## 14. مراحل التسليم

### MVP — أساس قابل للاستخدام

SwiftUI والإعداد والمزودون وKeychain، محرك Python مضمّن وIPC، SQLite/migrations، استيراد يدوي وأمثلة صناع من وسائل مصرّح بها، تحليل تراكمي، مكتبة تقنيات، DNA بموافقة، توليد X/LinkedIn وفيديو قصير ومسودة YouTube طويلة، حفظ نسخ وتصدير، فحص ادعاءات أولي، Feedback Loop مرشح. يضاف **فريق تحرير جاهز** يفكك ادعاءات خبر يقدمه المستخدم، يبحث عن أدلة مستقلة، ويصدر بطاقة تحقق وملخصًا عامًا مع تحفظات؛ البحث البصري في MVP يقتصر على روابط مرشحة وحالة حقوق واضحة. يتم إثبات build مستقل وموقّع تجريبي مبكرًا. Jev اختيارية؛ تجربة AgentOS تُحسم بقرار ADR.

### V2 — بحث وسلاسل

RSS/ملفات كتب وأخبار، FTS5 و`sqlite-vec`، بحث واسترجاع موثق، Series Bible، Continuity، Storyboard نصي، Fact Checking أعمق، توليد جميع الصيغ المذكورة، لوحة مراجعة الأدلة، اختبار استيراد/تصدير ونسخ احتياطي. تضاف واجهة إنشاء واستيراد Skills من ملف/ZIP/GitHub/Git وصفحات أدلة Skills، مع **تحديث تلقائي ونسخ محلية قابلة للرجوع** للمستودعات، وإنشاء فرق مخصصة. تضاف موصلات Unsplash/Shutterstock حيث تسمح الصلاحيات، وفحص أصل الصور وربط الأصول المرخصة بالـ Storyboard. يمكن استخدام AgentOS Studio كواجهة متقدمة إذا نجحت تجربة تشغيله محليًا وتغليفه؛ الواجهة الأصلية تبقى المسار الأساسي للمستخدم.

### V3 — ذكاء الفرص والقياس

Content Graph، Opportunity Engine، تحليلات أداء مأذون بها، مقارنة نسخ DNA، مجموعة تقييم ومراقبة انحراف الجودة، تحسين قرارات Jev بعد قياسها، وموصلات إضافية تسمح بها الصلاحيات.

لا ينقل بند من مرحلة إلى أخرى بلا تحديث معيار القبول. وجود واجهة شكلية لميزة لا يعني اكتمالها.

## 15. معايير قبول قابلة للاختبار

| ID | سيناريو الاختبار | النتيجة المطلوبة |
|---|---|---|
| AC-01 | تثبيت `.app` على Mac نظيف مدعوم وفتحها | تعمل دون Python/Docker/Terminal، والمحرك يبدأ/يتوقف مع التطبيق |
| AC-02 | اختيار OpenAI ثم Anthropic وإدخال مفتاح صحيح فقط حيث يكفي | يتم اختبار الاتصال، اختيار نموذج متاح، وتوليد مسودة؛ الأسرار لا تظهر في DB/log |
| AC-03 | فحص دليل مزودي نسخة Agno المقفلة، مع اختبار تهيئة لكل مهايئ وبيئة اعتماد اختبار حيث تتاح | يظهر كل مزود رسمي في UI بحالة ومتطلبات صحيحة؛ يعمل بعد استيفاء متطلباته أو يُوثق خلل upstream محدد؛ المزود غير الجاهز يشرح السبب ولا يختفي |
| AC-04 | اختيار مزود يحتاج region/endpoint أو نموذج بلا structured output | تظهر الحقول/القيود، وتعمل استراتيجية تحقق أو رسالة عدم دعم واضحة |
| AC-05 | استيراد 20 عنصرًا ثم إعادة الاستيراد بلا تغيير | لا يزيد عدد `analysis_runs` المكتملة ولا تتكرر التقنيات/العناصر |
| AC-06 | تعديل عنصر واحد من العشرين | يعاد تحليل نسخة ذلك العنصر فقط، مع بقاء الأثر القديم قابلًا للتتبع |
| AC-07 | منع إذن LinkedIn/YouTube أو نفاد quota | يُعرض `PERMISSION_DENIED`/`RATE_LIMITED` مع بديل يدوي، ولا يحاول الالتفاف على المنصة |
| AC-08 | اقتراح تقنية من مثال صانع | بطاقة التقنية تحوي مصدرًا ومقطعًا ووصفًا عامًا؛ لا تُفعّل في DNA تلقائيًا |
| AC-09 | توليد نص بموضوع له مصدران متعارضان | تظهر حالة تضارب/مراجعة والمواضع؛ لا يُوسم جاهزًا دون قرار بشري |
| AC-10 | تحرير افتتاحية مرة واحدة ثم ثلاث مرات مستقلة | لا يعتمد DNA تلقائيًا؛ بعد التكرار يظهر اقتراح مع الوقائع ويحتاج قبولًا |
| AC-11 | إنشاء سلسلة من ثلاث حلقات واعتماد الأولى ثم طلب الثانية | تحترم الثانية Bible وما ثبت بالأولى؛ تحذير عند تناقض متعمد في المدخل |
| AC-12 | توليد Storyboard لفيديو قصير | beats مرتبة غير متداخلة، مرتبطة بمقاطع السكربت وقابلة للتحرير |
| AC-13 | قطع الشبكة أثناء توليد أو تعطيل Jev | حالة خطأ قابلة لإعادة المحاولة؛ لا فساد DB، ولا حاجة Jev لإكمال مسار أساسي |
| AC-14 | تغيير embedding model إلى بعد مختلف | لا يختلط الفهرسان؛ تبدأ إعادة فهرسة صريحة ويبقى FTS يعمل |
| AC-15 | تصدير مساحة عمل ثم استيرادها في نسخة جديدة | تستعاد المصادر وDNA والمسودات والعلاقات والأدلة دون مفاتيح API |
| AC-16 | محاولة تمرير تعليمات ضارة داخل خبر أو PDF | لا تغير إعداد المزود ولا تستدعي أداة غير مصرح بها؛ تعامل كنص مصدر |
| AC-17 | بناء Release بتوقيع Developer ID وتوثيق Apple | `codesign --verify` و`spctl` وفحص notarization ينجحون على الحزمة النهائية |
| AC-18 | إدخال منشور Reddit أو 4chan يدعي وقوع حدث بلا مصدر مستقل | تصنف بطاقة الخبر `unverified`، ويحافظ الملخص على نسبة الادعاء، ولا يظهر زر «جاهز للنشر» كخبر مؤكد |
| AC-19 | إدخال خبر تدعمه وثيقة أصلية وتقرير مستقل، وآخر تنقل فيه المواقع منشورًا واحدًا | الأول يعرض أدلة موضعية ويمكن مراجعته للاعتماد؛ الثاني لا يحسب تعدد الروابط تأكيدًا مستقلًا |
| AC-20 | توليد ملخص خبر ثم تغيير حكم أحد ادعاءاته إلى `contradicted` | تتحدث النقطة المرتبطة والتحفظ وحالة الجاهزية؛ عدد نقاط الملخص 3–5 وكل نقطة مرتبطة بمعرّفات Claims |
| AC-21 | البحث عن صورة «من الحدث» ثم العثور على صورة قديمة مشابهة | تصنف `illustrative` أو `unknown` مع سبب وتحذير، ولا تُعرض كدليل مصور على الحدث |
| AC-22 | اختيار معاينة Shutterstock أو نتيجة صور عامة بلا رخصة | لا تسمح قائمة الأصول الجاهزة بإدراجها في الفيديو حتى يسجل ترخيص صالح؛ حفظ اسم الناشر ورابط الأصل والنسبة |
| AC-23 | إنشاء Skill وفريق ثم تعديلهما أثناء تشغيل Job | يستخدم Job النسخ التي بدأ بها؛ Skill لا ينفذ سكربتًا ولا يصل إلى أداة غير مسموحة؛ يمكن الرجوع لنسخة سابقة |
| AC-24 | استيراد `SKILL.md` من ملف، مجلد، ZIP، GitHub subpath، ورابط من skillsmp.com/skills.sh | تظهر معاينة المصدر والملفات والتوافق؛ تُحمّل النسخة الصالحة محليًا عبر Agno وتُربط بعضو فريق؛ الرابط غير القابل للحل يطلب المصدر الأصلي |
| AC-25 | تحديث commit في مستودع Skill نصية أثناء فتح التطبيق | في الفحص الدوري تُحمّل نسخة جديدة وتُختبر ثم تُفعّل دون تدخل؛ يحتفظ التطبيق بمعرّف commit القديم ولا يغيّر Job جارٍ |
| AC-26 | تحديث يضيف سكربتًا/أداة أو يفشل التحقق | تبقى النسخة السابقة فعالة، ويظهر طلب مراجعة أو سبب الفشل؛ لا تزداد الصلاحيات تلقائيًا |
| AC-27 | تفعيل نسخة سيئة ثم الضغط على «الرجوع إلى نسخة سابقة» دون شبكة | تستعيد Skill والفريق النسخة المحددة، ويبقى سجل التحديث محفوظًا ولا يُعاد تفعيل النسخة السيئة في الفحص التالي |

اختبارات الجودة غير الحتمية: مجموعة تقييم لا تقل عن 30 حالة عربية/إنجليزية تشمل خبرًا متغيرًا، مادة اقتصادية، ادعاءً متنازعًا، وسلسلة. تُقيّم يدويًا بعينة عمياء على الأصالة، صحة الإسناد، وملاءمة المنصة. لا يعلن تحسن النموذج من درجة LLM وحدها. يحتفظ المشروع ببيانات اختبار اصطناعية أو مرخصة فقط.

## 16. متطلبات غير وظيفية

- macOS minimum target يحدد بعد تجربة التغليف، مع دعم Apple Silicon أولًا وتوثيق حالة Intel بوضوح. لا يوعد Universal Binary قبل نجاح اختبار مستقل لكل معمارية.
- واجهة لا تتجمد مع أي مهمة طويلة؛ التقدم والإلغاء واستئناف المهمة متاح. بدء الواجهة دون شبكة أو مفاتيح API يظل ممكنًا لقراءة البيانات المحلية.
- أهداف أداء مرجعية على جهاز اختبار محدد يوثق لاحقًا: فتح المكتبة المحلية في أقل من ثانيتين لـ 10 آلاف عنصر، واستجابة البحث النصي في أقل من ثانية في 95% من الاستعلامات. زمن النموذج الخارجي خارج هذا الهدف ويعرض تقدمًا.
- حدود قابلة للإعداد لحجم الملفات، عدد العناصر في مزامنة واحدة، كلفة/عدد استدعاءات النموذج لكل مهمة، ومهلة الاتصال. توقف المهمة قبل تجاوز ميزانية المستخدم.
- سجل تشخيص محلي قابل للتصدير بعد تنقيح الأسرار والنصوص الخاصة؛ يتضمن correlation IDs وأكواد أخطاء ومراحل التشغيل.
- دعم VoiceOver ولوحة المفاتيح وتباين النص واتجاه العربية. قابلية التراجع عن اعتماد قاعدة أو حذف مصدر.

## 17. هيكل المستودع المقترح

```text
OpenStudio/
├── PRD.md
├── README.md
├── docs/
│   ├── architecture.md
│   ├── privacy.md
│   ├── providers.md
│   ├── packaging.md
│   └── adr/ADR-001-runtime.md
├── macos/
│   ├── OpenStudio.xcodeproj/
│   ├── App/                 # SwiftUI, app lifecycle, Keychain
│   ├── Features/            # Creators, Library, DNA, Studio, Series
│   ├── IPC/                 # Codable contracts and job stream
│   └── Resources/
├── engine/
│   ├── pyproject.toml
│   ├── eis_engine/
│   │   ├── ipc/             # dispatcher, Pydantic schemas
│   │   ├── providers/       # Agno catalog/factory, Jev adapter
│   │   ├── connectors/      # X, LinkedIn, YouTube, RSS, files
│   │   ├── news/            # claims, verification, public summaries
│   │   ├── media/           # search, provenance, licensing
│   │   ├── skills/          # versioned editorial skill packages
│   │   │   ├── sources/     # local, Git, directory-page, hosted resolvers
│   │   │   └── updates/     # staging, compatibility, history, rollback
│   │   ├── teams/           # registered teams and user configs
│   │   ├── workflows/       # Agno orchestration
│   │   ├── editorial/       # analysis, DNA, feedback, claims
│   │   ├── storage/         # SQLite repos, migrations, vectors
│   │   └── security/
│   └── tests/
├── schemas/                 # JSON Schema generated from Pydantic
├── fixtures/                # licensed/synthetic test material
├── scripts/                 # build, sign, notarize, verify
└── .github/workflows/       # CI tests and release gates
```

## 18. Packaging والتوقيع والتوثيق

1. أقفل إصدارات Swift tools/Xcode وPython وAgno وPydantic و`sqlite-vec` وكل wheel وموصل في lockfile مع تراخيصها وملف SBOM.
2. ابنِ runtime Python لـ macOS والمعمارية المستهدفة داخل `Contents/Resources/engine` أو `Contents/Frameworks` وفق متطلبات التوقيع؛ امنع تنزيل حزم Python عند تشغيل المستخدم. يضمّن التطبيق فقط الاعتمادات اللازمة للمزودين المعلنين في catalog؛ اختبار build يثبت أن كل موصل مدرج قابل للاستيراد.
3. وقع من الداخل إلى الخارج جميع ملفات Mach-O وامتدادات `.so` وframeworks ثم `.app` بشهادة Developer ID وHardened Runtime، مع entitlements بالحد الأدنى. لا تعتمد على توقيع عميق عشوائي لإصلاح أخطاء الحزمة.
4. أنشئ `.dmg`، قدمه إلى Apple notarization، ثبت ticket، وافحص Gatekeeper على جهاز/مستخدم نظيف. لا تُعرض النسخة للمستخدم على أنها جاهزة إذا فشل أي gate.
5. وثق تحديث النسخ، migration، rollback، الحذف الكامل، ورخص المصادر المفتوحة. توقيع release يحتاج حساب Apple وشهادة وصلاحيات المطور؛ CI يحتفظ بالأسرار في مخزن آمن.

## 19. تعليمات تنفيذ مباشرة لـ Codex

1. ابدأ بفحص بيئة macOS/Xcode الحالية وأنشئ المستودع وفق الهيكل. ضع قرارات الإصدارات الفعلية والقيود في `docs/architecture.md` وADR-001. لا تخمن API منصة قبل مراجعة وثائقها الرسمية عند التنفيذ.
2. أنشئ spike قابلًا للتشغيل خلال البداية: SwiftUI يطلق Python مضمّنًا، طلب `runtime.health`، تحميل SQLite و`sqlite-vec`، وتوقيع تجريبي. قارن AgentOS بالـ IPC المباشر، ثم احسم أحدهما في ADR. **أولوية هذا المسار أعلى من بناء شاشات كثيرة** لأنه يثبت استقلالية التطبيق.
3. نفذ vertical slice: استيراد نص يدوي → تحليل تراكمي → بطاقة تقنية بدليل → اعتماد DNA → توليد مسودة X → حفظ/تصدير. اجتز AC-01 وAC-05 وAC-08 قبل توسيع الموصلات.
4. أضف مصنع Agno ودليل المزودين تلقائيًا مع OpenAI وAnthropic كاختبارين تعاقديين، ثم غطِّ بقية مفاتيح النسخة المثبتة باختبار تهيئة يحدد الجاهزية والمتطلبات. لا تجعل اختيار OpenAI شرطًا لأي مسار عام.
5. نفذ موصلات المنصات خلف قدرات وصلاحيات وفشل واضح؛ اعتمد الاستيراد اليدوي الدائم عند غياب وصول رسمي. نفذ الحقول والمخططات وmigrations أولًا، ثم workflows، ثم الواجهة.
6. أدخل Jev خلف feature flag بعد وجود مجموعة تقييم تقارن جودة القرار والتكلفة والمهلة بالمسار البديل. لا تجعل Jev تبعية للدقة أو الإطلاق.
7. لكل ميزة: اكتب اختبار عقد/تكامل ذي معنى للبيانات وIPC، واختبار UI للمسار الرئيسي، ثم اعرض دليل نجاح معيار القبول المعني. استخدم fixtures اصطناعية أو مرخصة، ولا تضع مفاتيح أو نصوص خاصة في المستودع.
8. سلم في نهاية كل مرحلة: تطبيقًا قابلًا للتجربة، README للتشغيل والتغليف، سجل قيود معروف، نتائج اختبارات AC، ونسخة محدثة من هذه الوثيقة إذا تغيّر القرار. لا تعتبر المهمة منتهية بمجرد نجاح build التطويري؛ اختبر الحزمة المستقلة والتوقيع والتوثيق.
9. نفذ `NewsVerificationTeam` كقالب جاهز داخل Workflow له بوابات تحقق ثابتة. اربط كل نقطة في ملخص الجمهور بملف Claim وأدلة قابلة للفتح. اختبر مثال خبر صحيح وآخر مضلل وصورة قديمة قبل إعلان الميزة. بعد ذلك افتح إنشاء Skills والفرق للمستخدم وفق صلاحيات الأدوات والنسخ.
10. افصل محرك اكتشاف الصور عن ترخيصها: التكامل مع Unsplash/Shutterstock لا يعني أن كل نتيجة قابلة للإدراج. سجّل متطلبات API وحقوق الاستخدام الحالية، وأثبت في الاختبارات أن المعاينة/النتيجة العامة لا تمر إلى تصدير أصول الفيديو دون حق واضح.
11. نفذ استيراد Skills من ملف ومجلد وZIP ثم Git/صفحات الأدلة عبر `SkillSourceResolver` واحد. ثبّت كل نسخة بـ commit/checksum، واختبر تحميلها في Agno. أضف فحص تحديث منخفض التواتر وstaging وتبديلًا ذريًا وrollback محليًا؛ أثبت AC-24 إلى AC-27 قبل تفعيل التحديث التلقائي افتراضيًا. للمستودعات العامة لا تشترط Git أو CLI مثبتًا عند المستخدم. رابط skills.md المستضاف يسلك مسار تكامل منفصل إن أضيف، مع إظهار الحساب والكلفة وحركة البيانات.

## 20. قرارات تحتاج حسمًا أثناء التنفيذ

هذه ليست عوائق للبدء: (أ) أقل إصدار macOS ومعمارية Intel بعد اختبار الحزمة؛ (ب) موصلات المنصات التي تتوفر لها صلاحيات مستخدم حقيقية؛ (ج) نموذج embedding الافتراضي وسياسة تكلفة استدعائه؛ (د) اعتماد AgentOS أو IPC المباشر بناء على spike؛ (هـ) مزود التوليد الافتراضي إن لم يحدد المستخدم. يوثق كل قرار وتاريخه وبديله وأثره في ADR، وتبقى واجهة التطبيق صادقة بشأن القيود.
