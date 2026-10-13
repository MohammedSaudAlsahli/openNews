import Foundation
import AppKit
import Testing
@testable import OpenStudioApp

@MainActor @Test func systemAppearanceRecognizesDarkAndLightVariants() {
    #expect(SystemAppearanceObserver.isDarkAppearance(NSAppearance(named: .darkAqua)!) == true)
    #expect(SystemAppearanceObserver.isDarkAppearance(NSAppearance(named: .aqua)!) == false)
}

@Test func displayLocaleRetainsRegionAndExplicitNumberingOverride() {
    let base = Locale(identifier: "en_GB@numbers=latn")
    let arabic = DisplayFormat.locale(language: .arabic, regionalLocale: base)
    #expect(arabic.language.languageCode?.identifier == "ar")
    #expect(arabic.region?.identifier == "GB")
    #expect(arabic.numberingSystem == base.numberingSystem)
    #expect(DisplayFormat.locale(language: .english, regionalLocale: Locale(identifier: "ar_EG")).region?.identifier == "EG")
    #expect(DisplayFormat.integer(12345, language: .english, regionalLocale: Locale(identifier: "en_US")) == "12,345")
    #expect(DisplayFormat.integer(12345, language: .arabic, regionalLocale: Locale(identifier: "ar_EG@numbers=arab")) == "١٢٬٣٤٥")
}

@Test func displayDatesPreserveDateOnlyAndConvertInstants() {
    let region = Locale(identifier: "en_US@calendar=gregorian")
    let west = TimeZone(secondsFromGMT: -8 * 3600)!
    let east = TimeZone(secondsFromGMT: 14 * 3600)!
    #expect(DisplayFormat.date("2026-10-12", language: .english, regionalLocale: region, timeZone: west) == "Oct 12, 2026")
    #expect(DisplayFormat.date("2026-10-12", language: .english, regionalLocale: region, timeZone: east) == "Oct 12, 2026")
    let plain = DisplayFormat.date("2026-10-12T00:30:00Z", language: .english, regionalLocale: region, timeZone: west)
    let fractional = DisplayFormat.date("2026-10-12T00:30:00.123Z", language: .english, regionalLocale: region, timeZone: west)
    #expect(plain == fractional)
    #expect(plain.contains("Oct 11, 2026"))
    let arabic = DisplayFormat.date("2026-10-12", language: .arabic, regionalLocale: Locale(identifier: "ar_EG@calendar=gregorian;numbers=arab"), timeZone: west)
    #expect(arabic.contains("٢٠٢٦"))
    #expect(!arabic.contains("2026-10-12"))
    for invalid in ["", "undated", "2026-02-30", "2026-13-12"] {
        #expect(DisplayFormat.date(invalid, language: .english, regionalLocale: region) == invalid)
    }
}

@Test func technicalTokenIsolationIsExplicitAndLossless() {
    let token = "sources.yml:12"
    #expect(DisplayFormat.isolated(token, language: .arabic) == "\u{2068}sources.yml:12\u{2069}")
    #expect(DisplayFormat.isolated(token, language: .english) == token)
    #expect(DisplayFormat.isolated("", language: .arabic).isEmpty)
}

@Test func localizationFormatsOnlyNumericArguments() {
    let region = Locale(identifier: "ar_EG@numbers=arab")
    #expect(Localization.argument(12345, language: .arabic, regionalLocale: region) == "١٢٬٣٤٥")
    #expect(Localization.argument("12345", language: .arabic, regionalLocale: region) == "12345")
    #expect(Localization.argument("model-12345", language: .arabic, regionalLocale: region) == "model-12345")
}
