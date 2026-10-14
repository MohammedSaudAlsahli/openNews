import SwiftUI

/// An explicit, revocable preference. Credentials alone never imply permission to send content.
enum ModelPermission {
    static let key = "allowModelRequests"
    static func allowed(in defaults: UserDefaults = .standard) -> Bool { defaults.bool(forKey: key) }
}

struct ModelPermissionNotice: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @Environment(\.openSettings) private var openSettings
    var body: some View {
        let _ = interfaceLanguage
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "lock.shield")
            Text(L("فعّل استخدام النماذج مرة واحدة من الإعدادات للمتابعة.")).font(.callout)
            Spacer()
            Button(L("الإعدادات")) {
                UserDefaults.standard.set("permissions", forKey: "settingsSection")
                openSettings()
            }
        }.foregroundStyle(.secondary)
    }
}

struct PermissionsSettingsView: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @AppStorage(ModelPermission.key) private var allowed = false
    @Environment(\.openWindow) private var openWindow
    var body: some View {
        let _ = interfaceLanguage
        Form {
            Section(L("استخدام الذكاء الاصطناعي")) {
                Toggle(L("السماح باستخدام النماذج"), isOn: $allowed)
                Text(L("عندما تطلب كتابة أو تحليلًا، يُرسل طلبك والأسلوب والمراجع المرفقة إلى المزوّد الذي تختاره. قد تُحتسب تكلفة حسب حسابك. يمكنك إيقاف هذا الإذن في أي وقت."))
                    .font(.callout).foregroundStyle(.secondary)
                Text(L("لا نطلب الموافقة مجددًا لكل رسالة، ولا ننشر محتواك تلقائيًا.")).font(.caption).foregroundStyle(.secondary)
            }
            UpdateSettings()
            Section(L("إعداد التطبيق")) {
                Button(L("فتح دليل الإعداد")) {
                    openWindow(id: "studio")
                    NotificationCenter.default.post(name: .showEditorialSetup, object: nil)
                }
                Text(L("الملفات التي تختارها تُحفظ محليًا. إغلاق النافذة يبقي متابعة الأخبار في شريط القوائم؛ إنهاء التطبيق يوقفها."))
                    .font(.callout).foregroundStyle(.secondary)
            }
        }.formStyle(.grouped)
    }
}

