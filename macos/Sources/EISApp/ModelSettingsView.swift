import SwiftUI
import AppKit

struct ConnectionModelPicker: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Binding var profileID: String
    @Binding var modelID: String
    @Binding var ready: Bool
    var showsConnection = true
    @State private var result: ProviderModels?
    @State private var loading = false
    @State private var failure: String?
    @State private var choosingModel = false
    private var profiles: [ProviderProfile] { model.snapshot?.profiles ?? [] }
    private var connectionRevision: String { profileID + ":" + (profiles.first { $0.id == profileID }?.connection?.state ?? "") }
    var body: some View {
        let _ = interfaceLanguage
        Group {
            if showsConnection {
                VStack(alignment: .leading, spacing: 9) {
                    Text(L("الاتصال")).font(.callout.weight(.medium))
                    Menu {
                        Button(L("اختر اتصالًا")) { profileID = "" }
                        ForEach(profiles) { profile in
                            Button { profileID = profile.id } label: {
                                if profile.id == profileID { Label(profile.displayName, systemImage: "checkmark") }
                                else { Text(profile.displayName) }
                            }
                        }
                    } label: {
                        HStack(spacing: 12) {
                            Text(profiles.first { $0.id == profileID }?.displayName ?? L("اختر اتصالًا"))
                                .lineLimit(1).truncationMode(.middle)
                            Spacer(minLength: 4)
                            Image(systemName: "chevron.up.chevron.down").font(.caption)
                        }.padding(10).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 7))
                    }.menuStyle(.borderlessButton).menuIndicator(.hidden).accessibilityLabel(L("الاتصال"))

                }
            }
            if !profileID.isEmpty {
                VStack(alignment: .leading, spacing: 9) {
                    Text(L("النموذج")).font(.callout.weight(.medium))
                    Button { choosingModel = true } label: {
                        HStack(spacing: 8) {
                            Text(loading ? L("جارٍ جلب النماذج…") : (result?.models.first { $0.id == modelID }?.name ?? L("اختر نموذجًا")))
                                .lineLimit(1).truncationMode(.middle)
                            Image(systemName: "chevron.up.chevron.down").font(.caption)
                        }
                    }
                    .disabled(loading || (result?.models.isEmpty ?? true))
                    .accessibilityLabel(L("اختيار النموذج"))
                    .popover(isPresented: $choosingModel) {
                        ModelChooserList(models: result?.models ?? [], selectedID: $modelID) { choosingModel = false }
                            .editorialPresentation()
                    }
                }
                HStack {
                    if loading { ProgressView().controlSize(.small) }
                    if let date = result?.updatedAt { Text(L("آخر تحديث: {0}", DisplayFormat.date(date))).font(.caption).foregroundStyle(.secondary) }
                    Spacer()
                    Button(L("تحديث النماذج")) { Task { await load(refresh: true) } }.disabled(loading)
                }
                if let failure { Text(L(failure)).font(.caption).foregroundStyle(.red).textSelection(.enabled) }
                if let warning = result?.error, !warning.isEmpty { Text(L(warning)).font(.caption).foregroundStyle(.secondary) }
                if !loading && result?.models.isEmpty == true {
                    Text(L("لم تصل نماذج لهذا الاتصال. راجع بيانات الاتصال ثم حدّث القائمة.")).font(.caption).foregroundStyle(.secondary)
                }
            }
        }
        .task(id: connectionRevision) {
            await load(refresh: false)
            while !Task.isCancelled && !profileID.isEmpty {
                do { try await Task.sleep(nanoseconds: 60_000_000_000) } catch { break }
                await load(refresh: false, quietly: true)
            }
        }
        .onChange(of: modelID) { _, _ in updateReadiness() }
        .onChange(of: connectionRevision) { _, _ in choosingModel = false }
    }
    private func updateReadiness() { ready = !loading && result?.models.contains { $0.id == modelID && $0.available } == true }
    private func load(refresh: Bool, quietly: Bool = false) async {
        if quietly && loading { return }
        let requested = profileID
        if !quietly { ready = false; result = nil; failure = nil }
        guard !requested.isEmpty else { modelID = ""; loading = false; return }
        if !quietly { loading = true }
        do {
            let fetched = try await model.decoded("providers.models", ["profile_id": requested, "refresh": refresh], as: ProviderModels.self)
            guard !Task.isCancelled, requested == profileID else { return }
            result = fetched; failure = nil
            if !fetched.models.contains(where: { $0.id == modelID && $0.available }) {
                if !modelID.isEmpty {
                    modelID = ""
                    failure = L("النموذج السابق غير متاح لهذا الاتصال. اختر نموذجًا من القائمة.")
                } else {
                    let preferred = profiles.first { $0.id == requested }?.modelId
                    modelID = fetched.models.first { $0.id == preferred && $0.available }?.id ?? ""
                }
            }
            loading = false; updateReadiness()
        } catch {
            guard !Task.isCancelled, requested == profileID else { return }
            failure = error.localizedDescription; modelID = ""; loading = false; ready = false
        }
    }
}

