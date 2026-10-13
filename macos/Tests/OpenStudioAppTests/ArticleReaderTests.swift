import AppKit
import SwiftUI
import ImageIO
import Testing
@testable import OpenStudioApp

@Test func articleReaderDecodesImageOrderWithoutChangingEvidence() throws {
    let decoder = JSONDecoder(); decoder.keyDecodingStrategy = .convertFromSnakeCase
    let data = Data(#"{"text":"Original model evidence","reader":{"blocks":[{"type":"text","text":"مقدمة"},{"type":"image","id":"0","url":"https://example.com/photo.jpg","alt":"وصف","caption":"Photo credit"},{"type":"text","text":"End"}],"checked_at":"2026-10-12","origin":"article"}}"#.utf8)
    let detail = try decoder.decode(NewsArticleDetail.self, from: data)
    #expect(detail.text == "Original model evidence")
    #expect(detail.reader?.blocks?.map(\.type) == ["text", "image", "text"])
    #expect(detail.reader?.blocks?[1].caption == "Photo credit")
    #expect(detail.reader?.checkedAt == "2026-10-12")
}

@Test func readerImageDecoderDownsamplesAndRejectsNonImages() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let url = directory.appendingPathComponent("test.png")
    let context = try #require(CGContext(data: nil, width: 4096, height: 2048, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue))
    let image = try #require(context.makeImage())
    let destination = try #require(CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil))
    CGImageDestinationAddImage(destination, image, nil)
    #expect(CGImageDestinationFinalize(destination))
    let decoded = try #require(ReaderImageDecoder.image(at: url.path))
    #expect(decoded.size.width == 2048 && decoded.size.height == 1024)
    try Data("<script>not an image</script>".utf8).write(to: url)
    #expect(ReaderImageDecoder.image(at: url.path) == nil)
}

@MainActor @Test func chatReturnSendsButShiftAndCompositionKeepEditing() {
    #expect(MessageTextView.submits(keyCode: 36, modifiers: [], composing: false))
    #expect(MessageTextView.submits(keyCode: 76, modifiers: .command, composing: false))
    #expect(!MessageTextView.submits(keyCode: 36, modifiers: .shift, composing: false))
    #expect(!MessageTextView.submits(keyCode: 36, modifiers: [], composing: true))
    #expect(!MessageTextView.submits(keyCode: 0, modifiers: [], composing: false))
}

@Test func readerParsesTablesQuotesAndNestedFences() {
    #expect(RichTextBlock.parse("| Name | Value |\n| --- | --- |\n| A | 2 |") == [.table([["Name", "Value"], ["A", "2"]])])
    #expect(RichTextBlock.parse("> First\n>\n> Second") == [.quote("First\n\nSecond")])
    #expect(RichTextBlock.parse("````\n```example\n    code\n````") == [.code("```example\n    code")])
}

@MainActor @Test func menuReaderFitsInBothInterfaceDirections() throws {
    let original = UserDefaults.standard.object(forKey: "appLanguage")
    if let language = ProcessInfo.processInfo.environment["EIS_QA_LANGUAGE"] { UserDefaults.standard.set(language, forKey: "appLanguage") }
    defer {
        if let original { UserDefaults.standard.set(original, forKey: "appLanguage") }
        else { UserDefaults.standard.removeObject(forKey: "appLanguage") }
    }
    let model = StudioModel()
    for direction: LayoutDirection in [.leftToRight, .rightToLeft] {
        let host = NSHostingView(rootView: MenuBarReader().environmentObject(model).environment(\.layoutDirection, direction))
        host.frame = NSRect(x: 0, y: 0, width: 470, height: 700)
        host.layoutSubtreeIfNeeded()
        #expect(host.fittingSize.width <= 470.5)
        #expect(host.fittingSize.height <= 700.5)
        if let output = ProcessInfo.processInfo.environment["EIS_QA_OUTPUT_DIR"] {
            let bitmap = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
            host.cacheDisplay(in: host.bounds, to: bitmap)
            let data = try #require(bitmap.representation(using: .png, properties: [:]))
            try data.write(to: URL(fileURLWithPath: output).appendingPathComponent("menu-reader-" + AppLanguage.current.rawValue + (direction == .leftToRight ? "-ltr.png" : "-rtl.png")))
        }
    }
}
