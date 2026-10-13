import SwiftUI
import AppKit
import Foundation
import NaturalLanguage

enum RichTextBlock: Equatable {
    case heading(Int, String)
    case paragraph(String)
    case list(String, String, Int)
    case quote(String)
    case code(String)
    case divider
    case table([[String]])

    static func parse(_ text: String) -> [RichTextBlock] {
        var result: [RichTextBlock] = []
        var paragraph: [String] = []
        var code: [String] = []
        var fence: String?
        var table: [[String]] = []
        func cells(_ line: String) -> [String] {
            var value = line.trimmingCharacters(in: .whitespaces)
            if value.hasPrefix("|") { value.removeFirst() }
            if value.hasSuffix("|") { value.removeLast() }
            return value.components(separatedBy: "|").map { $0.trimmingCharacters(in: .whitespaces) }
        }
        func flush() {
            if !paragraph.isEmpty { result.append(.paragraph(paragraph.joined(separator: "\n"))); paragraph = [] }
        }
        for line in text.replacingOccurrences(of: "\r\n", with: "\n").components(separatedBy: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if let activeFence = fence {
                if trimmed.hasPrefix(activeFence) { result.append(.code(code.joined(separator: "\n"))); code = []; fence = nil }
                else { code.append(line) }
                continue
            }
            if !table.isEmpty {
                if trimmed.contains("|") && !trimmed.isEmpty { table.append(cells(trimmed)); continue }
                result.append(.table(table)); table = []
            }
            if trimmed.contains("|"), trimmed.range(of: #"^[| :\-]+$"#, options: .regularExpression) != nil,
               let header = paragraph.last, header.contains("|") {
                paragraph.removeLast(); flush(); table = [cells(header)]; continue
            }
            if trimmed.hasPrefix("```") || trimmed.hasPrefix("~~~") {
                flush(); fence = String(trimmed.prefix { $0 == trimmed.first }); continue
            }
            if trimmed.isEmpty { flush(); continue }
            let hashes = trimmed.prefix { $0 == "#" }.count
            if (1...6).contains(hashes), trimmed.dropFirst(hashes).first == " " {
                flush(); result.append(.heading(hashes, String(trimmed.dropFirst(hashes + 1)))); continue
            }
            if ["---", "***", "___"].contains(trimmed) { flush(); result.append(.divider); continue }
            if trimmed.hasPrefix(">") {
                flush()
                let value = String(trimmed.dropFirst()).trimmingCharacters(in: .whitespaces)
                if case .quote(let previous) = result.last { result[result.count - 1] = .quote(previous + "\n" + value) }
                else { result.append(.quote(value)) }
                continue
            }
            let depth = line.prefix { $0 == " " || $0 == "\t" }.reduce(0) { $0 + ($1 == "\t" ? 2 : 1) } / 2
            if trimmed.hasPrefix("- ") || trimmed.hasPrefix("* ") || trimmed.hasPrefix("+ ") || trimmed.hasPrefix("• ") {
                flush(); result.append(.list("•", String(trimmed.dropFirst(2)), depth)); continue
            }
            if let match = trimmed.range(of: #"^\d+[.)]\s+"#, options: .regularExpression) {
                flush()
                result.append(.list(String(trimmed[match]).trimmingCharacters(in: .whitespaces), String(trimmed[match.upperBound...]), depth))
                continue
            }
            paragraph.append(line)
        }
        if !table.isEmpty { result.append(.table(table)) }
        if fence != nil { result.append(.code(code.joined(separator: "\n"))) }
        flush()
        return result
    }
}

enum RichTextLinks {
    static func allowed(_ url: URL) -> Bool {
        ["http", "https"].contains(url.scheme?.lowercased() ?? "") && url.host != nil && url.user == nil && url.password == nil
    }

    static func attributed(_ value: String, interfaceDirection: LayoutDirection? = nil) -> AttributedString {
        // Image syntax becomes its alternate text. Rendering never requests remote assets.
        let source = value.replacingOccurrences(of: #"!\[([^\]]*)\]\([^\n]*?\)"#, with: "$1", options: .regularExpression)
        let parsed = (try? AttributedString(markdown: source, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))) ?? AttributedString(source)
        let native = NSMutableAttributedString(attributedString: NSAttributedString(parsed))
        let full = NSRange(location: 0, length: native.length)
        native.enumerateAttribute(.link, in: full) { value, range, _ in
            guard let value else { return }
            let url = (value as? URL) ?? (value as? String).flatMap(URL.init(string:))
            if url.map(allowed) != true { native.removeAttribute(.link, range: range) }
        }
        // NSDataDetector recognizes plain URLs without requiring Markdown link syntax.
        if let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue) {
            for match in detector.matches(in: native.string, range: full) {
                guard let url = match.url, allowed(url), native.attribute(.link, at: match.range.location, effectiveRange: nil) == nil else { continue }
                native.addAttribute(.link, value: url, range: match.range)
            }
        }
        native.enumerateAttribute(.link, in: full) { value, range, _ in
            if value != nil {
                native.addAttribute(.foregroundColor, value: NSColor.linkColor, range: range)
                native.addAttribute(.underlineStyle, value: NSUnderlineStyle.single.rawValue, range: range)
            }
        }
        let paragraph = paragraphStyle(interfaceDirection: interfaceDirection)
        native.addAttribute(.paragraphStyle, value: paragraph, range: full)
        return AttributedString(native)
    }

