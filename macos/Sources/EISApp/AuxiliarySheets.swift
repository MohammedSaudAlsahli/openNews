import SwiftUI
import AppKit
import UniformTypeIdentifiers

struct ImportSourceSheet: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    let onImported: (String) -> Void
    @State private var title = ""
    @State private var text = ""
    @State private var author = ""
    @State private var uri = ""
    @State private var rights = "unknown"
    @State private var purpose = "style"
    @State private var accessMethod = "user_paste"
    @State private var saving = false
    @State private var error: String?
    private var valid: Bool {
        !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && title.count <= 300 &&
        !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && text.count <= 120000 &&
        author.count <= 200 && uri.count <= 2000 && (purpose != "style" || rights != "unknown")
    }
    var body: some View {
        let _ = interfaceLanguage
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 6) {
                Text(L("إضافة نص")).font(.title2.bold())
                Text(L("ارفع مثالًا من كتابتك لتعلّم أسلوبك، أو نصًا مرجعيًا للرجوع إليه.")).foregroundStyle(.secondary)
            }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
            Divider()
            Form {
                Section {
                    Picker(L("الغرض من النص"), selection: $purpose) {
                        Text(L("من كتاباتي — لتعلّم أسلوبي")).tag("style")
                        Text(L("مرجع للمحتوى")).tag("reference")
                    }
                    TextField(L("العنوان"), text: $title, prompt: Text(L("مثال: مقال عن الكتابة الواضحة")))
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text(L("نص المصدر"))
                            Spacer()
                            Button(L("اختيار ملف…"), action: importFile).disabled(saving)
                        }
                        TextEditor(text: $text).font(.body).frame(minHeight: 190)
                            .accessibilityLabel(L("نص المصدر"))
                            .overlay(RoundedRectangle(cornerRadius: 5).stroke(.separator))
                        Text(L("TXT أو Markdown · حتى {0} حرف", 120000)).font(.caption).foregroundStyle(.secondary)
                    }
                    Picker(L("حقوق الاستخدام"), selection: $rights) {
                        Text(L("لم أحدد بعد")).tag("unknown")
                        Text(L("أملك النص")).tag("owned")
                        Text(L("لدي ترخيص مناسب")).tag("licensed")
                    }
                    if rights == "unknown" {
                        Text(purpose == "style" ? L("حدد ملكيتك للنص أو ترخيص استخدامه لإضافته إلى أمثلة أسلوبك.") : L("يمكن حفظ المصدر وتحليله محليًا. يلزم تحديد الحقوق قبل إرساله إلى نموذج.")).font(.caption).foregroundStyle(.secondary)
                    }
                }
                Section {
                    DisclosureGroup(L("تفاصيل اختيارية")) {
                        TextField(L("الكاتب"), text: $author)
                        LabeledContent(L("الرابط الأصلي")) {
                            TextField("", text: $uri, prompt: Text("https://…"))
                                .labelsHidden()
                                .environment(\.layoutDirection, .leftToRight)
                                .accessibilityLabel(L("الرابط الأصلي"))
                        }
                        Text(L("الرابط مرجع فقط؛ لن يفتح التطبيق الصفحة تلقائيًا. استخدم الرابط نفسه عند تحديث المصدر.")).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }.formStyle(.grouped).disabled(saving)
            if let error { sheetError(error) }
            Divider()
            HStack {
                Button(L("إلغاء"), role: .cancel) { dismiss() }.keyboardShortcut(.cancelAction).disabled(saving)
                Spacer()
                if saving { ProgressView().controlSize(.small) }
                Button(L("إضافة المصدر")) { Task { await save() } }
                    .buttonStyle(.borderedProminent).keyboardShortcut(.defaultAction)
                    .disabled(!valid || saving || model.health == nil)
            }.padding(20)
        }.frame(width: 620, height: 650).editorialPresentation().interactiveDismissDisabled(saving)
            
    }
    private func importFile() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.plainText, .text]
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
            guard size <= 512000 else { throw EngineError(message: L("اختر ملفًا أصغر من {0} كيلوبايت.", 500)) }
            let contents = try String(contentsOf: url, encoding: .utf8)
            guard contents.count <= 120000 else { throw EngineError(message: L("اختر نصًا لا يتجاوز {0} حرف.", 120000)) }
            text = contents; accessMethod = "user_file"; error = nil
            if title.isEmpty { title = url.deletingPathExtension().lastPathComponent }
        } catch { self.error = error.localizedDescription }
    }
    private func save() async {
        guard valid && !saving else { return }
        saving = true; error = nil
        defer { saving = false }
        do {
            let result = try await model.decoded("sources.add", ["title": title, "text": text, "author": author, "canonical_uri": uri, "rights_status": rights, "access_method": accessMethod, "purpose": purpose], as: ImportedSource.self)
            try await model.refresh()
            onImported(result.itemId)
            model.notice = result.status == "skipped" ? L("المصدر موجود في مكتبتك") : L("أُضيف المصدر إلى مكتبتك")
            dismiss()
        } catch { self.error = error.localizedDescription }
    }
}

