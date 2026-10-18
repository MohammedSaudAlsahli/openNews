import SwiftUI

struct NewsMemorySettings: View {
    @EnvironmentObject private var model: StudioModel
    @AppStorage("appLanguage") private var language = "ar"
    @State private var failure: String?
    @State private var saving = false
    @State private var choosingEmbedding = false
    @State private var inspecting = false

    var body: some View {
        Section(L("البحث الذكي في الأخبار")) {
            Toggle(L("البحث بالمعنى على هذا الجهاز"), isOn: Binding(
                get: { model.searchStatus?.enabled == true },
                set: { enabled in update("news.search.set", ["enabled": enabled]) }))
                .disabled(saving)
            Text(L("اختر نموذجًا من Ollama للبحث بالمعنى. الأخبار والبحث بالكلمات يعملان مباشرة دون تحميل نماذج."))
                .font(.caption).foregroundStyle(.secondary)
            Button(L("اختيار نموذج البحث وإدارة التحميل")) { choosingEmbedding = true }
                .sheet(isPresented: $choosingEmbedding) {
                    VStack(spacing: 0) {
                        HStack { Spacer(); Button(L("تم")) { choosingEmbedding = false } }.padding()
                        LocalSummaryModels(embedding: true)
                    }.frame(width: 820, height: 620)
                    .environment(\.layoutDirection, language == "ar" ? .rightToLeft : .leftToRight)
                    .environment(\.locale, Locale(identifier: language))
                }
            if let status = model.searchStatus {
                Text(status.model).font(.caption).foregroundStyle(.secondary)
                LabeledContent(L("أخبار مفهرسة بالمعنى"), value: DisplayFormat.integer(status.semantic))
                ProgressView(value: Double(status.semantic), total: Double(max(1, status.semantic + status.pending)))
                LabeledContent(L("بانتظار الفهرسة"), value: DisplayFormat.integer(status.pending))
                Text(L("يُفهرس العنوان والنص المتاح، أو المقتطف عند غياب النص الكامل. لا تحتاج الفهرسة إلى انتظار التلخيص."))
                    .font(.caption).foregroundStyle(.secondary)
                DisclosureGroup(L("تفاصيل الفهرسة"), isExpanded: $inspecting) {
                    if inspecting { SearchIndexDetails() }
                }

                if status.enabled {
                    Label(phase(status.phase), systemImage: status.phase == "unavailable" ? "exclamationmark.circle" : "internaldrive")
                        .font(.caption).foregroundStyle(.secondary)
                    if !status.currentTitle.isEmpty {
                        Text(status.currentTitle).font(.caption).lineLimit(2)
                    }
                }
            }
        }
        if let failure {
            Section { Label(failure, systemImage: "exclamationmark.circle").foregroundStyle(.red).textSelection(.enabled) }
        }
    }

    private func phase(_ value: String) -> String {
        switch value {
        case "resting": return L("راحة بين الدفعات لتخفيف استهلاك الجهاز")
        case "cooling": return L("متوقف مؤقتًا حتى تنخفض حرارة الجهاز")
        case "low_power": return L("متوقف مؤقتًا أثناء وضع توفير الطاقة")
        case "waiting_device": return L("بانتظار التحقق من حالة الجهاز")
        case "waiting_model": return L("بانتظار انتهاء طلبك؛ المحادثة لها الأولوية")
        case "needs_download": return L("اختر نموذجًا وحمّله لتفعيل البحث بالمعنى")
        case "preparing": return L("يجهّز النموذج المحلي ويفهرس الأخبار…")
        case "indexing": return L("جارٍ فهرسة الأخبار المحفوظة…")
        case "ready": return L("البحث بالمعنى جاهز")
        case "unavailable": return L("تعذّر تجهيز البحث بالمعنى. البحث بالكلمات متاح، وستتم المحاولة تلقائيًا.")
        default: return L("بانتظار تجهيز الأخبار")
        }
    }

    private func update(_ command: String, _ payload: [String: Any]) {
        saving = true; failure = nil
        Task {
            defer { saving = false }
            do {
                _ = try await model.call(command, payload)
                try await model.refresh()
            } catch { failure = error.localizedDescription }
        }
    }
}
