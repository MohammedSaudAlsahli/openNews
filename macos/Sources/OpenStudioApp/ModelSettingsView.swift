import SwiftUI
import AppKit

private enum SettingsSection: String, CaseIterable {
    case general, connections, agents, permissions, assistant
}

struct ModelSettingsView: View {
    @Environment(\.editorialTheme) private var theme
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @AppStorage("appearance") private var appearance = "system"
    @AppStorage("colorPalette") private var colorPalette = "paper"
    @AppStorage("appLanguage") private var appLanguage = "ar"
    @AppStorage("settingsSection") private var section: SettingsSection = .general
    var body: some View {
        let _ = interfaceLanguage
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 0) {
                Text(L("الإعدادات")).font(.title2.weight(.semibold)).padding(24)
                List(selection: $section) {
                    Section(L("مساحة العمل")) {
                        Label(L("الوكلاء"), systemImage: "person.2").tag(SettingsSection.agents)
                        Label(L("تخصيص المساعد"), systemImage: "slider.horizontal.3").tag(SettingsSection.assistant)
                    }
                    Section(L("التطبيق")) {
                        Label(L("مزوّدو الذكاء الاصطناعي"), systemImage: "network").tag(SettingsSection.connections)
                        Label(L("اللغة والمظهر"), systemImage: "globe").tag(SettingsSection.general)
                        Label(L("الصلاحيات والإعداد"), systemImage: "lock.shield").tag(SettingsSection.permissions)
                    }
                }.listStyle(.sidebar).scrollContentBackground(.hidden).padding(.horizontal, 10).padding(.top, 6)
            }.frame(width: 240).background(theme.page)
            Divider()
            // Keep each editor alive while navigating between settings sections.
            ZStack {
                VStack(alignment: .leading, spacing: 0) {
                    settingsHeading(L("اللغة والمظهر"), subtitle: L("خصّص لغة التطبيق ومظهره."))
                    general
                }.opacity(section == .general ? 1 : 0)
                    .allowsHitTesting(section == .general).disabled(section != .general).accessibilityHidden(section != .general)
                ConnectionsSettingsView().opacity(section == .connections ? 1 : 0)
                    .allowsHitTesting(section == .connections).disabled(section != .connections).accessibilityHidden(section != .connections)
                VStack(alignment: .leading, spacing: 0) {
                    settingsHeading(L("الصلاحيات والإعداد"), subtitle: L("اضبط صلاحيات التطبيق مرة واحدة، وغيّرها متى شئت."))
                    PermissionsSettingsView()
                }.opacity(section == .permissions ? 1 : 0)
                    .allowsHitTesting(section == .permissions).disabled(section != .permissions).accessibilityHidden(section != .permissions)
                VStack(alignment: .leading, spacing: 20) {
                    Text(L("تخصيص المساعد")).font(.title2.weight(.semibold))
                    Text(L("اضبط الدور والتعليمات والأسلوب مرة واحدة. يمكنك تخصيص كل وكيل أو محادثة بصورة مستقلة."))
                        .foregroundStyle(.secondary)
                    AssistantCustomizationButton(scope: "general").buttonStyle(.borderedProminent)
                    Spacer()
                }.padding(28).opacity(section == .assistant ? 1 : 0)
                    .allowsHitTesting(section == .assistant).disabled(section != .assistant).accessibilityHidden(section != .assistant)
                agents.opacity(section == .agents ? 1 : 0)
                    .allowsHitTesting(section == .agents).disabled(section != .agents).accessibilityHidden(section != .agents)
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: 900, idealWidth: 1000, minHeight: 680, idealHeight: 740)
        .textFieldStyle(.roundedBorder)
        .navigationTitle(L("الإعدادات"))
        .background(theme.page)
    }
    private var general: some View {
        Form {
            Section(L("اللغة والمظهر")) {
                Picker(L("لغة الواجهة"), selection: $appLanguage) {
                    Text(L("العربية")).tag("ar")
                    Text("English").tag("en")
                }.pickerStyle(.segmented).fixedSize(horizontal: true, vertical: false)
                Text(L("يتغير اتجاه الواجهة مع اللغة. تبقى نصوصك بلغتها الأصلية.")).font(.caption).foregroundStyle(.secondary)
                Picker(L("المظهر"), selection: $appearance) {
                    Text(L("حسب النظام")).tag("system")
                    Text(L("فاتح")).tag("light")
                    Text(L("داكن")).tag("dark")
                }.pickerStyle(.segmented).fixedSize(horizontal: true, vertical: false)
                    .disabled(EditorialTheme.preferredColorScheme(for: colorPalette) != nil)
                LabeledContent(L("لوحة الألوان")) {
                    NativeChoicePicker(title: L("لوحة الألوان"), selection: $colorPalette, choices: [
                        .init(value: "paper", label: L("ورقي")),
                        .init(value: "nord", label: "Nord"),
                        .init(value: "catppuccin", label: L("Catppuccin تلقائي (Latte / Mocha)")),
                        .init(value: CatppuccinFlavor.latte.rawValue, label: "Catppuccin Latte"),
                        .init(value: CatppuccinFlavor.frappe.rawValue, label: "Catppuccin Frappé"),
                        .init(value: CatppuccinFlavor.macchiato.rawValue, label: "Catppuccin Macchiato"),
                        .init(value: CatppuccinFlavor.mocha.rawValue, label: "Catppuccin Mocha")
                    ])
                }
                if EditorialTheme.preferredColorScheme(for: colorPalette) != nil {
                    Text(L("النكهة الثابتة تحدد المظهر تلقائيًا. اختر Catppuccin تلقائي لاتباع إعداد المظهر."))
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            Section(L("مساحة العمل")) {
                LabeledContent(L("حفظ النصوص"), value: L("محليًا على جهازك"))
                Text(L("تُرسل البيانات عند طلب الكتابة أو التحليل بعد تفعيل إذن استخدام النماذج. يمكنك تغيير الإذن من الصلاحيات والإعداد."))
                    .font(.callout).foregroundStyle(.secondary)
            }
            Section(L("تلخيص الأخبار في الخلفية")) {
                Toggle(L("جهّز ملخصات الأخبار تلقائيًا"), isOn: Binding(
                    get: { model.digestStatus?.enabled == true },
                    set: { enabled in
                        Task {
                            do {
                                _ = try await model.call("news.digest.set", ["enabled": enabled, "language": appLanguage])
                                try await model.refresh()
                            } catch { model.error = error.localizedDescription }
                        }
                    }))
                    .disabled(!ModelPermission.allowed() || model.snapshot?.assignments?.contains(where: { $0.role == "news" }) != true)
                if model.snapshot?.assignments?.contains(where: { $0.role == "news" }) != true {
                    Button(L("اختر نموذج ملخّص الأخبار")) { section = .agents }
                }
                if let digest = model.digestStatus {
                    Text(L("الملخصات الجاهزة: {0}، المتبقية: {1}", DisplayFormat.integer(digest.prepared), DisplayFormat.integer(digest.pending)))
                        .font(.caption).foregroundStyle(.secondary)
                    if !digest.currentTitle.isEmpty {
                        Label(L("يلخّص الآن: {0}", digest.currentTitle), systemImage: "sparkles")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
                Text(L("يستخدم النموذج الذي تختاره لملخّص الأخبار، على المقالات المتاحة فقط. قد تُحتسب تكلفة من مزودك."))
                    .font(.caption).foregroundStyle(.secondary)
            }
        }.formStyle(.grouped)
    }
    private var agents: some View {
        AgentsSettingsView { section = .connections }
    }
}
