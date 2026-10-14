import SwiftUI

/// Native, reading-oriented comparison with neutral context and marked changes.
struct ArticleRevisionDiff: View {
    let difference: String
    let initialRevision: Bool

    var body: some View {
        LazyVStack(alignment: .leading, spacing: 0) {
            if initialRevision {
                Label(L("أول نسخة محفوظة"), systemImage: "clock")
                    .font(.callout).foregroundStyle(.secondary).padding(.bottom, 8)
            }
            ForEach(Array(difference.components(separatedBy: "\n").enumerated()), id: \.offset) { _, line in
                if line.hasPrefix("--- ") {
                    Text(fieldName(line)).font(.headline).padding(.top, 20).padding(.bottom, 10)
                } else if line.hasPrefix("+++ ") {
                    EmptyView()
                } else if line.hasPrefix("@@") {
                    if !initialRevision { Divider().padding(.bottom, 8) }
                } else if !line.isEmpty {
                    changeLine(line)
                }
            }
        }
    }

    @ViewBuilder private func changeLine(_ line: String) -> some View {
        let added = line.hasPrefix("+") && !initialRevision
        let removed = line.hasPrefix("-") && !initialRevision
        let color: Color = added ? .green : removed ? .red : .clear
        let text = String(line.dropFirst())
        if text.trimmingCharacters(in: .whitespaces).isEmpty {
            Color.clear.frame(height: 8).accessibilityHidden(true)
        } else if initialRevision {
            paragraph(text).padding(.vertical, 4)
        } else {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: removed ? "minus" : "plus")
                    .font(.caption.weight(.semibold)).foregroundStyle(color)
                    .frame(width: 14).padding(.top, 3)
                    .accessibilityLabel(added ? L("نص مضاف") : removed ? L("نص محذوف") : "")
                    .accessibilityHidden(!added && !removed)
                paragraph(text)
            }
            .padding(.horizontal, 12).padding(.vertical, 8)
            .background(color.opacity(0.10))
            .overlay(alignment: .leading) { Rectangle().fill(color).frame(width: 2) }
        }
    }

    private func paragraph(_ text: String) -> some View {
        Text(text).font(.body).lineSpacing(3).textSelection(.enabled)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
            .environment(\.layoutDirection, RichTextDirection.detect(text))
    }

    private func fieldName(_ line: String) -> String {
        let key = line.dropFirst(4).components(separatedBy: " ").first ?? ""
        let names = ["title": "العنوان", "text": "نص المقالة", "summary": "الملخص",
                     "url": "رابط المصدر", "published_at": "تاريخ النشر", "body_status": "حالة المحتوى"]
        return L(names[key] ?? key)
    }
}
