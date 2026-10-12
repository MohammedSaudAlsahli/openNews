import SwiftUI
import AppKit

private struct LibraryLocation: Decodable { let path: String }
private struct FeedLibrary: Decodable { let version: Int; let feeds: [LibraryFeed]; let path: String }
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
    @State private var catalog = "online"
    @State private var submittedQuery = ""
    @State private var nextCursor = ""
    @State private var fetchedAt = ""
    @State private var stale = false
    @State private var requestID = UUID()
    @State private var feeds: [LibraryFeed] = []
    @State private var query = ""
    @State private var libraryPath = ""
    @State private var category = "all"
    @State private var feedLanguage = "all"
    @State private var pending = Set<String>()
    @State private var error: String?
    @State private var loading = true
    @State private var adding = false
    @State private var followedOnly = false
    @State private var fileOptions = false
    @State private var addedTitle: String?
    private var categories: [String] {
        let standard = ["general", "news", "technology", "ai", "science", "business", "sports", "podcasts"]
        if catalog == "online" { return ["all", "news", "technology", "ai", "science", "business", "sports", "podcasts", "gaming", "design", "food", "travel"] }
        let used = Set(feeds.map(\.category))
        return ["all"] + standard.filter { used.contains($0) } + used.subtracting(standard).sorted()
    }
    private var filtered: [LibraryFeed] {
        feeds.filter { feed in
            (!followedOnly || subscription(feed)?.enabled == true) && (catalog == "online" || category == "all" || feed.category == category) && (catalog == "online" || feedLanguage == "all" || feed.language == feedLanguage) &&
            (catalog == "online" || query.isEmpty || [feed.title, feed.url, feed.descriptionAr, feed.descriptionEn].contains { $0.localizedCaseInsensitiveContains(query) })
        }
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
            Picker(L("دليل المصادر"), selection: $catalog) {
                Text(L("دليل الإنترنت · RSS.mobi")).tag("online")
                Text(L("دليلي المحلي · YAML")).tag("local")
            }.pickerStyle(.segmented).labelsHidden().padding(.horizontal, 24).padding(.bottom, 16)
            HStack {
                TextField(L("ابحث عن مصدر أو موضوع"), text: $query).textFieldStyle(.roundedBorder)
                    .onSubmit { search() }
                if catalog == "online" {
                    Button(L("بحث")) { search() }.disabled(query.count > 100)
                } else {
                Picker(L("لغة المصادر"), selection: $feedLanguage) {
                    Text(L("كل اللغات")).tag("all")
                    Text(L("العربية")).tag("ar")
                    Text(L("الإنجليزية")).tag("en")
                }.frame(width: 220)
                }
            }.padding(.horizontal, 24).padding(.bottom, 16)
            if catalog == "online", query.count > 100 {
                Text(L("البحث بحد أقصى 100 حرف.")).font(.caption).foregroundStyle(.red).padding(.horizontal, 24).padding(.bottom, 8)
            }
            HStack(spacing: 12) {
                Toggle(L("مصادري فقط"), isOn: $followedOnly).toggleStyle(.switch).controlSize(.small)
                Spacer()
                Text(L(catalog == "online" ? "{0} مصدر محمّل" : "{0} مصدر", DisplayFormat.integer(filtered.count))).foregroundStyle(.secondary)
            }.font(.callout).padding(.horizontal, 24).padding(.bottom, 16)
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
                        if catalog == "online", !nextCursor.isEmpty, !loading {
                            Button(L("تحميل المزيد")) { Task { await load(append: true) } }
                                .frame(maxWidth: .infinity).padding(20)
                        }
                    }
                }.frame(maxWidth: .infinity)
            }
            Divider()
            VStack(alignment: .leading, spacing: 8) {
                if catalog == "online" {
                    HStack {
                        Link("RSS.mobi", destination: URL(string: "https://rss.mobi/")!)
                        Text(L("دليل مجتمعي؛ المتابعة تجلب الأخبار من الناشر مباشرة.")).foregroundStyle(.secondary)
                        Spacer()
                        Button(L("تحديث")) { Task { await load(refresh: true) } }.disabled(loading)
                    }
                    if stale {
                        Label(L("تعذّر الاتصال. نعرض نتائج محفوظة؛ أعد المحاولة للتحديث."), systemImage: "wifi.slash").foregroundStyle(.orange)
                    }
                    if !fetchedAt.isEmpty {
                        Text(L("آخر تحديث: {0}", DisplayFormat.date(fetchedAt))).foregroundStyle(.secondary)
                    }
                    Text(L("يُرسل نص البحث إلى RSS.mobi عند الضغط على بحث. أوصاف المصادر بلغتها الأصلية.")).foregroundStyle(.secondary)
                } else {
                DisclosureGroup(L("إدارة دليل المصادر"), isExpanded: $fileOptions) {
                    HStack {
                        Button { openLibraryFile() } label: { Label(L("تعديل ملف المصادر"), systemImage: "doc.text") }.disabled(libraryPath.isEmpty)
                        Button { Task { await load() } } label: { Label(L("إعادة تحميل"), systemImage: "arrow.clockwise") }.disabled(loading)
                        Spacer()
                        Text("sources.yml").environment(\.layoutDirection, .leftToRight).foregroundStyle(.secondary).help(libraryPath)
                    }.padding(.vertical, 8)
                }
                }
                if let error { Text(L(error)).foregroundStyle(.red) }
                Text(L("المتابعة تحدّث الأخبار كل ساعة أثناء تشغيل التطبيق. لم تجد مصدرك؟ استخدم إضافة رابط."))
                    .foregroundStyle(.secondary)
            }.font(.caption).padding(16)
        }.frame(width: 880, height: 700).editorialPresentation()
        .sheet(isPresented: $adding) { AddNewsSubscriptionSheet() }
        .task(id: "\(catalog)|\(category)|\(submittedQuery)") { await load() }
        .onChange(of: catalog) { _, _ in
            query = ""; submittedQuery = ""; category = "all"; feedLanguage = "all"
            followedOnly = false; addedTitle = nil
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
            Text(String(feed.title.prefix(1))).font(.title2.weight(.semibold))
                .frame(width: 46, height: 46)
                .background(Color.accentColor.opacity(0.10), in: RoundedRectangle(cornerRadius: 12))
                .accessibilityHidden(true)
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
    private func search() {
        guard query.count <= 100 else { return }
        let value = query.trimmingCharacters(in: .whitespacesAndNewlines)
        if value == submittedQuery { Task { await load() } }
        else { submittedQuery = value }
    }
    private func load(append: Bool = false, refresh: Bool = false) async {
        let token = UUID()
        requestID = token
        let requestedCatalog = catalog
        let requestedCursor = append ? nextCursor : ""
        loading = true
        if !append { feeds = []; nextCursor = ""; fetchedAt = ""; stale = false }
        defer { if requestID == token { loading = false } }
        error = nil
        do {
            if requestedCatalog == "online" {
                let page = try await model.decoded("news.directory", ["query": submittedQuery, "category": category, "cursor": requestedCursor, "refresh": refresh], as: DirectoryPage.self)
                guard !Task.isCancelled, requestID == token else { return }
                let ids = Set(feeds.map(\.id))
                feeds += page.feeds.filter { !ids.contains($0.id) }
                nextCursor = page.nextCursor; fetchedAt = page.fetchedAt; stale = page.stale
            } else {
                libraryPath = try await model.decoded("news.library.path", as: LibraryLocation.self).path
                let library = try await model.decoded("news.library", as: FeedLibrary.self)
                guard !Task.isCancelled, requestID == token else { return }
                feeds = library.feeds; libraryPath = library.path
                if !categories.contains(category) { category = "all" }
            }
        }
        catch { if !Task.isCancelled, requestID == token { self.error = error.localizedDescription } }
    }
    private func openLibraryFile() {
        let url = URL(fileURLWithPath: libraryPath)
        if !NSWorkspace.shared.open(url) { NSWorkspace.shared.activateFileViewerSelecting([url]) }
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
