import Foundation
import AppKit
import SwiftUI
import Testing
@testable import OpenStudioApp

@Test func richTextRecognizesDocumentStructure() {
    let blocks = RichTextBlock.parse("# عنوان\n\nفقرة **بارزة**\n\n- نقطة\n2. ثانية\n> اقتباس\n```swift\nlet a = 1\n```")
    #expect(blocks == [.heading(1, "عنوان"), .paragraph("فقرة **بارزة**"), .list("•", "نقطة", 0), .list("2.", "ثانية", 0), .quote("اقتباس"), .code("let a = 1", language: "swift")])
}

@Test func richTextRejectsExecutableAndLocalSchemes() {
    #expect(RichTextLinks.allowed(URL(string: "https://example.com/evidence")!))
    #expect(!RichTextLinks.allowed(URL(string: "javascript:alert(1)")!))
    #expect(!RichTextLinks.allowed(URL(string: "file:///tmp/private")!))
    #expect(!RichTextLinks.allowed(URL(string: "https://user:secret@example.com")!))
    let result = RichTextLinks.attributed("[unsafe](file:///tmp/private) and https://example.com/evidence")
    let links = result.runs.compactMap { $0.link }
    #expect(links.count == 1)
    #expect(links.first?.absoluteString == "https://example.com/evidence")
}

@Test func richTextPreservesInlineEmphasisWithoutRemoteImages() {
    let result = RichTextLinks.attributed("**قوي** و ![صورة](https://tracking.example/pixel)")
    #expect(String(result.characters).contains("قوي"))
    #expect(String(result.characters).contains("صورة"))
    #expect(!String(result.characters).contains("tracking.example"))
    #expect(result.runs.contains { $0.inlinePresentationIntent?.contains(.stronglyEmphasized) == true })
}

@Test func bilingualParagraphsKeepIndependentDirectionAndExactContent() {
    let arabic = "✨ «مرحبا بالعالم» — Apple 2026"
    let english = "📌 (Hello world) — مرحبا 2026"
    let document = arabic + "\n\n" + english
    #expect(RichTextBlock.parse(document) == [.paragraph(arabic), .paragraph(english)])
    #expect(RichTextDirection.detect(arabic) == .rightToLeft)
    #expect(RichTextDirection.detect(english) == .leftToRight)
    #expect(String(RichTextLinks.attributed(arabic).characters) == arabic)
    #expect(String(RichTextLinks.attributed(english).characters) == english)
    #expect(RichTextLinks.paragraphStyle().alignment == .natural)
    #expect(RichTextLinks.paragraphStyle().baseWritingDirection == .natural)
}

@Test func bilingualListsKeepInterfaceAlignmentAndNaturalCharacterOrder() {
    let document = "- Arabic بالعربية\n- العربية English"
    #expect(RichTextBlock.parse(document) == [.list("•", "Arabic بالعربية", 0), .list("•", "العربية English", 0)])
    for direction in [LayoutDirection.rightToLeft, .leftToRight] {
        let style = RichTextLinks.paragraphStyle(interfaceDirection: direction)
        #expect(style.alignment == (direction == .rightToLeft ? .right : .left))
        #expect(style.baseWritingDirection == .natural)
    }
    let content = "🔗 اقرأ [المصدر](https://example.com/path?q=abc) ثم تابع"
    let rendered = RichTextLinks.attributed(content, interfaceDirection: .rightToLeft)
    #expect(rendered.runs.compactMap { $0.link }.first?.absoluteString == "https://example.com/path?q=abc")
    #expect(String(rendered.characters) == "🔗 اقرأ المصدر ثم تابع")
    #expect(RichTextBlock.parse("```\nlet url = \"https://example.com\" // العربية\n```") == [.code("let url = \"https://example.com\" // العربية")])
}

@Test func shortAndLongParagraphsAlignToTheirOwnLanguage() {
    for text in ["Hello", "مرحبا", String(repeating: "English words. ", count: 40), String(repeating: "كلمات عربية. ", count: 40)] {
        let rendered = RichTextLinks.native(AttributedString(text), fontSize: 16, lineSpacing: 6)
        let style = rendered.attribute(.paragraphStyle, at: 0, effectiveRange: nil) as? NSParagraphStyle
        #expect(style?.alignment == (RichTextDirection.detect(text) == .rightToLeft ? .right : .left))
        #expect(style?.baseWritingDirection == (RichTextDirection.detect(text) == .rightToLeft ? .rightToLeft : .leftToRight))
        #expect(rendered.string == text)
    }
}

