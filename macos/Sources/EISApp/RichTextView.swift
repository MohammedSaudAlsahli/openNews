import SwiftUI
import AppKit

/// Read-only Markdown and plain-text rendering. No HTML, web views, image loading or scripts.
struct RichTextView: View {
    let text: String
    var fontSize: CGFloat = 16
    var lineSpacing: CGFloat = 6

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(Array(RichTextBlock.parse(text).enumerated()), id: \.offset) { _, block in
                switch block {
                case .heading(let level, let value):
                    inline(value).font(.system(size: fontSize + (level == 1 ? 6 : level == 2 ? 4 : 2), weight: .semibold))
                        .padding(.top, 6).accessibilityAddTraits(.isHeader)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .environment(\.layoutDirection, RichTextDirection.detect(value))
                case .paragraph(let value):
                    paragraphs(value).font(.system(size: fontSize))
                case .list(let marker, let value, let depth):
                    HStack(alignment: .top, spacing: 9) {
                        Text(verbatim: marker).foregroundStyle(.secondary).frame(minWidth: 15, alignment: .leading)
                        paragraphs(value).frame(maxWidth: .infinity, alignment: .leading)
                    }.font(.system(size: fontSize)).padding(.leading, CGFloat(min(depth, 4)) * 14)
                        .environment(\.layoutDirection, RichTextDirection.detect(value))
                case .quote(let value):
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: "quote.opening").font(.caption).foregroundStyle(.secondary).accessibilityHidden(true)
                        paragraphs(value).font(.system(size: fontSize)).foregroundStyle(.secondary)
                    }.padding(.vertical, 4)
                        .environment(\.layoutDirection, RichTextDirection.detect(value))
                case .code(let value):
                    ScrollView(.horizontal) {
                        Text(verbatim: value).font(.system(size: max(12, fontSize - 2), design: .monospaced))
                            .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                    }.padding(10).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 5))
                        .environment(\.layoutDirection, .leftToRight)
                case .divider:
                    Divider().padding(.vertical, 4)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .environment(\.openURL, OpenURLAction { url in
            RichTextLinks.allowed(url) ? .systemAction(url) : .discarded
        })
    }

    // Content keeps its own direction regardless of interface language or line count.
    private func paragraphs(_ value: String) -> some View {
        ParagraphText(value: RichTextLinks.attributed(value), fontSize: fontSize, lineSpacing: lineSpacing)
    }

    private func inline(_ value: String) -> some View {
        Text(RichTextLinks.attributed(value)).lineSpacing(lineSpacing)
            .multilineTextAlignment(.leading)
            .textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
    }
}

/// The reading column stays centered as the surrounding interface mirrors.
struct ReadingColumn<Content: View>: View {
    var maximumWidth: CGFloat = 680
    @ViewBuilder let content: Content
    var body: some View {
        content.frame(maxWidth: maximumWidth, alignment: .leading)
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.horizontal, 18).padding(.vertical, 20)
    }
}

struct ReadingSheet<Content: View>: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @Environment(\.dismiss) private var dismiss
    let title: String
    @ViewBuilder let content: Content
    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Text(title).font(.headline).lineLimit(1)
                Spacer()
                Button { dismiss() } label: { Image(systemName: "xmark") }
                    .buttonStyle(.borderless).keyboardShortcut(.cancelAction)
                    .help(L("إغلاق")).accessibilityLabel(L("إغلاق"))
            }.padding(18)
            Divider()
            content
        }.frame(width: 760, height: 700)
            .environment(\.layoutDirection, interfaceLanguage == "en" ? .leftToRight : .rightToLeft)
            .environment(\.locale, AppLanguage.current.locale)
    }
}

/// Plain source evidence: no Markdown interpretation or inserted direction marks.
/// Original characters remain selectable and retain their stored offsets.
struct ProseText: View {
    let text: String
    var fontSize: CGFloat = 16
    var lineSpacing: CGFloat = 6

    var body: some View {
        ParagraphText(value: AttributedString(text), fontSize: fontSize, lineSpacing: lineSpacing)
    }
}

