import SwiftUI
import AppKit

struct CitationSources: View {
    @Environment(\.editorialTheme) private var theme
    let citations: [ConversationCitation]
    @State private var expanded = false
    private var sites: [ConversationCitation] {
        var seen = Set<String>()
        return citations.filter { seen.insert(URL(string: $0.url)?.host ?? $0.url).inserted }
    }
    var body: some View {
        Button { expanded.toggle() } label: {
            HStack(spacing: 10) {
                HStack(spacing: -7) {
                    ForEach(Array(sites.prefix(4))) { site in
                        SiteIcon(address: site.url, size: 26).overlay(RoundedRectangle(cornerRadius: 7).stroke(theme.paper, lineWidth: 2))
                    }
                }.environment(\.layoutDirection, .leftToRight)
                Text(L("المصادر · {0}", citations.count)).font(.callout.weight(.medium))
                Image(systemName: "chevron.down").font(.caption2).foregroundStyle(.secondary)
            }.padding(.horizontal, 12).padding(.vertical, 9)
                .background(Color.primary.opacity(0.05), in: Capsule())
        }.buttonStyle(.plain).accessibilityLabel(L("عرض مصادر الرد"))
            .popover(isPresented: $expanded) {
                VStack(alignment: .leading, spacing: 14) {
                    Text(L("مصادر هذا الرد")).font(.title3.weight(.semibold)).padding(.horizontal, 18).padding(.top, 18)
                    ScrollView {
                        VStack(spacing: 0) {
                            ForEach(Array(citations.enumerated()), id: \.element.id) { index, citation in
                                Button {
                                    expanded = false
                                    if citation.origin == "web", let url = URL(string: citation.url), RichTextLinks.allowed(url) {
                                        NSWorkspace.shared.open(url)
                                    } else {
                                        NotificationCenter.default.post(name: .openEditorialArticle, object: citation.articleId)
                                    }
                                } label: {
                                    HStack(alignment: .top, spacing: 12) {
                                        SiteIcon(address: citation.url, size: 32)
                                        VStack(alignment: .leading, spacing: 5) {
                                            Text(citation.title).font(.callout.weight(.medium)).lineLimit(3)
                                                .environment(\.layoutDirection, RichTextDirection.detect(citation.title))
                                            Text(URL(string: citation.url)?.host ?? "").font(.caption).foregroundStyle(.secondary)
                                                .environment(\.layoutDirection, .leftToRight)
                                        }.frame(maxWidth: .infinity, alignment: .leading)
                                        Text(DisplayFormat.integer(index + 1)).font(.caption).foregroundStyle(.secondary)
                                    }.multilineTextAlignment(.leading).padding(16).contentShape(Rectangle())
                                }.buttonStyle(.plain)
                                Divider().padding(.horizontal, 16)
                            }
                        }
                    }.frame(maxHeight: 420)
                }.frame(width: 410).editorialPresentation()
            }
    }
}
