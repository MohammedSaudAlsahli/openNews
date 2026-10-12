import SwiftUI

struct WorkspaceSidebar: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @ObservedObject var chat: ChatSession
    @Binding var pane: String
    let newConversation: () -> Void
    let openDrafts: () -> Void
    @State private var query = ""
    @State private var showActivity = false
    @State private var discoverSources = false

    private var conversations: [ConversationSummary] {
        chat.conversations.filter { query.isEmpty || $0.title.localizedCaseInsensitiveContains(query) }
    }

    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 9) {
                Image(nsImage: BrandAssets.menuBarIcon).renderingMode(.template)
                Text("OpenStudio").font(.title3.weight(.semibold))
            }.padding(.horizontal, 18).padding(.vertical, 22)
            Button(action: newConversation) {
                HStack {
                    Label(L("محادثة جديدة"), systemImage: "square.and.pencil")
                    Spacer()
                    Text("⌘N").font(.caption).foregroundStyle(.secondary)
                }.padding(10).contentShape(Rectangle())
            }.buttonStyle(.plain)
                .background(chat.conversationID.isEmpty && pane == "conversation" ? Color.accentColor.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 8))
                .disabled(chat.sending || chat.loading).padding(.horizontal, 10)
            Button(action: openDrafts) {
                Label(L("المسودات المحفوظة"), systemImage: "doc.on.doc")
                    .frame(maxWidth: .infinity, alignment: .leading).padding(10).contentShape(Rectangle())
            }.buttonStyle(.plain).padding(.horizontal, 10).padding(.bottom, 4)
            Button { pane = "articles" } label: {
                Label(L("المقالات"), systemImage: "newspaper").frame(maxWidth: .infinity, alignment: .leading).padding(10).contentShape(Rectangle())
            }.buttonStyle(.plain).background(pane == "articles" ? Color.accentColor.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 8)).padding(.horizontal, 10)
            Button { discoverSources = true } label: {
                Label(L("اكتشف المصادر"), systemImage: "safari")
                    .frame(maxWidth: .infinity, alignment: .leading).padding(10).contentShape(Rectangle())
            }.buttonStyle(.plain).padding(.horizontal, 10).padding(.bottom, 16)
                .sheet(isPresented: $discoverSources) { FeedLibraryView() }
            Text(L("المحادثات")).font(.caption.weight(.semibold)).foregroundStyle(.secondary).padding(.horizontal, 20)
            TextField(L("ابحث في المحادثات"), text: $query)
                .textFieldStyle(.roundedBorder).padding(.horizontal, 14).padding(.vertical, 10)
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 3) {
                    ForEach(conversations) { item in
                        Button {
                            pane = "conversation"
                            Task { await chat.select(item.id, model) }
                        } label: {
                            HStack(alignment: .top, spacing: 8) {
                                Image(systemName: "bubble.left").foregroundStyle(.secondary)
                                Text(item.title).lineLimit(2).multilineTextAlignment(.leading)
                                Spacer(minLength: 0)
                                if chat.conversationID == item.id { Image(systemName: "checkmark").font(.caption).foregroundStyle(.secondary) }
                            }.padding(10).frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
                        }.buttonStyle(.plain).help(item.title)
                            .background(chat.conversationID == item.id && pane == "conversation" ? Color.accentColor.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 8))
                            .disabled(chat.sending || chat.loading)
                    }
                    if conversations.isEmpty {
                        Text(L(query.isEmpty ? "تظهر محادثاتك هنا بعد أول رسالة." : "لا توجد محادثات تطابق البحث."))
                            .font(.caption).foregroundStyle(.secondary).padding(10)
                    }
                }.padding(.horizontal, 10)
            }
            Divider().padding(.horizontal, 16)
            VStack(alignment: .leading, spacing: 4) {
                Button { showActivity.toggle() } label: {
                    Label(L("النشاط"), systemImage: "clock").frame(maxWidth: .infinity, alignment: .leading).padding(8).contentShape(Rectangle())
                }.buttonStyle(.plain)
                    .popover(isPresented: $showActivity) {
                        VStack(alignment: .leading, spacing: 12) {
                            Text(L("النشاط")).font(.headline)
                            if model.snapshot?.jobs.isEmpty != false { Text(L("ستظهر هنا عمليات التحليل والتوليد.")).foregroundStyle(.secondary) }
                            ScrollView { VStack(spacing: 12) { ForEach(model.snapshot?.jobs ?? []) { job in ActivityRow(job: job) } } }.frame(maxHeight: 360)
                        }.padding(20).frame(width: 360).editorialPresentation()
                    }
                SettingsLink {
                    Label(L("الإعدادات"), systemImage: "gearshape").frame(maxWidth: .infinity, alignment: .leading).padding(8).contentShape(Rectangle())
                }.buttonStyle(.plain).help(L("الإعدادات (⌘,)"))
            }.padding(10)
        }.frame(width: 220).background(Color(nsColor: .windowBackgroundColor))
    }
}
