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
            VStack(alignment: .leading, spacing: 14) {
                if let summary = execution?.reasoningSummary, !summary.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    Text(verbatim: Self.readableSummary(summary))
                        .font(.system(size: 15)).lineSpacing(5).foregroundStyle(.secondary)
                        .textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
                        .environment(\.layoutDirection, RichTextDirection.detect(summary))
                } else if active {
                    Text(execution?.summaryTranslationState == "translating"
                         ? (execution?.summaryLanguage == "ar" ? "جارٍ تجهيز ملخص التفكير بالعربية…" : "Preparing the English thinking summary…")
                         : title).font(.callout).foregroundStyle(.secondary)
                }
                if execution?.summaryTranslationState == "unavailable" {
                    Text(execution?.summaryLanguage == "ar" ? "تعذّرت ترجمة ملخص التفكير. نشاط المصادر محفوظ أدناه." : "Thinking summary translation is unavailable. Source activity is preserved below.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                if active {
                    if let step = execution?.steps.last(where: { $0.kind != "context" }) {
                        HStack(alignment: .top, spacing: 9) {
                            Image(systemName: symbol(step.kind)).frame(width: 17)
                            Text(verbatim: step.detail.isEmpty ? label(step.kind) : ActivityEventGroup.displayDetail(step.detail))
                                .lineLimit(2).help(step.detail)
                        }.font(.callout).foregroundStyle(.secondary)
                    }
                } else {
                ForEach(ActivityEventGroup.groups(execution?.steps ?? [])) { group in
                    DisclosureGroup {
                        VStack(alignment: .leading, spacing: 9) {
                            ForEach(group.details, id: \.self) { detail in
                                if let url = ActivityEventGroup.sourceURL(detail) {
                                    Link(ActivityEventGroup.displayDetail(detail), destination: url)
                                        .underline().help(detail)
                                } else {
                                    Text(verbatim: detail).textSelection(.enabled).help(detail)
                                }
                            }
                        }
                        .font(.callout).foregroundStyle(.secondary)
                        .lineLimit(2).padding(.leading, 26).padding(.top, 10)
                    } label: {
                        HStack(spacing: 9) {
                            Image(systemName: symbol(group.kind)).frame(width: 17)
                            Text(label(group.kind))
                            if !group.details.isEmpty {
                                Text("· \(group.details.count)").monospacedDigit()
                            }
                        }.font(.callout).foregroundStyle(.secondary)
                    }
                    .disclosureGroupStyle(ExecutionDisclosureStyle())
                }
                }
                if !active, let context = contextInfo ?? execution?.contextInfo, context.totalMessages > 0 {
                    DisclosureGroup(L("سياق هذه المحادثة")) {
                        Text(L("{0} رسائل في السياق من أصل {1} محفوظة", context.includedMessages, context.totalMessages))
                            .padding(.top, 8)
                    }.disclosureGroupStyle(ExecutionDisclosureStyle()).font(.callout).foregroundStyle(.secondary)
                }
            }.padding(.top, 12)
        } label: {
            HStack(spacing: 8) {
                if active { ProgressView().controlSize(.mini) }
                if active {
                    Text(L("يعمل منذ {0}", Self.duration(elapsed))).font(.callout).monospacedDigit()
                } else {
                    Text(L("عمل لمدة {0}", Self.duration(elapsed)))
                        .font(.callout).foregroundStyle(.secondary).monospacedDigit()
                }
            }
        }
        .disclosureGroupStyle(ExecutionDisclosureStyle())
        .onAppear { expanded = active }
        .onChange(of: active) { _, value in expanded = value }
        .foregroundStyle(.secondary)
        .tint(.secondary)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    static func readableSummary(_ summary: String) -> String {
        summary.replacingOccurrences(of: "**", with: "")
            .replacingOccurrences(of: "\\n[ \\t]*\\n(?:[ \\t]*\\n)+", with: "\n\n", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
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
        case "skill": return L("استخدام مهارة كتابة")
        case "history": return L("البحث في الرسائل السابقة")
        case "library": return L("البحث في الأخبار المحفوظة")
        case "web": return L("البحث في الويب")
        case "reading": return L("قراءة المصادر")
        default: return L("إعداد الرد")
        }
    }
    private func symbol(_ kind: String) -> String {
        switch kind {
        case "context": return "text.bubble"
        case "skill": return "wand.and.stars"
        case "history": return "clock.arrow.circlepath"
        case "library": return "books.vertical"
        case "web": return "globe"
        case "reading": return "doc.text"
        default: return "sparkles"
        }
    }
}

/// Consecutive operations share one disclosure; the timeline keeps its original order.
struct ActivityEventGroup: Identifiable {
    let id: String
    let kind: String
    var details: [String]

    static func groups(_ steps: [ConversationExecutionStep]) -> [Self] {
        var result: [Self] = []
        for step in steps where step.kind != "context" {
            let detail = step.detail.trimmingCharacters(in: .whitespacesAndNewlines)
            if result.last?.kind == step.kind {
                if !detail.isEmpty, !result[result.count - 1].details.contains(detail) {
                    result[result.count - 1].details.append(detail)
                }
            } else {
                result.append(Self(id: step.id, kind: step.kind, details: detail.isEmpty ? [] : [detail]))
            }
        }
        return result
    }

    static func sourceURL(_ detail: String) -> URL? {
        guard let url = URL(string: detail),
              ["https", "http"].contains(url.scheme?.lowercased() ?? ""),
              url.host != nil else { return nil }
        return url
    }

    static func displayDetail(_ detail: String) -> String {
        guard let host = sourceURL(detail)?.host else { return detail }
        return host.hasPrefix("www.") ? String(host.dropFirst(4)) : host
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
