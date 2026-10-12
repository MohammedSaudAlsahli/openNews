import SwiftUI

@MainActor final class ChatSession: ObservableObject {
    @Published var conversations: [ConversationSummary] = []
    @Published var conversationID = ""
    @Published var detail: ConversationDetail?
    @Published var composer = ""
    @Published var profileID = ""
    @Published var modelID = ""
    @Published var modelReady = false
    @Published var agentID = ""
    @Published var consent = false
    @Published var format = "discussion"
    @Published var seconds = 60
    @Published var useNews = true
    @Published var includeDraft = false
    @Published var loading = false
    @Published var loadingOlder = false
    @Published var sending = false
    @Published var error: String?
    @Published var jobID: String?
    private var initialized = false

    func start(_ model: StudioModel) async {
        guard model.health != nil, model.snapshot != nil, !initialized else { return }
        initialized = true
        if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
            profileID = assignment.profileId; modelID = assignment.modelId
        } else if let profiles = model.snapshot?.profiles, profiles.count == 1 { profileID = profiles[0].id }
        await refreshList(model)
        if let first = conversations.first { await select(first.id, model) }
    }
    func refreshList(_ model: StudioModel) async {
        do { conversations = try await model.decoded("chat.list", as: ConversationList.self).conversations }
        catch { self.error = error.localizedDescription }
    }
    func select(_ id: String, _ model: StudioModel) async {
        guard !sending else { return }
        loading = true; error = nil; consent = false
        defer { loading = false }
        do {
            let loaded = try await model.decoded("chat.detail", ["conversation_id": id], as: ConversationDetail.self)
            conversationID = id; detail = loaded; jobID = loaded.activeJobId; sending = jobID != nil
            if let last = loaded.lastJob, ["failed", "interrupted", "cancelled"].contains(last.state) {
                error = L("لم يكتمل آخر رد. يمكنك مراجعة النشاط أو إرسال رسالة جديدة.")
            }
        } catch { self.error = error.localizedDescription }
    }
    func loadOlder(_ model: StudioModel) async {
        guard !loadingOlder, let current = detail, current.hasMore == true,
              let before = current.nextBeforeMessageId ?? current.messages.first?.id else { return }
        let requested = current.id
        loadingOlder = true
        defer { loadingOlder = false }
        do {
            let older = try await model.decoded("chat.detail", ["conversation_id": requested, "before_message_id": before], as: ConversationDetail.self)
            guard conversationID == requested, let current = detail else { return }
            let existing = Set(current.messages.map(\.id))
            detail = ConversationDetail(id: current.id, title: current.title,
                messages: older.messages.filter { !existing.contains($0.id) } + current.messages,
                activeJobId: current.activeJobId, lastJob: current.lastJob,
                hasMore: older.hasMore, nextBeforeMessageId: older.nextBeforeMessageId)
        } catch { self.error = error.localizedDescription }
    }
    func newConversation(_ model: StudioModel) {
        guard !sending else { return }
        conversationID = ""; detail = nil; error = nil; consent = false; agentID = ""
        if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
            profileID = assignment.profileId; modelID = assignment.modelId
        }
    }
    func send(_ model: StudioModel, articleIDs: Set<String>, draftText: String, draftTitle: String) async {
        guard !sending, modelReady, consent, !composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        sending = true; error = nil
        let message = composer
        do {
            if conversationID.isEmpty {
                let created = try await model.decoded("chat.create", ["title": String(message.prefix(80))], as: CreatedConversation.self)
                conversationID = created.conversationId
            }
            var payload: [String: Any] = ["conversation_id": conversationID, "message": message, "profile_id": profileID, "model_id": modelID, "consent": true, "idempotency_key": UUID().uuidString, "article_ids": useNews ? Array(articleIDs) : [], "format": format, "days": 7, "include_news": useNews]
            if !agentID.isEmpty { payload["agent_id"] = agentID }
            if includeDraft && !draftText.isEmpty { payload["draft_text"] = draftText; payload["draft_title"] = draftTitle }
            if ["youtube_long", "tiktok"].contains(format) { payload["target_seconds"] = seconds }
            let submitted = try await model.decoded("chat.send", payload, as: SubmittedJob.self)
            jobID = submitted.jobId; composer = ""
            try await model.refresh()
            detail = try await model.decoded("chat.detail", ["conversation_id": conversationID], as: ConversationDetail.self)
            await refreshList(model)
        } catch { self.error = error.localizedDescription; sending = jobID != nil }
    }
    func update(_ model: StudioModel) async {
        guard let id = jobID, let job = model.snapshot?.jobs.first(where: { $0.id == id }), !job.active else { return }
        jobID = nil; sending = false
        if !conversationID.isEmpty {
            do { detail = try await model.decoded("chat.detail", ["conversation_id": conversationID], as: ConversationDetail.self) }
            catch { self.error = error.localizedDescription }
        }
        await refreshList(model)
        if job.state != "completed" { error = L("تعذّر إكمال الرد. راجع النشاط أو حاول برسالة جديدة.") }
    }
}

