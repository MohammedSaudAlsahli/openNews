import SwiftUI

struct RelatedNewsResult: Decodable {
    let segments, embedded: Int
    let coverage, state: String
    let articles: [NewsArticle]
}
struct RelatedNews: View {
    @EnvironmentObject private var model: StudioModel
    let articleID: String
    @State private var result: RelatedNewsResult?
    @State private var selected: NewsArticle?
    @State private var failure: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Divider()
            Text(L("أخبار ذات علاقة")).font(.headline)
            if let result {
                Text(L("يعتمد على التشابه في المعنى بين المقالات المفهرسة على جهازك."))
                    .font(.caption).foregroundStyle(.secondary)
                if result.state == "pending" {
                    Label(L("تنتظر هذه المقالة اكتمال الفهرسة بالمعنى"), systemImage: "clock")
                        .font(.callout).foregroundStyle(.secondary)
                } else if result.state == "unavailable" {
                    Text(L("البحث بالمعنى غير متاح حاليًا")).foregroundStyle(.secondary)
                } else if result.articles.isEmpty {
                    Text(L("لم نجد أخبارًا قريبة بما يكفي في الفهرس الحالي.")).foregroundStyle(.secondary)
                }
                ForEach(result.articles) { article in
                    Button { selected = article } label: {
                        HStack(alignment: .top, spacing: 12) {
                            SiteIcon(address: article.url, size: 24)
                            VStack(alignment: .leading, spacing: 5) {
                                Text(article.title).font(.body).lineLimit(3).multilineTextAlignment(.leading)
                                Text(article.sourceTitle + " · " + DisplayFormat.date(article.publishedAt ?? article.discoveredAt))
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer(minLength: 0)
                            Image(systemName: "chevron.forward").font(.caption).foregroundStyle(.secondary)
                        }.padding(.vertical, 8).contentShape(Rectangle())
                    }.buttonStyle(.plain)
                }
                DisclosureGroup(L("ما الذي فُهرس من هذه المقالة؟")) {
                    Text(L(result.coverage == "full" ? "العنوان والنص الكامل المتاح" : result.coverage == "title" ? "العنوان فقط؛ النص غير متاح" : "العنوان والمقتطف المتاح؛ ليس النص الكامل"))
                    Text("\(result.embedded) / \(result.segments) " + L("مقاطع مفهرسة بالمعنى"))
                }.font(.caption).foregroundStyle(.secondary)
            } else if let failure {
                Text(failure).font(.caption).foregroundStyle(.secondary)
                Button(L("حاول مجددًا")) { Task { await load() } }
            } else { ProgressView().controlSize(.small) }
        }
        .task(id: articleID) {
            result = nil
            await load()
            while !Task.isCancelled && result?.state == "pending" {
                do { try await Task.sleep(nanoseconds: 10_000_000_000) } catch { break }
                await load()
            }
        }
        .sheet(item: $selected) { article in
            ArticleReader(article: article, onClose: { selected = nil })
                .frame(minWidth: 720, minHeight: 600).editorialPresentation()
        }
    }
    private func load() async {
        do {
            result = try await model.decoded("news.related", ["article_id":articleID], as: RelatedNewsResult.self)
            failure = nil
        } catch { if !Task.isCancelled { failure = error.localizedDescription } }
    }
}

struct SearchIndexedArticle: Decodable, Identifiable {
    let id, title, bodyStatus: String
    let segments, embedded: Int
}
struct SearchIndexedArticles: Decodable { let articles: [SearchIndexedArticle] }
struct SearchIndexDetails: View {
    @EnvironmentObject private var model: StudioModel
    @State private var articles: [SearchIndexedArticle] = []
    @State private var failure: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(L("أحدث 30 مقالة؛ الفهرسة تعطي الأخبار الجديدة الأولوية.")).font(.caption).foregroundStyle(.secondary)
            ForEach(articles) { article in
                HStack {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(article.title).lineLimit(2)
                        Text(L(article.bodyStatus == "full" ? "العنوان والنص الكامل المتاح" : "العنوان والمقتطف المتاح؛ ليس النص الكامل"))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text("\(article.embedded) / \(article.segments)").monospacedDigit()
                }.padding(.vertical, 4)
            }
            if let failure { Text(failure).foregroundStyle(.secondary) }
        }.task {
            while !Task.isCancelled {
                do {
                    articles = try await model.decoded("news.search.inspect", as: SearchIndexedArticles.self).articles
                    failure = nil
                } catch { failure = error.localizedDescription }
                do { try await Task.sleep(nanoseconds: 5_000_000_000) } catch { break }
            }
        }
    }
}