@Test func nativeReaderPreservesMultilineBilingualTextAndLinkOrder() {
    let source = "✨ **عنوان عربي** ثم Apple\nEnglish sentence with [source](https://example.com/a?q=1).\n\nنهاية الفقرة."
    let inline = RichTextLinks.attributed(source)
    let native = RichTextLinks.native(inline, fontSize: 15, lineSpacing: 5)
    #expect(native.string == String(inline.characters))
    #expect(native.string.components(separatedBy: "\n").count == 4)
    let linkStart = (native.string as NSString).range(of: "source").location
    #expect((native.attribute(.link, at: linkStart, effectiveRange: nil) as? URL)?.absoluteString == "https://example.com/a?q=1")
    let boldStart = (native.string as NSString).range(of: "عنوان عربي").location
    let font = native.attribute(.font, at: boldStart, effectiveRange: nil) as? NSFont
    #expect(font.map { NSFontManager.shared.traits(of: $0).contains(.boldFontMask) } == true)
    let style = native.attribute(.paragraphStyle, at: 0, effectiveRange: nil) as? NSParagraphStyle
    #expect(style?.baseWritingDirection == .rightToLeft)
    #expect(style?.alignment == .right)
}

@Test func nativeEvidenceKeepsLiteralMarkdownAndBlankLines() {
    let source = "# عنوان\n\n**نص حرفي**\nEnglish with العربية\n"
    #expect(RichTextLinks.native(AttributedString(source), fontSize: 15, lineSpacing: 6).string == source)
    #expect(RichTextBlock.parse("first line\nsecond line\n\nnext paragraph") == [.paragraph("first line\nsecond line"), .paragraph("next paragraph")])
}

@Test func fencedLanguageAndIncompleteStreamsKeepLiteralCode() {
    #expect(RichTextBlock.parse("```json\n{\"url\": \"https://example.com\"}\n```") == [.code("{\"url\": \"https://example.com\"}", language: "json")])
    #expect(RichTextBlock.parse("~~~python\nprint('العربية')") == [.code("print('العربية')", language: "python")])
    #expect(RichTextBlock.parse("```text\n```not-a-close\n```") == [.code("```not-a-close", language: "text")])
}

@Test func inlineCodePreservesSpacingAndDoesNotAutolink() {
    let parsed = RichTextLinks.attributed("Run `bash install-images.sh --prepare-only`, then `http://127.0.0.1:5173`.")
    #expect(String(parsed.characters) == "Run bash install-images.sh --prepare-only, then http://127.0.0.1:5173.")
    #expect(parsed.runs.compactMap { $0.link }.isEmpty)
    let native = RichTextLinks.native(parsed, fontSize: 16, lineSpacing: 6)
    let offset = (native.string as NSString).range(of: "bash").location
    #expect(native.attribute(.inlineCode, at: offset, effectiveRange: nil) != nil)
    #expect(native.attribute(.backgroundColor, at: offset, effectiveRange: nil) == nil)
    #expect((native.attribute(.font, at: offset, effectiveRange: nil) as? NSFont)?.pointSize == 16 * 0.88)
}

@Test func highlightingNeverChangesCodeOrArabicComments() {
    let source = "# تشغيل بالعربية\nprint(\"https://example.com\")\n    return 42"
    for dark in [true, false] {
        let rendered = CodeHighlighting.render(source, language: "python", dark: dark)
        #expect(String(rendered.characters) == source)
        #expect(rendered.runs.count > 3)
        #expect(String(CodeHighlighting.render(source, language: "unknown", dark: dark).characters) == source)
    }
}

@Test func technicalTokensDoNotReverseArabicProse() {
    let source = "شغّل الأمر `bash install-images.sh --prepare-only` ثم افتح الرابط http://127.0.0.1:5173 وتابع القراءة."
    let rendered = RichTextLinks.native(RichTextLinks.attributed(source), fontSize: 17, lineSpacing: 6)
    let style = rendered.attribute(.paragraphStyle, at: 0, effectiveRange: nil) as? NSParagraphStyle
    #expect(style?.baseWritingDirection == .rightToLeft)
}
