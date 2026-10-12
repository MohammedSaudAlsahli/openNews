import SwiftUI
import AppKit

/// Retains the native editor, selection and undo history when the workspace changes columns.
@MainActor final class MarkdownEditorController: ObservableObject {
    var textView: NSTextView?
    var loadedDocumentID: String?
    private var linkRange: NSRange?

    func wrap(_ marker: String) {
        guard let editor = textView, editor.isEditable else { return }
        let range = editor.selectedRange()
        let text = editor.string as NSString
        guard NSMaxRange(range) <= text.length else { return }
        let selected = text.substring(with: range)
        let prefixCount = (marker as NSString).length
        if range.length >= prefixCount * 2 && selected.hasPrefix(marker) && selected.hasSuffix(marker) {
            let inner = String(selected.dropFirst(marker.count).dropLast(marker.count))
            replace(range, with: inner, selection: NSRange(location: range.location, length: (inner as NSString).length))
        } else if range.location >= prefixCount && NSMaxRange(range) + prefixCount <= text.length &&
                    text.substring(with: NSRange(location: range.location - prefixCount, length: prefixCount)) == marker &&
                    text.substring(with: NSRange(location: NSMaxRange(range), length: prefixCount)) == marker {
            replace(NSRange(location: range.location - prefixCount, length: range.length + prefixCount * 2), with: selected,
                    selection: NSRange(location: range.location - prefixCount, length: range.length))
        } else {
            replace(range, with: marker + selected + marker,
                    selection: NSRange(location: range.location + prefixCount, length: range.length))
        }
    }

    func prefixLines(_ marker: String) {
        guard let editor = textView, editor.isEditable else { return }
        let text = editor.string as NSString
        let selected = editor.selectedRange()
        guard NSMaxRange(selected) <= text.length else { return }
        // A selection ending at the start of the next line shouldn't format that line.
        let selectionForLines = NSRange(location: selected.location, length: max(0, selected.length - (selected.length > 0 ? 1 : 0)))
        let range = text.lineRange(for: selectionForLines)
        var lines = text.substring(with: range).components(separatedBy: "\n")
        let trailingNewline = lines.last == "" && lines.count > 1
        if trailingNewline { lines.removeLast() }
        let remove = !lines.isEmpty && lines.allSatisfy { $0.hasPrefix(marker) }
        lines = lines.map { line in
            if remove { return String(line.dropFirst(marker.count)) }
            if marker.hasPrefix("#"), let heading = line.range(of: #"^#{1,6} "#, options: .regularExpression) {
                return marker + String(line[heading.upperBound...])
            }
            return marker + line
        }
        let replacement = lines.joined(separator: "\n") + (trailingNewline ? "\n" : "")
        let length = (replacement as NSString).length
        let cursor = selected.length == 0 ? NSRange(location: min(range.location + length, selected.location + length - range.length), length: 0) : NSRange(location: range.location, length: length)
        replace(range, with: replacement, selection: NSRange(location: max(range.location, cursor.location), length: cursor.length))
    }

    func beginLink() -> String {
        guard let editor = textView else { return "" }
        let range = editor.selectedRange()
        linkRange = range
        let text = editor.string as NSString
        return NSMaxRange(range) <= text.length ? text.substring(with: range) : ""
    }

