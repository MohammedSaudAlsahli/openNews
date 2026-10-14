import SwiftUI

struct NewsPanel: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Binding var selectedArticleIDs: Set<String>
    @State private var adding = false
    @State private var subscriptions = false
    @State private var query = ""
    @State private var syncing = false
    @State private var error: String?
    private var feeds: [NewsSubscription] { model.snapshot?.subscriptions ?? [] }
    private var articles: [NewsArticle] { (model.snapshot?.articles ?? []).filter { query.isEmpty || $0.title.localizedCaseInsensitiveContains(query) || $0.sourceTitle.localizedCaseInsensitiveContains(query) } }
    private var feedsBusy: Bool { feeds.contains { ["queued", "syncing", "fetching", "running"].contains($0.status) } }
    var body: some View {
        let _ = interfaceLanguage
        VStack(spacing: 0) {
            HStack {
                Text(L("مراجع المحادثة")).font(.headline)
                Spacer()
                Button { subscriptions.toggle() } label: { Image(systemName: "list.bullet.rectangle") }.help(L("إدارة الاشتراكات")).accessibilityLabel(L("إدارة الاشتراكات"))
                Button { adding = true } label: { Image(systemName: "plus") }.help(L("إضافة RSS أو Reddit")).accessibilityLabel(L("إضافة RSS أو Reddit"))
            }.padding(16)
            Text(L("اختر مقالات لإرفاقها، أو اطلب البحث في أي فترة من المحادثة."))
                .font(.caption).foregroundStyle(.secondary).padding(.horizontal, 16).padding(.bottom, 12)
            if let error {
                Text(L(error)).font(.caption).foregroundStyle(.red).padding(.horizontal, 16)
            }
            if subscriptions { subscriptionList }
            else { articleList }
            Divider()
            HStack {
                Text(selectedArticleIDs.isEmpty ? L("الفترة حسب طلبك") : L("{0} أخبار محددة", DisplayFormat.integer(selectedArticleIDs.count))).font(.caption).foregroundStyle(.secondary)
                Spacer()
                if !selectedArticleIDs.isEmpty { Button(L("مسح التحديد")) { selectedArticleIDs.removeAll() }.font(.caption) }
                Button { Task { await sync() } } label: {
                    if syncing || feedsBusy { ProgressView().controlSize(.small) }
                    else { Image(systemName: "arrow.clockwise") }
                }.disabled(syncing || feedsBusy || feeds.isEmpty).help(L("تحديث الأخبار")).accessibilityLabel(L("تحديث الأخبار"))
            }.padding(14)
        }
        .sheet(isPresented: $adding) { AddNewsSubscriptionSheet() }

    }
    private var subscriptionList: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Button(L("العودة إلى الأخبار")) { subscriptions = false }.buttonStyle(.link)
                Text(L("الاشتراكات")).font(.title3.weight(.semibold))
                Text(L("تتحدث الاشتراكات كل ساعة أثناء تشغيل التطبيق. أخبار RSS وReddit للمحادثة، ولا تُضاف إلى أمثلة أسلوبك.")).font(.caption).foregroundStyle(.secondary)
                if feeds.isEmpty { Text(L("أضف أول رابط للبدء.")).foregroundStyle(.secondary) }
                ForEach(feeds) { feed in
                    VStack(alignment: .leading, spacing: 7) {
                        Toggle(feed.title, isOn: Binding(get: { feed.enabled }, set: { enabled in
                            Task {
                                do { _ = try await model.call("news.update", ["subscription_id": feed.id, "enabled": enabled]); try await model.refresh() }
                                catch { self.error = error.localizedDescription }
                            }
                        }))
                        Button(L("إلغاء الاشتراك مع الاحتفاظ بالأخبار"), role: .destructive) {
                            Task {
                                do { _ = try await model.call("news.unsubscribe", ["subscription_id": feed.id]); try await model.refresh() }
                                catch { self.error = error.localizedDescription }
                            }
                        }
                        Text(feed.kind == "reddit" ? "Reddit" : "RSS").font(.caption).foregroundStyle(.secondary)
                        if let url = URL(string: feed.url), ["https", "http"].contains(url.scheme?.lowercased() ?? "") { Link(L("فتح المصدر"), destination: url).font(.caption) }
                        if let date = feed.lastSuccess { Text(L("آخر جلب ناجح: {0}", DisplayFormat.date(date))).font(.caption2).foregroundStyle(.secondary) }
                        if let failure = feed.error, !failure.isEmpty { Text(L(failure)).font(.caption).foregroundStyle(.red) }
                        if ["queued", "syncing", "fetching", "running"].contains(feed.status) { ProgressView(L("جارٍ الجلب…")).controlSize(.small) }
                    }
                    Divider()
                }
                Button(L("إضافة اشتراك…")) { adding = true }
            }.padding(16)
        }
    }
    private var articleList: some View {
        VStack(spacing: 0) {
            TextField(L("ابحث في الأخبار"), text: $query).textFieldStyle(.roundedBorder).padding(.horizontal, 16).padding(.bottom, 12)
            if articles.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    Text(feeds.isEmpty ? L("تابع المصادر التي تهمك") : L("لا توجد أخبار لعرضها")).font(.headline)
                    Text(feeds.isEmpty ? L("أضف رابط RSS أو مجتمع Reddit. ستظهر أحدث المواد هنا لمناقشتها وتحويلها إلى محتوى.") : L("حدّث الاشتراكات، أو غيّر عبارة البحث. قد يتعذّر الوصول إلى بعض المصادر.")).font(.callout).foregroundStyle(.secondary)
                    Button(L("إضافة اشتراك…")) { adding = true }
                }.frame(maxWidth: .infinity, alignment: .leading).padding(16)
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        ForEach(articles) { article in
                            HStack(alignment: .top, spacing: 9) {
                                Toggle(L("تحديد {0}", article.title), isOn: selection(article.id)).labelsHidden().toggleStyle(.checkbox)
                                    .disabled(selectedArticleIDs.count >= 12 && !selectedArticleIDs.contains(article.id))
                                Button { NotificationCenter.default.post(name: .openEditorialArticle, object: article.id) } label: {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(article.title).font(.body.weight(.medium)).foregroundStyle(.primary).lineLimit(3)
                                        Text(article.sourceTitle).font(.caption).foregroundStyle(.secondary)
                                        Text(article.publishedAt.map { DisplayFormat.date($0) } ?? L("تاريخ النشر غير متوفر")).font(.caption2).foregroundStyle(.secondary)
                                    }.frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
                                }.buttonStyle(.plain)
                            }.padding(.horizontal, 16).padding(.vertical, 13)
                            Divider().padding(.horizontal, 16)
                        }
                    }
                }
            }
        }
    }
    private func selection(_ id: String) -> Binding<Bool> {
        Binding(get: { selectedArticleIDs.contains(id) }, set: { value in
            if value && selectedArticleIDs.count < 12 { selectedArticleIDs.insert(id) } else { selectedArticleIDs.remove(id) }
        })
    }
    private func sync() async {
        syncing = true; error = nil
        defer { syncing = false }
        do {
            _ = try await model.call("news.sync")
            try await model.refresh()

        } catch { self.error = error.localizedDescription }
    }
}

