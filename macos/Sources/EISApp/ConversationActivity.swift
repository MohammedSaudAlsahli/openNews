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
                    Text(L("مصادر أُرسلت مع الطلب ({0})", DisplayFormat.integer(progress.citations.count))).font(.subheadline.weight(.medium))
                    ScrollView {
                        VStack(alignment: .leading, spacing: 7) {
                            ForEach(progress.citations) { citation in
                                ActivitySource(citation: citation, model: model)
                            }
                        }
                    }.frame(maxHeight: 150)
                } else { Text(L("لا توجد أخبار مرفقة بهذا الطلب.")).foregroundStyle(.secondary) }
                Text(L("هذا سجل التنفيذ والمصادر المرفقة؛ لا يعرض التفكير الداخلي للنموذج ولا يعني أنه تصفّح الويب."))
                    .font(.caption).foregroundStyle(.secondary)
            }.font(.callout).padding(.top, 10)
        } label: {
            Label(L("نشاط المساعد") + (progress.citations.isEmpty ? "" : " · " + L("{0} مصادر", DisplayFormat.integer(progress.citations.count))), systemImage: "list.bullet.rectangle")
                .font(.callout.weight(.medium))
        }.padding(14).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
    }
    private var stageLabel: String {
        if progress.stage == "validating" { return "جارٍ التحقق من الرد والمراجع قبل الحفظ" }
        if ["queued", "waiting_model"].contains(progress.stage) { return "بانتظار بدء طلب النموذج" }
        return progress.message.isEmpty ? "أُرسل الطلب؛ بانتظار أول نص من النموذج" : "جارٍ استقبال الرد من النموذج"
    }
}

private struct ActivitySource: View {
    let citation: ConversationCitation
    @ObservedObject var model: StudioModel
    @State private var preview = false
    var body: some View {
        Button { preview.toggle() } label: {
            Label(citation.title, systemImage: "doc.text").lineLimit(2).multilineTextAlignment(.leading)
        }.buttonStyle(.link)
            .popover(isPresented: $preview) { CitationPreview(citation: citation, model: model) }
    }
}