/// Search belongs to the chooser it filters, not the connection form.
private struct ModelChooserList: View {
    let models: [ProviderModel]
    @Binding var selectedID: String
    let dismiss: () -> Void
    @State private var search = ""
    @FocusState private var searchFocused: Bool
    private var results: [ProviderModel] {
        let query = search.trimmingCharacters(in: .whitespacesAndNewlines)
        return models.filter { query.isEmpty || $0.name.localizedCaseInsensitiveContains(query) || $0.id.localizedCaseInsensitiveContains(query) }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(L("اختر نموذجًا")).font(.headline)
                Spacer()
                Button(L("إغلاق"), action: dismiss).keyboardShortcut(.cancelAction)
            }
            Text(L("اختر النموذج الذي سيستخدمه هذا الاتصال.")).font(.callout).foregroundStyle(.secondary)
            if models.count > 8 {
                TextField(L("ابحث بالاسم داخل هذه القائمة"), text: $search)
                    .textFieldStyle(.roundedBorder).focused($searchFocused)
                    .onSubmit { if let first = results.first(where: { $0.available }) { choose(first) } }
            }
            if results.isEmpty {
                Text(L("لا توجد نماذج مطابقة. جرّب اسمًا آخر.")).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, minHeight: 90)
            } else {
                ScrollViewReader { reader in
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(results) { item in
                                Button { choose(item) } label: {
                                    HStack(spacing: 12) {
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text(item.name).font(.body).foregroundStyle(.primary)
                                            if item.name != item.id {
                                                Text(technicalIdentifier(item.id)).font(.caption).foregroundStyle(.secondary)
                                            }
                                            if !item.available { Text(L("غير متاح")).font(.caption).foregroundStyle(.secondary) }
                                        }
                                        Spacer(minLength: 8)
                                        if item.id == selectedID { Image(systemName: "checkmark").foregroundStyle(Color.accentColor) }
                                    }.padding(10).frame(maxWidth: .infinity, alignment: .leading)
                                        .background(item.id == selectedID ? Color.accentColor.opacity(0.12) : Color.clear, in: RoundedRectangle(cornerRadius: 6))
                                        .contentShape(Rectangle())
                                }.buttonStyle(.plain).disabled(!item.available).id(item.id)
                                    .accessibilityAddTraits(item.id == selectedID ? [.isSelected] : [])
                            }
                        }
                    }.frame(height: min(CGFloat(results.count) * 62, 360))
                        .onAppear { if !selectedID.isEmpty { reader.scrollTo(selectedID, anchor: .center) } }
                }
            }
        }.padding(18).frame(width: 430)
            .onAppear { searchFocused = models.count > 8 }
    }
    private func choose(_ item: ProviderModel) {
        guard item.available else { return }
        selectedID = item.id
        dismiss()
    }
}

private enum SettingsSection: String, CaseIterable {
    case general, connections, agents, permissions, assistant
}

