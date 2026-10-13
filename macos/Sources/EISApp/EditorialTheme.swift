import SwiftUI
import AppKit

@MainActor final class SystemAppearanceObserver: ObservableObject {
    @Published private(set) var isDark: Bool
    private var observation: NSKeyValueObservation?

    init() {
        let application = NSApplication.shared
        isDark = Self.isDarkAppearance(application.effectiveAppearance)
        observation = application.observe(\.effectiveAppearance, options: [.new]) { [weak self] application, _ in
            Task { @MainActor [weak self] in
                self?.isDark = Self.isDarkAppearance(application.effectiveAppearance)
            }
        }
    }

    static func isDarkAppearance(_ appearance: NSAppearance) -> Bool {
        appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
    }
}

struct EditorialTheme {
    let page: Color
    let paper: Color
    let surface: Color
    let foreground: Color
    let accent: Color

    static func resolve(_ palette: String, dark: Bool) -> Self {
        switch (palette, dark) {
        case ("catppuccin", false):
            // Catppuccin Latte: Mantle, Base, Surface 0, Text, Blue.
            // https://github.com/catppuccin/catppuccin#palette
            return Self(page: Color(hex: 0xe6e9ef), paper: Color(hex: 0xeff1f5), surface: Color(hex: 0xccd0da), foreground: Color(hex: 0x4c4f69), accent: Color(hex: 0x1e66f5))
        case ("catppuccin", true):
            // Catppuccin Mocha uses the same semantic roles in dark mode.
            return Self(page: Color(hex: 0x181825), paper: Color(hex: 0x1e1e2e), surface: Color(hex: 0x313244), foreground: Color(hex: 0xcdd6f4), accent: Color(hex: 0x89b4fa))
        case ("nord", false):
            return Self(page: Color(hex: 0xe5e9f0), paper: Color(hex: 0xeceff4), surface: Color(hex: 0xd8dee9), foreground: Color(hex: 0x2e3440), accent: Color(hex: 0x5e81ac))
        case ("nord", true):
            return Self(page: Color(hex: 0x2e3440), paper: Color(hex: 0x303744), surface: Color(hex: 0x3b4252), foreground: Color(hex: 0xeceff4), accent: Color(hex: 0x88c0d0))
        case (_, true):
            return Self(page: Color(hex: 0x191a1b), paper: Color(hex: 0x202223), surface: Color(hex: 0x2b2d2f), foreground: Color(hex: 0xf1ede6), accent: Color(hex: 0xd7b88d))
        default:
            return Self(page: Color(hex: 0xf5f2ec), paper: Color(hex: 0xfffdf8), surface: Color(hex: 0xebe7df), foreground: Color(hex: 0x292722), accent: Color(hex: 0x8b6b46))
        }
    }
}

private extension Color {
    init(hex: UInt32) {
        self.init(.sRGB, red: Double((hex >> 16) & 0xff) / 255,
                  green: Double((hex >> 8) & 0xff) / 255,
                  blue: Double(hex & 0xff) / 255, opacity: 1)
    }
}

private struct EditorialThemeKey: EnvironmentKey {
    static let defaultValue = EditorialTheme.resolve("paper", dark: false)
}

extension EnvironmentValues {
    var editorialTheme: EditorialTheme {
        get { self[EditorialThemeKey.self] }
        set { self[EditorialThemeKey.self] = newValue }
    }
}

/// Keep Settings above studio windows while OpenStudio is active, but hide it
/// when the user switches to another app.
struct SettingsWindowHost: NSViewRepresentable {
    let dark: Bool
    func makeNSView(context: Context) -> AttachedView { AttachedView() }
    func updateNSView(_ view: AttachedView, context: Context) {
        view.apply = { window in
            window.level = .floating
            window.hidesOnDeactivate = true
            window.appearance = NSAppearance(named: dark ? .darkAqua : .aqua)
        }
        view.applyIfAttached()
    }
    final class AttachedView: NSView {
        var apply: ((NSWindow) -> Void)?
        override func viewDidMoveToWindow() { super.viewDidMoveToWindow(); applyIfAttached() }
        func applyIfAttached() { if let window { apply?(window) } }
    }
}
