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
    @Published var composerRevision = UUID()
    private var unsentMessages: [String: String] = [:]
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
        // Start on an explicit new conversation; history remains one click away.
    }
    func refreshList(_ model: StudioModel) async {
        do { conversations = try await model.decoded("chat.list", as: ConversationList.self).conversations }
        catch { self.error = error.localizedDescription }
    }
    func select(_ id: String, _ model: StudioModel) async {
        guard !sending && !loading else { return }
        unsentMessages[conversationID] = composer
        loading = true; error = nil
        defer { loading = false }
        do {
            let loaded = try await model.decoded("chat.detail", ["conversation_id": id], as: ConversationDetail.self)
            composer = unsentMessages[id] ?? ""
            conversationID = id; detail = loaded; jobID = loaded.activeJobId; sending = jobID != nil
            if let last = loaded.lastJob, ["failed", "interrupted", "cancelled"].contains(last.state) {
                error = Self.failureMessage(last.errorCode)
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
        guard !sending && !loading else { return }
        unsentMessages[conversationID] = composer
        conversationID = ""; detail = nil; error = nil; agentID = ""; jobID = nil
        composer = ""; format = "discussion"; includeDraft = false; seconds = 60
        composerRevision = UUID()
        if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
            profileID = assignment.profileId; modelID = assignment.modelId
        }
    }
    func send(_ model: StudioModel, articleIDs: Set<String>, draftText: String, draftTitle: String) async {
        guard !sending, !loading, modelReady, ModelPermission.allowed(), composer.count <= 12000, (!includeDraft || draftText.count <= 60000), !composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
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
            jobID = submitted.jobId; composer = ""; unsentMessages[conversationID] = nil
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
        if job.state != "completed" { error = Self.failureMessage(job.errorCode) }
    }
    static func failureMessage(_ code: String?) -> String {
        switch code {
        case "MODEL_RESPONSE_INVALID": return L("وصل رد بتنسيق غير صالح. أعد المحاولة؛ لا يعني هذا تسجيل خروجك.")
        case "MODEL_UNSUPPORTED": return L("هذا النموذج غير متاح لهذا الاتصال. اختر نموذجًا آخر.")
        case "AUTH_REQUIRED", "AUTH_EXPIRED", "MODEL_AUTH_FAILED": return L("يحتاج الاتصال إلى تسجيل الدخول مجددًا. افتح إعدادات المزوّد.")
        case "PERMISSION_DENIED": return L("فعّل استخدام النماذج من إعدادات الصلاحيات للمتابعة.")
        default: return L("لم يكتمل الرد. يمكنك إعادة المحاولة أو مراجعة الاتصال من الإعدادات.")
        }
    }
    func retry(_ model: StudioModel) async {
        guard !sending, ModelPermission.allowed(), let last = detail?.lastJob,
              ["failed", "interrupted", "cancelled"].contains(last.state) else { return }
        sending = true; error = nil
        do {
            _ = try await model.call("jobs.resume", ["job_id": last.id, "consent": true])
            jobID = last.id
            try await model.refresh()
        } catch { sending = false; self.error = error.localizedDescription }
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
    @AppStorage(ModelPermission.key) private var modelPermission = false
    @State private var modelOptions = false
    @State private var contextOptions = false
    @FocusState private var composerFocused: Bool
    private var canSend: Bool {
        !session.composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && session.composer.count <= 12000 &&
        (session.includeDraft ? draftText.count <= 60000 : true) && session.modelReady && modelPermission && !session.sending && model.health != nil
    }
    private var writerAssignmentRevision: String {
        guard let item = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) else { return "" }
        return item.profileId + "|" + item.modelId
    }
    private var jobRevision: [String] {
        let jobs: [Job] = model.snapshot?.jobs ?? []
        return jobs.map { $0.id + $0.state }
    }

    var body: some View {
        let _ = interfaceLanguage
        configuredConversation
                        .onChange(of: writerAssignmentRevision) { _, _ in
                if session.agentID.isEmpty, !session.sending,
                   let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    session.profileID = assignment.profileId; session.modelID = assignment.modelId
                }
            }
    }

    private var configuredConversation: some View {
        conversationLayout
            .task(id: model.snapshot?.workspaceId) { await session.start(model) }
            .task(id: session.profileID + "|" + session.modelID) { await validateModelSelection() }
            .onChange(of: agentRevision) { _, _ in updateAgentConfiguration() }
            .onChange(of: jobRevision) { _, _ in Task { await session.update(model) } }
            .onChange(of: session.format) { _, value in
                if value == "youtube_long" { session.seconds = 600 }
                else if value == "tiktok" { session.seconds = 60 }
            }
    }

    private var isWelcome: Bool { session.detail?.messages.isEmpty != false && !session.sending }
    private var conversationLayout: some View {
        VStack(spacing: 0) {
            conversationHeader
            Divider()
            if isWelcome {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(L("بماذا نبدأ؟")).font(.system(size: 30, weight: .semibold))
                            Text(L("ناقش فكرة أو حوّل أخبار مصادرِك إلى محتوى بأسلوبك."))
                                .font(.title3).foregroundStyle(.secondary)
                        }
                        composer
                        startingPrompts
                        if session.error != nil { failureNotice }
                    }.frame(maxWidth: 720, alignment: .leading).padding(32)
                        .padding(.top, 70).frame(maxWidth: .infinity)
                }
            } else {
                messageHistory
                composer.frame(maxWidth: 800).padding(20).frame(maxWidth: .infinity)
            }
        }.background(Color(nsColor: .textBackgroundColor))
    }
    private var conversationHeader: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 4) {
                Text(session.detail?.title ?? L("محادثة جديدة")).font(.headline).lineLimit(1)
                Text(L(session.loading ? "جارٍ تحميل المحادثة…" : session.sending ? "جارٍ إعداد الرد…" : session.error != nil ? "تحتاج المحادثة انتباهك" : session.conversationID.isEmpty ? "لم تبدأ المحادثة بعد" : "محفوظة على جهازك"))
                    .font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            if session.loading || session.sending { ProgressView().controlSize(.small) }
        }.padding(.horizontal, 24).padding(.vertical, 16)
    }
    private var failureNotice: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(session.error ?? "", systemImage: "exclamationmark.circle").foregroundStyle(.red).textSelection(.enabled)
            HStack {
                if let last = session.detail?.lastJob, ["failed", "interrupted", "cancelled"].contains(last.state) {
                    Button(L("إعادة المحاولة")) { Task { await session.retry(model) } }.disabled(!modelPermission || session.sending)
                }
                Button(L("إعدادات الاتصال")) { UserDefaults.standard.set("connections", forKey: "settingsSection"); openSettings() }
                Button(L("إغلاق التنبيه")) { session.error = nil }
            }.font(.caption)
            if let code = session.detail?.lastJob?.errorCode {
                DisclosureGroup(L("تفاصيل المشكلة")) { Text(code).font(.caption.monospaced()).textSelection(.enabled) }
            }
        }.font(.callout).padding(16).frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
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
                    ForEach(session.detail?.messages ?? []) { message in
                        messageView(message).id(message.id)
                    }
                    if session.sending {
                        HStack(spacing: 8) { ProgressView().controlSize(.small); Text(L("جارٍ إعداد الرد…")).font(.callout) }
                            .id("pending")
                    }
                    if session.error != nil { failureNotice }
                }.frame(maxWidth: 760, alignment: .leading).padding(24).frame(maxWidth: .infinity)
            }
            .onChange(of: session.detail?.messages.last?.id) { _, _ in
                if let last = session.detail?.messages.last?.id { proxy.scrollTo(last, anchor: .bottom) }
            }
        }
    }
    private var startingPrompts: some View {
        VStack(alignment: .leading, spacing: 14) {
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
                session.modelReady = false
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
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 10) {
                ZStack(alignment: .topLeading) {
                    if session.composer.isEmpty {
                        Text(L("اكتب طلبك أو ناقش فكرة…")).foregroundStyle(.secondary).padding(5).allowsHitTesting(false)
                    }
                    TextEditor(text: $session.composer).font(.body).scrollContentBackground(.hidden)
                        .focused($composerFocused)
                        .task(id: session.composerRevision) { await Task.yield(); composerFocused = true }
                        .accessibilityLabel(L("رسالة المحادثة"))
                        .frame(height: isWelcome ? 96 : 72)
                }
                HStack(spacing: 12) {
                    Button { contextOptions.toggle() } label: { Image(systemName: "plus.circle") }
                        .buttonStyle(.borderless).help(L("المراجع وخيارات الكتابة"))
                        .accessibilityLabel(L("المراجع وخيارات الكتابة"))
                        .popover(isPresented: $contextOptions) { contextControls.editorialPresentation() }
                    outputPicker
                    modelPickerButton
                    Spacer(minLength: 0)
                    if session.sending, let job = session.jobID {
                        Button(L("إيقاف"), systemImage: "stop.fill") { Task { await model.perform("jobs.cancel", ["job_id": job]) } }
                    } else {
                        Button { Task { await session.send(model, articleIDs: selectedArticleIDs, draftText: draftText, draftTitle: draftTitle) } } label: {
                            Image(systemName: "arrow.up").font(.body.weight(.semibold)).frame(width: 22, height: 22)
                        }.buttonStyle(.borderedProminent).disabled(!canSend)
                            .accessibilityLabel(L("إرسال")).help(L("إرسال (⌘↩)"))
                            .keyboardShortcut(.return, modifiers: .command)
                    }
                }
            }.padding(16).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 16))
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(nsColor: .separatorColor).opacity(0.6)))
            if !modelPermission { ModelPermissionNotice() }
            else if session.profileID.isEmpty || session.modelID.isEmpty {
                HStack { Text(L("اختر نموذجًا لبدء المحادثة.")).foregroundStyle(.secondary); Button(L("الإعدادات")) { openSettings() } }
            }
            if session.useNews || session.includeDraft {
                HStack(spacing: 12) {
                    if session.useNews { Label(selectedArticleIDs.isEmpty ? L("أخبار آخر 7 أيام") : L("الأخبار المحددة ({0})", selectedArticleIDs.count), systemImage: "newspaper") }
                    if session.includeDraft { Label(L("المسودة الحالية"), systemImage: "doc.text") }
                }.font(.caption).foregroundStyle(.secondary)
            }
            if session.composer.count > 12000 { Text(L("اختصر الرسالة إلى {0} حرف.", 12000)).font(.caption).foregroundStyle(.red) }
        }.disabled(session.loading)
    }
    private var contextControls: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(L("المراجع وخيارات الكتابة")).font(.headline)
            Toggle(selectedArticleIDs.isEmpty ? L("استخدم أخبار آخر {0} أيام من اشتراكاتي", 7) : L("استخدم الأخبار المحددة ({0})", selectedArticleIDs.count), isOn: $session.useNews)
            if !draftText.isEmpty { Toggle(L("إرفاق المسودة الحالية للنقاش أو إعادة الصياغة"), isOn: $session.includeDraft) }
            agentPicker
            if ["youtube_long", "tiktok"].contains(session.format) {
                Stepper(L("المدة: {0} ثانية", session.seconds), value: $session.seconds, in: 10...7200, step: 10)
            }
            Button(L("إضافة مصادر للأخبار…")) { contextOptions = false; showNews() }
        }.padding(22).frame(width: 380)
    }
}