struct ModelSettingsView: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @AppStorage("appearance") private var appearance = "system"
    @AppStorage("appLanguage") private var appLanguage = "ar"
    @AppStorage("settingsSection") private var section: SettingsSection = .general
    var body: some View {
        let _ = interfaceLanguage
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 0) {
                Text(L("الإعدادات")).font(.title2.weight(.semibold)).padding(24)
                List(selection: $section) {
                    Section(L("مساحة العمل")) {
                        Label(L("الوكلاء"), systemImage: "person.2").tag(SettingsSection.agents)
                        Label(L("تخصيص المساعد"), systemImage: "slider.horizontal.3").tag(SettingsSection.assistant)
                    }
                    Section(L("التطبيق")) {
                        Label(L("مزوّدو الذكاء الاصطناعي"), systemImage: "network").tag(SettingsSection.connections)
                        Label(L("اللغة والمظهر"), systemImage: "globe").tag(SettingsSection.general)
                        Label(L("الصلاحيات والإعداد"), systemImage: "lock.shield").tag(SettingsSection.permissions)
                    }
                }.listStyle(.sidebar).scrollContentBackground(.hidden).padding(.horizontal, 10).padding(.top, 6)
            }.frame(width: 240).background(Color(nsColor: .windowBackgroundColor))
            Divider()
            // Keep each editor alive while navigating between settings sections.
            ZStack {
                VStack(alignment: .leading, spacing: 0) {
                    settingsHeading(L("اللغة والمظهر"), subtitle: L("خصّص لغة التطبيق ومظهره."))
                    general
                }.opacity(section == .general ? 1 : 0)
                    .allowsHitTesting(section == .general).disabled(section != .general).accessibilityHidden(section != .general)
                ConnectionsSettingsView().opacity(section == .connections ? 1 : 0)
                    .allowsHitTesting(section == .connections).disabled(section != .connections).accessibilityHidden(section != .connections)
                VStack(alignment: .leading, spacing: 0) {
                    settingsHeading(L("الصلاحيات والإعداد"), subtitle: L("اضبط صلاحيات التطبيق مرة واحدة، وغيّرها متى شئت."))
                    PermissionsSettingsView()
                }.opacity(section == .permissions ? 1 : 0)
                    .allowsHitTesting(section == .permissions).disabled(section != .permissions).accessibilityHidden(section != .permissions)
                VStack(alignment: .leading, spacing: 20) {
                    Text(L("تخصيص المساعد")).font(.title2.weight(.semibold))
                    Text(L("اضبط الدور والتعليمات والأسلوب مرة واحدة. يمكنك تخصيص كل وكيل أو محادثة بصورة مستقلة."))
                        .foregroundStyle(.secondary)
                    AssistantCustomizationButton(scope: "general").buttonStyle(.borderedProminent)
                    Spacer()
                }.padding(28).opacity(section == .assistant ? 1 : 0)
                    .allowsHitTesting(section == .assistant).disabled(section != .assistant).accessibilityHidden(section != .assistant)
                agents.opacity(section == .agents ? 1 : 0)
                    .allowsHitTesting(section == .agents).disabled(section != .agents).accessibilityHidden(section != .agents)
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: 900, idealWidth: 1000, minHeight: 680, idealHeight: 740)
        .textFieldStyle(.roundedBorder)
        .navigationTitle(L("الإعدادات"))
    }
    private var general: some View {
        Form {
            Section(L("اللغة والمظهر")) {
                Picker(L("لغة الواجهة"), selection: $appLanguage) {
                    Text(L("العربية")).tag("ar")
                    Text("English").tag("en")
                }.pickerStyle(.segmented).fixedSize(horizontal: true, vertical: false)
                Text(L("يتغير اتجاه الواجهة مع اللغة. تبقى نصوصك بلغتها الأصلية.")).font(.caption).foregroundStyle(.secondary)
                Picker(L("المظهر"), selection: $appearance) {
                    Text(L("حسب النظام")).tag("system")
                    Text(L("فاتح")).tag("light")
                    Text(L("داكن")).tag("dark")
                }.pickerStyle(.segmented).fixedSize(horizontal: true, vertical: false)
            }
            Section(L("مساحة العمل")) {
                LabeledContent(L("حفظ النصوص"), value: L("محليًا على جهازك"))
                Text(L("تُرسل البيانات عند طلب الكتابة أو التحليل بعد تفعيل إذن استخدام النماذج. يمكنك تغيير الإذن من الصلاحيات والإعداد."))
                    .font(.callout).foregroundStyle(.secondary)
            }
        }.formStyle(.grouped)
    }
    private var agents: some View {
        AgentsSettingsView { section = .connections }
    }
}

