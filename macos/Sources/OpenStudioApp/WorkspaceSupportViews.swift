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

struct ActivitySummary: View {
    @EnvironmentObject private var model: StudioModel
    private var jobs: [Job] { model.snapshot?.jobs ?? [] }
    private func summaryPhase(_ phase: String) -> String {
        switch phase {
        case "disabled": return L("التلخيص التلقائي متوقف")
        case "low_power": return L("متوقف مؤقتًا أثناء وضع توفير الطاقة")
        case "cooling": return L("متوقف مؤقتًا حتى تنخفض حرارة الجهاز")
        case "resting": return L("راحة بين الملخصات لتخفيف استهلاك الجهاز")
        case "waiting_model": return L("بانتظار انتهاء طلبك؛ المحادثة لها الأولوية")
        case "retrying": return L("تعذّر التلخيص؛ ستتم إعادة المحاولة تلقائيًا")
        case "needs_model", "needs_download": return L("اختر نموذجًا متاحًا للتلخيص")
        case "daily_limit": return L("اكتمل الحد اليومي؛ يستأنف التلخيص غدًا")
        case "waiting_device": return L("بانتظار التحقق من حالة الجهاز")
        case "waiting_articles": return L("بانتظار وصول نصوص المقالات الكاملة")
        case "ready": return L("كل المقالات المتاحة ملخصة")
        case "summarizing": return L("جارٍ تجهيز الملخصات")
        default: return L("مقالات جاهزة للتلخيص في الخلفية")
        }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let digest = model.digestStatus {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Label(L("التلخيص في الخلفية"), systemImage: "doc.text")
                        Spacer()
                        Text(L(digest.language == "ar" ? "العربية" : "الإنجليزية")).font(.caption).foregroundStyle(.secondary)
                    }.font(.callout.weight(.medium))
                    Text(L("{0} ملخص جاهز · {1} بانتظار التلخيص", digest.prepared, digest.pending)).font(.caption).foregroundStyle(.secondary)
                    Text(summaryPhase(digest.phase ?? "disabled")).font(.caption).foregroundStyle(.secondary)
                    if !digest.currentTitle.isEmpty { Text(digest.currentTitle).font(.caption).lineLimit(2) }
                }
                Divider()
            }
            let attention = jobs.filter { $0.state != "completed" }
            if attention.isEmpty {
                Label(L("لا توجد مهام قيد التنفيذ"), systemImage: "checkmark.circle")
                    .foregroundStyle(.secondary)
            } else {
                ScrollView {
                    VStack(spacing: 12) { ForEach(attention) { ActivityRow(job: $0) } }
                }.frame(maxHeight: 300)
            }
            let completed = jobs.filter { $0.state == "completed" }.count
            if completed > 0 {
                Text(L("{0} مهام مكتملة مؤخرًا", completed)).font(.caption).foregroundStyle(.secondary)
            }
        }
    }
}
