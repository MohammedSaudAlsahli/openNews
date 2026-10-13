import SwiftUI
import AppKit

struct MenuBarReader: View {
    @Environment(\.editorialTheme) private var theme
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.openWindow) private var openWindow
    @State private var query = ""
    @State private var scope = "all"
    @State private var articles: [NewsArticle] = []
    @State private var loading = false
    @State private var more = false
    @State private var request = UUID()
    @State private var sourceID = ""
    @State private var selected: NewsArticle?
    @State private var refreshing = false
    @State private var error: String?
    private var feeds: [NewsSubscription] { model.snapshot?.subscriptions ?? [] }
    private var unread: Int { feeds.reduce(0) { $0 + $1.unreadCount } }
    private var syncing: Bool { feeds.contains { $0.status == "syncing" } }
    var body: some View {
        let _ = interfaceLanguage
        VStack(spacing: 0) {
            HStack {
                if selected != nil {
                    Button { selected = nil; error = nil } label: { Label(L("الأخبار"), systemImage: "chevron.backward") }
                        .buttonStyle(.borderless)
                } else {
                    Text(L("آخر الأخبار")).font(.headline)
                    Text(L("{0} غير مقروء", unread)).font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                if selected == nil {
                if syncing || refreshing { ProgressView().controlSize(.small) }
                Button { Task { await refreshFeeds() } } label: { Image(systemName: "arrow.clockwise") }
                    .help(L("تحديث الأخبار")).accessibilityLabel(L("تحديث الأخبار"))
                    .disabled(syncing || refreshing || model.health == nil || feeds.isEmpty)
                }
            }.padding(14)
            Divider()
            if let error { Text(L(error)).font(.caption).foregroundStyle(.red).padding(10) }
            if model.health == nil {
                VStack(spacing: 12) {
                    Text(model.connecting ? L("جارٍ تشغيل المتابعة…") : L("المتابعة متوقفة"))
                    Button(L("إعادة الاتصال")) { Task { await model.start() } }.disabled(model.connecting)
                }.frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ZStack {
                    articleList.accessibilityElement(children: .contain).opacity(selected == nil ? 1 : 0).allowsHitTesting(selected == nil).disabled(selected != nil).accessibilityHidden(selected != nil)
                    if let selected { ArticleReader(article: selected, compact: true).id(selected.id) }
                }
            }
            Divider()
            HStack {
                Button(L("فتح مساحة التحرير"), action: showStudio)
                Spacer()
                Menu {
                    Text(L("إغلاق النافذة يبقي المتابعة فعّالة."))
                    Text(L("إنهاء التطبيق يوقف المتابعة."))
                    Divider()
                    Button(L("إنهاء التطبيق")) { NSApp.terminate(nil) }
                } label: { Image(systemName: "ellipsis.circle") }
                    .menuStyle(.borderlessButton).menuIndicator(.hidden).frame(width: 32, height: 28).accessibilityLabel(L("خيارات التطبيق"))
            }.padding(14)
        }
        .frame(width: 470, height: 700)
        .background(theme.page)
        .task(id: query + sourceID + scope + (model.health?.workspaceId ?? "")) {
            request = UUID()
            do { try await Task.sleep(for: .milliseconds(250)) } catch { return }
            await load()
        }
        .onReceive(NotificationCenter.default.publisher(for: .editorialArticleRead)) { notification in
            if let id = notification.object as? String, let index = articles.firstIndex(where: { $0.id == id }) { articles[index].isRead = true }
        }
        .onReceive(NotificationCenter.default.publisher(for: .editorialBookmarksChanged)) { notification in
            guard let id = (notification.object as? String) ?? selected?.id else { return }
            Task {
                if let updated = try? await model.decoded("news.preview", ["article_id": id], as: NewsArticle.self), let index = articles.firstIndex(where: { $0.id == updated.id }) {
                    articles[index] = updated
                    if scope == "saved" && updated.isBookmarked != true { articles.remove(at: index) }
                }
            }
        }

    }

    private var articleList: some View {
        VStack(spacing: 10) {
            TextField(L("ابحث في أحدث الأخبار"), text: $query).textFieldStyle(.roundedBorder)
            HStack {
                Picker(L("المصدر"), selection: $sourceID) {
                    Text(L("كل المصادر")).tag("")
                    ForEach(feeds) { Text($0.title).tag($0.id) }
                }.labelsHidden().accessibilityLabel(L("تصفية المصدر"))
                Picker(L("تصفية"), selection: $scope) {
                    Text(L("الكل")).tag("all")
                    Text(L("غير المقروء")).tag("unread")
                    Text(L("المحفوظات")).tag("saved")
                }.labelsHidden().frame(width: 135)
            }
            if feeds.contains(where: { $0.error != nil }) {
                Text(L("تعذر تحديث بعض المصادر. الأخبار المحفوظة متاحة؛ راجع الاشتراكات في مساحة التحرير."))
                    .font(.caption).foregroundStyle(.secondary)
            }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    if articles.isEmpty {
                        Text(feeds.isEmpty ? L("أضف RSS أو Reddit من مساحة التحرير لتبدأ المتابعة.") : L("لا توجد مقالات مطابقة"))
                            .foregroundStyle(.secondary).padding(.vertical, 24)
                    }
                    ForEach(articles) { article in
                        ArticleCard(article: article, compact: true) { selected = article; error = nil }.padding(.bottom, 14)
                    }
                    if more { Button(L("تحميل المزيد")) { Task { await load(append: true) } }.disabled(loading).padding(16) }
                    if loading { ProgressView().padding(16) }
                }
            }
        }.padding(.horizontal, 14).padding(.top, 12)
    }
    private func load(append: Bool = false) async {
        guard model.health != nil else { return }
        let token = UUID(); request = token; loading = true
        defer { if request == token { loading = false } }
        do {
            let page = try await model.decoded("news.list", ["query":query,"source_id":sourceID,"scope":scope,"offset":append ? articles.count : 0], as: NewsArticlePage.self)
            guard !Task.isCancelled, request == token else { return }
            if append { let known = Set(articles.map(\.id)); articles += page.articles.filter { !known.contains($0.id) } }
            else { articles = page.articles }
            more = page.hasMore
        } catch { if !Task.isCancelled, request == token { self.error = error.localizedDescription } }
    }
    private func showStudio() {
        if let window = NSApp.windows.first(where: { $0.identifier?.rawValue == "editorial-studio" }) {
            window.makeKeyAndOrderFront(nil)
        } else { openWindow(id: "studio") }
        NSApp.activate(ignoringOtherApps: true)
    }
    private func refreshFeeds() async {
        refreshing = true; error = nil
        defer { refreshing = false }
        do { _ = try await model.call("news.sync"); try await model.refresh(); await load() }
        catch { self.error = error.localizedDescription }
    }
}
