import SwiftUI
import AppKit

struct AddConnectionView: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    let onAdded: (String) -> Void
    @State private var choosingProvider = true
    @State private var authMethod = ""
    @State private var providerID = ""
    @State private var providerSearch = ""
    @State private var ollamaMode = "local"
    @State private var label = ""
    @State private var credentials: [String: String] = [:]
    @State private var config: [String: String] = [:]
    @State private var working = false
    @State private var createdProfileID = ""
    @State private var selectedModelID = ""
    @State private var modelReady = false
    @State private var failure: String?
    private var providers: [Provider] { (model.catalog?.providers ?? []).sorted { $0.displayName.localizedCaseInsensitiveCompare($1.displayName) == .orderedAscending } }
    private var selected: Provider? { providers.first { $0.id == providerID } }
    private var supportsChatGPT: Bool { ["openai", "openai-chat", "openai-responses", "openai-chatgpt"].contains(providerID) }
    private var isOllama: Bool { providerID == "ollama" || providerID == "ollama-responses" }
    private var isOllamaCloud: Bool { isOllama && ollamaMode == "cloud" }
    private var credentialFields: [String] {
        if isOllama { return isOllamaCloud ? ["api_key"] : [] }
        return selected?.credentialFields ?? ["api_key"]
    }
    private var missingCloudKey: Bool {
        if isOllamaCloud { return (credentials["api_key"] ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        return selected?.credential == "api_key" && credentialFields.allSatisfy { (credentials[$0] ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }
    private var choices: [Provider] {
        let query = providerSearch.trimmingCharacters(in: .whitespacesAndNewlines)
        return providers.filter { $0.id != "openai-chatgpt" && (query.isEmpty || $0.id.localizedCaseInsensitiveContains(query) || $0.displayName.localizedCaseInsensitiveContains(query)) }
    }
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 12) {
                if let selected, !choosingProvider { ProviderBrandView(provider: selected, size: 32) }
                VStack(alignment: .leading, spacing: 4) {
                    Text(choosingProvider ? L("ربط مزوّد") : (selected?.displayName ?? L("اتصال جديد"))).font(.title2.weight(.semibold))
                    Text(choosingProvider ? L("اختر المزوّد وطريقة الاتصال المتاحة له.") : (createdProfileID.isEmpty ? L("أضف بيانات الاتصال، ثم اختر نموذجًا.") : L("اختر نموذجًا لهذا الاتصال.")))
                        .font(.callout).foregroundStyle(.secondary)
                }
                Spacer()
            }.padding(24)
            Divider()
            if choosingProvider {
                providerList
            } else if supportsChatGPT && createdProfileID.isEmpty && authMethod.isEmpty {
                authenticationMethods
            } else if supportsChatGPT && createdProfileID.isEmpty && authMethod == "browser" {
                ProviderSignInView { id in createdProfileID = id }
            } else {
                connectionForm
            }
            if let failure { Text(L(failure)).font(.callout).foregroundStyle(.red).textSelection(.enabled).padding(.horizontal, 22).padding(.bottom, 12) }
            Divider()
            HStack {
                Button(L("إغلاق"), role: .cancel) { dismiss() }.keyboardShortcut(.cancelAction)
                if !choosingProvider && createdProfileID.isEmpty {
                    Button(L("رجوع")) { if supportsChatGPT && !authMethod.isEmpty { authMethod = "" } else { choosingProvider = true }; failure = nil }
                }
                if working { ProgressView().controlSize(.small) }
                Spacer()
                if !choosingProvider {
                    if createdProfileID.isEmpty && (!supportsChatGPT || authMethod == "key") {
                        Button(L("حفظ الاتصال وجلب النماذج")) { save() }.buttonStyle(.borderedProminent)
                            .disabled(selected == nil || missingCloudKey || model.health == nil)
                    } else if !createdProfileID.isEmpty {
                        Button(L("اختيار النموذج لاحقًا")) { onAdded(createdProfileID) }
                        Button(L("حفظ النموذج")) { finish() }.buttonStyle(.borderedProminent)
                            .disabled(!modelReady || model.health == nil)
                    }
                }
            }.padding(18)
        }.frame(width: 640, height: choosingProvider ? 680 : (supportsChatGPT && createdProfileID.isEmpty && authMethod.isEmpty ? 400 : (authMethod == "browser" && createdProfileID.isEmpty ? 380 : 620))).disabled(working).interactiveDismissDisabled(working)
            .environment(\.layoutDirection, interfaceLanguage == "en" ? .leftToRight : .rightToLeft)
            .environment(\.locale, AppLanguage.current.locale)
            .onChange(of: ollamaMode) { _, mode in
                guard isOllama, createdProfileID.isEmpty else { return }
                config["host"] = mode == "cloud" ? "https://ollama.com" : "http://localhost:11434"
                credentials = [:]; failure = nil
            }
    }
    private var authenticationMethods: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(L("اختر طريقة الربط")).font(.headline)
            Button { authMethod = "browser" } label: {
                HStack(spacing: 12) {
                    Image(systemName: "person.crop.circle").font(.title2)
                    VStack(alignment: .leading, spacing: 5) {
                        Text(L("تسجيل الدخول بحساب ChatGPT")).fontWeight(.semibold)
                        Text(L("تابع في المتصفح باستخدام اشتراكك والنماذج المتاحة لحسابك.")).font(.callout).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Image(systemName: "chevron.forward")
                }.padding(16).contentShape(Rectangle())
            }.buttonStyle(.plain).background(.quaternary, in: RoundedRectangle(cornerRadius: 10))
            Button { authMethod = "key" } label: {
                HStack(spacing: 12) {
                    Image(systemName: "key").font(.title2)
                    VStack(alignment: .leading, spacing: 5) {
                        Text(L("مفتاح API")).fontWeight(.semibold)
                        Text(L("ألصق مفتاح المزوّد؛ يُحفظ لهذا الاتصال على جهازك.")).font(.callout).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Image(systemName: "chevron.forward")
                }.padding(16).contentShape(Rectangle())
            }.buttonStyle(.plain).background(.quaternary, in: RoundedRectangle(cornerRadius: 10))
            Spacer()
        }.padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
    private var providerList: some View {
        VStack(spacing: 0) {
            HStack {
                TextField(L("ابحث عن مزوّد"), text: $providerSearch).textFieldStyle(.roundedBorder).multilineTextAlignment(.leading)
                if !providerSearch.isEmpty {
                    Button { providerSearch = "" } label: { Image(systemName: "xmark.circle.fill") }
                        .buttonStyle(.plain).foregroundStyle(.secondary)
                        .help(L("مسح البحث")).accessibilityLabel(L("مسح البحث"))
                }
            }.padding(20)
            ScrollView {
                LazyVStack(spacing: 0) {
                    if model.catalog == nil {
                        ProgressView(L("انتظر فتح مساحة العمل.")).padding(24)
                    } else if choices.isEmpty {
                        Text(L("لا توجد نتائج لهذا البحث. جرّب اسمًا آخر أو امسح البحث.")).foregroundStyle(.secondary).padding(24)
                    }
                    ForEach(choices) { provider in
                        HStack(spacing: 14) {
                            ProviderBrandView(provider: provider, size: 32)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(provider.displayName).font(.headline)
                                Text(authenticationHint(provider)).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button(L("ربط")) { choose(provider) }
                                .accessibilityLabel(L("ربط {0}", provider.displayName))
                        }.padding(.horizontal, 24).padding(.vertical, 14)
                        Divider().padding(.horizontal, 24)
                    }
                }
            }
        }
    }
    private func authenticationHint(_ provider: Provider) -> String {
        if ["openai", "openai-chat", "openai-responses"].contains(provider.id) { return L("حساب ChatGPT أو مفتاح API") }
        if provider.id == "ollama" || provider.id == "ollama-responses" { return L("خادم محلي أو Ollama Cloud بمفتاح API") }
        if provider.credential == "local_server" { return L("خادم محلي") }
        if (provider.credentialFields ?? ["api_key"]) == ["api_key"] { return L("مفتاح API") }
        return L("بيانات حساب المزوّد")
    }
    private func choose(_ provider: Provider) {
        if providerID != provider.id {
            providerID = provider.id; credentials = [:]; config = [:]; label = ""; ollamaMode = "local"
            if isOllama { config["host"] = "http://localhost:11434" }
        }
        failure = nil; choosingProvider = false
    }
    private var connectionForm: some View {
        Form {
            if createdProfileID.isEmpty {
                Section(L("إعداد الاتصال")) {
                    if isOllama {
                        Picker(L("طريقة تشغيل Ollama"), selection: $ollamaMode) {
                            Text(L("محلي على الجهاز")).tag("local")
                            Text("Ollama Cloud").tag("cloud")
                        }.pickerStyle(.segmented).disabled(!createdProfileID.isEmpty)
                        Text(isOllamaCloud ? L("اتصال مباشر بسحابة Ollama؛ لا يتطلب تشغيل الخادم المحلي.") : L("اتصال بخادم Ollama المحلي على جهازك؛ لا يتطلب مفتاح API."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    if selected != nil {
                        TextField(L("اسم الاتصال"), text: $label, prompt: Text(L("اختياري، مثل: حساب العمل")))
                            .disabled(!createdProfileID.isEmpty)
                    }
                }
            }
                if let selected, createdProfileID.isEmpty {
                    Section(L("بيانات الدخول")) {
                        if selected.credential == "local_server" && !isOllamaCloud {
                            Text(L("يستخدم هذا المزوّد خادمًا محليًا. أضف عنوانه في الخيارات المتقدمة عند الحاجة.")).font(.callout).foregroundStyle(.secondary)
                        }
                        ForEach(credentialFields, id: \.self) { field in
                            if field == "service_account_info" {
                                DisclosureGroup(L("حساب خدمة Google — JSON")) {
                                    TextEditor(text: Binding(get: { credentials[field] ?? "" }, set: { credentials[field] = $0 }))
                                        .font(.caption.monospaced()).frame(height: 110).environment(\.layoutDirection, .leftToRight)
                                        .accessibilityLabel(L("بيانات حساب الخدمة JSON"))
                                }
                            } else {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(credentialLabel(field)).font(.callout.weight(.medium))
                                    SecureField("", text: Binding(get: { credentials[field] ?? "" }, set: { credentials[field] = $0 }), prompt: Text(L("ألصق المفتاح هنا")))
                                        .labelsHidden().textFieldStyle(.roundedBorder).controlSize(.large)
                                        .environment(\.layoutDirection, .leftToRight)
                                        .accessibilityLabel(credentialLabel(field))
                                        .help(field)
                                }
                            }
                        }
                        if isOllamaCloud {
                            Link(L("إنشاء مفتاح Ollama API"), destination: URL(string: "https://ollama.com/settings/keys")!)
                            Text(L("أدخل مفتاح API للاتصال السحابي وجلب نماذجه.")).font(.caption).foregroundStyle(.secondary)
                        }
                        if !selected.note.isEmpty && !isOllamaCloud { Text(L(selected.note)).font(.caption).foregroundStyle(.secondary) }
                    }
                    if !selected.fields.isEmpty {
                        Section {
                            DisclosureGroup(L("خيارات متقدمة")) {
                                ForEach(selected.fields, id: \.self) { field in
                                    LabeledContent(fieldLabel(field)) {
                                        TextField("", text: Binding(get: { config[field] ?? "" }, set: { config[field] = $0 }), prompt: Text(["host", "base_url", "api_base"].contains(field) ? (selected.defaultBaseUrl ?? "") : L("اختياري")))
                                            .labelsHidden()
                                            .environment(\.layoutDirection, .leftToRight)
                                            .accessibilityLabel(fieldLabel(field))
                                            .help(field)
                                    }
                                }
                            }
                        }
                    }
                }
                if selected != nil {
                    Section(L("النموذج")) {
                        if createdProfileID.isEmpty {
                            Text(L("بعد حفظ بيانات الاتصال، سنجلب قائمة النماذج لتبحث وتختار منها. لا تحتاج إلى كتابة معرّف النموذج.")).font(.callout).foregroundStyle(.secondary)
                            if selected?.credential == "local_server" && !isOllamaCloud {
                                Text(L("شغّل الخادم المحلي أولًا؛ ستظهر النماذج المتاحة عليه.")).font(.caption).foregroundStyle(.secondary)
                            } else {
                                Text(L("قد يتطلب جلب النماذج بيانات دخول صالحة وإعدادات الحساب أو المنطقة.")).font(.caption).foregroundStyle(.secondary)
                            }
                        } else {
                            ConnectionModelPicker(profileID: $createdProfileID, modelID: $selectedModelID, ready: $modelReady, showsConnection: false)
                            Text(L("حُفظ الاتصال. اختر نموذجًا لإكمال الإعداد، أو اختره لاحقًا من هذا الاتصال.")).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                Section {
                    Text(L("تُحفظ بيانات هذا الاتصال في ملف خاص داخل مساحة العمل بصلاحية وصول لحسابك فقط.")).font(.caption).foregroundStyle(.secondary)
                }
        }.formStyle(.grouped)
    }
    private func finish() {
        working = true; failure = nil
        Task {
            defer { working = false }
            do {
                _ = try await model.call("providers.update", ["profile_id": createdProfileID, "model_id": selectedModelID])
                try await model.refresh()
                onAdded(createdProfileID)
            } catch { failure = error.localizedDescription }
        }
    }
    private func save() {
        working = true; failure = nil
        let defaultName = isOllama ? (isOllamaCloud ? "Ollama Cloud" : L("Ollama محلي")) : ""
        let provider = providerID, name = label.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? defaultName : label
        let values = credentials, fields = credentialFields, options = config.filter { !$0.value.isEmpty }
        Task {
            defer { working = false }
            do {
                var object: [String: Any] = [:]
                for field in fields {
                    let value = values[field] ?? ""
                    if field == "service_account_info" && !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        guard let info = try JSONSerialization.jsonObject(with: Data(value.utf8)) as? [String: Any] else {
                            throw EngineError(message: L("بيانات حساب الخدمة يجب أن تكون كائن JSON."))
                        }
                        object[field] = info
                    } else { object[field] = value }
                }
                let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
                let saved = try await model.decoded("providers.save", ["provider_key": provider, "model_id": "", "label": name, "config": options], as: SavedConnection.self)
                try ProviderCredentials.saveJSON(String(decoding: data, as: UTF8.self), workspace: model.workspace, profileID: saved.profileId)
                createdProfileID = saved.profileId
                credentials = [:]
                try await model.refresh()
            } catch { try? await model.refresh(); failure = error.localizedDescription }
        }
    }
}
