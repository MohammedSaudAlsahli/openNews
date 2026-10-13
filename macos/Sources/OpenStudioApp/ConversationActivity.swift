import SwiftUI

/// Describes observable work and the frozen sources in chat.progress. Does not
/// infer a model's private reasoning or pretend a browser/tool ran.
struct ConversationActivity: View {
    let progress: ConversationProgress
    @ObservedObject var model: StudioModel
    @State private var expanded = false
    var body: some View {
        DisclosureGroup(isExpanded: $expanded) {
            VStack(alignment: .leading, spacing: 10) {
                Label(L("تم تجهيز سياق المحادثة"), systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.secondary)
                Label(L(stageLabel), systemImage: progress.stage == "validating" ? "checkmark.shield" : "waveform")
                if !progress.citations.isEmpty {
                    Text(L("يراجع {0} مصادر. ستظهر مراجع الرد مرة واحدة بعد اكتماله.", DisplayFormat.integer(progress.citations.count)))
                        .foregroundStyle(.secondary)
                }
                Text(L("هذا سجل التنفيذ؛ لا يعرض التفكير الداخلي للنموذج."))
                    .font(.caption).foregroundStyle(.secondary)
            }.font(.callout).padding(.top, 10)
        } label: {
            Label(L("نشاط المساعد") + (progress.citations.isEmpty ? "" : " · " + L("{0} مصادر", DisplayFormat.integer(progress.citations.count))), systemImage: "list.bullet.rectangle")
                .font(.callout.weight(.medium))
        }.padding(14).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
    }
    private var stageLabel: String {
        if progress.stage == "validating" { return "جارٍ التحقق من الرد والمراجع قبل الحفظ" }
        if progress.stage == "researching" { return L("يبحث عن تقارير حديثة ويقرأ المصادر العامة") }
        if ["queued", "waiting_model"].contains(progress.stage) { return L("بانتظار بدء طلب النموذج") }
        return progress.message.isEmpty ? "أُرسل الطلب؛ بانتظار أول نص من النموذج" : "جارٍ استقبال الرد من النموذج"
    }
}
