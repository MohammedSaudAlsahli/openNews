import Foundation
import Testing
@testable import EISApp

@Test func interfaceLanguageTranslationsAndFallback() {
    #expect(Localization.text("حفظ", language: .english) == "Save")
    #expect(Localization.text("حفظ", language: .arabic) == "حفظ")
    #expect(Localization.text("Unregistered text", language: .english) == "Unregistered text")
    #expect(AppLanguage.arabic.isRightToLeft)
    #expect(!AppLanguage.english.isRightToLeft)
    #expect(AppLanguage.resolve("invalid") == .arabic)
    #expect(AppLanguage.resolve(nil) == .arabic)
    #expect(AppLanguage.resolve("en") == .english)
    #expect(Localization.text("Save", language: .arabic) == "حفظ")
}

@Test func localizedInterpolationPreservesArgumentContent() {
    #expect(Localization.text("{0} كلمة · {1} حرف", arguments: ["12", "84"], language: .english) == "12 words · 84 characters")
    #expect(Localization.text("{0} كلمة · {1} حرف", arguments: ["١٢", "٨٤"], language: .arabic) == "١٢ كلمة · ٨٤ حرف")
    #expect(Localization.text("{0} كلمة · {1} حرف", arguments: ["{1}", "literal"], language: .english) == "{1} words · literal characters")
    #expect(Localization.text("تحديد {0}", arguments: ["عنوان المستخدم"], language: .english) == "Select عنوان المستخدم")
}

@Test func localizationCatalogsMatchAndKeepPlaceholders() throws {
    #expect(Localization.english.count > 400)
    #expect(Set(Localization.english.keys) == Set(Localization.arabic.keys))
    let regex = try NSRegularExpression(pattern: #"\{[0-9]+\}"#)
    func placeholders(_ value: String) -> [String] {
        let string = value as NSString
        return regex.matches(in: value, range: NSRange(location: 0, length: string.length)).map { string.substring(with: $0.range) }.sorted()
    }
    for (key, translation) in Localization.english {
        #expect(!translation.isEmpty)
        #expect(placeholders(key) == placeholders(translation))
    }
}

@Test func structuredYamlErrorsKeepLocationsAndFieldNames() {
    #expect(Localization.text("ملف sources.yml: معرّف مكرر في المصدر رقم 7.", language: .english) == "sources.yml: Duplicate ID in source 7.")
    #expect(Localization.text("ملف sources.yml: صياغة YAML غير صالحة في السطر 12، العمود 4. صحّح الملف وأعد التحميل؛ لم يُعدّل الملف.", language: .english) == "sources.yml: Invalid YAML syntax at line 12, column 4. Correct the file and reload; the file was not modified.")
    #expect(Localization.text("ملف sources.yml: الحقل title يجب أن يكون نصًا بطول 1–300 حرف.", language: .english) == "sources.yml: Field title must be text with a length of 1–300 characters.")
}
