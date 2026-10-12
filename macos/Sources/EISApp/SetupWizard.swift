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
    @AppStorage("appLanguage") private var language = "ar"
    @AppStorage("setupCompleted") private var completed = false
    @AppStorage(ModelPermission.key) private var savedPermission = false
    @State private var permission = false
    @State private var step = 0
    @State private var profileID = ""
    @State private var modelID = ""
    @State private var ready = false
    @State private var adding = false
    @State private var saving = false
    @State private var error: String?
    private var titles: [String] { [L("مرحبًا بك في OpenStudio"), L("اختر نموذجك"), L("أنت تتحكم بصلاحيات التطبيق")] }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Image(nsImage: BrandAssets.menuBarIcon).renderingMode(.template)
                Text("OpenStudio").font(.headline)
                Spacer()
                Text(L("الخطوة {0} من {1}", step + 1, 3)).font(.caption).foregroundStyle(.secondary)
            }.padding(28)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    Text(titles[step]).font(.largeTitle.weight(.semibold))
                    if step == 0 { welcome }
                    else if step == 1 { connection }
                    else { permissions }
                    if let error { Text(L(error)).foregroundStyle(.red).textSelection(.enabled) }
                }.frame(maxWidth: .infinity, alignment: .leading).padding(32)
            }
            Divider()
            HStack {
                if step > 0 { Button(L("السابق")) { step -= 1 }.disabled(saving) }
                Spacer()
                if step == 1 { Button(L("سأربط مزودًا لاحقًا")) { step = 2 } }
                Button(L(step == 2 ? "ابدأ الاستخدام" : "متابعة")) {
                    if step == 1 { Task { await saveModel() } }
                    else if step == 2 { savedPermission = permission; completed = true; dismiss() }
                    else { step += 1 }
                }.buttonStyle(.borderedProminent).disabled(saving || (step == 1 && !ready))
            }.padding(24)
        }.frame(width: 680, height: 560).interactiveDismissDisabled()
            .editorialPresentation()
            .onAppear {
                permission = savedPermission
                if let assigned = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    profileID = assigned.profileId; modelID = assigned.modelId
                } else if let profiles = model.snapshot?.profiles, profiles.count == 1 { profileID = profiles[0].id }
            }
            .sheet(isPresented: $adding) {
                AddConnectionView { id in profileID = id; modelID = ""; adding = false }.editorialPresentation()
            }
    }
    private var welcome: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(L("ناقش فكرة، تابع مصادر الأخبار، وحوّلها إلى مسودات بأسلوبك. نضبط الأساسيات الآن، ويمكنك تغييرها لاحقًا من الإعدادات."))
                .font(.title3).foregroundStyle(.secondary)
            Picker(L("لغة الواجهة"), selection: $language) { Text("العربية").tag("ar"); Text("English").tag("en") }.pickerStyle(.segmented)
            Label(L("محادثاتك ومسوداتك محفوظة على جهازك"), systemImage: "internaldrive")
            Label(L("إعداد مرة واحدة، ثم ابدأ الكتابة"), systemImage: "checkmark.circle")
        }
    }
    private var connection: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(L("استخدم اتصالًا موجودًا أو اربط مزودًا. لا تحتاج إلى تسجيل الدخول مجددًا أو إجراء اختبار يدوي قبل كل رسالة."))
                .foregroundStyle(.secondary)
            if model.snapshot?.profiles.isEmpty == false {
                ConnectionModelPicker(profileID: $profileID, modelID: $modelID, ready: $ready)
            }
            Button { adding = true } label: { Label(L("ربط مزوّد"), systemImage: "plus") }
            Text(L("يمكنك إضافة مزودين آخرين وتخصيص نموذج كل وكيل من الإعدادات."))
                .font(.caption).foregroundStyle(.secondary)
        }.textFieldStyle(.roundedBorder)
    }
    private var permissions: some View {
        VStack(alignment: .leading, spacing: 20) {
            Toggle(L("السماح باستخدام النماذج"), isOn: $permission).toggleStyle(.switch)
            Text(L("عندما تطلب كتابة أو تحليلًا، يُرسل طلبك والأسلوب والمراجع المرفقة إلى المزوّد الذي تختاره. قد تُحتسب تكلفة حسب حسابك. يمكنك إيقاف هذا الإذن في أي وقت."))
                .foregroundStyle(.secondary)
            Text(L("يمكنك المتابعة دون هذا الإذن للقراءة والكتابة محليًا."))
                .font(.callout).foregroundStyle(.secondary)
            Divider()
            Label(L("الإعدادات متاحة دائمًا في الشريط الجانبي"), systemImage: "gearshape")
            Text(L("الملفات التي تختارها تُحفظ محليًا. إغلاق النافذة يبقي متابعة الأخبار في شريط القوائم؛ إنهاء التطبيق يوقفها."))
                .font(.caption).foregroundStyle(.secondary)
        }
    }
    private func saveModel() async {
        guard ready else { return }
        saving = true; error = nil
        defer { saving = false }
        do {
            _ = try await model.call("agents.assign", ["role": "writer", "profile_id": profileID, "model_id": modelID])
            try await model.refresh()
            step = 2
        } catch { self.error = error.localizedDescription }
    }
}
