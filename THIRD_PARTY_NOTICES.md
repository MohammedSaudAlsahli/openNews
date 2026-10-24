# إشعارات الأطراف الثالثة / Third-party notices

رخصة MIT في جذر المشروع تخص شفرة openNews المملوكة للمساهمين. لا تغيّر تراخيص الاعتمادات أو النماذج أو الصور والخطوط أو الأخبار أو المهارات المستوردة. راجع تراخيص المصادر الأصلية قبل إعادة توزيعها.

The root MIT license covers openNews code owned by its contributors. Dependencies, models, images/fonts, news content and imported skills keep their own terms. Check original licenses before redistributing them.

- JavaScript inventory: `desktop/package-lock.json`; dependency license information is in each original npm package.
- Rust inventory: `desktop/src-tauri/Cargo.lock`; consult each crate's license and notices.
- Python inventory: `engine/uv.lock`; the packaged runtime retains installed `*.dist-info` license metadata and CPython's license.
- Model weights are downloaded separately and are not included in the application release. Ollama model availability is not a license grant from openNews.
- Imported skills display available source/license metadata; metadata can be missing and does not replace reading the source license.
- Source articles retain their authors' rights. Local reading or attribution does not automatically permit republication.

ملفات القفل قوائم اعتماد وليست SBOM معياريًا أو تدقيق تراخيص شاملًا. / Lockfiles are dependency inventories, not a standards-compliant SBOM or a complete license audit.
