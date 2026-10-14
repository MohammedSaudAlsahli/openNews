import SwiftUI

/// One quiet disclosure for real execution events; source references stay with the answer.
struct ConversationActivity: View {
    let execution: ConversationExecution?
    let contextInfo: ConversationContextInfo?
    let title: String
    let elapsed: Int
    let active: Bool
    @State private var expanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $expanded) {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(stepKinds, id: \.self) { kind in
                    let steps = (execution?.steps ?? []).filter { $0.kind == kind }
                    DisclosureGroup {
                        VStack(alignment: .leading, spacing: 6) {
                            ForEach(steps) { step in
                                if !step.detail.isEmpty {
                                    Text(verbatim: step.detail)
                                        .font(.caption).foregroundStyle(.secondary)
                                        .textSelection(.enabled)
                                        .environment(\.layoutDirection, RichTextDirection.detect(step.detail))
                                }
                            }
                        }.padding(.vertical, 6)
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: symbol(kind)).frame(width: 16).accessibilityHidden(true)
                            Text(label(kind))
                            Text("· \(steps.count)").monospacedDigit()
                        }.font(.caption).foregroundStyle(.secondary)
                    }
                }
                if let summary = execution?.reasoningSummary, !summary.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    RichTextView(text: summary.replacingOccurrences(of: "****", with: "**\n\n**").trimmingCharacters(in: .whitespacesAndNewlines), fontSize: 13, lineSpacing: 4)
                        .foregroundStyle(.secondary)
                }
                if let context = contextInfo ?? execution?.contextInfo, context.totalMessages > 0 {
                    DisclosureGroup(L("سياق هذه المحادثة")) {
                        Text(L("{0} رسائل في السياق من أصل {1} محفوظة", context.includedMessages, context.totalMessages))
                            .padding(.top, 4)
                    }.font(.caption).foregroundStyle(.secondary)
                }
            }.padding(.leading, 20).padding(.top, 12).padding(.bottom, 6)
        } label: {
            HStack(spacing: 8) {
                if active { ProgressView().controlSize(.mini) }
                if active {
                    Text(title).font(.callout).lineLimit(2)
                    Text(Self.duration(elapsed)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                } else {
                    Text(L("عمل لمدة {0}", Self.duration(elapsed)))
                        .font(.callout).foregroundStyle(.secondary).monospacedDigit()
                }
            }
        }
        .disclosureGroupStyle(ExecutionDisclosureStyle())
        .tint(.secondary)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var stepKinds: [String] {
        var seen = Set<String>()
        return (execution?.steps ?? []).compactMap { step in
            guard step.kind != "context", seen.insert(step.kind).inserted else { return nil }
            return step.kind
        }
    }

    static func duration(_ seconds: Int) -> String {
        let value = max(0, seconds)
        if value >= 3600 { return L("{0} س {1} د {2} ث", value / 3600, (value % 3600) / 60, value % 60) }
        if value >= 60 { return L("{0} د {1} ث", value / 60, value % 60) }
        return L("{0} ث", value)
    }

    private func label(_ kind: String) -> String {
        switch kind {
        case "context": return L("تجهيز سياق المحادثة")
        case "history": return L("البحث في الرسائل السابقة")
        case "library": return L("البحث في الأخبار المحفوظة")
        case "web": return L("البحث في الويب")
        case "reading": return L("قراءة مصدر")
        default: return L("إعداد الرد")
        }
    }
    private func symbol(_ kind: String) -> String {
        switch kind {
        case "context": return "text.bubble"
        case "history": return "clock.arrow.circlepath"
        case "library": return "books.vertical"
        case "web": return "globe"
        case "reading": return "doc.text"
        default: return "sparkles"
        }
    }
}

/// Native SwiftUI button with the disclosure indicator after the duration.
private struct ExecutionDisclosureStyle: DisclosureGroupStyle {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    func makeBody(configuration: Configuration) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation(reduceMotion ? nil : .easeOut(duration: 0.18)) {
                    configuration.isExpanded.toggle()
                }
            } label: {
                HStack(spacing: 6) {
                    configuration.label
                    Image(systemName: configuration.isExpanded ? "chevron.down" : "chevron.forward")
                        .font(.caption).foregroundStyle(.secondary).accessibilityHidden(true)
                }.contentShape(Rectangle())
            }.buttonStyle(.plain)
                .accessibilityValue(L(configuration.isExpanded ? "موسّع" : "مطوي"))
            if configuration.isExpanded { configuration.content }
        }
    }
}
