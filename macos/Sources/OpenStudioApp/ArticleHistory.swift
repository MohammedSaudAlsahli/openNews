import SwiftUI

private struct ArticleRevision: Decodable, Identifiable {
    let id: Int
    let capturedAt: String
    enum CodingKeys: String, CodingKey { case id; case capturedAt = "captured_at" }
}
private struct RevisionList: Decodable { let revisions: [ArticleRevision] }
private struct RevisionComparison: Decodable {
    let diff: String
    let previousID: Int?
    enum CodingKeys: String, CodingKey { case diff; case previousID = "previous_id" }
}

struct ArticleHistory: View {
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    let articleID: String
    let articleTitle: String
    @State private var revisions: [ArticleRevision] = []
    @State private var selected: Int?
    @State private var difference = ""
    @State private var initialRevision = false
    @State private var failure: String?
    @State private var loading = true
    @State private var comparing = false
    @State private var retry = 0

    var body: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                Text(L("سجل تعديلات المقالة")).font(.title2.weight(.semibold))
                Text(articleTitle).font(.body).foregroundStyle(.secondary).lineLimit(2)
                    .environment(\.layoutDirection, RichTextDirection.detect(articleTitle))
                    .frame(maxWidth: .infinity, alignment: .leading)
                if !revisions.isEmpty {
                    HStack(spacing: 16) {
                        Picker(L("النسخة المحفوظة"), selection: $selected) {
                            ForEach(revisions) { revision in
                                Text(DisplayFormat.date(revision.capturedAt)).tag(Optional(revision.id))
                            }
                        }.fixedSize().disabled(loading)
                        Spacer(minLength: 0)
                        if !comparing && !initialRevision {
                            Label { Text(L("نص مضاف")).foregroundStyle(.secondary) } icon: { Image(systemName: "plus").foregroundStyle(.green) }
                            Label { Text(L("نص محذوف")).foregroundStyle(.secondary) } icon: { Image(systemName: "minus").foregroundStyle(.red) }
                        }
                    }.font(.callout).padding(.top, 12)
                }
            }.padding(24)
            Divider()
            Group {
                if loading || comparing {
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let failure {
                    ContentUnavailableView {
                        Label(L("تعذّر تحميل سجل التعديلات"), systemImage: "exclamationmark.triangle")
                    } description: { Text(failure) } actions: {
                        Button(L("إعادة المحاولة")) { retry += 1 }
                    }
                } else if revisions.isEmpty {
                    ContentUnavailableView(L("لا توجد نسخ محفوظة بعد"), systemImage: "clock")
                } else {
                    ScrollView {
                        ArticleRevisionDiff(difference: difference, initialRevision: initialRevision)
                            .frame(maxWidth: 720).padding(24).frame(maxWidth: .infinity)
                    }.id(selected)
                }
            }.background(.background)
            Divider()
            HStack(spacing: 24) {
                Text(L("كل إصدار يُقارن بالإصدار السابق. يبدأ السجل من أول نسخة حفظها التطبيق."))
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 0)
                Button(L("إغلاق")) { dismiss() }.keyboardShortcut(.cancelAction)
            }.padding(.horizontal, 24).padding(.vertical, 16)
        }
        .frame(width: 820, height: 620)
        .environment(\.layoutDirection, AppLanguage.current.isRightToLeft ? .rightToLeft : .leftToRight)
        .task(id: retry) { await loadHistory() }
        .task(id: selected) { await loadComparison() }
    }

    private func loadHistory() async {
        loading = true
        failure = nil
        defer { loading = false }
        do {
            let data = try await model.call("news.history", ["article_id": articleID])
            guard !Task.isCancelled else { return }
            revisions = try JSONDecoder().decode(RevisionList.self, from: data).revisions
            if selected == nil { selected = revisions.first?.id }
            else { await loadComparison() }
        } catch { if !Task.isCancelled { failure = error.localizedDescription } }
    }

    private func loadComparison() async {
        guard let selected else { return }
        comparing = true
        failure = nil
        defer { if !Task.isCancelled { comparing = false } }
        do {
            let data = try await model.call("news.revision", ["article_id": articleID, "revision_id": selected])
            let result = try JSONDecoder().decode(RevisionComparison.self, from: data)
            guard !Task.isCancelled else { return }
            initialRevision = result.previousID == nil
            difference = result.diff
        } catch { if !Task.isCancelled { failure = error.localizedDescription } }
    }
}