struct ConversationPanel: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.openSettings) private var openSettings
    @ObservedObject var session: ChatSession
    @Binding var selectedArticleIDs: Set<String>
    let draftText: String
    let draftTitle: String
    let openDraft: (String) -> Void
    let showNews: () -> Void
    @State private var modelOptions = false
    private var canSend: Bool {
        !session.composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && session.composer.count <= 12000 &&
        (session.includeDraft ? draftText.count <= 60000 : true) && session.modelReady && session.consent && !session.sending && model.health != nil
    }
    private var jobRevision: [String] {
        let jobs: [Job] = model.snapshot?.jobs ?? []
        return jobs.map { $0.id + $0.state }
    }

    var body: some View {
        let _ = interfaceLanguage
        configuredConversation
            .onChange(of: session.seconds) { _, _ in session.consent = false }
            .onChange(of: model.snapshot?.dnaVersion.id) { _, _ in session.consent = false }
            .onChange(of: model.snapshot?.assignments?.first(where: { $0.role == "writer" })?.modelId) { _, _ in
                if session.profileID.isEmpty, let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    session.profileID = assignment.profileId; session.modelID = assignment.modelId
                }
            }
            .onChange(of: session.useNews) { _, _ in session.consent = false }
            .onChange(of: session.includeDraft) { _, _ in session.consent = false }
            .onChange(of: draftText) { _, _ in if session.includeDraft { session.consent = false } }
            .onChange(of: selectedArticleIDs) { _, _ in session.consent = false }
    }

    private var configuredConversation: some View {
        conversationLayout
            .task(id: model.snapshot?.workspaceId) { await session.start(model) }
            .task(id: session.profileID + "|" + session.modelID) { await validateModelSelection() }
            .onChange(of: agentRevision) { _, _ in updateAgentConfiguration() }
            .onChange(of: jobRevision) { _, _ in Task { await session.update(model) } }
            .onChange(of: session.profileID) { _, _ in session.consent = false }
            .onChange(of: session.modelID) { _, _ in session.consent = false }
            .onChange(of: session.format) { _, value in
                session.consent = false
                if value == "youtube_long" { session.seconds = 600 }
                else if value == "tiktok" { session.seconds = 60 }
            }
    }

    private var conversationLayout: some View {
        VStack(spacing: 0) {
            conversationHeader
            Divider()
            messageHistory
            Divider()
            composer.frame(maxWidth: 800).frame(maxWidth: .infinity)
        }.background(Color(nsColor: .controlBackgroundColor))
    }

    private var conversationHeader: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(L("المحادثة")).font(.headline)
                Text(session.detail?.title ?? L("فكّر بصوتٍ عالٍ، ثم اكتب")).font(.caption).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer()
            Menu {
                Button(L("محادثة جديدة"), systemImage: "plus") { session.newConversation(model) }
                Button(L("تحديث المحادثات"), systemImage: "arrow.clockwise") {
                    Task { await session.refreshList(model); if !session.conversationID.isEmpty { await session.select(session.conversationID, model) } }
                }
                Divider()
                ForEach(session.conversations) { conversation in
                    Button(conversation.title) { Task { await session.select(conversation.id, model) } }
                }
            } label: { Image(systemName: "clock.arrow.circlepath") }
                .menuStyle(.borderlessButton).frame(width: 24).disabled(session.sending)
                .help(L("المحادثات السابقة ومحادثة جديدة"))
        }.padding(18)
    }

    private var messageHistory: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 22) {
                    if session.detail?.hasMore == true {
                        HStack {
                            Button(L("تحميل رسائل أقدم")) { Task { await session.loadOlder(model) } }.disabled(session.loadingOlder)
                            if session.loadingOlder { ProgressView().controlSize(.small) }
                        }.font(.caption)
                    }
                    if session.detail?.messages.isEmpty != false { startingPrompts }
                    ForEach(session.detail?.messages ?? []) { message in
                        messageView(message).id(message.id)
                    }
                    if session.sending {
                        HStack(spacing: 8) { ProgressView().controlSize(.small); Text(L("جارٍ إعداد الرد…")).font(.callout) }
                            .id("pending")
                    }
                    if let error = session.error {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(L(error)).font(.callout).foregroundStyle(.red).textSelection(.enabled)
                            Button(L("إغلاق التنبيه")) { session.error = nil }.font(.caption)
                        }
                    }
                }.frame(maxWidth: 760, alignment: .leading).padding(24).frame(maxWidth: .infinity)
            }
            .onChange(of: session.detail?.messages.last?.id) { _, _ in
                if let last = session.detail?.messages.last?.id { proxy.scrollTo(last, anchor: .bottom) }
            }
        }
    }
    private var startingPrompts: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(L("من خبرٍ إلى فكرة تستحق الكتابة")).font(.title3.weight(.semibold))
            Text(L("ناقش زاوية، راجع أخبار الأسبوع، أو اطلب مسودات قابلة للتحرير. الأخبار لا تغيّر أسلوبك؛ أنت تعتمد قواعده من كتاباتك."))
                .font(.callout).foregroundStyle(.secondary).lineSpacing(4)
            Button(L("ناقش معي أخبار هذا الأسبوع")) { session.composer = L("لخّص أهم أخبار هذا الأسبوع من اشتراكاتي، ثم اقترح ثلاث زوايا تستحق النقاش."); session.format = "discussion" }
                .buttonStyle(.link)
            Button(L("حوّل فكرة إلى منشورات X")) { session.composer = L("ساعدني على اختيار زاوية واضحة، ثم اكتب عدة منشورات X مستقلة بأسلوبي."); session.format = "x_posts" }
                .buttonStyle(.link)
            Button(L("إضافة مصادر للأخبار…"), action: showNews).buttonStyle(.link)
        }.padding(.vertical, 8)
    }
    private func messageView(_ message: ConversationMessage) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(message.role == "user" ? L("أنت") : L("المساعد التحريري"), systemImage: message.role == "user" ? "person.crop.circle" : "sparkles")
                .font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            RichTextView(text: message.content, fontSize: 14, lineSpacing: 5)
            if let outputs = message.outputs, !outputs.isEmpty {
                ForEach(outputs) { output in
                    Button { openDraft(output.draftId) } label: {
                        Label(L("فتح المسودة: ") + output.title, systemImage: "doc.text")
                            .multilineTextAlignment(.leading)
                    }.buttonStyle(.bordered).disabled(model.busy)
                }
            }
            if let citations = message.citations, !citations.isEmpty {
                DisclosureGroup(L("المراجع ({0})", citations.count)) {
                    ForEach(citations) { citation in
                        if let url = URL(string: citation.url), ["https", "http"].contains(url.scheme?.lowercased() ?? "") {
                            Link(citation.title, destination: url).font(.caption)
                        }
                    }
                    Text(L("روابط مرجعية؛ لا تمثّل تحققًا مستقلًا من الوقائع.")).font(.caption).foregroundStyle(.secondary)
                }.font(.caption)
            }
        }.frame(maxWidth: .infinity, alignment: .leading)
    }
    private func validateModelSelection() async {
        let profile = session.profileID, selected = session.modelID
        session.modelReady = false
        guard !profile.isEmpty, !selected.isEmpty else { return }
        do {
            let result = try await model.decoded("providers.models", ["profile_id": profile, "refresh": false], as: ProviderModels.self)
            guard !Task.isCancelled, session.profileID == profile, session.modelID == selected else { return }
            session.modelReady = result.models.contains { $0.id == selected && $0.available }
        } catch {
            guard !Task.isCancelled, session.profileID == profile else { return }
            session.error = error.localizedDescription
        }
    }
    private var agentRevision: [String] { model.customAgents.map { $0.id + $0.updatedAt } }
    private func updateAgentConfiguration() {
        guard !session.agentID.isEmpty else { return }
        session.consent = false
        if let agent = model.customAgents.first(where: { $0.id == session.agentID }) {
            session.profileID = agent.profileId; session.modelID = agent.modelId
        } else { session.agentID = ""; session.modelReady = false }
    }
    private var agentPicker: some View {
            Picker(L("الوكيل"), selection: $session.agentID) {
                Text(L("الكاتب الافتراضي")).tag("")
                ForEach(model.customAgents) { Text($0.name).tag($0.id) }
            }.labelsHidden().accessibilityLabel(L("الوكيل")).fixedSize().disabled(session.sending)
            .onChange(of: session.agentID) { _, selected in
                session.consent = false; session.modelReady = false
                if let agent = model.customAgents.first(where: { $0.id == selected }) {
                    session.profileID = agent.profileId; session.modelID = agent.modelId
                } else if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    session.profileID = assignment.profileId; session.modelID = assignment.modelId
                }
            }
    }
    private var outputPicker: some View {
            HStack {
                Picker(L("المخرج"), selection: $session.format) {
                    Text(L("نقاش")).tag("discussion")
                    Text(L("منشورات X")).tag("x_posts")
                    Text(L("YouTube طويل")).tag("youtube_long")
                    Text("TikTok").tag("tiktok")
                }.labelsHidden().accessibilityLabel(L("نوع نتيجة المحادثة")).fixedSize()
            }
    }
    private var modelPickerButton: some View {
            Button { modelOptions.toggle() } label: {
                HStack(spacing: 7) {
                    Image(systemName: "cpu")
                    Text(session.modelID.isEmpty ? L("اختر نموذجًا") : DisplayFormat.isolated(session.modelID)).lineLimit(1)
                    Image(systemName: "chevron.down").font(.caption2)
                }
            }.buttonStyle(.borderless)
                .accessibilityLabel(L("اختيار النموذج والاتصال"))
                .popover(isPresented: $modelOptions) {
                    VStack(alignment: .leading, spacing: 16) {
                        Text(L("النموذج والاتصال")).font(.headline)
                        if model.snapshot?.profiles.isEmpty != false {
                            Text(L("اختر نموذجًا لبدء المحادثة."))
                            Button(L("الإعدادات…")) { modelOptions = false; openSettings() }
                        } else {
                            ConnectionModelPicker(profileID: $session.profileID, modelID: $session.modelID, ready: $session.modelReady)
                                .id(session.agentID).disabled(!session.agentID.isEmpty)
                            if !session.agentID.isEmpty { Text(L("لتغيير نموذج هذا الوكيل، افتح إعدادات الوكلاء.")).font(.caption).foregroundStyle(.secondary) }
                        }
                        HStack { Spacer(); Button(L("تم")) { modelOptions = false } }
                    }.padding(24).frame(width: 430).editorialPresentation()
                }
    }
    private var composer: some View {
        VStack(alignment: .leading, spacing: 10) {
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 14) { agentPicker; outputPicker; Spacer(); modelPickerButton }
                VStack(alignment: .leading, spacing: 10) { agentPicker; outputPicker; modelPickerButton }
            }
            if ["youtube_long", "tiktok"].contains(session.format) {
                Stepper(L("المدة: {0} ثانية", session.seconds), value: $session.seconds, in: 10...7200, step: 10).font(.caption)
            }
            Toggle(selectedArticleIDs.isEmpty ? L("استخدم أخبار آخر {0} أيام من اشتراكاتي", 7) : L("استخدم الأخبار المحددة ({0})", selectedArticleIDs.count), isOn: $session.useNews)
                .font(.caption)
            if !draftText.isEmpty {
                Toggle(L("إرفاق المسودة الحالية للنقاش أو إعادة الصياغة"), isOn: $session.includeDraft).font(.caption)
            }
            ZStack(alignment: .topLeading) {
                if session.composer.isEmpty { Text(L("اكتب طلبك أو ناقش فكرة…")).foregroundStyle(.secondary).font(.body).padding(5).allowsHitTesting(false) }
                TextEditor(text: $session.composer).font(.body).scrollContentBackground(.hidden)
                    .accessibilityLabel(L("رسالة المحادثة")).frame(minHeight: 65, maxHeight: 110)
            }.padding(10).background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 10))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(nsColor: .separatorColor)))
            Toggle(L("أسمح باستخدام النموذج لهذا النقاش والأسلوب والمراجع المرفقة؛ قد تُحتسب تكلفة."), isOn: $session.consent)
                .font(.caption).fixedSize(horizontal: false, vertical: true)
            HStack {
                if session.composer.count > 12000 { Text(L("اختصر الرسالة إلى {0} حرف.", 12000)).font(.caption).foregroundStyle(.red) }
                Spacer()
                if session.sending, let job = session.jobID {
                    Button(L("إيقاف")) { Task { await model.perform("jobs.cancel", ["job_id": job]) } }
                } else {
                    Button(L("إرسال")) { Task { await session.send(model, articleIDs: selectedArticleIDs, draftText: draftText, draftTitle: draftTitle) } }
                        .buttonStyle(.borderedProminent).disabled(!canSend)
                }
            }
        }.padding(16).disabled(session.loading)
    }
}
