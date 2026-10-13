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
    @Published var progress: ConversationProgress?
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
            progress = nil
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
        progress = nil
        conversationID = ""; detail = nil; error = nil; agentID = ""; jobID = nil
        composer = ""; format = "discussion"; includeDraft = false; seconds = 60
        composerRevision = UUID()
        if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
            profileID = assignment.profileId; modelID = assignment.modelId
        }
    }
    func send(_ model: StudioModel, articleIDs: Set<String>, draftText: String, draftTitle: String) async {
        guard !sending, !loading, modelReady, ModelPermission.allowed(), composer.count <= 12000, (!includeDraft || draftText.count <= 60000), !composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        sending = true; error = nil; progress = nil
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
        if !conversationID.isEmpty {
            do { detail = try await model.decoded("chat.detail", ["conversation_id": conversationID], as: ConversationDetail.self) }
            catch { self.error = error.localizedDescription }
        }
        // Keep the streamed answer visible until the persisted message is ready.
        // Clearing progress first makes a completed reply disappear and reappear.
        jobID = nil; sending = false; progress = nil
        await refreshList(model)
        if job.state != "completed" { error = Self.failureMessage(job.errorCode) }
    }
    func monitor(_ model: StudioModel, job: String) async {
        while !Task.isCancelled && jobID == job {
            do {
                let next = try await model.decoded("chat.progress", ["job_id": job], as: ConversationProgress.self)
                guard !Task.isCancelled, jobID == job else { return }
                progress = next
                if !["queued", "running"].contains(next.state) {
                    try await model.refresh(); await update(model); return
                }
                try await Task.sleep(for: .milliseconds(300))
            } catch {
                if Task.isCancelled { return }
                // The normal snapshot monitor still handles completion if a poll fails.
                try? await Task.sleep(for: .seconds(1))
            }
        }
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
        sending = true; error = nil; progress = nil
        do {
            _ = try await model.call("jobs.resume", ["job_id": last.id, "consent": true])
            jobID = last.id
            try await model.refresh()
        } catch { sending = false; self.error = error.localizedDescription }
    }

}
