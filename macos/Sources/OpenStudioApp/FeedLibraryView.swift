import SwiftUI
import AppKit

private struct DirectoryPage: Decodable {
    let feeds: [LibraryFeed]
    let nextCursor, provider, fetchedAt: String
    let cached, stale: Bool
}
private struct LibraryFeed: Decodable, Identifiable {
    let id, title, url, category, language, descriptionAr, descriptionEn, publisherUrl, verifiedAt: String
}

struct FeedLibraryView: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    @AppStorage("appLanguage") private var language = "ar"
    @State private var sortAlphabetically = false
    @State private var submittedQuery = ""
    @State private var nextCursor = ""
    @State private var fetchedAt = ""
    @State private var stale = false
    @State private var requestID = UUID()
    @State private var feeds: [LibraryFeed] = []
    @State private var query = ""
    @State private var category = "all"
    @State private var feedLanguage = "all"
    @State private var pending = Set<String>()
    @State private var error: String?
    @State private var loading = true
    @State private var adding = false
    @State private var followedOnly = false
    @State private var addedTitle: String?
    private var categories: [String] { ["all", "news", "technology", "ai", "science", "business", "sports", "podcasts", "gaming", "design", "food", "travel"] }
    private var filtered: [LibraryFeed] {
        let matches = feeds.filter { feed in
            (!followedOnly || subscription(feed)?.enabled == true) &&
            (feedLanguage == "all" || feed.language.hasPrefix(feedLanguage))
        }
        return sortAlphabetically ? matches.sorted { $0.title.localizedStandardCompare($1.title) == .orderedAscending } : matches
    }
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(L("اكتشف المصادر")).font(.largeTitle.weight(.semibold))
                    Text(L("اختر ما تتابعه. تصلك الأخبار في مساحة العمل وقارئ شريط القوائم.")).foregroundStyle(.secondary)
                }
                Spacer()
                Button { adding = true } label: { Label(L("إضافة رابط"), systemImage: "plus") }.buttonStyle(.borderedProminent)
                Button(L("تم")) { dismiss() }.keyboardShortcut(.cancelAction)
            }.padding(24)
            HStack(spacing: 12) {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                TextField(L("ابحث عن مصدر أو موضوع"), text: $query).textFieldStyle(.plain)
                    .accessibilityLabel(L("ابحث عن مصدر أو موضوع"))
                if !query.isEmpty { Button { query = "" } label: { Image(systemName: "xmark.circle.fill") }.buttonStyle(.plain).help(L("مسح البحث")) }
                if loading { ProgressView().controlSize(.small) }
            }.padding(12).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 10))
                .padding(.horizontal, 24).padding(.bottom, 12)
            HStack(spacing: 16) {
                Menu {
                    Picker(L("لغة النتائج المحمّلة"), selection: $feedLanguage) {
                        Text(L("كل اللغات")).tag("all")
                        Text(L("العربية")).tag("ar")
                        Text(L("الإنجليزية")).tag("en")
                    }
                    Toggle(L("مصادري فقط"), isOn: $followedOnly)
                    Toggle(L("ترتيب أبجدي"), isOn: $sortAlphabetically)
                } label: { Label(L("تصفية النتائج"), systemImage: "line.3.horizontal.decrease") }
                .fixedSize()
                if feedLanguage != "all" || followedOnly || sortAlphabetically {
                    Button(L("مسح الفلاتر")) { feedLanguage = "all"; followedOnly = false; sortAlphabetically = false }.buttonStyle(.borderless)
                }
                Spacer()
                Text(L("{0} مصدر", DisplayFormat.integer(filtered.count))).foregroundStyle(.secondary)
                Link("RSS.mobi", destination: URL(string: "https://rss.mobi/")!).font(.caption)
                    .help(L("دليل مجتمعي؛ المتابعة تجلب الأخبار من الناشر مباشرة."))
            }.padding(.horizontal, 24).padding(.bottom, 16)
            if let addedTitle {
                Label(L("بدأت متابعة {0}. ستظهر أخباره في الأخبار.", addedTitle), systemImage: "checkmark.circle.fill")
                    .font(.callout).foregroundStyle(.green).padding(.horizontal, 24).padding(.bottom, 12)
            }
            Divider()
            HStack(spacing: 0) {
                List(selection: Binding<String?>(get: { category }, set: { category = $0 ?? "all" })) {
                    ForEach(categories, id: \.self) { item in Text(categoryTitle(item)).lineLimit(2).fixedSize(horizontal: false, vertical: true).tag(item) }
                }.listStyle(.sidebar).frame(width: 170)
                Divider()
                ScrollView {
                    // A bounded page uses eager rows: macOS accessibility scroll-to-end
                    // can trap while resolving SwiftUI lazy collection identifiers.
                    VStack(alignment: .leading, spacing: 0) {
                        if loading { ProgressView(L("جارٍ فتح المكتبة…")).padding(24) }
                        else if filtered.isEmpty {
                            Text(L("لا توجد مصادر مطابقة. جرّب تصنيفًا آخر أو غيّر البحث.")).foregroundStyle(.secondary).padding(24)
                        }
                        ForEach(filtered) { feed in
                            feedRow(feed)
                            Divider().padding(.horizontal, 20)
                        }
                        if !nextCursor.isEmpty, !loading {
                            Button(L("تحميل المزيد")) { Task { await load(append: true) } }
                                .frame(maxWidth: .infinity).padding(20)
                        }
                    }
                }.frame(maxWidth: .infinity)
            }
            if stale || error != nil || query.count > 100 {
                HStack {
                    Text(L(query.count > 100 ? "البحث بحد أقصى 100 حرف." : error ?? "تعذّر الاتصال. نعرض نتائج محفوظة؛ أعد المحاولة للتحديث.")).font(.caption).foregroundStyle(.secondary)
                    Spacer()
                    if error != nil || stale { Button(L("إعادة المحاولة")) { Task { await load(refresh: true) } } }
                }.padding(16)
            }
        }.frame(width: 880, height: 700).editorialPresentation()
        .sheet(isPresented: $adding) { AddNewsSubscriptionSheet() }
        .task(id: query + "|" + category) {
            // Cancellation plus request identity prevents older responses replacing newer searches.
            requestID = UUID()
            guard query.count <= 100 else { loading = false; return }
            loading = true
            do { try await Task.sleep(for: .milliseconds(350)) } catch { return }
            submittedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
            await load()
        }
    }
    private func categoryTitle(_ value: String) -> String {
        switch value {
        case "general": return L("عامة")
        case "news": return L("أخبار")
        case "technology": return L("تقنية")
        case "ai": return L("ذكاء اصطناعي")
        case "science": return L("علوم")
        case "business": return L("أعمال واقتصاد")
        case "sports": return L("رياضة")
        case "podcasts": return L("بودكاست")
        case "gaming": return L("ألعاب")
        case "design": return L("تصميم")
        case "food": return L("طعام")
        case "travel": return L("سفر")
        case "all": return L("كل المصادر")
        default: return value
        }
    }
    private func subscription(_ feed: LibraryFeed) -> NewsSubscription? {
        model.snapshot?.subscriptions?.first { $0.url == feed.url || $0.feedUrl == feed.url }
    }
    private func feedRow(_ feed: LibraryFeed) -> some View {
        HStack(alignment: .top, spacing: 16) {
            SiteIcon(address: feed.publisherUrl.isEmpty ? feed.url : feed.publisherUrl, size: 38)
            VStack(alignment: .leading, spacing: 7) {
                Text(verbatim: feed.title).font(.headline)
                Text(verbatim: language == "en" ? feed.descriptionEn : feed.descriptionAr).font(.callout).foregroundStyle(.secondary)
                HStack(spacing: 10) {
                    Text(feed.language == "ar" ? L("العربية") : feed.language == "en" ? L("الإنجليزية") : feed.language == "und" ? L("لغة غير محددة") : feed.language)
                    if let url = URL(string: feed.url) { Link("RSS", destination: url) }
                    if !feed.publisherUrl.isEmpty, let url = URL(string: feed.publisherUrl) { Link(L("موقع الناشر"), destination: url) }
                }.font(.caption)
                if let existing = subscription(feed) {
                    Label(L(!existing.enabled ? "المتابعة متوقفة مؤقتًا" : existing.error != nil ? "تعذّر آخر تحديث؛ أعد المحاولة من الأخبار" : ["queued", "syncing", "fetching", "running"].contains(existing.status) ? "جارٍ جلب الأخبار…" : "تتابع هذا المصدر"), systemImage: existing.error != nil ? "exclamationmark.circle" : "dot.radiowaves.left.and.right")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
            if pending.contains(feed.id) { ProgressView().controlSize(.small).frame(width: 80) }
            else if subscription(feed)?.enabled == true {
                Label(L("تتابعه"), systemImage: "checkmark.circle.fill").font(.callout).foregroundStyle(.secondary).frame(width: 80)
            } else {
                Button(subscription(feed) == nil ? L("متابعة") : L("استئناف")) { Task { await add(feed) } }
                    .buttonStyle(.bordered).frame(minWidth: 80).disabled(model.health == nil)
            }
        }.padding(20)
    }
    private func load(append: Bool = false, refresh: Bool = false) async {
        let token = UUID(); requestID = token
        let requestedCursor = append ? nextCursor : ""
        loading = true; error = nil
        if !append { nextCursor = "" }
        defer { if requestID == token { loading = false } }
        do {
            let page = try await model.decoded("news.directory", ["query": submittedQuery, "category": category, "cursor": requestedCursor, "refresh": refresh], as: DirectoryPage.self)
            guard !Task.isCancelled, requestID == token else { return }
            if !append { feeds = [] }
            let ids = Set(feeds.map(\.id))
            feeds += page.feeds.filter { !ids.contains($0.id) }
            nextCursor = page.nextCursor; fetchedAt = page.fetchedAt; stale = page.stale
        } catch { if !Task.isCancelled, requestID == token { feeds = []; self.error = error.localizedDescription } }
    }
    private func add(_ feed: LibraryFeed) async {
        guard !pending.contains(feed.id) else { return }
        pending.insert(feed.id); error = nil
        defer { pending.remove(feed.id) }
        do {
            if let existing = subscription(feed) {
                _ = try await model.call("news.update", ["subscription_id": existing.id, "enabled": true])
                _ = try await model.call("news.sync", ["subscription_id": existing.id])
            } else {
                _ = try await model.call("news.subscribe", ["url": feed.url, "title": feed.title, "kind": "rss"])
            }
            try await model.refresh()
            addedTitle = feed.title
        } catch { self.error = error.localizedDescription }
    }
}
