import SwiftUI
import AppKit

/// Keeps a proposed post visible and sends edits to the saved draft editor.
struct ConversationDraftCard: View {
    let output: ConversationOutput
    let openDraft: (String) -> Void
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(output.format == "x_post" ? L("مسودة منشور X") : output.title,
                  systemImage: "square.and.pencil").font(.callout.weight(.semibold))
            if let text = output.text, !text.isEmpty {
                Text(verbatim: text).font(.body).textSelection(.enabled)
                    .environment(\.layoutDirection, RichTextDirection.detect(text))
                    .frame(maxWidth: .infinity, alignment: .leading)
                if output.format == "x_post" {
                    Text(L("{0} / 280 حرفًا", text.count)).font(.caption).foregroundStyle(.secondary)
                }
            }
            HStack(spacing: 12) {
                Button(L("تعديل المسودة"), systemImage: "pencil") { openDraft(output.draftId) }
                    .buttonStyle(.borderedProminent)
                if let text = output.text, !text.isEmpty {
                    Button(copied ? L("تم النسخ") : L("نسخ النص"), systemImage: copied ? "checkmark" : "doc.on.doc") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(text, forType: .string)
                        copied = true
                    }.buttonStyle(.bordered)
                }
            }
        }
        .padding(18)
        .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color(nsColor: .separatorColor).opacity(0.5)))
    }
}
