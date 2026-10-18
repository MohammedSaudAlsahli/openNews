import SwiftUI

extension Notification.Name {
    static let openEditorialArticle = Self("eis.openArticle")
    static let editorialArticleRead = Self("eis.articleRead")
    static let editorialArticleContentChanged = Self("eis.articleContentChanged")
    static let editorialBookmarksChanged = Self("eis.bookmarksChanged")
}

struct ArticlesWorkspace: View {
    @Environment(\.editorialTheme) private var theme
    @EnvironmentObject private var model: StudioModel
    @Binding var selectedArticleIDs: Set<String>
    var onDiscuss: (() -> Void)? = nil
    @State private var query = ""
    @State private var sourceID = ""
    @State private var scope = "all"
    @State private var days = 0
    @State private var order = "newest"
    @State private var summaryStates: [String: String] = [:]
    @State private var articles: [NewsArticle] = []
    @State private var selected: NewsArticle?
    @State private var loading = false
    @State private var more = false
    @State private var request = UUID()
    @State private var error: String?
    @State private var discover = false
    private var filters: String { "\(query)|\(sourceID)|\(scope)|\(days)|\(order)" }
    private var summaryRefreshKey: String {
        let digest = model.digestStatus
        let articleKeys: [String] = articles.map { article in
            "\(article.id):\(article.bodyStatus)"
        }
        let parts: [String] = [articleKeys.joined(separator: "|"), String(digest?.prepared ?? 0),
                               digest?.currentId ?? "", digest?.localModel ?? "",
                               digest?.engine ?? "", digest?.language ?? ""]
        return parts.joined(separator: "|")
    }
    var body: some View {
        ZStack {
            library.accessibilityElement(children: .contain).opacity(selected == nil ? 1 : 0).allowsHitTesting(selected == nil).disabled(selected != nil).accessibilityHidden(selected != nil)
            if let article = selected {
                ArticleReader(article: article, useInConversation: Binding(get: { selectedArticleIDs.contains(article.id) }, set: { value in
                    if value && selectedArticleIDs.count < 12 { selectedArticleIDs.insert(article.id) }
                    else { selectedArticleIDs.remove(article.id) }
                }), onClose: { selected = nil }, onDiscuss: {
                    selectedArticleIDs = [article.id]
                    onDiscuss?()
                }).id(article.id)
            }
        }.background(theme.page)
            .task(id: summaryRefreshKey) {
                let ids = articles.map(\.id)
                for start in stride(from: 0, to: ids.count, by: 100) {
                    guard !Task.isCancelled else { return }
                    if let result = try? await model.decoded("news.summary.states", ["ids": Array(ids[start..<min(start+100,ids.count)])], as: ArticleSummaryStates.self) {
                        guard !Task.isCancelled else { return }
                        summaryStates.merge(result.states) { _, new in new }
                    }
                }
            }
            .sheet(isPresented: $discover) { FeedLibraryView() }
            .task(id: filters + (model.health?.workspaceId ?? "") + (model.snapshot?.subscriptions ?? []).map { $0.id + ($0.lastSuccess ?? "") }.joined()) {
                request = UUID()
                guard model.health != nil else { return }
                do { try await Task.sleep(for: .milliseconds(250)) } catch { return }
                await load()
            }
            .onReceive(NotificationCenter.default.publisher(for: .openEditorialArticle)) { notification in
                guard let id = notification.object as? String else { return }
                Task {
                    do { selected = try await model.decoded("news.preview", ["article_id": id], as: NewsArticle.self) }
                    catch { self.error = error.localizedDescription }
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .editorialArticleRead)) { notification in
                if let id = notification.object as? String, let index = articles.firstIndex(where: { $0.id == id }) { articles[index].isRead = true }
            }
            .onReceive(NotificationCenter.default.publisher(for: .editorialArticleContentChanged)) { notification in
                guard let id = notification.object as? String else { return }
                Task { await refreshArticleContent(id) }
            }
            .onReceive(NotificationCenter.default.publisher(for: .editorialBookmarksChanged)) { notification in
                guard let id = (notification.object as? String) ?? selected?.id else { return }
                Task {
                    if let updated = try? await model.decoded("news.preview", ["article_id": id], as: NewsArticle.self),
                       let index = articles.firstIndex(where: { $0.id == updated.id }) {
                        articles[index] = updated
                        if scope == "saved" && updated.isBookmarked != true { articles.remove(at: index) }
                    }
                }
            }
    }
    private func refreshArticleContent(_ id: String) async {
        if let updated = try? await model.decoded("news.preview", ["article_id": id], as: NewsArticle.self),
           let index = articles.firstIndex(where: { $0.id == id }) {
            articles[index] = updated
        }
        if let result = try? await model.decoded("news.summary.states", ["ids": [id]], as: ArticleSummaryStates.self) {
            summaryStates.merge(result.states) { _, new in new }
        }
    }
    private var library: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 6) {
                    Text(L("المقالات")).font(.largeTitle.weight(.semibold))
                    Text(L("مساحة للقراءة والاحتفاظ بما يهمك.")).foregroundStyle(.secondary)
                }
                Spacer()
                Button { discover = true } label: { Label(L("اكتشف المصادر"), systemImage: "plus") }.buttonStyle(.borderedProminent)
            }.padding(28)
            HStack(spacing: 16) {
                Picker(L("المقالات"), selection: $scope) {
                    Text(L("الكل")).tag("all")
                    Text(L("غير المقروء" )).tag("unread")
                    Text(L("المحفوظات")).tag("saved")
                }.pickerStyle(.segmented).labelsHidden().frame(width: 300)
                Spacer()
                Picker(L("المصدر"), selection: $sourceID) {
                    Text(L("كل المصادر")).tag("")
                    ForEach(model.snapshot?.subscriptions ?? []) { Text($0.title).tag($0.id) }
                }.frame(maxWidth: 260)
                if loading { ProgressView().controlSize(.small) }
            }.padding(.horizontal, 28).padding(.bottom, 16)
            HStack(spacing: 12) {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                TextField(L("ابحث في العناوين ونصوص المقالات"), text: $query).textFieldStyle(.plain)
                if !query.isEmpty { Button { query = "" } label: { Image(systemName: "xmark.circle.fill") }.buttonStyle(.plain).help(L("مسح البحث")) }
                Menu {
                    Picker(L("التاريخ"), selection: $days) {
                        Text(L("كل الأوقات")).tag(0)
                        Text(L("آخر يوم")).tag(1)
                        Text(L("آخر أسبوع")).tag(7)
                        Text(L("آخر شهر")).tag(30)
                    }
                    Picker(L("الترتيب"), selection: $order) {
                        Text(L("الأحدث أولًا")).tag("newest")
                        Text(L("الأقدم أولًا")).tag("oldest")
                    }
                    Divider()
                    Button(L("مسح الفلاتر")) { sourceID = ""; days = 0; order = "newest" }
                } label: { Label(L("تصفية"), systemImage: "line.3.horizontal.decrease") }.fixedSize()
            }.padding(12).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 10))
                .padding(.horizontal, 28).padding(.bottom, 16)
            if !sourceID.isEmpty || days != 0 {
                HStack { Text((model.snapshot?.subscriptions?.first { $0.id == sourceID }?.title ?? L("كل المصادر")) + " · " + (days == 0 ? L("كل الأوقات") : L("آخر {0} أيام", days))).font(.caption).foregroundStyle(.secondary); Spacer() }.padding(.horizontal, 28).padding(.bottom, 12)
            }
            if let error { Text(L(error)).foregroundStyle(.red).font(.callout).padding(12) }
            ScrollView {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 290, maximum: 480), spacing: 22, alignment: .top)], alignment: .center, spacing: 24) {
                    ForEach(articles) { article in
                        ArticleCard(summaryState: summaryStates[article.id] ?? "pending", article: article) { selected = article }.id(article.id)
                            .task {
                                if article.id == articles.last?.id && more && !loading && error == nil {
                                    await load(append: true)
                                }
                            }
                    }
                }.padding(28)
                if articles.isEmpty && !loading {
                    ContentUnavailableView(L(scope == "saved" ? "لم تحفظ مقالات بعد" : "لا توجد مقالات مطابقة"), systemImage: scope == "saved" ? "bookmark" : "newspaper", description: Text(L("جرّب تغيير البحث أو اكتشف مصادر جديدة."))).padding(40)
                }
                if more {
                    Button(L("تحميل المزيد")) { Task { await load(append: true) } }
                        .disabled(loading).padding(24)
                }
            }
        }
    }
    private func load(append: Bool = false) async {
        guard !append || (!loading && more) else { return }
        let token = UUID(); request = token; loading = true; error = nil
        defer { if request == token { loading = false } }
        do {
            let page = try await model.decoded("news.list", ["query":query,"source_id":sourceID,"scope":scope,"days":days,"order":order,"offset":append ? articles.count : 0,"limit":24], as: NewsArticlePage.self)
            guard !Task.isCancelled, request == token else { return }
            if append { let known = Set(articles.map(\.id)); articles += page.articles.filter { !known.contains($0.id) } }
            else { articles = page.articles }
            more = page.hasMore
        } catch { if !Task.isCancelled, request == token { self.error = error.localizedDescription } }
    }
}
