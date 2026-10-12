import SwiftUI

/// Window-independent form state; closing Settings never discards an in-progress agent.
struct AgentEditorState {
    var selection: String = "writer"
    var name: String = ""
    var instructions: String = ""
    var profileID: String = ""
    var modelID: String = ""
    var ready: Bool = false
    var saving: Bool = false
    var baseline: [String] = ["", "", "", ""]
    var pendingSelection: String? = nil
    var confirmNavigation: Bool = false
    var confirmDelete: Bool = false
    var failure: String? = nil
    var notice: String? = nil
    var hasUnsavedChanges: Bool {
        selection != "writer" && selection != "analyst" && [name, instructions, profileID, modelID] != baseline
    }
}

struct AgentsSettingsView: View {
    @EnvironmentObject private var model: StudioModel
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    let onSetupConnection: () -> Void
    private var selection: String {
        get { model.agentEditor.selection }
        nonmutating set { model.agentEditor.selection = newValue }
    }
    private var name: String {
        get { model.agentEditor.name }
        nonmutating set { model.agentEditor.name = newValue }
    }
    private var instructions: String {
        get { model.agentEditor.instructions }
        nonmutating set { model.agentEditor.instructions = newValue }
    }
    private var profileID: String {
        get { model.agentEditor.profileID }
        nonmutating set { model.agentEditor.profileID = newValue }
    }
    private var modelID: String {
        get { model.agentEditor.modelID }
        nonmutating set { model.agentEditor.modelID = newValue }
    }
    private var ready: Bool {
        get { model.agentEditor.ready }
        nonmutating set { model.agentEditor.ready = newValue }
    }
    private var saving: Bool {
        get { model.agentEditor.saving }
        nonmutating set { model.agentEditor.saving = newValue }
    }
    private var baseline: [String] {
        get { model.agentEditor.baseline }
        nonmutating set { model.agentEditor.baseline = newValue }
    }
    private var pendingSelection: String? {
        get { model.agentEditor.pendingSelection }
        nonmutating set { model.agentEditor.pendingSelection = newValue }
    }
    private var confirmNavigation: Bool {
        get { model.agentEditor.confirmNavigation }
        nonmutating set { model.agentEditor.confirmNavigation = newValue }
    }
    private var confirmDelete: Bool {
        get { model.agentEditor.confirmDelete }
        nonmutating set { model.agentEditor.confirmDelete = newValue }
    }
    private var failure: String? {
        get { model.agentEditor.failure }
        nonmutating set { model.agentEditor.failure = newValue }
    }
    private var notice: String? {
        get { model.agentEditor.notice }
        nonmutating set { model.agentEditor.notice = newValue }
    }

    private var isBuiltin: Bool { selection == "writer" || selection == "analyst" }
    private var values: [String] { [name, instructions, profileID, modelID] }
    private var dirty: Bool { !isBuiltin && values != baseline }
    private var canSave: Bool {
        !saving && ready && !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
        !instructions.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && name.count <= 120 && instructions.count <= 12000
    }

