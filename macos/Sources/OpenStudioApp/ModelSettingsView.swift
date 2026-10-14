import SwiftUI
import AppKit

private enum SettingsSection: String, CaseIterable {
    case general, connections, agents, permissions, assistant, newsMemory, summaryModels
}

struct ModelSettingsView: View {
    @Environment(\.editorialTheme) private var theme
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @AppStorage("appearance") private var appearance = "system"
    @AppStorage("colorPalette") private var colorPalette = "paper"
    @AppStorage("appLanguage") private var appLanguage = "ar"
    @AppStorage("settingsSection") private var section: SettingsSection = .general
    @State private var visited: Set<SettingsSection> = []
    var body: some View {
        let _ = interfaceLanguage
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 0) {
                Text(L("الإعدادات")).font(.title2.weight(.semibold)).padding(24)
                List(selection: $section) {
                    Section(L("مساحة العمل")) {
                        Label(L("الوكلاء"), systemImage: "person.2").tag(SettingsSection.agents)
                        Label(L("تخصيص المساعد"), systemImage: "slider.horizontal.3").tag(SettingsSection.assistant)
                        Label(L("ذاكرة الأخبار"), systemImage: "books.vertical").tag(SettingsSection.newsMemory)
                        Label(L("التلخيص والنماذج"), systemImage: "text.alignleft").tag(SettingsSection.summaryModels)
                    }
                    Section(L("التطبيق")) {
                        Label(L("مزوّدو الذكاء الاصطناعي"), systemImage: "network").tag(SettingsSection.connections)
                        Label(L("اللغة والمظهر"), systemImage: "globe").tag(SettingsSection.general)
                        Label(L("الصلاحيات والإعداد"), systemImage: "lock.shield").tag(SettingsSection.permissions)
                    }
                }.font(.callout).listStyle(.sidebar).scrollContentBackground(.hidden).padding(.horizontal, 10).padding(.top, 6)
            }.frame(width: 240).background(theme.page)
            Divider()
            // Keep each editor alive while navigating between settings sections.
            ZStack {
                if section == .general || visited.contains(.general) {
                VStack(alignment: .leading, spacing: 0) {
                    settingsHeading(L("اللغة والمظهر"), subtitle: L("خصّص لغة التطبيق ومظهره."))
                    general
                }.opacity(section == .general ? 1 : 0)
                    .allowsHitTesting(section == .general).disabled(section != .general).accessibilityHidden(section != .general)
                }
                if section == .newsMemory || visited.contains(.newsMemory) {
                VStack(alignment: .leading, spacing: 0) {
                    settingsHeading(L("ذاكرة الأخبار"), subtitle: L("أخبار محفوظة، بحث أسرع، وملخصات جاهزة للنقاش."))
                    Form { NewsMemorySettings { section = .summaryModels } }.formStyle(.grouped)
                }.opacity(section == .newsMemory ? 1 : 0)
                    .allowsHitTesting(section == .newsMemory).disabled(section != .newsMemory).accessibilityHidden(section != .newsMemory)
                }
                if section == .summaryModels {
                    VStack(alignment: .leading, spacing: 0) {
                        settingsHeading(L("التلخيص والنماذج"), subtitle: L("اختر ما يناسب جهازك. حمّل مرة واحدة، واترك الباقي للتطبيق."))
                        LocalSummaryModels { section = .agents }
                    }
                }
                if section == .connections || visited.contains(.connections) {
                ConnectionsSettingsView().opacity(section == .connections ? 1 : 0)
                    .allowsHitTesting(section == .connections).disabled(section != .connections).accessibilityHidden(section != .connections)
                }
                if section == .permissions || visited.contains(.permissions) {
                VStack(alignment: .leading, spacing: 0) {
                    settingsHeading(L("الصلاحيات والإعداد"), subtitle: L("اضبط صلاحيات التطبيق مرة واحدة، وغيّرها متى شئت."))
                    PermissionsSettingsView()
                }.opacity(section == .permissions ? 1 : 0)
                    .allowsHitTesting(section == .permissions).disabled(section != .permissions).accessibilityHidden(section != .permissions)
                }
                if section == .assistant || visited.contains(.assistant) {
                VStack(alignment: .leading, spacing: 20) {
                    Text(L("تخصيص المساعد")).font(.title2.weight(.semibold))
                    Text(L("اضبط الدور والتعليمات والأسلوب مرة واحدة. يمكنك تخصيص كل وكيل أو محادثة بصورة مستقلة."))
                        .foregroundStyle(.secondary)
                    AssistantCustomizationButton(scope: "general").buttonStyle(.borderedProminent)
                    Spacer()
                }.padding(28).opacity(section == .assistant ? 1 : 0)
                    .allowsHitTesting(section == .assistant).disabled(section != .assistant).accessibilityHidden(section != .assistant)
                }
                if section == .agents || visited.contains(.agents) {
                agents.opacity(section == .agents ? 1 : 0)
                    .allowsHitTesting(section == .agents).disabled(section != .agents).accessibilityHidden(section != .agents)
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: 1000, idealWidth: 1080, minHeight: 680, idealHeight: 740)
        .onAppear { visited.insert(section) }
        .onChange(of: section) { _, value in visited.insert(value) }
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
        }.formStyle(.grouped)
    }
    private var agents: some View {
        AgentsSettingsView { section = .connections }
    }
}
