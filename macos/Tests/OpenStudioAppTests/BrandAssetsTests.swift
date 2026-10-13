import AppKit
import Testing
@testable import OpenStudioApp

@Test func menuBarBrandUsesATransparentRetinaTemplate() throws {
    let image = BrandAssets.menuBarIcon
    #expect(image.isTemplate)
    #expect(image.size == NSSize(width: 18, height: 18))
    let representations = image.representations.compactMap { $0 as? NSBitmapImageRep }
    #expect(Set(representations.map(\.pixelsWide)) == [18, 36])
    for rep in representations {
        #expect(rep.hasAlpha)
        #expect(rep.size == NSSize(width: 18, height: 18))
        #expect(rep.colorAt(x: 0, y: 0)?.alphaComponent == 0)
    }
}
