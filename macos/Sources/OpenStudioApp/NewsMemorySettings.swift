import SwiftUI

struct NewsMemorySettings: View {
    @EnvironmentObject private var model: StudioModel
    @AppStorage("appLanguage") private var language = "ar"
    var chooseModel: () -> Void
    @State private var saving = false

    var body: some View {
        Section(L("البحث الذكي في الأخبار")) {
            Toggle(L("البحث بالمعنى على هذا الجهاز"), isOn: Binding(
                get: { model.searchStatus?.enabled == true },
                set: { enabled in update("news.search.set", ["enabled": enabled]) }))
                .disabled(saving)
            Text(L("يحمّل EmbeddingGemma مرة واحدة، ثم يفهرس الأخبار محليًا. يبقى البحث بالكلمات متاحًا أثناء التجهيز."))
                .font(.caption).foregroundStyle(.secondary)
            if let status = model.searchStatus {
                LabeledContent(L("أخبار مفهرسة بالمعنى"), value: DisplayFormat.integer(status.semantic))
                if status.enabled {
                    Label(phase(status.phase), systemImage: status.phase == "unavailable" ? "exclamationmark.circle" : "internaldrive")
                        .font(.caption).foregroundStyle(.secondary)
                    if !status.currentTitle.isEmpty {
                        Text(status.currentTitle).font(.caption).lineLimit(2)
                    }
                }
            }
        }
        Section(L("التلخيص التلقائي")) {
            Button(L("اختيار نموذج وإدارة التلخيص"), action: chooseModel)
            if let digest = model.digestStatus {
                LabeledContent(L("ملخص جاهز"), value: DisplayFormat.integer(digest.prepared))
                LabeledContent(L("مقالة تنتظر التلخيص"), value: DisplayFormat.integer(digest.pending))
            }
        }
    }

    private func phase(_ value: String) -> String {
        switch value {
        case "preparing": return L("يجهّز النموذج المحلي ويفهرس الأخبار…")
        case "indexing": return L("جارٍ فهرسة الأخبار المحفوظة…")
        case "ready": return L("البحث بالمعنى جاهز")
        case "unavailable": return L("تعذّر تجهيز البحث بالمعنى. البحث بالكلمات متاح، وستتم المحاولة تلقائيًا.")
        default: return L("بانتظار تجهيز الأخبار")
        }
    }

    private func update(_ command: String, _ payload: [String: Any]) {
        saving = true
        Task {
            defer { saving = false }
            do {
                _ = try await model.call(command, payload)
                try await model.refresh()
            } catch { model.error = error.localizedDescription }
        }
    }
}
