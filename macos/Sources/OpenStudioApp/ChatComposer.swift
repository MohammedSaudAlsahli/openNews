import SwiftUI
import AppKit

struct ChatComposer: NSViewRepresentable {
    @Binding var text: String
    @Binding var height: CGFloat
    @Binding var focused: Bool
    var canSend: Bool
    let send: () -> Void
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView()
        scroll.drawsBackground = false
        scroll.hasVerticalScroller = true
        scroll.autohidesScrollers = true
        let editor = MessageTextView()
        editor.isRichText = false
        editor.drawsBackground = false
        editor.font = .systemFont(ofSize: 15)
        editor.textColor = .textColor
        editor.insertionPointColor = .controlAccentColor
        editor.textContainerInset = NSSize(width: 0, height: 7)
        editor.minSize = .zero
        editor.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        editor.isVerticallyResizable = true
        editor.isHorizontallyResizable = false
        editor.autoresizingMask = [.width]
        editor.textContainer?.widthTracksTextView = true
        editor.textContainer?.containerSize = NSSize(width: 0, height: CGFloat.greatestFiniteMagnitude)
        editor.delegate = context.coordinator
        editor.layoutChanged = { [weak coordinator = context.coordinator] in coordinator?.measure() }
        editor.focusChanged = { [weak coordinator = context.coordinator] value in
            DispatchQueue.main.async { coordinator?.parent.focused = value }
        }
        context.coordinator.editor = editor
        editor.setAccessibilityLabel(L("رسالة المحادثة"))
        scroll.documentView = editor
        return scroll
    }
    func updateNSView(_ scroll: NSScrollView, context: Context) {
        context.coordinator.parent = self
        guard let editor = scroll.documentView as? MessageTextView else { return }
        if editor.string != text { editor.string = text; editor.refreshParagraphDirections() }
        editor.send = { if canSend { send() } }
        editor.setAccessibilityLabel(L("رسالة المحادثة"))
        context.coordinator.measure()
    }
    final class Coordinator: NSObject, NSTextViewDelegate {
        weak var editor: MessageTextView?
        var parent: ChatComposer
        init(_ parent: ChatComposer) { self.parent = parent }
        func textDidChange(_ notification: Notification) {
            guard let editor = notification.object as? MessageTextView else { return }
            editor.refreshParagraphDirections()
            parent.text = editor.string
            measure()
        }
        func measure() {
            guard let editor, let container = editor.textContainer, let layout = editor.layoutManager,
                  editor.bounds.width > 0 else { return }
            layout.ensureLayout(for: container)
            let measured = min(160, max(38, ceil(layout.usedRect(for: container).height + 16)))
            DispatchQueue.main.async { [weak self] in
                guard let self, abs(self.parent.height - measured) > 1 else { return }
                self.parent.height = measured
            }
        }
    }
}

final class MessageTextView: NSTextView {
    var send: (() -> Void)?
    var layoutChanged: (() -> Void)?
    var focusChanged: ((Bool) -> Void)?
    override func setFrameSize(_ newSize: NSSize) {
        super.setFrameSize(newSize)
        layoutChanged?()
    }
    override func becomeFirstResponder() -> Bool {
        let accepted = super.becomeFirstResponder()
        if accepted { focusChanged?(true) }
        return accepted
    }
    override func resignFirstResponder() -> Bool {
        let accepted = super.resignFirstResponder()
        if accepted { focusChanged?(false) }
        return accepted
    }
    func refreshParagraphDirections() {
        guard !hasMarkedText(), let storage = textStorage else { return }
        let content = string as NSString
        var offset = 0
        while offset < content.length {
            let range = content.paragraphRange(for: NSRange(location: offset, length: 0))
            let rtl = RichTextDirection.detect(content.substring(with: range)) == .rightToLeft
            let style = NSMutableParagraphStyle()
            style.alignment = rtl ? .right : .left
            style.baseWritingDirection = rtl ? .rightToLeft : .leftToRight
            style.lineSpacing = 3
            storage.addAttribute(.paragraphStyle, value: style, range: range)
            if NSLocationInRange(selectedRange().location, range) || selectedRange().location == NSMaxRange(range) {
                typingAttributes[.paragraphStyle] = style
            }
            offset = NSMaxRange(range)
        }
    }
    static func submits(keyCode: UInt16, modifiers: NSEvent.ModifierFlags, composing: Bool) -> Bool {
        [36, 76].contains(keyCode) && !modifiers.contains(.shift) && !modifiers.contains(.option) && !composing
    }
    override func keyDown(with event: NSEvent) {
        if Self.submits(keyCode: event.keyCode, modifiers: event.modifierFlags, composing: hasMarkedText()) { send?() }
        else { super.keyDown(with: event) }
    }
}
