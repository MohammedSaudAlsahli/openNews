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
    @State private var pending = Set<String>()
    @State private var error: String?
    @State private var loading = true
    @State private var adding = false
    @State private var followedOnly = false
    @State private var notice: String?
    @State private var removing: NewsSubscription?
    @State private var subscriptionFilter = "all"
    private var subscriptions: [NewsSubscription] { model.snapshot?.subscriptions ?? [] }
    private var categories: [String] { ["all", "news", "technology", "ai", "science", "business", "sports", "podcasts", "gaming", "design", "food", "travel", "security", "movies", "apple", "programming", "music", "world-news", "crypto", "photography", "web-development", "android", "education", "environment", "space"] }
    private var filtered: [LibraryFeed] {
        let candidates: [LibraryFeed] = followedOnly ? (model.snapshot?.subscriptions ?? []).map {
            LibraryFeed(id: $0.id, title: $0.title, url: $0.feedUrl.isEmpty ? $0.url : $0.feedUrl,
                        category: "general", language: "und", descriptionAr: "", descriptionEn: "",
                        publisherUrl: $0.url, verifiedAt: "")
        } : feeds
        let matches = candidates.filter { feed in
            if followedOnly, let existing = subscription(feed) {
                if subscriptionFilter == "active" && !existing.enabled { return false }
                if subscriptionFilter == "paused" && existing.enabled { return false }
                if subscriptionFilter == "error" && existing.error == nil { return false }
            }
            return !followedOnly || query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                (feed.title + " " + feed.url + " " + feed.publisherUrl).localizedCaseInsensitiveContains(query.trimmingCharacters(in: .whitespacesAndNewlines))
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
                Picker(L("عرض المصادر"), selection: $followedOnly) {
                    Text(L("اكتشاف")).tag(false)
                    Text(L("مصادري ({0})", DisplayFormat.integer(subscriptions.count))).tag(true)
                }.pickerStyle(.segmented).labelsHidden().frame(width: 250)
                Menu {
                    Toggle(L("ترتيب أبجدي"), isOn: $sortAlphabetically)
                    if followedOnly {
                        Picker(L("حالة المصدر"), selection: $subscriptionFilter) {
                            Text(L("الكل")).tag("all")
                            Text(L("نشطة")).tag("active")
                            Text(L("متوقفة مؤقتًا")).tag("paused")
                            Text(L("تحتاج انتباهًا")).tag("error")
                        }
                    }
                } label: { Label(L("تصفية النتائج"), systemImage: "line.3.horizontal.decrease") }.fixedSize()
                if sortAlphabetically || subscriptionFilter != "all" {
                    Button(L("مسح الفلاتر")) { subscriptionFilter = "all"; sortAlphabetically = false }.buttonStyle(.borderless)
                }
                Spacer()
                Text(L("{0} مصدر", DisplayFormat.integer(filtered.count))).foregroundStyle(.secondary)
                if !followedOnly {
                    Link("RSS.mobi", destination: URL(string: "https://rss.mobi/")!).font(.caption)
                        .help(L("دليل مجتمعي؛ المتابعة تجلب الأخبار من الناشر مباشرة."))
                }
            }.padding(.horizontal, 24).padding(.bottom, 16)
            if let notice {
                HStack {
                    Label(notice, systemImage: "checkmark.circle").font(.callout)
                    Spacer()
                    Button { self.notice = nil } label: { Image(systemName: "xmark") }
                        .buttonStyle(.plain).accessibilityLabel(L("إخفاء الرسالة"))
                }.padding(.horizontal, 24).padding(.bottom, 12)
            }
            Text(L(followedOnly ? "كل اشتراكاتك، بما فيها الروابط التي أضفتها والمصادر المتوقفة مؤقتًا." : "مصادر RSS.mobi كاملة؛ البحث يشمل الدليل كله، والمتابعة اختيارية."))
                .font(.caption).foregroundStyle(.secondary).padding(.horizontal, 24).padding(.bottom, 12)
            Divider()
            HStack(spacing: 0) {
                if !followedOnly { List(selection: Binding<String?>(get: { category }, set: { category = $0 ?? "all" })) {
                    ForEach(categories, id: \.self) { item in Text(categoryTitle(item)).lineLimit(2).fixedSize(horizontal: false, vertical: true).tag(item) }
                }.listStyle(.sidebar).frame(width: 170)
                Divider() }
                ScrollView {
                    // Load the catalog once; construct visible rows lazily.
                    LazyVStack(alignment: .leading, spacing: 0) {
                        if loading { ProgressView(L("جارٍ فتح المكتبة…")).padding(24) }
                        else if filtered.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                Text(L(followedOnly && subscriptions.isEmpty ? "لم تتابع أي مصدر بعد" : "لا توجد مصادر مطابقة"))
                                    .font(.headline)
                                Text(L(followedOnly && subscriptions.isEmpty ? "اكتشف مصدرًا أو أضف رابطًا لتصلك أخباره هنا." : "غيّر البحث أو امسح الفلاتر لعرض المزيد."))
                                    .foregroundStyle(.secondary)
                                Button(L(followedOnly && subscriptions.isEmpty ? "اكتشاف المصادر" : "مسح الفلاتر")) {
                                    query = ""; subscriptionFilter = "all"; category = "all"
                                    if subscriptions.isEmpty { followedOnly = false }
                                }
                            }.padding(24)
                        }
                        ForEach(filtered) { feed in
                            feedRow(feed)
                            Divider().padding(.horizontal, 20)
                        }
                        if !followedOnly, !nextCursor.isEmpty, !loading {
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
                    if !followedOnly && (error != nil || stale) { Button(L("إعادة المحاولة")) { Task { await load(refresh: true) } } }
                    Button { error = nil } label: { Image(systemName: "xmark") }.buttonStyle(.plain).accessibilityLabel(L("إخفاء الرسالة"))
                }.padding(16)
            }
        }.frame(width: 880, height: 700).editorialPresentation()
        .sheet(isPresented: $adding) { AddNewsSubscriptionSheet() }
        .alert(L("إلغاء متابعة المصدر؟"), isPresented: Binding(get: { removing != nil }, set: { if !$0 { removing = nil } })) {
            Button(L("إلغاء المتابعة"), role: .destructive) {
                if let existing = removing { Task { await manage(existing, action: "remove") } }
            }
            Button(L("رجوع"), role: .cancel) { removing = nil }
        } message: {
            Text(L("ستتوقف الأخبار الجديدة من {0}. تبقى المقالات السابقة والمحفوظة، ويمكنك متابعة المصدر مجددًا.", removing?.title ?? ""))
        }
        .task(id: query + "|" + category + "|" + String(followedOnly)) {
            // Cancellation plus request identity prevents older responses replacing newer searches.
            requestID = UUID()
            if followedOnly { loading = false; error = nil; stale = false; return }
            guard query.count <= 100 else { loading = false; return }
            loading = true
            do { try await Task.sleep(for: .milliseconds(350)) } catch { return }
            submittedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
            await load()
        }
    }
    private func categoryTitle(_ value: String) -> String {
        switch value {
        case "security": return L("أمن سيبراني")
        case "movies": return L("أفلام")
        case "apple": return L("Apple")
        case "programming": return L("برمجة")
        case "music": return L("موسيقى")
        case "world-news": return L("أخبار العالم")
        case "crypto": return L("عملات رقمية")
        case "photography": return L("تصوير")
        case "web-development": return L("تطوير الويب")
        case "android": return L("Android")
        case "education": return L("تعليم")
        case "environment": return L("بيئة")
        case "space": return L("فضاء")
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
        model.snapshot?.subscriptions?.first { $0.id == feed.id || $0.url == feed.url || $0.feedUrl == feed.url }
    }
    private func feedRow(_ feed: LibraryFeed) -> some View {
        HStack(alignment: .top, spacing: 16) {
            SiteIcon(address: feed.publisherUrl.isEmpty ? feed.url : feed.publisherUrl, size: 38)
            VStack(alignment: .leading, spacing: 7) {
                Text(verbatim: feed.title).font(.headline)
                if !feed.descriptionEn.isEmpty { Text(verbatim: language == "en" ? feed.descriptionEn : feed.descriptionAr).font(.callout).foregroundStyle(.secondary) }
                HStack(spacing: 10) {
                    if feed.language != "und" { Text(feed.language == "ar" ? L("العربية") : feed.language == "en" ? L("الإنجليزية") : feed.language == "und" ? L("لغة غير محددة") : feed.language) }
                    if let url = URL(string: feed.url) { Link(subscription(feed)?.kind == "webpage" ? L("صفحة مقالات") : "RSS", destination: url) }
                    if !feed.publisherUrl.isEmpty, feed.publisherUrl != feed.url, let url = URL(string: feed.publisherUrl) { Link(L("موقع الناشر"), destination: url) }
                }.font(.caption)
                if let existing = subscription(feed) {
                    if !followedOnly || !existing.enabled || existing.error != nil || ["queued", "syncing", "fetching", "running"].contains(existing.status) {
                    Label(L(!existing.enabled ? "المتابعة متوقفة مؤقتًا" : existing.error != nil ? "تعذّر آخر تحديث" : ["queued", "syncing", "fetching", "running"].contains(existing.status) ? "جارٍ جلب الأخبار…" : "تتابع هذا المصدر"), systemImage: existing.error != nil ? "exclamationmark.circle" : "dot.radiowaves.left.and.right")
                        .font(.caption).foregroundStyle(.secondary)
                    }
                    if followedOnly {
                        HStack {
                            Text(L("{0} غير مقروء", DisplayFormat.integer(existing.unreadCount)))
                            if let date = existing.lastSuccess {
                                Text(L("آخر جلب ناجح: {0}", DisplayFormat.date(date)))
                            }
                        }.font(.caption).foregroundStyle(.secondary)
                        if let failure = existing.error, !failure.isEmpty {
                            Text(L(failure)).font(.caption).foregroundStyle(.secondary).lineLimit(3)
                        }
                    }
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
            if pending.contains(subscription(feed)?.id ?? feed.id) {
                ProgressView().controlSize(.small).frame(width: 110)
            } else if let existing = subscription(feed) {
                VStack(alignment: .trailing, spacing: 10) {
                    Menu {
                        Button(L(existing.enabled ? "إيقاف مؤقت" : "استئناف المتابعة")) {
                            Task { await manage(existing, action: existing.enabled ? "pause" : "resume") }
                        }
                        Button(L("تحديث الآن")) { Task { await manage(existing, action: "sync") } }
                            .disabled(!existing.enabled || ["queued", "syncing", "running"].contains(existing.status))
                        Divider()
                        Button(L("إلغاء المتابعة"), role: .destructive) { removing = existing }
                    } label: {
                        Label(L(existing.enabled ? "تتابعه" : "متوقفة مؤقتًا"), systemImage: existing.enabled ? "checkmark" : "pause")
                    }.fixedSize().accessibilityLabel(L("إدارة {0}", feed.title))
                    if followedOnly {
                        Button(L("إلغاء المتابعة")) { removing = existing }
                            .buttonStyle(.borderless).font(.caption)
                    }
                }
            } else {
                Button(L("متابعة")) { Task { await add(feed) } }
                    .buttonStyle(.bordered).frame(minWidth: 80).disabled(model.health == nil)
            }
        }.padding(20)
    }
    private func manage(_ existing: NewsSubscription, action: String) async {
        guard !pending.contains(existing.id) else { return }
        pending.insert(existing.id); error = nil; notice = nil
        defer { pending.remove(existing.id) }
        do {
            switch action {
            case "remove":
                _ = try await model.call("news.unsubscribe", ["subscription_id": existing.id])
                notice = L("أُلغيت متابعة {0}. احتفظنا بمقالاته السابقة.", existing.title)
            case "pause", "resume":
                _ = try await model.call("news.update", ["subscription_id": existing.id, "enabled": action == "resume"])
                notice = L(action == "resume" ? "استؤنفت متابعة {0}." : "أُوقفت متابعة {0} مؤقتًا.", existing.title)
                if action == "resume" { _ = try await model.call("news.sync", ["subscription_id": existing.id]) }
            default:
                _ = try await model.call("news.sync", ["subscription_id": existing.id])
                notice = L("بدأ تحديث {0} في الخلفية.", existing.title)
            }
            try await model.refresh()
        } catch { self.error = error.localizedDescription }
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
        } catch { if !Task.isCancelled, requestID == token { self.error = error.localizedDescription } }
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
            notice = L("بدأت متابعة {0}. ستظهر أخباره في الأخبار.", feed.title)
        } catch { self.error = error.localizedDescription }
    }
}