/// Native TextKit lays out the complete paragraph once. Direction is a text
/// attribute, never a mirrored view or state update during measurement.
private struct ParagraphText: NSViewRepresentable {
    let value: AttributedString
    let fontSize: CGFloat
    let lineSpacing: CGFloat

    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> NSTextView {
        let view = NSTextView(frame: .zero)
        view.isEditable = false
        view.isSelectable = true
        view.drawsBackground = false
        view.textContainerInset = .zero
        view.textContainer?.lineFragmentPadding = 0
        view.textContainer?.widthTracksTextView = true
        view.isHorizontallyResizable = false
        view.isVerticallyResizable = true
        view.minSize = .zero
        view.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        view.delegate = context.coordinator
        view.linkTextAttributes = [.foregroundColor: NSColor.linkColor, .underlineStyle: NSUnderlineStyle.single.rawValue]
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        return view
    }
    func updateNSView(_ view: NSTextView, context: Context) {
        let rendered = RichTextLinks.native(value, fontSize: fontSize, lineSpacing: lineSpacing)
        if !view.attributedString().isEqual(to: rendered) {
            view.textStorage?.setAttributedString(rendered)
        }
    }
    func sizeThatFits(_ proposal: ProposedViewSize, nsView view: NSTextView, context: Context) -> CGSize? {
        guard let width = proposal.width, width.isFinite, width > 0,
              let container = view.textContainer, let layout = view.layoutManager else { return nil }
        container.containerSize = NSSize(width: width, height: .greatestFiniteMagnitude)
        view.setFrameSize(NSSize(width: width, height: view.frame.height))
        layout.ensureLayout(for: container)
        return CGSize(width: width, height: ceil(layout.usedRect(for: container).height))
    }
    final class Coordinator: NSObject, NSTextViewDelegate {
        func textView(_ textView: NSTextView, clickedOnLink link: Any, at charIndex: Int) -> Bool {
            let url = (link as? URL) ?? (link as? String).flatMap(URL.init(string:))
            if let url, RichTextLinks.allowed(url) { NSWorkspace.shared.open(url) }
            return true
        }
    }
}

enum RichTextBlock: Equatable {
    case heading(Int, String)
    case paragraph(String)
    case list(String, String, Int)
    case quote(String)
    case code(String)
    case divider

    static func parse(_ text: String) -> [RichTextBlock] {
        var result: [RichTextBlock] = []
        var paragraph: [String] = []
        var code: [String] = []
        var fence: String?
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
            if trimmed.hasPrefix("```") || trimmed.hasPrefix("~~~") {
                flush(); fence = String(trimmed.prefix(3)); continue
            }
            if trimmed.isEmpty { flush(); continue }
            let hashes = trimmed.prefix { $0 == "#" }.count
            if (1...6).contains(hashes), trimmed.dropFirst(hashes).first == " " {
                flush(); result.append(.heading(hashes, String(trimmed.dropFirst(hashes + 1)))); continue
            }
            if ["---", "***", "___"].contains(trimmed) { flush(); result.append(.divider); continue }
            if trimmed.hasPrefix(">") {
                flush(); result.append(.quote(String(trimmed.dropFirst()).trimmingCharacters(in: .whitespaces))); continue
            }
            let depth = line.prefix { $0 == " " || $0 == "\t" }.reduce(0) { $0 + ($1 == "\t" ? 2 : 1) } / 2
            if trimmed.hasPrefix("- ") || trimmed.hasPrefix("* ") || trimmed.hasPrefix("+ ") {
                flush(); result.append(.list("•", String(trimmed.dropFirst(2)), depth)); continue
            }
            if let match = trimmed.range(of: #"^\d+[.)]\s+"#, options: .regularExpression) {
                flush()
                result.append(.list(String(trimmed[match]).trimmingCharacters(in: .whitespaces), String(trimmed[match.upperBound...]), depth))
                continue
            }
            paragraph.append(line)
        }
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
            if let link = run.link, allowed(link) { native.addAttribute(.foregroundColor, value: NSColor.linkColor, range: range) }
            location += length
        }
        let style = NSMutableParagraphStyle()
        style.baseWritingDirection = .natural
        style.alignment = .natural
        style.lineSpacing = lineSpacing
        native.addAttribute(.paragraphStyle, value: style, range: full)
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
        guard let scalar = text.unicodeScalars.first(where: { CharacterSet.letters.contains($0) }) else { return .leftToRight }
        let value = scalar.value
        let rightToLeft = (0x0590...0x08FF).contains(value) || (0xFB1D...0xFDFF).contains(value) ||
            (0xFE70...0xFEFF).contains(value) || (0x10800...0x10FFF).contains(value) || (0x1E900...0x1EEFF).contains(value)
        return rightToLeft ? .rightToLeft : .leftToRight
    }
}
