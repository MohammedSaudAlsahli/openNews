import SwiftUI

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
                    NativeChoicePicker(title: L("الاتصال"), selection: $profileID,
                                       choices: [PickerChoice(value: "", label: L("اختر اتصالًا"))]
                                       + profiles.map { PickerChoice(value: $0.id, label: $0.displayName) })

                }
            }
            if !profileID.isEmpty {
                VStack(alignment: .leading, spacing: 9) {
                    Text(L("النموذج")).font(.callout.weight(.medium))
                    HStack(spacing: 8) {
                        Picker(L("النموذج"), selection: $modelID) {
                            Text(loading ? L("جارٍ جلب النماذج…") : L("اختر نموذجًا")).tag("")
                            ForEach(result?.models ?? []) { item in
                                Text(item.name).tag(item.id).disabled(!item.available)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.menu)
                        .fixedSize(horizontal: true, vertical: false)
                        .disabled(loading || (result?.models.isEmpty ?? true))
                        .accessibilityLabel(L("اختيار النموذج"))
                        if (result?.models.count ?? 0) > 8 {
                            Button { choosingModel = true } label: {
                                Image(systemName: "magnifyingglass")
                            }
                            .buttonStyle(.bordered)
                            .help(L("ابحث عن نموذج"))
                            .accessibilityLabel(L("ابحث عن نموذج"))
                            .disabled(loading)
                        }
                    }
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
                List(selection: $selectedID) {
                    ForEach(results) { item in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.name)
                            if item.name != item.id {
                                Text(technicalIdentifier(item.id)).font(.caption).foregroundStyle(.secondary)
                            }
                            if !item.available { Text(L("غير متاح")).font(.caption).foregroundStyle(.secondary) }
                        }
                        .tag(item.id)
                        .disabled(!item.available)
                    }
                }
                .listStyle(.inset)
                .frame(height: min(CGFloat(results.count) * 62, 360))
                .onChange(of: selectedID) { _, _ in dismiss() }
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
