import SwiftUI
import AppKit

/// Native, selectable text with a delayed source preview. Ordinary links retain
/// their normal behavior; only citations supplied by the conversation are previewed.
final class CitationTextView: NSTextView {
    var preview: ((URL) -> AnyView?)?
    private var tracking: NSTrackingArea?
    private var pending: DispatchWorkItem?
    private var popover: NSPopover?
    private var hovered: URL?

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let tracking { removeTrackingArea(tracking) }
        let area = NSTrackingArea(rect: .zero, options: [.mouseMoved, .mouseEnteredAndExited, .activeInKeyWindow, .inVisibleRect], owner: self)
        addTrackingArea(area); tracking = area
    }
    override func mouseMoved(with event: NSEvent) {
        super.mouseMoved(with: event)
        guard let (url, index) = citation(at: convert(event.locationInWindow, from: nil)), preview?(url) != nil else {
            leave(); return
        }
        guard hovered != url else { return }
        pending?.cancel(); popover?.close(); hovered = url
        let work = DispatchWorkItem { [weak self] in _ = self?.showPreview(url: url, at: index) }
        pending = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3, execute: work)
    }
    override func mouseExited(with event: NSEvent) { super.mouseExited(with: event); leave() }
    override func viewWillMove(toWindow newWindow: NSWindow?) {
        if newWindow == nil { pending?.cancel(); popover?.close() }
        super.viewWillMove(toWindow: newWindow)
    }
    func citation(at point: NSPoint) -> (URL, Int)? {
        guard let layout = layoutManager, let container = textContainer, layout.numberOfGlyphs > 0 else { return nil }
        let position = NSPoint(x: point.x - textContainerOrigin.x, y: point.y - textContainerOrigin.y)
        let text = attributedString()
        var match: (URL, Int)?
        // Hit-test the actual link rectangles, not the nearest character. In
        // mixed RTL/LTR text nearest-glyph lookup can resolve the adjacent run.
        text.enumerateAttribute(.link, in: NSRange(location: 0, length: text.length)) { value, range, stop in
            guard let value, let url = (value as? URL) ?? (value as? String).flatMap(URL.init(string:)), RichTextLinks.allowed(url) else { return }
            let glyphs = layout.glyphRange(forCharacterRange: range, actualCharacterRange: nil)
            for glyph in glyphs.location..<NSMaxRange(glyphs) {
                if layout.boundingRect(forGlyphRange: NSRange(location: glyph, length: 1), in: container).insetBy(dx: -2, dy: -2).contains(position) {
                    match = (url, range.location); stop.pointee = true; break
                }
            }
        }
        return match
    }
    @discardableResult func showPreview(url: URL, at index: Int) -> Bool {
        guard RichTextLinks.allowed(url), let content = preview?(url), let layout = layoutManager,
              let container = textContainer, window != nil, index < attributedString().length else { return false }
        pending?.cancel()
        if popover?.isShown == true, hovered == url { return true }
        popover?.close(); hovered = url
        let panel = NSPopover()
        panel.behavior = .semitransient
        panel.appearance = effectiveAppearance
        panel.contentViewController = NSHostingController(rootView: content)
        var rect = layout.boundingRect(forGlyphRange: layout.glyphRange(forCharacterRange: NSRange(location: index, length: 1), actualCharacterRange: nil), in: container)
        rect.origin.x += textContainerOrigin.x; rect.origin.y += textContainerOrigin.y
        popover = panel
        panel.show(relativeTo: rect, of: self, preferredEdge: .maxY)
        return true
    }
    private func leave() {
        pending?.cancel()
        let work = DispatchWorkItem { [weak self] in
            guard let self else { return }
            if let panelWindow = self.popover?.contentViewController?.view.window,
               panelWindow.frame.contains(NSEvent.mouseLocation) { return }
            self.popover?.close(); self.hovered = nil
        }
        pending = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.45, execute: work)
    }
}

struct CitationPreview: View {
    let citation: ConversationCitation
    @ObservedObject var model: StudioModel
    @State private var detail: NewsArticleDetail?
    @State private var loading = true
    @State private var failed = false
    private var excerpt: String {
        guard let detail else { return "" }
        return detail.text.isEmpty ? (detail.summary ?? "") : detail.text
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) { SiteIcon(address: citation.url, size: 28); Text(L("معاينة المصدر")).font(.caption).foregroundStyle(.secondary) }.environmentObject(model)
            Text(citation.title).font(.headline).fixedSize(horizontal: false, vertical: true)
                .environment(\.layoutDirection, RichTextDirection.detect(citation.title))
            if let url = URL(string: citation.url), RichTextLinks.allowed(url) {
                Text(url.host ?? "").font(.caption).foregroundStyle(.secondary).environment(\.layoutDirection, .leftToRight)
                if let date = citation.publishedAt { Text(DisplayFormat.date(date)).font(.caption).foregroundStyle(.secondary) }
                Divider()
                if loading { ProgressView(L("جارٍ فتح النص…")).controlSize(.small) }
                else if let detail, !excerpt.isEmpty {
                    ScrollView { ProseText(text: String(excerpt.prefix(1800)), fontSize: 14, lineSpacing: 4) }.frame(height: 170)
                    Text(L(detail.bodyStatus == "full" ? "مقتطف من النص المحفوظ على جهازك." : "المتاح ملخص الخلاصة؛ لم تُقرأ صفحة المقال كاملة.")).font(.caption).foregroundStyle(.secondary)
                } else { Text(L("لا يتوفر نص محفوظ لهذا المرجع. يمكنك فتح المصدر الأصلي.")).font(.callout).foregroundStyle(.secondary) }
                if failed { Button(L("إعادة المحاولة")) { Task { await load() } } }
                Button { NotificationCenter.default.post(name: .openEditorialArticle, object: citation.articleId) } label: { Label(L("المقالات"), systemImage: "newspaper") }.font(.callout)
            }
        }.padding(18).frame(width: 360, height: 450, alignment: .topLeading).editorialPresentation()
            .task(id: citation.id) { await load() }
    }
    private func load() async {
        loading = true; failed = false
        defer { loading = false }
        do { detail = try await model.decoded("news.preview", ["article_id": citation.articleId], as: NewsArticleDetail.self) }
        catch { failed = true }
    }
}
