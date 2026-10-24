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

## التحديث التلقائي وسجل Swift

النشر على GitHub مستقل عن قناة Tauri الموقّعة. `desktop/scripts/package-update.py` يجهّز تحديثًا موقّعًا محليًا فقط، بمفتاح خارج المستودع. لا تُنشئ مفتاحًا بديلًا للقناة ولا تضعه في CI أو السجلات. يلزم اختبار ترقية بين نسختين مع بقاء البيانات قبل نشر feed. لم تُفعّل القناة بعد، ولا ندّعي تحديثًا تفاضليًا. لا تعدّل appcast الخاص بـSwift.

[الإجراء التاريخي لـSwift](legacy/RELEASING.md) ليس مسار الإصدار الحالي.