private struct ConnectionsSettingsView: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @State private var selectedID = ""
    @State private var adding = false
    private var profiles: [ProviderProfile] { model.snapshot?.profiles ?? [] }
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                if !selectedID.isEmpty {
                    Button { selectedID = "" } label: { Label(L("الاتصالات"), systemImage: "chevron.backward") }
                } else {
                    Text(L("الاتصالات")).font(.title2.weight(.semibold))
                }
                Spacer()
                Button { adding = true } label: { Label(L("ربط مزوّد"), systemImage: "plus") }
                    .buttonStyle(.borderedProminent)
            }.padding(24)
            Divider()
            if let profile = profiles.first(where: { $0.id == selectedID }) {
                ConnectionSettingsDetail(profile: profile).id(profile.id)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        Text(L("اتصالاتك المحفوظة. يمكنك إضافة أكثر من حساب للمزوّد نفسه."))
                            .foregroundStyle(.secondary).padding(.bottom, 20)
                        if profiles.isEmpty {
                            Text(L("أضف اتصالًا أولًا")).font(.headline).padding(.vertical, 20)
                        }
                        ForEach(profiles) { profile in
                            ConnectionStatusRow(profile: profile) { selectedID = profile.id }
                            Divider()
                        }
                    }.padding(24)
                }
            }
        }.sheet(isPresented: $adding) {
            AddConnectionView { id in selectedID = id; adding = false }
                .environmentObject(model)
        }
    }
}

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

struct AgentModelAssignment: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    let role: String
    let title: String
    @State private var profileID = ""
    @State private var modelID = ""
    @State private var ready = false
    @State private var saving = false
    @State private var message: String?
    @State private var failed = false
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 22) {
            Text(role == "writer" ? L("للمحادثة وإنشاء المسودات.") : L("لاستخراج تقنيات الكتابة من أمثلتك."))
                .font(.caption).foregroundStyle(.secondary)
            ConnectionModelPicker(profileID: $profileID, modelID: $modelID, ready: $ready)
            HStack {
                if saving { ProgressView().controlSize(.small) }
                Spacer()
                Button(L("حفظ اختيار {0}", title)) {
                    saving = true; message = nil; failed = false
                    Task {
                        defer { saving = false }
                        do {
                            _ = try await model.call("agents.assign", ["role": role, "profile_id": profileID, "model_id": modelID])
                            try await model.refresh(); message = L("حُفظ اختيار {0}.", title)
                        } catch { failed = true; message = error.localizedDescription }
                    }
                }.buttonStyle(.borderedProminent).disabled(!ready || saving || (model.snapshot?.assignments?.first { $0.role == role }.map { $0.profileId == profileID && $0.modelId == modelID } ?? false))
            }
            if let message { Text(L(message)).font(.caption).foregroundStyle(failed ? Color.red : Color.secondary) }
        }.padding(.vertical, 12).onAppear {
            if let assignment = model.snapshot?.assignments?.first(where: { $0.role == role }) {
                profileID = assignment.profileId; modelID = assignment.modelId
            } else if let first = model.snapshot?.profiles.first { profileID = first.id }
        }.disabled(saving)
    }
}

