import SwiftUI
import AppKit

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
            Text(role == "writer" ? L("للمحادثة وإنشاء المسودات.") : role == "news" ? L("لتلخيص الأخبار الجديدة في الخلفية؛ اختر نموذجًا اقتصاديًا يناسبك.") : L("لاستخراج تقنيات الكتابة من أمثلتك."))
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
