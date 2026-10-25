# نشر إصدار رسمي

[English](RELEASING.en.md) · [بناء الحزمة](packaging.md)

## الأرقام والحدود

المصدر الأساسي لإصدار التطبيق هو `desktop/package.json`. يجب تطابقه مع جذري `desktop/package-lock.json` و`desktop/src-tauri/tauri.conf.json` ونسخة حزمة التطبيق في `Cargo.toml` و`Cargo.lock`. `VERSION` و`BUILD_VERSION` و`appcast.xml` تخص سجل Swift؛ لا تستخدمها لإصدار Tauri. حزمة Python لها رقم داخلي مستقل.

## خطوات النشر

1. حدّث أرقام التطبيق، `CHANGELOG.md` وملاحظات `docs/releases/v<version>.md` بالعربية والإنجليزية. لا تستخدم لاحقة preview للإصدار الرسمي.
2. راجع التغييرات والأسرار المحتملة وبيانات الاختبار. لا تنشر أدلة QA المحلية أو قواعد البيانات أو المفاتيح.
3. شغّل `bash scripts/test.sh` والبناء واختبارات Cargo. ارفع commit إلى `main` وانتظر نجاح **openNews tests and Tauri bundle** على نفس SHA.
4. أنشئ وادفع وسمًا annotated باسم `v<version>` عند SHA الذي نجح. لا تنقل وسمًا منشورًا ولا تستبدل أصول إصدار موجود.
5. شغّل workflow **Publish official Tauri release** مع الوسم ورقم CI الناجح. يتحقق من الـSHA ونوع الحدث والفرع وملف workflow، ويحمل الحزمة نفسها ثم يتحقق من بصمتها وينشر إصدارًا رسميًا، لا prerelease.
6. تحقق من الإصدار والوسم والأصول، وحمّل ZIP للتحقق من SHA-256. يتضمن `build-info.json` نسخة التطبيق وSHA ورابط CI والمنصة وحدود التوقيع.

مثال من جذر المستودع بعد نجاح CI:

```sh
git tag -a v0.3.0 -m 'openNews 0.3.0'
git push origin v0.3.0
gh workflow run release.yml -f tag=v0.3.0 -f run_id=CI_RUN_ID
```

الـZIP من CI الناجح، لا من تثبيت المستخدم. SHA-256 تحقق سلامة؛ ليست توقيع ناشر مستقلًا. CI الحالي لا يتصل بحسابات المستخدم أو يشغّل نموذجًا حيًا.

## قناة التحديث الموقّع

نشر ZIP وحده لا يحدّث التطبيق المثبت. بعد نجاح الإصدار الرسمي، جهّز حزمة التحديث من الحزمة المنشورة نفسها، بمفتاح المالك الأصلي خارج المستودع:

```sh
engine/.venv/bin/python desktop/scripts/package-update.py --version 0.3.0
engine/.venv/bin/python desktop/scripts/test-update.py --prepared build/updater/v0.3.0
```

يجب توفر اعتماد Rust المجهّز باختبارات Tauri قبل أداة QA؛ شغّل اختبارات Cargo الأصلية أولًا عند تجهيز جهاز بناء جديد. يختبر المسار نسختين فعليتين في مجلد مؤقت، ويرفض التوقيع المعدل والإصدار غير المطابق ويعيد فتح المحرك الجديد للتحقق من البيانات الاصطناعية المحفوظة.

بعد النجاح، أضف `.app.tar.gz` وتوقيعه `.sig` و`updater-SHA256SUMS` وبيانات البناء والتحقق إلى إصدار GitHub نفسه دون استبدال أصول منشورة. ثم انسخ `tauri-preview.json` الناتج إلى `updates/tauri-preview.json` وادفعه إلى `main`. **الأصول أولًا، ثم القناة.** تحقق بعد النشر:

```sh
engine/.venv/bin/python desktop/scripts/test-update.py --prepared build/updater/v0.3.0 --public
```

قناة 0.3.0 فعّالة. يبقى اسم الملف ومعرّف البيانات والمفتاح القديم للتوافق مع التطبيقات المثبتة؛ لا يعني اسم `preview` أن الإصدار تجريبي. اختُبر الانتقال الفعلي من 0.3.0-preview.1 إلى 0.3.0 مع بقاء المقالة والمحادثة ونسخ المسودة والتعليمات وملفات اعتماد ونموذج اصطناعية. لا تضع المفتاح الخاص في GitHub أو CI أو السجلات ولا تنشئ مفتاحًا بديلًا. لا ندّعي تحديثًا تفاضليًا.

توقيع Tauri يتحقق من أصالة التحديث، وهو مستقل عن توثيق Apple. قناة Swift وملف appcast التاريخي مستقلان؛ [إجراء Swift القديم](legacy/RELEASING.md) ليس مسار Tauri الحالي.
