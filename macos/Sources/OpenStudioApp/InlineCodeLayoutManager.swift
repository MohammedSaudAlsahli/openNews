import AppKit

extension NSAttributedString.Key {
    static let inlineCode = NSAttributedString.Key("OpenStudioInlineCode")
}

/// Paint each visual fragment independently without inserting padding characters
/// into selectable text or changing the source's Unicode offsets.
final class InlineCodeLayoutManager: NSLayoutManager {
    override func drawBackground(forGlyphRange glyphsToShow: NSRange, at origin: NSPoint) {
        if let storage = textStorage {
            let visible = characterRange(forGlyphRange: glyphsToShow, actualGlyphRange: nil)
            storage.enumerateAttribute(.inlineCode, in: visible) { value, range, _ in
                guard value != nil else { return }
                let glyphs = glyphRange(forCharacterRange: range, actualCharacterRange: nil)
                enumerateLineFragments(forGlyphRange: glyphs) { lineRect, _, container, lineRange, _ in
                    let fragment = NSIntersectionRange(glyphs, lineRange)
                    var rect = self.boundingRect(forGlyphRange: fragment, in: container)
                    let character = self.characterIndexForGlyph(at: fragment.location)
                    let font = storage.attribute(.font, at: character, effectiveRange: nil) as? NSFont ?? .systemFont(ofSize: 14)
                    // The glyph bounding rect includes paragraph leading. A code
                    // capsule follows the font's baseline, not the whole line box.
                    let baseline = lineRect.minY + self.location(forGlyphAt: fragment.location).y
                    rect.origin.y = baseline - font.ascender - 1
                    rect.size.height = ceil(font.ascender - font.descender + 2)
                    rect.origin.x += origin.x
                    rect.origin.y += origin.y
                    NSColor.labelColor.withAlphaComponent(0.09).setFill()
                    NSBezierPath(roundedRect: rect.insetBy(dx: -2, dy: 0), xRadius: 3, yRadius: 3).fill()
                }
            }
        }
        super.drawBackground(forGlyphRange: glyphsToShow, at: origin)
    }
}
