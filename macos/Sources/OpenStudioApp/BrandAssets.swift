import AppKit

enum BrandAssets {
    /// AppKit uses the alpha mask to choose the correct menu-bar appearance.
    /// Loading both representations preserves sharp edges on Retina displays.
    static let menuBarIcon: NSImage = {
        let image = NSImage(size: NSSize(width: 18, height: 18))
        for suffix in ["", "@2x"] {
            guard let url = Bundle.module.url(forResource: "OpenStudioMenuBar\(suffix)", withExtension: "png"),
                  let data = try? Data(contentsOf: url),
                  let representation = NSBitmapImageRep(data: data) else {
                preconditionFailure("Missing packaged OpenStudio menu bar image")
            }
            representation.size = NSSize(width: 18, height: 18)
            image.addRepresentation(representation)
        }
        image.isTemplate = true
        image.accessibilityDescription = "OpenStudio"
        return image
    }()
}
