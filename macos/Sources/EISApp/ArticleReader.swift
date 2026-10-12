import SwiftUI
import AppKit
import ImageIO

/// The same reading surface serves the workspace and the compact menu-bar reader.
struct ArticleReader: View {
    @EnvironmentObject private var model: StudioModel
    @AppStorage("readerFontSize") private var preferredSize = 18.0
    @AppStorage("readerShowsImages") private var showsImages = true
    let article: NewsArticle
    var compact = false
    var useInConversation: Binding<Bool>? = nil
    var onClose: (() -> Void)? = nil
    @State private var detail: NewsArticleDetail?
    @State private var loading = true
    @State private var enriching = false
    @State private var failure: String?
    private var size: CGFloat { CGFloat(min(24, max(14, preferredSize))) - (compact ? 2 : 0) }
    private var text: String { detail?.text.isEmpty == false ? detail!.text : article.summary }
    private var content: [ArticleReadingBlock] { detail?.reader?.blocks ?? [] }
    private var status: String { detail?.reader?.origin == "article" ? "full" : detail?.bodyStatus ?? article.bodyStatus }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                if let onClose {
                    Button(action: onClose) { Label(L("الأخبار"), systemImage: "chevron.backward") }.keyboardShortcut(.cancelAction)
                } else { Label(L("وضع القراءة"), systemImage: "book").font(.callout.weight(.medium)) }
                Spacer()
                if enriching { ProgressView().controlSize(.small).help(L("جارٍ تجهيز الصور وتنسيق المقال…")) }
                Menu {
                    Button(L("تكبير النص")) { preferredSize = min(24, preferredSize + 1) }
                        .disabled(preferredSize >= 24)
                    Button(L("تصغير النص")) { preferredSize = max(14, preferredSize - 1) }
                        .disabled(preferredSize <= 14)
                    Divider()
                    Toggle(L("عرض صور المقال"), isOn: $showsImages)
                    Button(L("إعادة تحميل المقال")) { Task { await enrich(force: true) } }.disabled(enriching || loading)
                    if let useInConversation { Divider(); Toggle(L("استخدم هذا الخبر في المحادثة"), isOn: useInConversation) }
                } label: { Image(systemName: "textformat.size") }
                    .menuStyle(.borderlessButton).frame(width: 28)
                    .help(L("خيارات القراءة")).accessibilityLabel(L("خيارات القراءة"))
                if let url = URL(string: article.url), RichTextLinks.allowed(url) {
                    ShareLink(item: url) { Image(systemName: "square.and.arrow.up") }.labelStyle(.iconOnly)
                        .help(L("مشاركة المقال")).accessibilityLabel(L("مشاركة المقال"))
                    Link(destination: url) { Image(systemName: "arrow.up.right.square") }
                        .help(L("قراءة المصدر الأصلي")).accessibilityLabel(L("قراءة المصدر الأصلي"))
                }
            }.buttonStyle(.borderless).padding(.horizontal, compact ? 16 : 24).padding(.vertical, 13)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: compact ? 20 : 26) {
                    VStack(alignment: .leading, spacing: 14) {
                        Text(article.sourceTitle).font(.system(size: 12, weight: .semibold)).foregroundStyle(.secondary)
                        Text(article.title).font(.system(size: compact ? 24 : 34, weight: .bold, design: .serif))
                            .fixedSize(horizontal: false, vertical: true).textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .environment(\.layoutDirection, RichTextDirection.detect(article.title))
                        if let author = detail?.reader?.author, !author.isEmpty { Text(author).font(.callout).foregroundStyle(.secondary) }
                        Text(metadata).font(.caption).foregroundStyle(.secondary)
                    }
                    if status != "full" {
                        Label(L(status == "media_summary" ? "وصف الحلقة فقط؛ لم يُفرّغ الصوت أو الفيديو." : "ملخص الخلاصة فقط؛ النص الكامل غير متاح."), systemImage: "doc.text")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    if let failure {
                        HStack(alignment: .top) {
                            Text(L(failure)).font(.caption).foregroundStyle(.secondary)
                            Spacer()
                            Button(L("حاول مجددًا")) { Task { await load(force: true) } }.font(.caption)
                        }
                    }
                    if loading && detail == nil { ProgressView(L("جارٍ فتح النص…")).frame(maxWidth: .infinity).padding(40) }
                    else if content.isEmpty { RichTextView(text: text, fontSize: size, lineSpacing: 8) }
                    else {
                        ForEach(Array(content.enumerated()), id: \.offset) { _, block in
                            if block.type == "image", showsImages, let id = block.id {
                                ArticleFigure(articleID: article.id, imageID: id, alt: block.alt ?? "", caption: block.caption ?? "")
                            } else if block.type == "text", let value = block.text {
                                RichTextView(text: ArticleReaderText.withoutRepeatedTitle(value, title: article.title, firstBlock: true), fontSize: size, lineSpacing: 8)
                            }
                        }
                    }
                    Divider().padding(.top, 12)
                    if let url = URL(string: article.url), RichTextLinks.allowed(url) {
                        Link(L("قراءة المصدر الأصلي"), destination: url).font(.callout)
                    }
                }.frame(maxWidth: compact ? 400 : 660, alignment: .leading)
                    .padding(.horizontal, compact ? 20 : 40).padding(.vertical, compact ? 24 : 36)
                    .frame(maxWidth: .infinity, alignment: .center)
            }.background(Color(nsColor: .textBackgroundColor))
        }.task(id: article.id) { await load() }
    }
    private var metadata: String {
        let date = article.publishedAt.map { DisplayFormat.date($0) } ?? L("بلا تاريخ نشر")
        let minutes = max(1, text.split(whereSeparator: \.isWhitespace).count / 200)
        return DisplayFormat.isolated(date) + " · " + L("قراءة نحو {0} دقيقة", DisplayFormat.integer(minutes))
    }
    private func load(force: Bool = false) async {
        loading = true; failure = nil
        do {
            let saved = try await model.decoded("news.article", ["article_id":article.id], as: NewsArticleDetail.self)
            guard !Task.isCancelled else { return }
            detail = saved
            try? await model.refresh()
        }
        catch { failure = error.localizedDescription }
        loading = false
        if !Task.isCancelled, detail != nil, force || detail?.reader?.checkedAt == nil { await enrich(force: force) }
    }
    private func enrich(force: Bool = false) async {
        enriching = true
        defer { enriching = false }
        do {
            let next = try await model.decoded("news.reader", ["article_id":article.id,"refresh":force], as: NewsArticleDetail.self)
            guard !Task.isCancelled else { return }
            detail = next
            failure = next.reader?.refreshFailed == true ? "تعذّر تحديث المقال؛ نعرض النسخة المحفوظة." : nil
        } catch { if !Task.isCancelled { failure = error.localizedDescription } }
    }
}

struct ArticleReaderSheet: View {
    @Environment(\.dismiss) private var dismiss
    let article: NewsArticle
    var useInConversation: Binding<Bool>? = nil
    var body: some View {
        ArticleReader(article: article, useInConversation: useInConversation, onClose: { dismiss() })
            .id(article.id).frame(width: 840, height: 760).editorialPresentation()
    }
}

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
    static func image(at path: String) -> NSImage? {
        guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, [kCGImageSourceShouldCache:false] as CFDictionary),
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString:Any],
              let width = properties[kCGImagePropertyPixelWidth] as? Int,
              let height = properties[kCGImagePropertyPixelHeight] as? Int,
              width > 0, height > 0, width <= 20000, height <= 20000, width * height <= 50_000_000,
              let decoded = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways:true,
                  kCGImageSourceThumbnailMaxPixelSize:2048, kCGImageSourceCreateThumbnailWithTransform:true] as CFDictionary) else { return nil }
        return NSImage(cgImage: decoded, size: NSSize(width: decoded.width, height: decoded.height))
    }
}
