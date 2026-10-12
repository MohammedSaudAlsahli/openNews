import SwiftUI
import AppKit

struct MenuBarReader: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.openWindow) private var openWindow
    @State private var query = ""
    @State private var unreadOnly = false
    @State private var sourceID = ""
    @State private var selected: NewsArticle?
    @State private var refreshing = false
    @State private var error: String?
    private var feeds: [NewsSubscription] { model.snapshot?.subscriptions ?? [] }
    private var unread: Int { feeds.reduce(0) { $0 + $1.unreadCount } }
    private var syncing: Bool { feeds.contains { $0.status == "syncing" } }
    private var articles: [NewsArticle] {
        (model.snapshot?.articles ?? []).filter {
            (sourceID.isEmpty || $0.subscriptionId == sourceID) && (!unreadOnly || $0.isRead != true) &&
            (query.isEmpty || $0.title.localizedCaseInsensitiveContains(query) || $0.sourceTitle.localizedCaseInsensitiveContains(query))
        }
    }
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
                if syncing || refreshing { ProgressView().controlSize(.small) }
                Button { Task { await refreshFeeds() } } label: { Image(systemName: "arrow.clockwise") }
                    .help(L("تحديث الأخبار")).accessibilityLabel(L("تحديث الأخبار"))
                    .disabled(syncing || refreshing || model.health == nil || feeds.isEmpty)
            }.padding(14)
            Divider()
            if let error { Text(L(error)).font(.caption).foregroundStyle(.red).padding(10) }
            if model.health == nil {
                VStack(spacing: 12) {
                    Text(model.connecting ? L("جارٍ تشغيل المتابعة…") : L("المتابعة متوقفة"))
                    Button(L("إعادة الاتصال")) { Task { await model.start() } }.disabled(model.connecting)
                }.frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let selected { ArticleReader(article: selected, compact: true).id(selected.id) }
            else { articleList }
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
                    .menuStyle(.borderlessButton).frame(width: 24).accessibilityLabel(L("خيارات التطبيق"))
            }.padding(14)
        }
        .frame(width: 420, height: 580)
        .background(Color(nsColor: .windowBackgroundColor))
        .task { if model.health != nil { do { try await model.refresh() } catch { self.error = error.localizedDescription } } }

    }

    private var articleList: some View {
        VStack(spacing: 10) {
            TextField(L("ابحث في أحدث الأخبار"), text: $query).textFieldStyle(.roundedBorder)
            HStack {
                Picker(L("المصدر"), selection: $sourceID) {
                    Text(L("كل المصادر")).tag("")
                    ForEach(feeds) { Text($0.title).tag($0.id) }
                }.labelsHidden().accessibilityLabel(L("تصفية المصدر"))
                Toggle(L("غير المقروء"), isOn: $unreadOnly).toggleStyle(.checkbox).font(.caption)
            }
            if feeds.contains(where: { $0.error != nil }) {
                Text(L("تعذر تحديث بعض المصادر. الأخبار المحفوظة متاحة؛ راجع الاشتراكات في مساحة التحرير."))
                    .font(.caption).foregroundStyle(.secondary)
            }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    if articles.isEmpty {
                        Text(feeds.isEmpty ? L("أضف RSS أو Reddit من مساحة التحرير لتبدأ المتابعة.") : L("لا توجد أخبار مطابقة في أحدث {0} مادة محفوظة.", 100))
                            .foregroundStyle(.secondary).padding(.vertical, 24)
                    }
                    ForEach(articles) { article in
                        Button { selected = article; error = nil } label: {
                            VStack(alignment: .leading, spacing: 6) {
                                Text(article.title).font(.system(size: 13, weight: article.isRead == true ? .regular : .semibold))
                                    .foregroundStyle(.primary).multilineTextAlignment(.leading).lineLimit(3)
                                Text(DisplayFormat.isolated(article.sourceTitle) + " · " + DisplayFormat.isolated(dateLabel(article.publishedAt)))
                                    .font(.caption2).foregroundStyle(.secondary)
                            }.frame(maxWidth: .infinity, alignment: .leading).padding(.vertical, 12).contentShape(Rectangle())
                        }.buttonStyle(.plain)
                        Divider()
                    }
                }
            }
        }.padding(.horizontal, 14).padding(.top, 12)
    }
    private func dateLabel(_ value: String?) -> String {
        guard let value else { return L("بلا تاريخ") }
        return DisplayFormat.date(value)
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
        do { _ = try await model.call("news.sync"); try await model.refresh() }
        catch { self.error = error.localizedDescription }
    }
}
