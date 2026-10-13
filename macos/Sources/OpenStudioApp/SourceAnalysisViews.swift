import SwiftUI
import AppKit

struct SourceTechniqueSuggestion: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject var model: StudioModel
    let technique: TechniqueCard
    @State private var statement = ""
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 10) {
            Text(technique.name).font(.body.weight(.semibold))
            Text(technique.description).font(.callout)
            Text(technique.applicability).font(.caption).foregroundStyle(.secondary)
            ProseText(text: technique.excerpt, fontSize: 13)
                .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 5))
            Text(technique.method == "agno" ? L("اقتراح بالذكاء الاصطناعي") : L("اقتراح من فحص بنية النص")).font(.caption2).foregroundStyle(.secondary)
            if technique.status == "approved" {
                Label(L("مضافة إلى أسلوبي"), systemImage: "checkmark").font(.caption).foregroundStyle(.secondary)
            } else {
                DisclosureGroup(L("تعديل صياغة القاعدة")) {
                    TextField(L("القاعدة"), text: $statement, axis: .vertical).lineLimit(3...8).textFieldStyle(.roundedBorder)
                }.font(.caption)
                Button(L("أضف إلى أسلوبي")) {
                    Task { await model.perform("dna.approve", ["technique_id": technique.id, "statement": statement], message: L("أُضيفت القاعدة إلى أسلوبك.")) }
                }.disabled(model.busy || statement.trimmingCharacters(in: .whitespacesAndNewlines).count < 3 || statement.unicodeScalars.count > 1500)
            }
        }.onAppear { if statement.isEmpty { statement = technique.description } }
    }
}

struct AnalyzeSourceSheet: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject var model: StudioModel
    @Environment(\.dismiss) var dismiss
    @Environment(\.openSettings) var openSettings
    let source: Source
    @State private var profile = ""
    @State private var modelID = ""
    @State private var modelReady = false
    @AppStorage(ModelPermission.key) private var consent = false
    @State private var submitting = false
    @State private var errorMessage: String?
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 18) {
            Text(L("تحليل بالذكاء الاصطناعي")).font(.title2.weight(.semibold))
            Text(source.title).foregroundStyle(.secondary)
            if model.snapshot?.profiles.isEmpty != false {
                Text(L("أضف نموذجًا من الإعدادات أولًا. يمكنك استخدام التحليل المحلي الآن دون إعداد.")).font(.callout)
                Button(L("فتح الإعدادات")) { dismiss(); openSettings() }
            } else {
                ConnectionModelPicker(profileID: $profile, modelID: $modelID, ready: $modelReady).disabled(submitting)
                if !consent { ModelPermissionNotice() }
                Text(L("يطلب هذا الإجراء تحليلًا جديدًا عند تغيير النموذج، حتى إذا سبق فحص النص محليًا. الاقتراحات تحتاج موافقتك قبل إضافتها لأسلوبك.")).font(.caption).foregroundStyle(.secondary)
            }
            HStack {
                Button(L("إلغاء"), role: .cancel) { dismiss() }.keyboardShortcut(.cancelAction).disabled(submitting)
                Spacer()
                if submitting { ProgressView().controlSize(.small) }
                Button(L("ابدأ التحليل")) { submit() }.buttonStyle(.borderedProminent)
                    .disabled(profile.isEmpty || !modelReady || !consent || submitting || source.rightsStatus == "unknown")
            }
        }.padding(24).frame(width: 480).editorialPresentation()
        .interactiveDismissDisabled(submitting)
        .onAppear {
            if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "analyst" }) {
                profile = assignment.profileId; modelID = assignment.modelId
            } else if let profiles = model.snapshot?.profiles, profiles.count == 1 { profile = profiles[0].id }
        }
        .alert(L("تعذّر بدء التحليل"), isPresented: Binding(get: { errorMessage != nil }, set: { if !$0 { errorMessage = nil } })) {
            Button(L("حسنًا"), role: .cancel) { errorMessage = nil }
        } message: { Text(L(errorMessage ?? "")) }
    }
    private func submit() {
        guard consent && modelReady && !submitting else { return }
        submitting = true
        Task {
            defer { submitting = false }
            do {
                _ = try await model.call("analysis.run", ["item_ids": [source.id], "profile_id": profile, "model_id": modelID, "mode": "explicit_rebuild", "consent": true, "idempotency_key": UUID().uuidString])
                try await model.refresh()
                model.notice = L("بدأ التحليل. ستظهر الاقتراحات بجوار المصدر.")
                dismiss()
            } catch { errorMessage = error.localizedDescription }
        }
    }
}
