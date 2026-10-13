import SwiftUI
import AppKit

struct ConnectionsSettingsView: View {
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