struct GenerationSheet: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openSettings) private var openSettings
    let onSubmitted: (String) -> Void
    let onShowSources: () -> Void
    @State private var topic = ""
    @State private var format = "x_post"
    @State private var language = "ar"
    @State private var seconds = 60
    @State private var profileID = ""
    @State private var modelID = ""
    @State private var modelReady = false
    @State private var sourceIDs = Set<String>()
    @AppStorage(ModelPermission.key) private var consent = false
    @State private var submitting = false
    @State private var error: String?
    private var profiles: [ProviderProfile] { model.snapshot?.profiles ?? [] }
    private var sources: [Source] { (model.snapshot?.sources ?? []).filter { ["owned", "licensed"].contains($0.rightsStatus) } }
    private var video: Bool { ["youtube_long", "shorts", "reels", "tiktok"].contains(format) }
    private var hasRules: Bool { model.snapshot?.rules.contains { $0.status == "approved" } == true }
    private var valid: Bool {
        (3...2000).contains(topic.trimmingCharacters(in: .whitespacesAndNewlines).count) &&
        profiles.contains { $0.id == profileID } && modelReady && hasRules && consent && model.health != nil && !submitting
    }
    var body: some View {
        let _ = interfaceLanguage
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 6) {
                Text(L("مساعدة في الكتابة")).font(.title2.bold())
                Text(L("أنشئ مسودة جديدة بأسلوبك، ثم راجعها وعدّلها.")).foregroundStyle(.secondary)
            }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
            Divider()
            Form {
                Section(L("الفكرة")) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(L("ماذا تريد أن تكتب؟"))
                        TextEditor(text: $topic).frame(minHeight: 70).accessibilityLabel(L("فكرة المسودة"))
                            .overlay(RoundedRectangle(cornerRadius: 5).stroke(.separator))
                    }
                    Picker(L("نوع المسودة"), selection: $format) {
                        Text(L("منشور X")).tag("x_post")
                        Text(L("سلسلة منشورات X")).tag("x_thread")
                        Text(L("منشور LinkedIn")).tag("linkedin")
                        Text(L("فيديو YouTube")).tag("youtube_long")
                        Text("YouTube Shorts").tag("shorts")
                        Text("Instagram Reels").tag("reels")
                        Text("TikTok").tag("tiktok")
                    }
                    Picker(L("اللغة"), selection: $language) { Text(L("العربية")).tag("ar"); Text("English").tag("en") }
                    if video { Stepper(L("المدة: {0} ثانية", DisplayFormat.integer(seconds)), value: $seconds, in: 10...7200, step: 10) }
                }
                Section(L("أسلوبك ومراجعك")) {
                    if hasRules {
                        Text(L("سيستخدم الأساليب التي اعتمدتها في «أسلوبي».")).font(.callout).foregroundStyle(.secondary)
                    } else {
                        Text(L("اعتمد أسلوبًا واحدًا من مصادرك قبل طلب المساعدة.")).font(.callout)
                        Button(L("الانتقال إلى المصادر")) { dismiss(); onShowSources() }
                    }
                    DisclosureGroup(L("مصادر مرجعية اختيارية ({0} من {1})", sourceIDs.count, 12)) {
                        if sources.isEmpty { Text(L("أضف مصدرًا تملكه أو لديك ترخيص باستخدامه ليظهر هنا.")).font(.caption).foregroundStyle(.secondary) }
                        ForEach(sources) { source in
                            Toggle(source.title, isOn: Binding(get: { sourceIDs.contains(source.id) }, set: { selected in
                                if selected { sourceIDs.insert(source.id) } else { sourceIDs.remove(source.id) }
                            })).disabled(sourceIDs.count >= 12 && !sourceIDs.contains(source.id))
                        }
                    }
                }
                Section(L("النموذج والموافقة")) {
                    if profiles.isEmpty {
                        Text(L("أضف نموذجًا في الإعدادات لتفعيل المساعدة.")).font(.callout)
                        Button(L("إعداد النموذج…")) { dismiss(); openSettings() }
                    } else {
                        ConnectionModelPicker(profileID: $profileID, modelID: $modelID, ready: $modelReady)
                    }
                    if !consent { ModelPermissionNotice() }
                }
            }.formStyle(.grouped).disabled(submitting)
            if let error { sheetError(error) }
            Divider()
            HStack {
                Button(L("إلغاء"), role: .cancel) { dismiss() }.keyboardShortcut(.cancelAction).disabled(submitting)
                Spacer()
                if submitting { ProgressView().controlSize(.small) }
                Button(L("إنشاء مسودة")) { Task { await submit() } }.buttonStyle(.borderedProminent)
                    .keyboardShortcut(.defaultAction).disabled(!valid)
            }.padding(20)
        }.frame(width: 620, height: 650).editorialPresentation().interactiveDismissDisabled(submitting)
            
            .onAppear {
                if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    profileID = assignment.profileId; modelID = assignment.modelId
                } else if profiles.count == 1 { profileID = profiles[0].id }
            }
    }
    private func submit() async {
        guard valid, let snapshot = model.snapshot else { return }
        submitting = true; error = nil
        defer { submitting = false }
        var payload: [String: Any] = ["topic": topic, "format": format, "language": language, "profile_id": profileID, "model_id": modelID, "dna_version_id": snapshot.dnaVersion.id, "source_ids": Array(sourceIDs), "consent": consent, "idempotency_key": UUID().uuidString]
        if video { payload["target_seconds"] = seconds }
        do {
            let submitted = try await model.decoded("drafts.generate", payload, as: SubmittedJob.self)
            onSubmitted(submitted.jobId)
            try await model.refresh()
            model.notice = L("بدأ إعداد المسودة؛ تابع التقدم من النشاط")
            dismiss()
        } catch { self.error = error.localizedDescription }
    }
}

private func sheetError(_ message: String) -> some View {
    Label(message, systemImage: "exclamationmark.circle")
        .font(.callout).foregroundStyle(.red).textSelection(.enabled)
        .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 24).padding(.vertical, 10)
}
