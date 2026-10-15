import SwiftUI
import AppKit
import NaturalLanguage

/// Read-only Markdown and plain-text rendering. No HTML, web views, image loading or scripts.
struct RichTextView: View {
    @Environment(\.editorialTheme) private var theme
    let text: String
    var fontSize: CGFloat = 16
    var lineSpacing: CGFloat = 6
    var citationPreview: ((URL) -> AnyView?)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            ForEach(Array(RichTextBlock.parse(text).enumerated()), id: \.offset) { _, block in
                switch block {
                case .heading(let level, let value):
                    inline(value).font(.system(size: fontSize + (level == 1 ? 6 : level == 2 ? 4 : 2), weight: .semibold))
                        .padding(.top, 10).accessibilityAddTraits(.isHeader)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .environment(\.layoutDirection, RichTextDirection.markdown(value))
                case .paragraph(let value):
                    paragraphs(value).font(.system(size: fontSize))
                case .list(let marker, let value, let depth):
                    HStack(alignment: .top, spacing: 9) {
                        Text(verbatim: marker).foregroundStyle(.secondary).frame(minWidth: 15, alignment: .leading)
                        paragraphs(value).frame(maxWidth: .infinity, alignment: .leading)
                    }.font(.system(size: fontSize)).padding(.leading, CGFloat(min(depth, 4)) * 14)
                        .environment(\.layoutDirection, RichTextDirection.markdown(value))
                case .quote(let value):
                    HStack(alignment: .top, spacing: 10) {
                        paragraphs(value).font(.system(size: fontSize)).foregroundStyle(.secondary)
                    }.padding(.horizontal, 16).padding(.vertical, 4)
                        .overlay(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 2).fill(Color.accentColor.opacity(0.55)).frame(width: 3)
                        }
                        .environment(\.layoutDirection, RichTextDirection.markdown(value))
                case .code(let value, let language):
                    MarkdownCodeBlock(code: value, language: language, fontSize: fontSize)
                case .table(let rows):
                    ScrollView(.horizontal) {
                        VStack(spacing: 0) {
                            ForEach(Array(rows.enumerated()), id: \.offset) { index, cells in
                                HStack(alignment: .top, spacing: 0) {
                                    ForEach(Array(cells.enumerated()), id: \.offset) { _, cell in
                                        Text(RichTextLinks.attributed(cell)).font(.system(size: fontSize - 2, weight: index == 0 ? .semibold : .regular))
                                            .frame(width: 150, alignment: .leading).padding(12)
                                    }
                                }.background(index == 0 ? theme.surface : Color.clear)
                                Divider()
                            }
                        }.overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.primary.opacity(0.1)))
                    }.environment(\.layoutDirection, RichTextDirection.detect(rows.flatMap { $0 }.joined(separator: " ")))
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
        ParagraphText(value: RichTextLinks.attributed(value), fontSize: fontSize, lineSpacing: lineSpacing, citationPreview: citationPreview)
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
    var citationPreview: ((URL) -> AnyView?)? = nil

    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> NSTextView {
        let storage = NSTextStorage()
        let layout = InlineCodeLayoutManager()
        let container = NSTextContainer(containerSize: .zero)
        storage.addLayoutManager(layout)
        layout.addTextContainer(container)
        let view = CitationTextView(frame: .zero, textContainer: container)
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
        (view as? CitationTextView)?.preview = citationPreview
        guard context.coordinator.lastValue != value || context.coordinator.lastFontSize != fontSize || context.coordinator.lastLineSpacing != lineSpacing else { return }
        context.coordinator.lastValue = value
        context.coordinator.lastFontSize = fontSize
        context.coordinator.lastLineSpacing = lineSpacing
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
        var lastValue: AttributedString?
        var lastFontSize: CGFloat?
        var lastLineSpacing: CGFloat?

        func textView(_ textView: NSTextView, clickedOnLink link: Any, at charIndex: Int) -> Bool {
            let url = (link as? URL) ?? (link as? String).flatMap(URL.init(string:))
            if let url, let view = textView as? CitationTextView, view.showPreview(url: url, at: charIndex) { return true }
            if let url, RichTextLinks.allowed(url) { NSWorkspace.shared.open(url) }
            return true
        }
    }
}
