import SwiftUI
import AppKit

enum ArticleExcerpt {
    static func plain(_ text: String) -> String {
        let clean = RichTextLinks.attributed(text).characters
        return String(String(clean).replacingOccurrences(of: #"(?m)^\s*[#>*-]+\s*"#, with: "", options: .regularExpression)
            .split(whereSeparator: \.isWhitespace).joined(separator: " ").prefix(320))
    }
}

struct SiteIcon: View {
    @Environment(\.editorialTheme) private var theme
    @EnvironmentObject private var model: StudioModel
    let address: String
    var size: CGFloat = 24
    @State private var icon: NSImage?
    private var host: String { URL(string: address)?.host?.replacingOccurrences(of: "www.", with: "") ?? "" }
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.24).fill(theme.surface)
            if let icon { Image(nsImage: icon).resizable().aspectRatio(contentMode: .fit).padding(size * 0.15) }
            else { Text(String(host.prefix(1)).uppercased()).font(.system(size: size * 0.5, weight: .semibold)).foregroundStyle(.secondary) }
        }.frame(width: size, height: size).accessibilityHidden(true)
            .task(id: host) {
                if let cached = SiteIconCache.images.object(forKey: host as NSString) { icon = cached; return }
                guard let file = try? await model.decoded("news.icon", ["url": address], as: ArticleImageFile.self), !file.path.isEmpty else { return }
                icon = await Task.detached(priority: .utility) { ReaderImageDecoder.image(at: file.path) }.value
                if let icon { SiteIconCache.images.setObject(icon, forKey: host as NSString) }
            }
    }
}

struct ArticleCard: View {
    @Environment(\.editorialTheme) private var theme
    @EnvironmentObject private var model: StudioModel
    @State private var saved = false
    @State private var saving = false
    @State private var failure: String?
    let article: NewsArticle
    var compact = false
    let open: () -> Void
    var body: some View {
        Button(action: open) {
            VStack(alignment: .leading, spacing: 12) {
                ArticleThumbnail(articleID: article.id, imageID: article.coverImageId, height: compact ? 135 : 200)
                VStack(alignment: .leading, spacing: 9) {
                    HStack(spacing: 7) {
                        SiteIcon(address: article.url, size: 20)
                        Text(article.sourceTitle).lineLimit(1)
                        Spacer(minLength: 0)

                        if article.isRead != true { Circle().fill(Color.accentColor).frame(width: 6, height: 6).accessibilityLabel(L("غير المقروء")) }
                    }.font(.caption).foregroundStyle(.secondary)
                    Text(article.title).font(.system(size: compact ? 16 : 21, weight: .semibold, design: .serif))
                        .lineLimit(3).frame(height: compact ? 58 : 78, alignment: .topLeading)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .environment(\.layoutDirection, RichTextDirection.detect(article.title))
                    Text(ArticleExcerpt.plain(article.summary)).font(.system(size: compact ? 13 : 14)).foregroundStyle(.secondary)
                        .lineLimit(3).lineSpacing(3).frame(height: compact ? 54 : 60, alignment: .topLeading).frame(maxWidth: .infinity, alignment: .leading)
                        .environment(\.layoutDirection, RichTextDirection.detect(article.summary))
                    Text(DisplayFormat.date(article.publishedAt ?? article.discoveredAt)).font(.caption2).foregroundStyle(.tertiary)
                }.padding(compact ? 14 : 18)
            }.frame(maxWidth: .infinity, alignment: .leading).multilineTextAlignment(.leading)
                .background(theme.paper, in: RoundedRectangle(cornerRadius: 14))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.primary.opacity(0.08)))
                .clipShape(RoundedRectangle(cornerRadius: 14)).contentShape(Rectangle())
        }.buttonStyle(.plain).accessibilityLabel(article.title)
        .overlay(alignment: .topTrailing) {
            Button {
                saving = true
                Task {
                    defer { saving = false }
                    do {
                        _ = try await model.call("news.bookmark", ["article_id": article.id, "saved": !saved])
                        saved.toggle()
                        NotificationCenter.default.post(name: .editorialBookmarksChanged, object: article.id)
                    } catch { failure = error.localizedDescription }
                }
            } label: {
                Image(systemName: saved ? "bookmark.fill" : "bookmark").font(.system(size: 15, weight: .medium))
                    .frame(width: 32, height: 32).background(.regularMaterial, in: Circle())
            }.buttonStyle(.plain).disabled(saving).padding(10)
                .help(L(saved ? "إزالة من المحفوظات" : "حفظ المقال"))
                .accessibilityLabel(L(saved ? "إزالة من المحفوظات" : "حفظ المقال") + " · " + article.title)
        }
        .onAppear { saved = article.isBookmarked == true }
        .onChange(of: article.isBookmarked) { _, value in saved = value == true }
        .alert(L("تعذّر حفظ المقال"), isPresented: Binding(get: { failure != nil }, set: { if !$0 { failure = nil } })) { Button(L("إغلاق")) { failure = nil } } message: { Text(failure ?? "") }
    }
}

private struct ArticleThumbnail: View {
    @Environment(\.editorialTheme) private var theme
    @EnvironmentObject private var model: StudioModel
    let articleID: String
    let imageID: String?
    let height: CGFloat
    @State private var image: NSImage?
    @State private var loading = false
    var body: some View {
        ZStack {
            theme.surface
            if let image {
                GeometryReader { geometry in
                    Image(nsImage: image).resizable().scaledToFill().frame(width: geometry.size.width, height: height).clipped()
                }
            } else {
                VStack(spacing: 10) {
                    Image(systemName: "photo").font(.system(size: 28, weight: .light))
                    if loading { ProgressView().controlSize(.small) }
                    else { Text(L("لا توجد صورة")).font(.caption) }
                }.foregroundStyle(.secondary)
            }
        }.frame(height: height).accessibilityHidden(true)
            .task(id: articleID + (imageID ?? "")) {
                image = nil
                guard let imageID else { return }
                loading = true
                defer { loading = false }
                guard let file = try? await model.decoded("news.image", ["article_id": articleID, "image_id": imageID], as: ArticleImageFile.self) else { return }
                image = await Task.detached(priority: .utility) { ReaderImageDecoder.image(at: file.path) }.value
            }
    }
}

private enum SiteIconCache {
    static let images: NSCache<NSString, NSImage> = { let cache = NSCache<NSString, NSImage>(); cache.countLimit = 300; return cache }()
}