private struct ConnectionSettingsDetail: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    let profile: ProviderProfile
    @State private var profileID = ""
    @State private var modelID = ""
    @State private var label = ""
    @State private var autoRefresh = true
    @State private var ready = false
    @AppStorage(ModelPermission.key) private var consent = false
    @State private var working = false
    @State private var editing = false
    @State private var signingIn = false
    @State private var disconnecting = false
    @State private var deleting = false
    @State private var checking = false
    @State private var credentialText = ""
    @State private var message: String?
    @State private var failed = false
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 0) {
            settingsHeading(profile.displayName, subtitle: technicalIdentifier(profile.providerKey))
            Form {
                Section(L("حالة الاتصال")) {
                    ConnectionStatusView(profile: profile, detailed: true, checking: checking)
                    HStack {
                        Button(L("تحقق الآن")) {
                            checking = true
                            Task {
                                defer { checking = false }
                                do { _ = try await model.call("providers.check", ["profile_id": profile.id]); try await model.refresh() }
                                catch { failed = true; message = error.localizedDescription; try? await model.refresh() }
                            }
                        }.disabled(checking || profile.connection?.state == "disconnected" || model.health == nil)
                        Spacer()
                        Button(L("حذف الاتصال…"), role: .destructive) { deleting = true }
                            .disabled(checking || model.health == nil)
                        Button(L("فصل الاتصال…"), role: .destructive) { disconnecting = true }
                            .disabled(profile.connection?.state == "disconnected" || checking || model.health == nil)
                    }
                }
                Section(L("إعداد الاتصال")) {
                    TextField(L("اسم الاتصال"), text: $label)
                    ConnectionModelPicker(profileID: $profileID, modelID: $modelID, ready: $ready, showsConnection: false)
                    Toggle(L("تحديث قائمة النماذج تلقائيًا"), isOn: $autoRefresh)
                }
                Section(L("بيانات الدخول")) {
                    if profile.providerKey == "openai-chatgpt" {
                        Text(L("طريقة الربط: تسجيل الدخول بحساب ChatGPT. لربط حساب آخر، أضف اتصالًا جديدًا.")).font(.callout).foregroundStyle(.secondary)
                        Button(L("تسجيل الدخول مجددًا")) { signingIn = true }
                    } else {
                        Button(L("تعديل بيانات الاتصال…"), action: editCredentials)
                        if profile.connection?.state == "disconnected" {
                            Button(L("إعادة الربط")) { perform("providers.reconnect", ["profile_id": profile.id], success: L("أُعيد تفعيل الاتصال. تحقّق منه الآن.")) }
                        }
                    }
                    DisclosureGroup(L("مكان الحفظ")) {
                        Text(L("ملف JSON خاص بهذا الاتصال. لا تُستخدم إعدادات التطبيقات الأخرى.")).font(.caption).foregroundStyle(.secondary)
                        Button(L("إظهار الملف في Finder"), action: revealCredentials)
                    }
                }
                Section {
                    DisclosureGroup(L("اختبار الاتصال")) {
                        if !consent { ModelPermissionNotice() }
                        Button(L("اختبار النموذج")) {
                            perform("providers.validate", ["profile_id": profile.id, "model_id": modelID, "consent": true], success: L("نجح اختبار النموذج."))
                        }.disabled(!ready || !consent || working)
                    }
                }
            }.formStyle(.grouped).disabled(working)
            if let message { Text(L(message)).font(.callout).foregroundStyle(failed ? Color.red : Color.secondary).textSelection(.enabled).padding(.horizontal, 22).padding(.bottom, 12) }
            Divider()
            HStack {
                if working { ProgressView().controlSize(.small) }
                Spacer()
                Button(L("حفظ التغييرات")) {
                    var payload: [String: Any] = ["profile_id": profile.id, "label": label, "auto_refresh": autoRefresh]
                    if ready { payload["model_id"] = modelID }
                    perform("providers.update", payload, success: L("حُفظ إعداد الاتصال."))
                }.buttonStyle(.borderedProminent).disabled(working || model.health == nil)
            }.padding(18)
        }
        .onAppear { profileID = profile.id; modelID = profile.modelId; label = profile.label ?? ""; autoRefresh = profile.autoRefresh ?? true }
        .confirmationDialog(L("حذف هذا الاتصال؟"), isPresented: $deleting, titleVisibility: .visible) {
            Button(L("حذف الاتصال"), role: .destructive) { perform("providers.delete", ["profile_id": profile.id], success: L("حُذف الاتصال.")) }
            Button(L("إلغاء"), role: .cancel) {}
        } message: { Text(L("ستُزال بيانات الدخول والاتصال من القائمة. ستحتاج الوكلاء المرتبطة به إلى اختيار اتصال آخر. تبقى المحادثات والمسودات محفوظة.")) }
        .confirmationDialog(L("فصل هذا الاتصال؟"), isPresented: $disconnecting, titleVisibility: .visible) {
            Button(L("فصل الاتصال"), role: .destructive) { perform("providers.disconnect", ["profile_id": profile.id], success: L("تم فصل الاتصال على هذا الجهاز.")) }
            Button(L("إلغاء"), role: .cancel) {}
        } message: { Text(L("ستُزال بيانات الدخول المحلية، وستتوقف الوكلاء التي تستخدم هذا الاتصال حتى تعيد ربطه. يمكنك إعادة تسجيل الدخول لاحقًا.")) }
        .sheet(isPresented: $signingIn) {
            VStack(spacing: 0) {
                ProviderSignInView(existingProfileID: profile.id, onConnected: { _ in signingIn = false })
                HStack { Spacer(); Button(L("إغلاق")) { signingIn = false }.keyboardShortcut(.cancelAction) }.padding(18)
            }.frame(width: 520, height: 380)
                .environment(\.layoutDirection, interfaceLanguage == "en" ? .leftToRight : .rightToLeft)
        }
        .sheet(isPresented: $editing) {
            CredentialEditor(text: $credentialText, profile: profile, fields: model.catalog?.providers.first { $0.id == profile.providerKey }?.credentialFields ?? ["api_key"]) {
                try ProviderCredentials.saveJSON(credentialText, workspace: model.workspace, profileID: profile.id)
                perform("providers.reconnect", ["profile_id": profile.id], success: L("حُفظ الملف. تحقّق من الاتصال الآن."))
            }
        }
    }
    private func editCredentials() {
        do {
            credentialText = try ProviderCredentials.read(workspace: model.workspace, profileID: profile.id)
            if credentialText.trimmingCharacters(in: .whitespacesAndNewlines) == "{}" {
                let fields = model.catalog?.providers.first { $0.id == profile.providerKey }?.credentialFields ?? ["api_key"]
                let template = Dictionary(uniqueKeysWithValues: fields.map { ($0, "") })
                credentialText = String(decoding: try JSONSerialization.data(withJSONObject: template, options: [.prettyPrinted, .sortedKeys]), as: UTF8.self)
            }
            editing = true
        } catch { failed = true; message = error.localizedDescription }
    }
    private func revealCredentials() {
        do {
            let url = try ProviderCredentials.fileURL(workspace: model.workspace, profileID: profile.id)
            if !FileManager.default.fileExists(atPath: url.path) { try ProviderCredentials.saveJSON("{}", workspace: model.workspace, profileID: profile.id) }
            NSWorkspace.shared.activateFileViewerSelecting([url])
        } catch { failed = true; message = error.localizedDescription }
    }
    private func perform(_ command: String, _ payload: [String: Any], success: String) {
        working = true; message = nil; failed = false
        Task {
            defer { working = false }
            do { _ = try await model.call(command, payload); try await model.refresh(); message = success }
            catch { failed = true; message = error.localizedDescription; try? await model.refresh() }
        }
    }
}

