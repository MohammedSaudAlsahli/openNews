import SwiftUI
import AppKit
import ImageIO

struct ArticleReader: View {
    @Environment(\.editorialTheme) private var theme
    @EnvironmentObject private var model: StudioModel
    @Environment(\.openSettings) private var openSettings
    @AppStorage("readerFontSize") private var preferredSize = 18.0
    @AppStorage("readerShowsImages") private var showsImages = true
    let article: NewsArticle
    var compact = false
    var useInConversation: Binding<Bool>? = nil
    var onClose: (() -> Void)? = nil
    var onDiscuss: (() -> Void)? = nil
    @State private var detail: NewsArticleDetail?
    @State private var loading = true
    @State private var enriching = false
    @State private var failure: String?
    @State private var tab = "reader"
    @State private var openedWebsite = false
    @State private var history = false
    @State private var bookmarked = false
    @State private var saving = false
    @State private var summarizing = false
    @State private var summary: ArticleAISummary?
    @State private var summaryError: String?
    @State private var publicCapture = PublicPageCapture()
    private var size: CGFloat { compact ? min(preferredSize, 18) : preferredSize }
    private var text: String { detail?.text.isEmpty == false ? detail!.text : article.summary }
    private var content: [ArticleReadingBlock] { detail?.reader?.blocks ?? [] }
    private var cover: ArticleReadingBlock? { content.first { $0.type == "image" } }
    private var status: String { detail?.bodyStatus ?? article.bodyStatus }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: compact ? 10 : 18) {
                if let onClose {
                    Button(action: onClose) { Image(systemName: "chevron.backward") }.help(L("العودة للمقالات")).accessibilityLabel(L("العودة للمقالات"))
                }
                Picker(L("عرض المقال"), selection: $tab) {
                    Text(L("القارئ")).tag("reader")
                    Text(L("الموقع الأصلي")).tag("website")
                }.pickerStyle(.segmented).labelsHidden().frame(maxWidth: 230)
                Spacer(minLength: 0)
                if enriching { ProgressView().controlSize(.small).help(L("جارٍ تجهيز الصور وتنسيق المقال…")) }
                if let onDiscuss {
                    Button(action: onDiscuss) { Label(L("ناقش الخبر"), systemImage: "bubble.left") }
                        .help(L("ناقش هذا الخبر مع المساعد"))
                }
                Button { Task { await bookmark() } } label: { Image(systemName: bookmarked ? "bookmark.fill" : "bookmark") }
                    .disabled(saving).help(L(bookmarked ? "إزالة من المحفوظات" : "حفظ المقال"))
                    .accessibilityLabel(L(bookmarked ? "إزالة من المحفوظات" : "حفظ المقال"))
                Menu {
                    Button(L("سجل تعديلات المقالة")) { history = true }
                    Button(L("تكبير النص")) { preferredSize = min(24, preferredSize + 1) }.disabled(preferredSize >= 24)
                    Button(L("تصغير النص")) { preferredSize = max(14, preferredSize - 1) }.disabled(preferredSize <= 14)
                    Toggle(L("عرض صور المقال"), isOn: $showsImages)
                    if let useInConversation { Divider(); Toggle(L("استخدم هذا الخبر في المحادثة"), isOn: useInConversation) }
                    if let url = URL(string: article.url), RichTextLinks.allowed(url) {
                        Divider()
                        ShareLink(item: url) { Label(L("مشاركة المقال"), systemImage: "square.and.arrow.up") }
                    }
                } label: { Image(systemName: "textformat.size") }
                    .menuStyle(.borderlessButton).frame(width: 26).help(L("خيارات القراءة")).accessibilityLabel(L("خيارات القراءة"))
            }.buttonStyle(.borderless).padding(.horizontal, compact ? 14 : 26).padding(.vertical, 14)
            Divider()
            ZStack {
                readerBody.accessibilityElement(children: .contain).disabled(tab != "reader").opacity(tab == "reader" ? 1 : 0).allowsHitTesting(tab == "reader").accessibilityHidden(tab != "reader")
                if openedWebsite, let url = URL(string: article.url), RichTextLinks.allowed(url) {
                    ArticleWebsite(url: url, active: tab == "website").accessibilityElement(children: .contain).disabled(tab != "website").opacity(tab == "website" ? 1 : 0)
                        .allowsHitTesting(tab == "website").accessibilityHidden(tab != "website")
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }.background(theme.paper)
            .sheet(isPresented: $history) { ArticleHistory(articleID: article.id, articleTitle: article.title) }
            .task(id: article.id) { bookmarked = article.isBookmarked == true; await load() }
            .onChange(of: tab) { _, value in if value == "website" { openedWebsite = true } }
    }
    private var readerBody: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: compact ? 20 : 28) {
                if showsImages, let cover, let id = cover.id {
                    ArticleFigure(articleID: article.id, imageID: id, alt: cover.alt ?? "", caption: cover.caption ?? "")
                }
                VStack(alignment: .leading, spacing: 14) {
                    HStack(spacing: 8) { SiteIcon(address: article.url, size: 22); Text(article.sourceTitle).font(.callout.weight(.medium)).foregroundStyle(.secondary) }
                    Text(article.title).font(.system(size: compact ? 25 : 36, weight: .bold, design: .serif))
                        .fixedSize(horizontal: false, vertical: true).textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .environment(\.layoutDirection, RichTextDirection.detect(article.title))
                    if let author = detail?.reader?.author, !author.isEmpty { Text(author).font(.callout).foregroundStyle(.secondary) }
                    Text(metadata).font(.caption).foregroundStyle(.secondary)
                    let excerpt = ArticleExcerpt.plain(article.summary)
                    if !excerpt.isEmpty {
                        ProseText(text: excerpt, fontSize: compact ? 15 : 18, lineSpacing: 6).opacity(0.76)
                    }
                }
                VStack(alignment: .leading, spacing: 14) {
                    if summarizing { ProgressView(L("جارٍ تلخيص المقال…")).controlSize(.small) }
                    else if summary == nil {
                        Button { Task { await summarize() } } label: { Label(L("لخّص بالذكاء الاصطناعي"), systemImage: "sparkles") }.buttonStyle(.bordered)
                    }
                    if let summary {
                        Label(L("الخلاصة بالذكاء الاصطناعي"), systemImage: "sparkles").font(.headline)
                        RichTextView(text: summary.summary, fontSize: compact ? 15 : 17, lineSpacing: 6)
                        Text(summary.model).font(.caption).foregroundStyle(.secondary)
                    }
                    if let summaryError {
                        Text(L(summaryError)).font(.caption).foregroundStyle(.secondary)
                        if !ModelPermission.allowed() { Button(L("الإعدادات")) { openSettings() } }
                    }
                }.padding(16).frame(maxWidth: .infinity, alignment: .leading)
                    .background(theme.surface, in: RoundedRectangle(cornerRadius: 12))
                if status != "full" && !loading && !enriching {
                    Label(L(status == "media_summary" ? "وصف الحلقة فقط؛ لم يُفرّغ الصوت أو الفيديو." : "ملخص الخلاصة فقط؛ النص الكامل غير متاح."), systemImage: "doc.text").font(.caption).foregroundStyle(.secondary)
                }
                if let failure {
                    HStack(alignment: .top) {
                        Text(L(failure)).font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button(L("حاول مجددًا")) { Task { await load(force: true) } }.font(.caption)
                    }
                }
                if loading && detail == nil { ProgressView(L("جارٍ فتح النص…")).frame(maxWidth: .infinity).padding(40) }
                else if content.isEmpty { RichTextView(text: text, fontSize: size, lineSpacing: 5) }
                else {
                    ForEach(Array(content.enumerated()), id: \.offset) { _, block in
                        if block.type == "image", showsImages, let id = block.id, id != cover?.id {
                            ArticleFigure(articleID: article.id, imageID: id, alt: block.alt ?? "", caption: block.caption ?? "")
                        } else if block.type == "text", let value = block.text {
                            RichTextView(text: ArticleReaderText.withoutRepeatedTitle(value, title: article.title, firstBlock: true), fontSize: size, lineSpacing: 5)
                        }
                    }
                }
                RelatedNews(articleID: article.id)
            }.frame(maxWidth: compact ? 450 : 700, alignment: .leading)
                .padding(.horizontal, compact ? 22 : 48).padding(.vertical, compact ? 24 : 40)
                .frame(maxWidth: .infinity, alignment: .center)
        }
    }
    private var metadata: String {
        let date = article.publishedAt.map { DisplayFormat.date($0) } ?? L("بلا تاريخ نشر")
        let minutes = max(1, text.split(whereSeparator: \.isWhitespace).count / 200)
        return DisplayFormat.isolated(date) + " · " + L("قراءة نحو {0} دقيقة", DisplayFormat.integer(minutes))
    }
    private func bookmark() async {
        saving = true
        defer { saving = false }
        do {
            _ = try await model.call("news.bookmark", ["article_id": article.id, "saved": !bookmarked])
            bookmarked.toggle(); try await model.refresh()
            NotificationCenter.default.post(name: .editorialBookmarksChanged, object: nil)
        } catch { failure = error.localizedDescription }
    }
    private func summarize() async {
        guard ModelPermission.allowed() else { summaryError = "فعّل استخدام النماذج من إعدادات الصلاحيات للمتابعة."; return }
        summarizing = true; summaryError = nil
        defer { summarizing = false }
        do { summary = try await model.decoded("news.summarize", ["article_id":article.id,"consent":true], as: ArticleAISummary.self) }
        catch { summaryError = error.localizedDescription }
    }
    private func load(force: Bool = false) async {
        loading = true; failure = nil
        do {
            detail = try await model.decoded("news.article", ["article_id":article.id], as: NewsArticleDetail.self)
            summary = detail?.preparedSummary
            bookmarked = detail?.isBookmarked == true
            NotificationCenter.default.post(name: .editorialArticleRead, object: article.id)
            try? await model.refresh()
        } catch { failure = error.localizedDescription }
        loading = false
        if !Task.isCancelled, detail != nil {
            enriching = true
            defer { enriching = false }
            do {
                let next = try await model.decoded("news.reader", ["article_id":article.id,"refresh":force], as: NewsArticleDetail.self)
                guard !Task.isCancelled else { return }
                detail = next
                NotificationCenter.default.post(name: .editorialArticleContentChanged, object: article.id)
                failure = next.reader?.refreshFailed == true ? "تعذّر تحديث المقال؛ نعرض النسخة المحفوظة." : nil
                if next.bodyStatus != "full", next.bodyStatus != "media_summary", let url = URL(string: article.url) {
                    publicCapture.load(url) { html in
                        Task {
                            if let rendered = try? await model.decoded("news.reader.capture", ["article_id": article.id, "html": html], as: NewsArticleDetail.self) {
                                detail = rendered
                                NotificationCenter.default.post(name: .editorialArticleContentChanged, object: article.id)
                                failure = nil
                            }
                        }
                    }
                }
            } catch { if !Task.isCancelled { failure = error.localizedDescription } }
        }
    }
}