    var body: some View {
        let _ = interfaceLanguage
        HStack(alignment: .top, spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                Text(L("الوكلاء الأساسيون")).font(.caption).foregroundStyle(.secondary)
                selectionButton(L("الكاتب"), id: "writer", icon: "pencil")
                selectionButton(L("المحلل"), id: "analyst", icon: "text.magnifyingglass")
                Divider()
                Text(L("وكلاؤك")).font(.caption).foregroundStyle(.secondary)
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(model.customAgents) { agent in
                            selectionButton(agent.name, id: agent.id, icon: "person.crop.square")
                        }
                    }
                }
                Button { navigate("new") } label: { Label(L("وكيل جديد"), systemImage: "plus") }
            }.frame(width: 170).padding()
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if isBuiltin {
                        Text(selection == "writer" ? L("الكاتب") : L("المحلل")).font(.title2.bold())
                        AgentModelAssignment(role: selection, title: selection == "writer" ? L("الكاتب") : L("المحلل"))
                            .id(selection)
                    } else {
                        editor
                    }
                    if let failure { Text(L(failure)).foregroundStyle(.red).textSelection(.enabled) }
                    if let notice { Text(L(notice)).foregroundStyle(.secondary) }
                }.padding().frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .disabled(saving)
        .interactiveDismissDisabled(dirty || saving)
        .alert(L("حفظ تغييرات الوكيل؟"), isPresented: $model.agentEditor.confirmNavigation) {
            Button(L("حفظ")) { Task { await save(thenNavigate: true) } }.disabled(!canSave)
            Button(L("تجاهل التغييرات"), role: .destructive) { if let target = pendingSelection { load(target) } }
            Button(L("إلغاء"), role: .cancel) { pendingSelection = nil }
        } message: { Text(L("لديك تعديلات لم تُحفظ على هذا الوكيل.")) }
        .alert(L("حذف الوكيل؟"), isPresented: $model.agentEditor.confirmDelete) {
            Button(L("حذف"), role: .destructive) { Task { await delete() } }
            Button(L("إلغاء"), role: .cancel) {}
        } message: { Text(L("ستبقى المحادثات والمسودات السابقة محفوظة.")) }
    }

    private var editor: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(selection == "new" ? L("وكيل جديد") : L("تعديل الوكيل")).font(.title2.bold())
            Text(L("حدد تخصص الوكيل وتعليماته، ثم اختره في المحادثة.")).foregroundStyle(.secondary)
            TextField(L("اسم الوكيل"), text: $model.agentEditor.name).textFieldStyle(.roundedBorder)
            Text(L("تعليمات الوكيل")).font(.headline)
            TextEditor(text: $model.agentEditor.instructions).font(.body).frame(minHeight: 150)
                .overlay(RoundedRectangle(cornerRadius: 5).stroke(Color(nsColor: .separatorColor)))
                .accessibilityLabel(L("تعليمات الوكيل"))
            Text(L("يستخدم الوكيل المصادر المرفقة وقواعد التحقق نفسها؛ لا يحصل على أدوات أو صلاحيات إضافية."))
                .font(.caption).foregroundStyle(.secondary)
            if model.snapshot?.profiles.isEmpty != false {
                SetupConnectionCTA(onSetupConnection: { navigate("connection") })
            } else {
                ConnectionModelPicker(profileID: $model.agentEditor.profileID, modelID: $model.agentEditor.modelID, ready: $model.agentEditor.ready).id(selection)
            }
            HStack {
                if selection != "new" {
                    Button(L("حذف الوكيل"), role: .destructive) { confirmDelete = true }
                }
                Spacer()
                if saving { ProgressView().controlSize(.small) }
                Button(L("حفظ الوكيل")) { Task { await save() } }.buttonStyle(.borderedProminent).disabled(!canSave)
            }
        }
    }

    private func selectionButton(_ title: String, id: String, icon: String) -> some View {
        Button { navigate(id) } label: {
            Label(title, systemImage: icon).frame(maxWidth: .infinity, alignment: .leading)
                .padding(7).background(selection == id ? Color.accentColor.opacity(0.15) : Color.clear, in: RoundedRectangle(cornerRadius: 6))
        }.buttonStyle(.plain)
    }

    private func navigate(_ target: String) {
        if target == "connection" { onSetupConnection(); return }
        guard target != selection else { return }
        if dirty { pendingSelection = target; confirmNavigation = true }
        else { load(target) }
    }

    private func load(_ target: String) {
        pendingSelection = nil
        if target == "connection" { onSetupConnection(); return }
        selection = target; failure = nil; notice = nil; ready = false
        let agent = model.customAgents.first { $0.id == target }
        name = agent?.name ?? ""; instructions = agent?.instructions ?? ""
        profileID = agent?.profileId ?? ""; modelID = agent?.modelId ?? ""
        baseline = values
    }

    private func save(thenNavigate: Bool = false) async {
        guard canSave else { return }
        saving = true; failure = nil; notice = nil
        defer { saving = false }
        var payload: [String: Any] = ["name": name, "instructions": instructions, "profile_id": profileID, "model_id": modelID]
        if selection != "new" { payload["id"] = selection }
        do {
            let result = try await model.decoded("agents.save", payload, as: SavedCustomAgent.self)
            selection = result.agentId; baseline = values
            try await model.refresh()
            notice = L("حُفظ الوكيل.")
            if thenNavigate, let target = pendingSelection { load(target) }
        } catch { failure = error.localizedDescription }
    }

    private func delete() async {
        saving = true; failure = nil
        defer { saving = false }
        do {
            _ = try await model.call("agents.delete", ["agent_id": selection])
            model.customAgents.removeAll { $0.id == selection }
            load("writer")
            try await model.refresh()
        } catch { failure = error.localizedDescription }
    }
}

private struct SetupConnectionCTA: View {
    let onSetupConnection: () -> Void
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(L("أضف اتصالًا بالنموذج لحفظ الوكيل واستخدامه."))
            Button(L("إعداد الاتصال"), action: onSetupConnection)
        }
    }
}