private struct CredentialEditor: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var text: String
    let profile: ProviderProfile
    let fields: [String]
    let save: () throws -> Void
    @State private var values: [String: String] = [:]
    @State private var failure: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(L("بيانات اتصال {0}", profile.displayName)).font(.title2.weight(.semibold))
            Text(L("ألصق بيانات الدخول لهذا المزوّد. تُحفظ على جهازك فقط.")).font(.callout).foregroundStyle(.secondary)
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    ForEach(fields, id: \.self) { field in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(credentialLabel(field)).font(.callout.weight(.medium))
                            if field == "service_account_info" {
                                TextEditor(text: binding(field)).font(.body.monospaced()).frame(height: 160)
                                    .environment(\.layoutDirection, .leftToRight)
                            } else {
                                SecureField(L("ألصق المفتاح هنا"), text: binding(field)).textFieldStyle(.roundedBorder).controlSize(.large)
                                    .environment(\.layoutDirection, .leftToRight).accessibilityLabel(credentialLabel(field))
                            }
                        }
                    }
                }.padding(2)
            }
            if let failure { Text(L(failure)).foregroundStyle(.red).font(.callout) }
            HStack {
                Button(L("إلغاء"), role: .cancel) { text = ""; dismiss() }.keyboardShortcut(.cancelAction)
                Spacer()
                Button(L("حفظ المفتاح")) {
                    do {
                        var object = (try? JSONSerialization.jsonObject(with: Data(text.utf8))) as? [String: Any] ?? [:]
                        for field in fields {
                            let value = values[field] ?? ""
                            if field == "service_account_info", !value.isEmpty {
                                object[field] = try JSONSerialization.jsonObject(with: Data(value.utf8))
                            } else { object[field] = value }
                        }
                        text = String(decoding: try JSONSerialization.data(withJSONObject: object), as: UTF8.self)
                        try save(); text = ""; dismiss()
                    } catch { failure = error.localizedDescription }
                }.buttonStyle(.borderedProminent)
            }
        }.padding(28).frame(width: 500, height: 380).editorialPresentation()
        .onAppear {
            let object = (try? JSONSerialization.jsonObject(with: Data(text.utf8))) as? [String: Any] ?? [:]
            for field in fields {
                if let value = object[field] as? String { values[field] = value }
                else if let value = object[field], let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted]) { values[field] = String(decoding: data, as: UTF8.self) }
            }
        }
    }
    private func binding(_ field: String) -> Binding<String> { Binding(get: { values[field] ?? "" }, set: { values[field] = $0 }) }
}

