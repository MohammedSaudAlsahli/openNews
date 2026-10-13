import SwiftUI
import AppKit

struct DraftReview: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    let detail: DraftDetail
    var body: some View {
        let _ = interfaceLanguage
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(L("المراجعة والنسخ")).font(.headline)
                Text(L("هذه مسودة غير معتمدة. راجع الوقائع والأصالة قبل النشر.")).font(.callout).foregroundStyle(.secondary)
                if let latest = detail.versions.first, let data = latest.warningsJson.data(using: .utf8), let warnings = try? JSONDecoder().decode([String].self, from: data) {
                    ForEach(warnings, id: \.self) { Label(L($0), systemImage: "exclamationmark.circle").font(.callout) }
                }
                ForEach(detail.claims) { claim in
                    DisclosureGroup {
                        Text(claim.rationale).font(.callout)
                        ForEach(claim.evidence) { Text($0.text).font(.callout).textSelection(.enabled) }
                    } label: { VStack(alignment: .leading, spacing: 4) {
                        Label(claim.text, systemImage: "questionmark.circle")
                        Text(claim.verdict == "opinion" ? L("رأي") : L("يحتاج مراجعة")).foregroundStyle(.secondary).font(.caption)
                    }.font(.callout) }
                }
                if let evidence = detail.newsEvidence, !evidence.isEmpty {
                    DisclosureGroup(L("مراجع الأخبار ({0})", evidence.count)) {
                        ForEach(evidence) { item in
                            VStack(alignment: .leading, spacing: 6) {
                                if let url = URL(string: item.url), ["https", "http"].contains(url.scheme?.lowercased() ?? "") { Link(item.title, destination: url) }
                                if let date = item.publishedAt { Text(DisplayFormat.date(date)).font(.caption).foregroundStyle(.secondary) }
                                if !item.excerpt.isEmpty { Text(item.excerpt).font(.callout).textSelection(.enabled) }
                            }
                        }
                        Text(L("هذه مراجع مستخدمة في المسودة؛ راجع الوقائع قبل النشر.")).font(.caption).foregroundStyle(.secondary)
                    }
                }
                if detail.versions.count > 1 {
                    DisclosureGroup(L("النسخ السابقة ({0})", detail.versions.count - 1)) {
                        ForEach(detail.versions.dropFirst()) { version in
                            DisclosureGroup(DisplayFormat.date(version.createdAt)) { RichTextView(text: version.text, fontSize: 14) }
                        }
                    }.font(.callout)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

struct ActivityRow: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject var model: StudioModel
    let job: Job
    @AppStorage(ModelPermission.key) private var consent = false
    private var state: String { ["queued": L("في الانتظار"), "running": L("جارٍ التنفيذ"), "completed": L("اكتملت"), "failed": L("تعذّرت"), "interrupted": L("توقفت"), "cancelled": L("أُلغيت")][job.state] ?? L("تحتاج مراجعة") }
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                if job.active { ProgressView().controlSize(.small) }
                Text(job.type == "analysis.run" ? L("تحليل المصدر") : (job.type == "chat.send" ? L("رد المحادثة") : L("كتابة مسودة"))).fontWeight(.medium)
                Spacer(); Text(state).foregroundStyle(.secondary)
            }
            if let code = job.errorCode {
                Text(L("تعذّرت العملية. راجع الإعدادات والموافقة قبل إعادة المحاولة.")).font(.caption)
                DisclosureGroup(L("تفاصيل المشكلة")) { Text(code).font(.caption.monospaced()).textSelection(.enabled) }
            }
            if job.active { Button(L("إلغاء العملية")) { Task { await model.perform("jobs.cancel", ["job_id": job.id]) } } }
            if ["failed", "interrupted", "cancelled"].contains(job.state) { Button(L("إعادة المحاولة")) { Task { await model.perform("jobs.resume", ["job_id": job.id, "consent": consent]) } } }
            Divider()
        }.font(.callout)
    }
}

struct BackgroundWindowHost: NSViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> NSView { NSView() }
    func updateNSView(_ view: NSView, context: Context) {
        DispatchQueue.main.async {
            if let window = view.window {
                window.identifier = NSUserInterfaceItemIdentifier("editorial-studio")
                window.delegate = context.coordinator
            }
        }
    }
    final class Coordinator: NSObject, NSWindowDelegate {
        func windowShouldClose(_ sender: NSWindow) -> Bool {
            // Keep editor/chat state alive. Explicit Quit still checks unsaved edits.
            sender.orderOut(nil)
            return false
        }
    }
}