struct SetupWizard: View {
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AppStorage("appLanguage") private var language = "ar"
    @AppStorage("setupCompleted") private var completed = false
    @AppStorage("onboardingStep") private var step = 0
    @AppStorage(ModelPermission.key) private var savedPermission = false
    @State private var permission = false
    @State private var profileID = ""
    @State private var modelID = ""
    @State private var ready = false
    @State private var adding = false
    @State private var sources = false
    @State private var saving = false
    @State private var error: String?
    private var titles: [String] { [L("من خبر إلى فكرة تستحق الكتابة"), L("ابدأ بمصدر يهمك"), L("اختر من يساعدك في الكتابة"), L("جرّب أول نقاش") ] }
    private var hasSources: Bool { model.snapshot?.subscriptions?.isEmpty == false }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Image(nsImage: BrandAssets.menuBarIcon).renderingMode(.template)
                Text("OpenStudio").font(.headline)
                Spacer()
                Button(L("استكشف بنفسي")) { finish() }.disabled(saving)
            }.padding(24)
            ProgressView(value: Double(step + 1), total: 4).tint(.accentColor).accessibilityLabel(L("الخطوة {0} من {1}", step + 1, 4))
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    Text(titles[min(max(step, 0), 3)]).font(.largeTitle.weight(.semibold))
                    switch step {
                    case 0: welcome
                    case 1: sourceStep
                    case 2: connection
                    default: firstConversation
                    }
                    if let error { Label(L(error), systemImage: "exclamationmark.circle").foregroundStyle(.red).textSelection(.enabled) }
                }.frame(maxWidth: .infinity, alignment: .leading).padding(32)
            }
            Divider()
            HStack {
                if step > 0 { Button(L("السابق")) { move(step - 1) }.disabled(saving) }
                Text(L("الخطوة {0} من {1}", step + 1, 4)).font(.caption).foregroundStyle(.secondary)
                Spacer()
                if step == 2 { Button(L("سأربط مزودًا لاحقًا")) { move(3) }.disabled(saving) }
                Button(L(step == 3 ? "افتح أخبارك" : "التالي")) {
                    if step == 2 { Task { await saveModel() } }
                    else if step == 3 {
                        finish()
                        NotificationCenter.default.post(name: .onboardingReadNews, object: nil)
                    } else { move(step + 1) }
                }.buttonStyle(.borderedProminent).keyboardShortcut(.defaultAction)
                    .disabled(saving || (step == 2 && !ready))
            }.padding(24)
        }.frame(width: 720, height: 620)
            .editorialPresentation()
            .onAppear {
                step = min(max(step, 0), 3)
                permission = savedPermission
                if let assigned = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    profileID = assigned.profileId; modelID = assigned.modelId
                } else if let profiles = model.snapshot?.profiles, profiles.count == 1 { profileID = profiles[0].id }
            }
            .sheet(isPresented: $adding) { AddConnectionView { id in profileID = id; modelID = ""; adding = false }.editorialPresentation() }
            .sheet(isPresented: $sources, onDismiss: { Task { try? await model.refresh() } }) { FeedLibraryView() }
    }
    private func move(_ next: Int) {
        error = nil
        withAnimation(reduceMotion ? nil : .easeOut(duration: 0.18)) { step = next }
    }
    private func finish() { savedPermission = permission; completed = true; step = 0; dismiss() }
    private var welcome: some View {
        VStack(alignment: .leading, spacing: 22) {
            Text(L("اجمع الأخبار التي تهمك، افهم سياقها، ثم حوّلها إلى مسودة بصوتك. سنبدأ بمصدر واحد ونقاش واحد."))
                .font(.title3).foregroundStyle(.secondary)
            Picker(L("لغة الواجهة"), selection: $language) { Text("العربية").tag("ar"); Text("English").tag("en") }.pickerStyle(.segmented)
            Divider()
            Label(L("أخبارك ومسوداتك تبقى محفوظة على جهازك"), systemImage: "internaldrive")
            Label(L("لا حساب جديد، ولا تنزيل نموذج للبدء بالقراءة"), systemImage: "book")
            Text(L("كل خطوة اختيارية. يمكنك العودة لهذه البداية من الإعدادات."))
                .font(.callout).foregroundStyle(.secondary)
        }
    }
    private var sourceStep: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(L("اختر موقعًا تتابعه من دليل المصادر أو أضف رابط RSS. سنحتفظ بالأخبار الجديدة حتى لو اختفت من الخلاصة."))
                .foregroundStyle(.secondary)
            Button { sources = true } label: { Label(L("اختر أول مصدر"), systemImage: "plus") }.buttonStyle(.borderedProminent)
            if hasSources {
                Label(L("مصادرك جاهزة؛ ستصل الأخبار أثناء تشغيل التطبيق"), systemImage: "checkmark.circle").foregroundStyle(.secondary)
                ForEach(Array((model.snapshot?.subscriptions ?? []).prefix(3))) { source in Text(source.title).font(.callout) }
            } else {
                Text(L("تقدر تتخطى هذه الخطوة وتضيف مصادرك لاحقًا.")) .font(.callout).foregroundStyle(.secondary)
            }
        }
    }
    private var connection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(L("اربط مزوّدك للمناقشة والكتابة. القراءة وحفظ الأخبار لا تحتاج إلى نموذج.")) .foregroundStyle(.secondary)
            if model.snapshot?.profiles.isEmpty == false { ConnectionModelPicker(profileID: $profileID, modelID: $modelID, ready: $ready) }
            Button { adding = true } label: { Label(L("ربط مزوّد"), systemImage: "plus") }
            Divider()
            Toggle(L("السماح باستخدام النماذج"), isOn: $permission).toggleStyle(.switch)
            Text(L("عندما تطلب كتابة أو تحليلًا، يُرسل طلبك والأسلوب والمراجع المرفقة إلى المزوّد الذي تختاره. قد تُحتسب تكلفة حسب حسابك. يمكنك إيقاف هذا الإذن في أي وقت."))
                .font(.callout).foregroundStyle(.secondary)
            Text(L("التلخيص المحلي اختياري؛ تختار نموذجه وتنزّله لاحقًا من الإعدادات.")) .font(.caption).foregroundStyle(.secondary)
        }
    }
    private var firstConversation: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(L("افتح خبرًا من صفحة المقالات، ثم اختر مناقشته. سيبقى الخبر مرجعًا واضحًا في محادثتك.")) .font(.title3).foregroundStyle(.secondary)
            GroupBox(L("جرّب هذا الطلب")) {
                Text(L("اشرح لي وش صار وليش يهمني، وابحث عن خبر سابق مرتبط فيه، ثم اقترح بوست إكس بلهجة سعودية."))
                    .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading).padding(12)
            }
            Label(L("راجع الشرح والمصادر قبل اعتماد المسودة"), systemImage: "checkmark.bubble")
            Label(L("احفظ مسودتك وعدّلها؛ لا ينشر التطبيق نيابة عنك"), systemImage: "square.and.pencil")
            if !hasSources { Button(L("أضف مصدرًا أولًا")) { move(1) } }
        }
    }
    private func saveModel() async {
        guard ready else { return }
        saving = true; error = nil
        defer { saving = false }
        do {
            _ = try await model.call("agents.assign", ["role": "writer", "profile_id": profileID, "model_id": modelID])
            try await model.refresh()
            move(3)
        } catch { self.error = error.localizedDescription }
    }
}
