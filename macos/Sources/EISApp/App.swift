import SwiftUI
import AppKit

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    var model: StudioModel?
    func applicationWillTerminate(_ notification: Notification) { model?.stop() }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if let window = sender.windows.first(where: { $0.identifier?.rawValue == "editorial-studio" }) {
            window.makeKeyAndOrderFront(nil)
        }
        return true
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard model?.hasUnsavedChanges == true || model?.agentEditor.hasUnsavedChanges == true || model?.agentEditor.saving == true else { return .terminateNow }
        let alert = NSAlert()
        alert.messageText = L("لديك تعديلات غير محفوظة")
        alert.informativeText = L("ارجع واحفظ تعديلاتك قبل إنهاء التطبيق.")
        alert.addButton(withTitle: L("الرجوع إلى التطبيق"))
        alert.addButton(withTitle: L("تجاهل وإنهاء"))
        return alert.runModal() == .alertSecondButtonReturn ? .terminateNow : .terminateCancel
    }
}

@main struct EditorialIntelligenceStudioApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var model = StudioModel()
    @Environment(\.colorScheme) private var systemScheme
    @AppStorage("appearance") private var appearance = "system"
    @AppStorage("colorPalette") private var colorPalette = "paper"
    @AppStorage("appLanguage") private var appLanguage = "ar"
    @AppStorage(ModelPermission.key) private var modelPermission = false
    private var direction: LayoutDirection { appLanguage == "en" ? .leftToRight : .rightToLeft }
    private var colorScheme: ColorScheme { appearance == "light" ? .light : appearance == "dark" ? .dark : systemScheme }
    private var theme: EditorialTheme { .resolve(colorPalette, dark: colorScheme == .dark) }
    var body: some Scene {
        Window(L("مساحة التحرير"), id: "studio") {
            ContentView().environmentObject(model).preferredColorScheme(colorScheme).environment(\.editorialTheme, theme).tint(theme.accent)
                .environment(\.layoutDirection, direction).environment(\.locale, AppLanguage.current.locale)
                .frame(minWidth: 900, minHeight: 640)
                .onChange(of: appLanguage) { _, _ in model.objectWillChange.send() }
                .onChange(of: modelPermission) { _, allowed in if !allowed { Task { await model.perform("news.digest.set", ["enabled": false, "language": appLanguage]) } } }
                .task { delegate.model = model; if model.health == nil { await model.start() } }
        }
        .defaultSize(width: 1400, height: 850)
        .windowStyle(.titleBar)
        .commands {
            CommandGroup(replacing: .newItem) {
                command(L("محادثة جديدة"), .newEditorialConversation, "n")
                command(L("مسودة جديدة"), .newEditorialDraft, "n", [.command, .shift])
                command(L("المسودات المحفوظة…"), .openEditorialDrafts, "o")
                command(L("إضافة مصدر…"), .importEditorialSource, "i", [.command, .shift])
            }
            CommandGroup(replacing: .saveItem) {
                command(L("حفظ نسخة"), .saveEditorialDraft, "s")
                command(L("تصدير المسودة…"), .exportEditorialDraft, "e", [.command, .shift])
            }
            CommandMenu(L("الكتابة")) {
                command(L("مساعدة في الكتابة…"), .helpEditorialWriting, "j", [.command, .option])
                command(L("إظهار أو إخفاء المصادر والأسلوب"), .toggleEditorialReferences, "r", [.command, .option])
            }
        }
        MenuBarExtra {
            MenuBarReader().environmentObject(model).preferredColorScheme(colorScheme).environment(\.editorialTheme, theme).tint(theme.accent)
                .environment(\.layoutDirection, direction).environment(\.locale, AppLanguage.current.locale)
                .task { delegate.model = model; if model.health == nil { await model.start() } }
        } label: {
            Label {
                Text(L("الأخبار"))
            } icon: {
                Image(nsImage: BrandAssets.menuBarIcon).renderingMode(.template)
            }
                .accessibilityLabel(L("أخبار Editorial Intelligence Studio"))
        }.menuBarExtraStyle(.window)
        Settings {
            ModelSettingsView().environmentObject(model).preferredColorScheme(colorScheme).environment(\.editorialTheme, theme).tint(theme.accent)
                .environment(\.layoutDirection, direction).environment(\.locale, AppLanguage.current.locale)
                .background(SettingsWindowHost(dark: colorScheme == .dark))
                .onChange(of: modelPermission) { _, allowed in if !allowed { Task { await model.perform("news.digest.set", ["enabled": false, "language": appLanguage]) } } }
        }
    }
    private func command(_ title: String, _ name: Notification.Name, _ key: KeyEquivalent, _ modifiers: EventModifiers = .command) -> some View {
        Button(title) { NotificationCenter.default.post(name: name, object: nil) }.keyboardShortcut(key, modifiers: modifiers)
    }
}