private func settingsHeading(_ title: String, subtitle: String) -> some View {
    VStack(alignment: .leading, spacing: 6) {
        Text(title).font(.title2.weight(.semibold))
        Text(subtitle).font(.callout).foregroundStyle(.secondary)
    }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
}

private func credentialLabel(_ field: String) -> String {
    ["api_key": L("مفتاح API"), "aws_access_key_id": L("معرّف مفتاح AWS"), "aws_secret_access_key": L("المفتاح السري AWS"), "aws_session_token": L("رمز جلسة AWS"), "azure_management_token": L("رمز إدارة Azure"), "portkey_api_key": L("مفتاح Portkey"), "virtual_key": L("المفتاح الافتراضي"), "auth_token": L("رمز المصادقة")][field] ?? field
}

private func fieldLabel(_ field: String) -> String {
    ["base_url": L("عنوان الخدمة"), "host": L("عنوان الخادم"), "api_base": L("عنوان API"), "region": L("المنطقة"), "aws_region": L("منطقة AWS"), "project_id": L("معرّف المشروع"), "location": L("الموقع"), "subscription_id": L("معرّف الاشتراك"), "resource_group": L("مجموعة الموارد"), "account_name": L("اسم الحساب"), "timeout": L("مهلة الاتصال"), "organization": L("المؤسسة")][field] ?? field
}

// Isolate technical identifiers without changing the surrounding interface direction.
func technicalIdentifier(_ value: String) -> String {
    "\u{2066}" + value + "\u{2069}"
}
