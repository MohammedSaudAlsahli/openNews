import SwiftUI
import AppKit
import UserNotifications

struct DailyReportConfiguration: Decodable {
    let enabled: Bool
    let hour, minute: Int
    let timezone, language: String
}
struct DailyNewsReport: Decodable, Identifiable {
    var id: String { day }
    let day, state, body, error: String
}
struct DailyReportStatus: Decodable {
    let settings: DailyReportConfiguration
    let nextAt: String?
    let reports: [DailyNewsReport]
    let instructionsPath: String
}

struct DailyReportSettings: View {
    @EnvironmentObject private var model: StudioModel
    @State private var status: DailyReportStatus?
    @State private var enabled = false
    @State private var time = Date()
    @State private var language = "ar"
    @State private var timezone = "Asia/Riyadh"
    @State private var failure: String?
    @State private var saving = false
    @State private var selected: DailyNewsReport?
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            settingsHeading(L("التقرير اليومي"), subtitle: L("شرح لأخبار اليوم من المصادر التي تتابعها، محفوظ على جهازك."))
            Form {
                Section {
                    Toggle(L("تفعيل التقرير اليومي"), isOn: $enabled)
                    DatePicker(L("وقت التقرير"), selection: $time, displayedComponents: .hourAndMinute)
                    Picker(L("المنطقة الزمنية"), selection: $timezone) {
                        Text("Asia/Riyadh").tag("Asia/Riyadh")
                        if TimeZone.current.identifier != "Asia/Riyadh" { Text(TimeZone.current.identifier).tag(TimeZone.current.identifier) }
                    }
                    Picker(L("لغة التقرير"), selection: $language) {
                        Text("العربية").tag("ar")
                        Text("English").tag("en")
                    }
                    Text(L("يعمل أثناء تشغيل التطبيق، حتى عند إغلاق نافذته. إذا كان الجهاز نائمًا أو التطبيق مغلقًا، يُجهّز تقرير اليوم عند العودة بعد الموعد. يستخدم نموذج تلخيص الأخبار وحدّ طلباته."))
                        .font(.caption).foregroundStyle(.secondary)
                    Button(saving ? L("جارٍ الحفظ…") : L("حفظ الإعدادات")) { Task { await save() } }.disabled(saving || status == nil)
                    if let next = status?.nextAt { Text(L("الموعد القادم") + ": " + DisplayFormat.date(next)).font(.caption).foregroundStyle(.secondary) }
                    if let failure { Text(failure).foregroundStyle(.red).font(.callout) }
                }
                Section(L("تعليمات النموذج")) {
                    Text(L("ملف مستقل لشرح المقالات وآخر للتقرير اليومي. تعديلهما يطبّق على النتائج الجديدة، ولا يضيع مع تحديث التطبيق."))
                        .font(.caption).foregroundStyle(.secondary)
                    Button(L("فتح مجلد التعليمات")) {
                        if let path = status?.instructionsPath { NSWorkspace.shared.open(URL(fileURLWithPath: path)) }
                    }
                }
                Section(L("التقارير المحفوظة")) {
                    if status?.reports.isEmpty != false { Text(L("سيظهر تقريرك هنا بعد الموعد المحدد.")).foregroundStyle(.secondary) }
                    ForEach(status?.reports ?? []) { report in
                        HStack {
                            Text(report.day)
                            Spacer()
                            if report.state == "ready" { Button(L("قراءة التقرير")) { selected = report } }
                            else if report.state == "running" { ProgressView().controlSize(.small) }
                            else { Text(report.error).font(.caption).foregroundStyle(.secondary) }
                        }
                    }
                }
            }.formStyle(.grouped)
        }.task {
            await load()
            while !Task.isCancelled {
                do { try await Task.sleep(nanoseconds: 5_000_000_000) } catch { break }
                if let value = try? await model.decoded("daily.get", as: DailyReportStatus.self) { status = value }
            }
        }
        .sheet(item: $selected) { report in
            VStack(alignment: .leading) {
                HStack { Text(L("التقرير اليومي") + " · " + report.day).font(.headline); Spacer(); Button(L("إغلاق")) { selected = nil } }
                ScrollView { RichTextView(text: report.body, fontSize: 16, lineSpacing: 5).frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled) }
            }.padding(24).frame(width: 720, height: 600)
        }
    }
    private func load() async {
        do {
            let value = try await model.decoded("daily.get", as: DailyReportStatus.self)
            status = value; enabled = value.settings.enabled; language = value.settings.language; timezone = value.settings.timezone
            time = Calendar.current.date(bySettingHour: value.settings.hour, minute: value.settings.minute, second: 0, of: Date()) ?? Date()
        } catch { failure = error.localizedDescription }
    }
    private func save() async {
        saving = true; failure = nil
        defer { saving = false }
        do {
            let parts = Calendar.current.dateComponents([.hour, .minute], from: time)
            status = try await model.decoded("daily.set", ["enabled":enabled,"hour":parts.hour ?? 22,"minute":parts.minute ?? 0,"timezone":timezone,"language":language,"consent":enabled], as: DailyReportStatus.self)
            if enabled {
                let allowed = try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert,.sound])
                if !allowed { failure = L("التنبيهات غير مفعلة في macOS؛ سيبقى التقرير متاحًا هنا.") }
            }
        } catch { failure = error.localizedDescription }
    }
}

@MainActor enum DailyReportNotifications {
    static func check(_ model: StudioModel) async {
        guard let status = try? await model.decoded("daily.check", ["consent":ModelPermission.allowed()], as: DailyReportStatus.self), status.settings.enabled,
              let report = status.reports.first, report.state == "ready" else { return }
        let key = "dailyReportNotified." + report.day
        guard !UserDefaults.standard.bool(forKey: key) else { return }
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .authorized else { return }
        let content = UNMutableNotificationContent()
        content.title = L("تقرير أخبارك اليومي جاهز")
        content.body = L("افتح الإعدادات ← التقرير اليومي لقراءته.")
        content.sound = .default
        do {
            try await center.add(UNNotificationRequest(identifier: key, content: content, trigger: nil))
            UserDefaults.standard.set(true, forKey: key)
        } catch { /* Keep the saved report available and retry notification later. */ }
    }
}
