import SwiftUI
import Testing
@testable import OpenStudioApp

@Test func allOfficialCatppuccinFlavorsHaveTheirOwnPalette() {
    let expected: [(CatppuccinFlavor, UInt32, UInt32, UInt32, UInt32, UInt32, ColorScheme)] = [
        (.latte, 0xe6e9ef, 0xeff1f5, 0xccd0da, 0x4c4f69, 0x1e66f5, .light),
        (.frappe, 0x292c3c, 0x303446, 0x414559, 0xc6d0f5, 0x8caaee, .dark),
        (.macchiato, 0x1e2030, 0x24273a, 0x363a4f, 0xcad3f5, 0x8aadf4, .dark),
        (.mocha, 0x181825, 0x1e1e2e, 0x313244, 0xcdd6f4, 0x89b4fa, .dark),
    ]
    #expect(CatppuccinFlavor.allCases.count == 4)
    for (flavor, page, paper, surface, foreground, accent, scheme) in expected {
        let colors = flavor.colors
        #expect(colors.page == page)
        #expect(colors.paper == paper)
        #expect(colors.surface == surface)
        #expect(colors.foreground == foreground)
        #expect(colors.accent == accent)
        #expect(EditorialTheme.preferredColorScheme(for: flavor.rawValue) == scheme)
    }
    #expect(EditorialTheme.preferredColorScheme(for: "catppuccin") == nil)
    #expect(EditorialTheme.preferredColorScheme(for: "paper") == nil)
}
