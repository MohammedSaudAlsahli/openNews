import SwiftUI
import AppKit

enum ArticleReaderText {
    static func withoutRepeatedTitle(_ text: String, title: String, firstBlock: Bool) -> String {
        guard firstBlock else { return text }
        return text.components(separatedBy: "\n").filter { line in
            !(line.hasPrefix("# ") && String(line.dropFirst(2)).trimmingCharacters(in: .whitespaces) == title.trimmingCharacters(in: .whitespaces))
        }.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct ArticleFigure: View {
    @EnvironmentObject private var model: StudioModel
    let articleID, imageID, alt, caption: String
    @State private var image: NSImage?
    @State private var failed = false
    @State private var enlarged = false
    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            if let image {
                Button { enlarged = true } label: {
                    Image(nsImage: image).resizable().aspectRatio(contentMode: .fit).frame(maxWidth: .infinity)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }.buttonStyle(.plain).help(L("تكبير الصورة"))
                    .accessibilityLabel(alt.isEmpty ? L("صورة المقال") : alt)
            } else {
                ZStack {
                    RoundedRectangle(cornerRadius: 8).fill(Color.secondary.opacity(0.07))
                    if failed {
                        VStack(spacing: 8) {
                            Label(L("تعذّر تحميل الصورة"), systemImage: "photo")
                            Button(L("إعادة المحاولة")) { Task { await load() } }
                        }.font(.caption).foregroundStyle(.secondary)
                    } else { ProgressView().controlSize(.small).accessibilityLabel(L("جارٍ تحميل الصورة…")) }
                }.frame(height: 180)
            }
            if !caption.isEmpty { Text(caption).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading).environment(\.layoutDirection, RichTextDirection.detect(caption)) }
        }.task(id: articleID + imageID) { await load() }
            .sheet(isPresented: $enlarged) {
                VStack(spacing: 16) {
                    HStack { Spacer(); Button(L("إغلاق")) { enlarged = false }.keyboardShortcut(.cancelAction) }
                    if let image { Image(nsImage: image).resizable().aspectRatio(contentMode: .fit).frame(maxWidth: .infinity, maxHeight: .infinity).accessibilityLabel(alt.isEmpty ? L("صورة المقال") : alt) }
                    if !caption.isEmpty { Text(caption).font(.callout).textSelection(.enabled) }
                }.padding(24).frame(width: 800, height: 620).editorialPresentation()
            }
    }
    private func load() async {
        failed = false
        for attempt in 0..<2 {
            do {
                let file = try await model.decoded("news.image", ["article_id":articleID,"image_id":imageID], as: ArticleImageFile.self)
                let decoded = await Task.detached(priority: .utility) { ReaderImageDecoder.image(at: file.path) }.value
                guard !Task.isCancelled else { return }
                image = decoded; failed = decoded == nil
                return
            } catch {
                guard !Task.isCancelled else { return }
                if attempt == 0 {
                    do { try await Task.sleep(nanoseconds: 400_000_000) } catch { return }
                } else { failed = true }
            }
        }
    }
}

enum ReaderImageDecoder {
    static func image(at path: String, maxPixelSize: Int = 2048) -> NSImage? {
        guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, [kCGImageSourceShouldCache:false] as CFDictionary),
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString:Any],
              let width = properties[kCGImagePropertyPixelWidth] as? Int,
              let height = properties[kCGImagePropertyPixelHeight] as? Int,
              width > 0, height > 0, width <= 20000, height <= 20000, width * height <= 50_000_000,
              let decoded = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways:true,
                  kCGImageSourceThumbnailMaxPixelSize:maxPixelSize, kCGImageSourceCreateThumbnailWithTransform:true] as CFDictionary) else { return nil }
        return NSImage(cgImage: decoded, size: NSSize(width: decoded.width, height: decoded.height))
    }
}