    static func native(_ value: AttributedString, fontSize: CGFloat, lineSpacing: CGFloat) -> NSAttributedString {
        let native = NSMutableAttributedString(attributedString: NSAttributedString(value))
        let full = NSRange(location: 0, length: native.length)
        native.addAttributes([.font: NSFont.systemFont(ofSize: fontSize), .foregroundColor: NSColor.textColor], range: full)
        var location = 0
        for run in value.runs {
            let length = String(value[run.range].characters).utf16.count
            let range = NSRange(location: location, length: length)
            let intent = run.inlinePresentationIntent ?? []
            var font = intent.contains(.code) ? NSFont.monospacedSystemFont(ofSize: fontSize, weight: .regular) : NSFont.systemFont(ofSize: fontSize)
            if intent.contains(.stronglyEmphasized) { font = NSFontManager.shared.convert(font, toHaveTrait: .boldFontMask) }
            if intent.contains(.emphasized) { font = NSFontManager.shared.convert(font, toHaveTrait: .italicFontMask) }
            native.addAttribute(.font, value: font, range: range)
            if intent.contains(.code) { native.addAttribute(.backgroundColor, value: NSColor.quaternaryLabelColor, range: range) }
            if intent.contains(.strikethrough) { native.addAttribute(.strikethroughStyle, value: NSUnderlineStyle.single.rawValue, range: range) }
            if let link = run.link, allowed(link) { native.addAttribute(.foregroundColor, value: NSColor.linkColor, range: range) }
            location += length
        }
        // NSTextAlignment.natural follows the app's base localization, which
        // need not match the document or our in-app language selection.
        let text = native.string as NSString
        var start = 0
        while start < text.length {
            let range = text.paragraphRange(for: NSRange(location: start, length: 0))
            let style = NSMutableParagraphStyle()
            let rtl = RichTextDirection.detect(text.substring(with: range)) == .rightToLeft
            style.baseWritingDirection = rtl ? .rightToLeft : .leftToRight
            style.alignment = rtl ? .right : .left
            style.lineSpacing = lineSpacing
            native.addAttribute(.paragraphStyle, value: style, range: range)
            start = NSMaxRange(range)
        }
        return native
    }

    static func paragraphStyle(interfaceDirection: LayoutDirection? = nil) -> NSParagraphStyle {
        let paragraph = NSMutableParagraphStyle()
        // Keep native Unicode bidirectional ordering. Alignment alone follows the
        // interface for labels/list items; never force their character order.
        paragraph.baseWritingDirection = .natural
        paragraph.alignment = interfaceDirection.map { $0 == .rightToLeft ? .right : .left } ?? .natural
        return paragraph
    }
}

/// Content direction is independent of the chosen interface language.
enum RichTextDirection {
    static func detect(_ text: String) -> LayoutDirection {
        // A brand name at the beginning (e.g. GitHub) must not reverse an
        // otherwise Arabic paragraph. Use the paragraph language, then the
        // first strong character when the short text cannot be identified.
        let recognizer = NLLanguageRecognizer()
        recognizer.processString(text)
        if let language = recognizer.dominantLanguage {
            if [.arabic, .hebrew, .persian, .urdu].contains(language) { return .rightToLeft }
            if language != .undetermined { return .leftToRight }
        }
        guard let scalar = text.unicodeScalars.first(where: { CharacterSet.letters.contains($0) }) else { return .leftToRight }
        let value = scalar.value
        let rightToLeft = (0x0590...0x08FF).contains(value) || (0xFB1D...0xFDFF).contains(value) ||
            (0xFE70...0xFEFF).contains(value) || (0x10800...0x10FFF).contains(value) || (0x1E900...0x1EEFF).contains(value)
        return rightToLeft ? .rightToLeft : .leftToRight
    }
}