    func insertLink(label: String, url: String) -> Bool {
        guard let parsed = URL(string: url.trimmingCharacters(in: .whitespacesAndNewlines)), RichTextLinks.allowed(parsed),
              let editor = textView, editor.isEditable else { return false }
        let range = linkRange ?? editor.selectedRange()
        guard NSMaxRange(range) <= (editor.string as NSString).length else { return false }
        let title = label.isEmpty ? parsed.absoluteString : label
        let escapedTitle = title.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "[", with: "\\[").replacingOccurrences(of: "]", with: "\\]").replacingOccurrences(of: "\n", with: " ")
        let target = parsed.absoluteString.replacingOccurrences(of: "(", with: "%28").replacingOccurrences(of: ")", with: "%29").replacingOccurrences(of: ">", with: "%3E").replacingOccurrences(of: "<", with: "%3C")
        let replacement = "[" + escapedTitle + "](" + target + ")"
        replace(range, with: replacement, selection: NSRange(location: range.location + (replacement as NSString).length, length: 0))
        linkRange = nil
        return true
    }

    private func replace(_ range: NSRange, with value: String, selection: NSRange) {
        guard let editor = textView else { return }
        editor.window?.makeFirstResponder(editor)
        editor.insertText(value, replacementRange: range)
        editor.setSelectedRange(selection)
        editor.scrollRangeToVisible(selection)
    }
}

struct MarkdownEditor: NSViewRepresentable {
    @Binding var text: String
    @ObservedObject var controller: MarkdownEditorController
    var documentID = "new"
    var interfaceLanguage = "ar"
    var editable = true
    var fontSize: CGFloat = 18
    var lineSpacing: CGFloat = 8

    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.hasHorizontalScroller = false
        scroll.autohidesScrollers = true
        scroll.borderType = .noBorder
        scroll.drawsBackground = false
        let editor = controller.textView ?? NSTextView(frame: .zero)
        editor.removeFromSuperview()
        editor.isRichText = false
        editor.importsGraphics = false
        editor.allowsUndo = true
        editor.isContinuousSpellCheckingEnabled = true
        editor.isAutomaticQuoteSubstitutionEnabled = false
        editor.isAutomaticDashSubstitutionEnabled = false
        editor.isAutomaticLinkDetectionEnabled = false
        editor.usesFindBar = true
        editor.isVerticallyResizable = true
        editor.isHorizontallyResizable = false
        editor.autoresizingMask = [.width]
        editor.minSize = .zero
        editor.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        editor.textContainer?.containerSize = NSSize(width: scroll.contentSize.width, height: CGFloat.greatestFiniteMagnitude)
        editor.textContainer?.widthTracksTextView = true
        editor.textContainerInset = NSSize(width: 5, height: 5)
        editor.drawsBackground = false
        editor.delegate = context.coordinator
        editor.setAccessibilityLabel(Localization.text("نص المسودة", language: AppLanguage.resolve(interfaceLanguage)))
        controller.textView = editor
        scroll.documentView = editor
        updateNSView(scroll, context: context)
        return scroll
    }
    func updateNSView(_ scroll: NSScrollView, context: Context) {
        context.coordinator.parent = self
        guard let editor = scroll.documentView as? NSTextView else { return }
        editor.isEditable = editable
        editor.isSelectable = true
        editor.setAccessibilityLabel(Localization.text("نص المسودة", language: AppLanguage.resolve(interfaceLanguage)))
        let externalChange = editor.string != text || controller.loadedDocumentID != documentID
        controller.loadedDocumentID = documentID
        if externalChange {
            editor.string = text
            editor.undoManager?.removeAllActions()
            editor.setSelectedRange(NSRange(location: 0, length: 0))
        }
        let paragraph = NSMutableParagraphStyle()
        // Each paragraph follows its own first strong character, independent of interface language.
        paragraph.baseWritingDirection = .natural
        paragraph.alignment = .natural
        paragraph.lineSpacing = lineSpacing
        let font = NSFont.systemFont(ofSize: fontSize)
        editor.font = font
        editor.textColor = .textColor
        editor.insertionPointColor = .textColor
        editor.defaultParagraphStyle = paragraph
        editor.typingAttributes = [.font: font, .foregroundColor: NSColor.textColor, .paragraphStyle: paragraph]
        if externalChange || context.coordinator.lastSpacing != lineSpacing || context.coordinator.lastSize != fontSize {
            editor.textStorage?.addAttributes([.font: font, .foregroundColor: NSColor.textColor, .paragraphStyle: paragraph], range: NSRange(location: 0, length: (editor.string as NSString).length))
            context.coordinator.lastSpacing = lineSpacing; context.coordinator.lastSize = fontSize
        }
    }
    final class Coordinator: NSObject, NSTextViewDelegate {
        var parent: MarkdownEditor
        var lastSpacing: CGFloat?
        var lastSize: CGFloat?
        init(_ parent: MarkdownEditor) { self.parent = parent }
        func textDidChange(_ notification: Notification) {
            guard let editor = notification.object as? NSTextView else { return }
            parent.text = editor.string
        }
    }
}