struct AddNewsSubscriptionSheet: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    @State private var url = ""
    @State private var title = ""
    @State private var kind = "auto"
    @State private var saving = false
    @State private var error: String?
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 18) {
            Text(L("اشتراك أخبار جديد")).font(.title2.weight(.semibold))
            Text(L("أضف رابط RSS أو رابط مجتمع Reddit لجلب مواده. سيُتصل بالمصدر عند الإضافة والتحديث.")).font(.callout).foregroundStyle(.secondary)
            Form {
                LabeledContent(L("الرابط")) {
                    TextField("", text: $url, prompt: Text("https://…"))
                        .labelsHidden()
                        .environment(\.layoutDirection, .leftToRight)
                        .accessibilityLabel(L("الرابط"))
                }
                TextField(L("اسم المصدر"), text: $title, prompt: Text(L("اختياري")))
                LabeledContent(L("نوع المصدر")) {
                    NativeChoicePicker(title: L("نوع المصدر"), selection: $kind, choices: [
                        .init(value: "auto", label: L("تحديد تلقائي")),
                        .init(value: "rss", label: "RSS / Atom"),
                        .init(value: "reddit", label: "Reddit")
                    ])
                }
            }.formStyle(.grouped).frame(height: 190)
            if let error { Text(L(error)).font(.callout).foregroundStyle(.red) }
            HStack {
                Button(L("إلغاء"), role: .cancel) { dismiss() }.keyboardShortcut(.cancelAction)
                Spacer()
                if saving { ProgressView().controlSize(.small) }
                Button(L("إضافة الاشتراك")) { Task { await save() } }.buttonStyle(.borderedProminent)
                    .disabled(url.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || model.health == nil)
            }
        }.padding(24).frame(width: 560).editorialPresentation().disabled(saving).interactiveDismissDisabled(saving)
    }
    private func save() async {
        saving = true; error = nil
        defer { saving = false }
        do {
            _ = try await model.call("news.subscribe", ["url": url, "title": title, "kind": kind])
            try await model.refresh(); model.notice = L("أُضيف الاشتراك إلى الأخبار"); dismiss()
        } catch { self.error = error.localizedDescription }
    }
}
