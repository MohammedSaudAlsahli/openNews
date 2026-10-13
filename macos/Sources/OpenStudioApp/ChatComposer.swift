import SwiftUI
import AppKit

struct ChatComposer: NSViewRepresentable {
    @Binding var text: String
    var canSend: Bool
    let send: () -> Void
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView()
        scroll.drawsBackground = false
        scroll.hasVerticalScroller = true
        let editor = MessageTextView()
        editor.isRichText = false
        editor.drawsBackground = false
        editor.font = .systemFont(ofSize: 14)
        editor.textColor = .textColor
        editor.insertionPointColor = .controlAccentColor
        editor.textContainerInset = NSSize(width: 4, height: 6)
        editor.minSize = .zero
        editor.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        editor.isVerticallyResizable = true
        editor.isHorizontallyResizable = false
        editor.autoresizingMask = [.width]
        editor.textContainer?.widthTracksTextView = true
        editor.textContainer?.containerSize = NSSize(width: 0, height: CGFloat.greatestFiniteMagnitude)
        editor.delegate = context.coordinator
        editor.setAccessibilityLabel(L("رسالة المحادثة"))
        scroll.documentView = editor
        return scroll
    }
    func updateNSView(_ scroll: NSScrollView, context: Context) {
        context.coordinator.parent = self
        guard let editor = scroll.documentView as? MessageTextView else { return }
        if editor.string != text { editor.string = text }
        editor.send = { if canSend { send() } }
        editor.setAccessibilityLabel(L("رسالة المحادثة"))
    }
    final class Coordinator: NSObject, NSTextViewDelegate {
        var parent: ChatComposer
        init(_ parent: ChatComposer) { self.parent = parent }
        func textDidChange(_ notification: Notification) {
            guard let editor = notification.object as? NSTextView else { return }
            parent.text = editor.string
        }
    }
}

final class MessageTextView: NSTextView {
    var send: (() -> Void)?
    static func submits(keyCode: UInt16, modifiers: NSEvent.ModifierFlags, composing: Bool) -> Bool {
        [36, 76].contains(keyCode) && !modifiers.contains(.shift) && !modifiers.contains(.option) && !composing
    }
    override func keyDown(with event: NSEvent) {
        if Self.submits(keyCode: event.keyCode, modifiers: event.modifierFlags, composing: hasMarkedText()) { send?() }
        else { super.keyDown(with: event) }
    }
}
