import AppKit
import Foundation
import Testing
@testable import OpenStudioApp

@Test func citationsBecomeSafeClickableReferencesWithoutChangingProse() {
    let id = "88a3ed40-5421-457c-b9f2-7210e17a0e4c"
    let citation = ConversationCitation(articleId: id, title: "مصدر", url: "https://example.com/a(b)?q=1", publishedAt: nil)
    let message = "خبر عربي [\(id)]\nEnglish [\(id.uppercased())]"
    let text = ConversationPresentation.markdown(message, citations: [citation])
    #expect(!text.contains(id))
    let links = RichTextLinks.attributed(text).runs.compactMap { $0.link }
    #expect(links.count == 2)
    #expect(links.allSatisfy { $0.absoluteString == citation.url })
    #expect(ConversationPresentation.markdown("خبر [\(id)]", citations: []).contains(L("[مرجع غير متاح]")))
    let unsafe = ConversationCitation(articleId: id, title: "Unsafe", url: "file:///tmp/private", publishedAt: nil)
    #expect(!ConversationPresentation.markdown(message, citations: [unsafe]).contains("file:"))
    #expect(ConversationPresentation.markdown("خبر [88a3ed40-542", citations: [citation], partial: true) == "خبر ")
}

@MainActor @Test func nativeParagraphGeometryFollowsContentLanguage() throws {
    // Check real glyph placement, not just a paragraph-style property.
    for (text, rightAligned) in [("مرحبا بالعالم", true), ("Hello world", false)] {
        let storage = NSTextStorage(attributedString: RichTextLinks.native(AttributedString(text), fontSize: 17, lineSpacing: 6))
        let layout = NSLayoutManager()
        let container = NSTextContainer(containerSize: NSSize(width: 500, height: 1000))
        container.lineFragmentPadding = 0
        storage.addLayoutManager(layout); layout.addTextContainer(container)
        layout.ensureLayout(for: container)
        let rect = layout.boundingRect(forGlyphRange: layout.glyphRange(for: container), in: container)
        #expect(rightAligned ? rect.minX > 250 : rect.minX < 10)
        let line = layout.lineFragmentUsedRect(forGlyphAt: 0, effectiveRange: nil)
        #expect(line.maxX <= 501)
    }
    let text = "عربي أولًا\nEnglish next\nعربي مجددًا"
    let rendered = RichTextLinks.native(AttributedString(text),fontSize: 16,lineSpacing: 6)
    for (word, alignment) in [("عربي أولًا", NSTextAlignment.right), ("English", .left), ("عربي مجددًا", .right)] {
        let index = (text as NSString).range(of: word).location
        let style = try #require(rendered.attribute(.paragraphStyle,at: index,effectiveRange: nil) as? NSParagraphStyle)
        #expect(style.alignment == alignment)
        #expect(style.baseWritingDirection == (alignment == .right ? .rightToLeft : .leftToRight))
    }
    #expect(RichTextBlock.parse("• خبر جديد") == [.list("•", "خبر جديد", 0)])
}

@Test func customizationUsesTheSameKeysAcrossIPCAndUI() throws {
    let json = #"{"settings":{"system_prompt":"هوية","developer_prompt":"تنفيذ","style":"واضح"},"inherited":[{"scope":"general","target_id":"","settings":{"role":"writer"}}]}"#
    let decoder = JSONDecoder(); decoder.keyDecodingStrategy = .convertFromSnakeCase
    let preferences = try decoder.decode(AssistantPreferences.self, from: Data(json.utf8))
    #expect(preferences.settings["system_prompt"] == "هوية")
    #expect(preferences.settings["developer_prompt"] == "تنفيذ")
    #expect(preferences.inherited.first?.targetId == "")
}

@Test func leadingProductNamesDoNotReverseArabicParagraphs() {
    let arabic = "GitHub سجّل اضطرابات في الخدمات. عادت طلبات المراجعة للعمل بصورة طبيعية، لكن بعض التأخير والأخطاء استمرت."
    let english = "GitHub reported service interruptions. Most services have now recovered."
    #expect(RichTextDirection.detect(arabic) == .rightToLeft)
    #expect(RichTextDirection.detect(english) == .leftToRight)
    let rendered = RichTextLinks.native(AttributedString(arabic),fontSize: 16,lineSpacing: 6)
    let style = rendered.attribute(.paragraphStyle,at: 0,effectiveRange: nil) as? NSParagraphStyle
    #expect(style?.alignment == .right)
    #expect(style?.baseWritingDirection == .rightToLeft)
    #expect(rendered.string == arabic)
}

@MainActor @Test func citationHoverOnlyTargetsActualLinkGlyphs() throws {
    for text in ["خبر عربي [1](https://example.org/story)", "English news [1](https://example.org/story)"] {
        let view = CitationTextView(frame: NSRect(x: 0, y: 0, width: 500, height: 200))
        view.textContainerInset = .zero
        view.textContainer?.lineFragmentPadding = 0
        view.textContainer?.containerSize = NSSize(width: 500, height: 200)
        view.textStorage?.setAttributedString(RichTextLinks.native(RichTextLinks.attributed(text), fontSize: 16, lineSpacing: 6))
        let layout = try #require(view.layoutManager)
        let container = try #require(view.textContainer)
        layout.ensureLayout(for: container)
        let index = (view.string as NSString).range(of: "1").location
        let range = layout.glyphRange(forCharacterRange: NSRange(location: index, length: 1), actualCharacterRange: nil)
        let rect = layout.boundingRect(forGlyphRange: range, in: container)
        let result = view.citation(at: NSPoint(x: rect.midX + view.textContainerOrigin.x, y: rect.midY + view.textContainerOrigin.y))
        #expect(result?.0.absoluteString == "https://example.org/story")
        #expect(result?.1 == index)
        #expect(view.citation(at: NSPoint(x: 250, y: 190)) == nil)
    }
}