struct MarkdownFormattingToolbar: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @ObservedObject var controller: MarkdownEditorController
    @Binding var preview: Bool
    var enabled = true
    @State private var linking = false
    @State private var linkLabel = ""
    @State private var linkURL = ""
    @State private var error: String?
    var body: some View {
        let _ = interfaceLanguage
        ViewThatFits(in: .horizontal) {
            controls
            ScrollView(.horizontal, showsIndicators: false) { controls }
        }
        .controlSize(.small)
        .sheet(isPresented: $linking) {
            VStack(alignment: .leading, spacing: 16) {
                Text(L("إدراج رابط")).font(.title2)
                TextField(L("النص الظاهر"), text: $linkLabel)
                LabeledContent(L("الرابط")) {
                    TextField("", text: $linkURL, prompt: Text("https://…"))
                        .environment(\.layoutDirection, .leftToRight)
                        .accessibilityLabel(L("الرابط"))
                }
                Text(L("يدعم روابط HTTP وHTTPS فقط.")).font(.caption).foregroundStyle(.secondary)
                if let error { Text(error).font(.callout).foregroundStyle(.red) }
                HStack {
                    Button(L("إلغاء"), role: .cancel) { linking = false }.keyboardShortcut(.cancelAction)
                    Spacer()
                    Button(L("إدراج")) {
                        if controller.insertLink(label: linkLabel, url: linkURL) { linking = false }
                        else { error = L("أدخل رابط HTTP أو HTTPS صالحًا، دون بيانات دخول.") }
                    }.buttonStyle(.borderedProminent).disabled(linkURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }.padding(24).frame(width: 460).editorialPresentation().textFieldStyle(.roundedBorder)
        }
    }
    private var controls: some View {
        HStack(spacing: 6) {
            Group {
                Menu {
                    Button(L("عنوان رئيسي")) { controller.prefixLines("# ") }
                    Button(L("عنوان فرعي")) { controller.prefixLines("## ") }
                    Button(L("عنوان صغير")) { controller.prefixLines("### ") }
                } label: { Image(systemName: "textformat.size") }.help(L("تنسيق العنوان")).accessibilityLabel(L("تنسيق العنوان")).frame(width: 35)
                formatButton(L("غامق"), icon: "bold") { controller.wrap("**") }
                formatButton(L("مائل"), icon: "italic") { controller.wrap("*") }
                formatButton(L("قائمة"), icon: "list.bullet") { controller.prefixLines("- ") }
                formatButton(L("اقتباس"), icon: "text.quote") { controller.prefixLines("> ") }
                formatButton(L("رابط"), icon: "link") { linkLabel = controller.beginLink(); linkURL = ""; error = nil; linking = true }
            }.disabled(preview || !enabled)
            Spacer(minLength: 8)
            Picker(L("عرض المسودة"), selection: $preview) {
                Text(L("تحرير")).tag(false)
                Text(L("معاينة")).tag(true)
            }.pickerStyle(.segmented).frame(width: 140).labelsHidden().accessibilityLabel(L("تحرير أو معاينة المسودة"))
        }.padding(.vertical, 5)
    }
    private func formatButton(_ title: String, icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) { Image(systemName: icon).frame(width: 19, height: 18) }
            .help(title).accessibilityLabel(title)
    }
}
