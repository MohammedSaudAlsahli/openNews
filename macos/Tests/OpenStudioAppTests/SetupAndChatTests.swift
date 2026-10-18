import Foundation
import Testing
@testable import OpenStudioApp

@Test func modelPermissionRequiresOptInAndCanBeRevoked() throws {
    let suite = "OpenStudio.permission-test.\(UUID().uuidString)"
    let defaults = try #require(UserDefaults(suiteName: suite))
    defer { defaults.removePersistentDomain(forName: suite) }
    #expect(!ModelPermission.allowed(in: defaults))
    defaults.set(true, forKey: ModelPermission.key)
    let reopened = try #require(UserDefaults(suiteName: suite))
    #expect(ModelPermission.allowed(in: reopened))
    reopened.set(false, forKey: ModelPermission.key)
    #expect(!ModelPermission.allowed(in: defaults))
}

@MainActor @Test func newConversationResetsContextWithoutDeletingHistory() {
    let chat = ChatSession()
    chat.composer = "Previous unfinished request"
    chat.conversationID = "old-chat"
    chat.includeDraft = true
    chat.format = "youtube_long"
    chat.seconds = 600
    chat.error = "Old failure"
    let revision = chat.composerRevision
    chat.newConversation(StudioModel())
    #expect(chat.conversationID.isEmpty)
    #expect(chat.composer.isEmpty)
    #expect(!chat.includeDraft)
    #expect(chat.format == "auto")
    #expect(chat.seconds == 60)
    #expect(chat.error == nil)
    #expect(chat.composerRevision != revision)
}

@MainActor @Test func newConversationCanLeaveAnActiveReply() {
    let chat = ChatSession()
    chat.conversationID = "active-chat"
    chat.composer = "Keep this"
    chat.sending = true
    chat.jobID = "running-job"
    chat.newConversation(StudioModel())
    #expect(chat.conversationID.isEmpty)
    #expect(chat.jobID == nil)
    #expect(!chat.sending)
    #expect(chat.composer.isEmpty)
}

@MainActor @Test func invalidResponseDoesNotMasqueradeAsLogout() {
    #expect(ChatSession.failureMessage("MODEL_RESPONSE_INVALID") != ChatSession.failureMessage("MODEL_AUTH_FAILED"))
    #expect(ChatSession.failureMessage("MODEL_RESPONSE_INVALID") == L("وصل رد بتنسيق غير صالح. أعد المحاولة؛ لا يعني هذا تسجيل خروجك."))
}


@MainActor @Test func revokedPermissionBlocksModelRequestBeforeTransport() async throws {
    let suite = "OpenStudio.dispatch-test.\(UUID().uuidString)"
    let defaults = try #require(UserDefaults(suiteName: suite))
    defer { defaults.removePersistentDomain(forName: suite) }
    let model = StudioModel(permissionDefaults: defaults)
    defaults.set(true, forKey: ModelPermission.key)
    defaults.set(false, forKey: ModelPermission.key)
    for command in ["chat.send", "drafts.generate", "analysis.run", "providers.validate", "jobs.resume"] {
        do {
            _ = try await model.call(command, ["consent": true])
            Issue.record("Revoked permission must block \(command)")
        } catch {
            #expect(error.localizedDescription == L("فعّل استخدام النماذج من إعدادات الصلاحيات للمتابعة."))
        }
    }
}


@MainActor @Test func switchingRunningConversationsRestoresDraftAndJob() async throws {
    var calls: [String] = []
    let model = StudioModel(requestOverride: { command, payload in
        calls.append(command)
        let id = payload["conversation_id"] as! String
        return try JSONSerialization.data(withJSONObject: ["id":id,"title":id,"messages":[],"active_job_id":id == "first" ? "job-first" : NSNull()])
    })
    let chat = ChatSession()
    chat.conversationID = "first"; chat.jobID = "job-first"; chat.sending = true
    chat.composer = "First draft"
    await chat.select("second", model)
    #expect(chat.conversationID == "second" && !chat.sending && chat.jobID == nil)
    chat.composer = "Second draft"
    await chat.select("first", model)
    #expect(chat.composer == "First draft" && chat.jobID == "job-first" && chat.sending)
    await chat.select("second", model)
    #expect(chat.composer == "Second draft")
    #expect(calls == ["chat.detail", "chat.detail", "chat.detail"])
}

@MainActor @Test func lateCompletionCannotReplaceNewConversation() async throws {
    var completion: CheckedContinuation<Data, Error>?
    let model = StudioModel(requestOverride: { command, payload in
        if command == "chat.detail", payload["conversation_id"] as? String == "first" {
            return try await withCheckedThrowingContinuation { completion = $0 }
        }
        return try JSONSerialization.data(withJSONObject: ["id":"second","title":"second","messages":[]])
    })
    model.snapshot = try JSONDecoder.engine.decode(Snapshot.self, from: Data(#"{"workspace_id":"w","sources":[],"techniques":[],"drafts":[],"rules":[],"profiles":[],"dna_version":{"id":"d","rules_json":"[]","created_at":"now"},"jobs":[{"id":"job-first","type":"chat.send","state":"completed"}]}"#.utf8))
    let chat = ChatSession()
    chat.conversationID = "first"; chat.jobID = "job-first"; chat.sending = true
    let pending = Task { await chat.update(model) }
    while completion == nil { await Task.yield() }
    await chat.select("second", model)
    chat.composer = "Do not overwrite"
    completion?.resume(returning: Data(#"{"id":"first","title":"first","messages":[]}"#.utf8))
    await pending.value
    #expect(chat.detail?.id == "second" && chat.conversationID == "second")
    #expect(chat.composer == "Do not overwrite" && chat.jobID == nil && !chat.sending)
}

@MainActor @Test func navigationWaitsOnlyForSubmissionAcknowledgement() {
    let chat = ChatSession()
    chat.conversationID = "first"; chat.submitting = true; chat.sending = true
    chat.newConversation(StudioModel())
    #expect(chat.conversationID == "first")
}

@Test func executionDurationHandlesMinutesHoursAndInvalidValues() {
    #expect(ConversationActivity.duration(47 * 60 + 18) == L("{0} د {1} ث", 47, 18))
    #expect(ConversationActivity.duration(3661) == L("{0} س {1} د {2} ث", 1, 1, 1))
    #expect(ConversationActivity.duration(-1) == L("{0} ث", 0))
}

@MainActor @Test func completedReplyWaitsForNavigationInsteadOfLosingMonitor() async throws {
    let snapshot = Data(#"{"workspace_id":"w","sources":[],"techniques":[],"drafts":[],"rules":[],"profiles":[],"dna_version":{"id":"d","rules_json":"[]","created_at":"now"},"jobs":[{"id":"job","type":"chat.send","state":"completed"}]}"#.utf8)
    var polls = 0
    let model = StudioModel(requestOverride: { command, _ in
        switch command {
        case "chat.progress":
            polls += 1
            return Data(#"{"job_id":"job","state":"completed","stage":"completed","message":"","citations":[],"elapsed_seconds":1}"#.utf8)
        case "workspace.snapshot": return snapshot
        case "agents.list": return Data(#"{"agents":[]}"#.utf8)
        case "chat.list": return Data(#"{"conversations":[]}"#.utf8)
        default: return Data(#"{"id":"first","title":"first","messages":[]}"#.utf8)
        }
    })
    let chat = ChatSession()
    chat.conversationID = "first"; chat.jobID = "job"; chat.sending = true; chat.loading = true
    let monitor = Task { await chat.monitor(model, job:"job") }
    while polls == 0 { await Task.yield() }
    // Let the first completion poll encounter navigation in progress.
    try await Task.sleep(for:.milliseconds(20))
    chat.loading = false
    await monitor.value
    #expect(polls >= 2)
    #expect(chat.jobID == nil && !chat.sending && chat.detail?.id == "first")
}

@Test func activityGroupsPreserveOrderAndCollapseRepeatedDetails() {
    let steps = [
        ConversationExecutionStep(id: "1", kind: "context", detail: "context", elapsedSeconds: 0),
        ConversationExecutionStep(id: "2", kind: "reading", detail: "Article", elapsedSeconds: 1),
        ConversationExecutionStep(id: "3", kind: "reading", detail: "Article", elapsedSeconds: 2),
        ConversationExecutionStep(id: "4", kind: "reading", detail: "Other", elapsedSeconds: 3),
        ConversationExecutionStep(id: "5", kind: "web", detail: "query", elapsedSeconds: 4),
        ConversationExecutionStep(id: "6", kind: "reading", detail: "Last", elapsedSeconds: 5)
    ]
    let groups = ActivityEventGroup.groups(steps)
    #expect(groups.map(\.kind) == ["reading", "web", "reading"])
    #expect(groups[0].details == ["Article", "Other"])
    #expect(ActivityEventGroup.displayDetail("https://www.githubstatus.com/incidents/123") == "githubstatus.com")
    #expect(ActivityEventGroup.sourceURL("file:///etc/passwd") == nil)
    #expect(ActivityEventGroup.displayDetail("Article title") == "Article title")
}

@Test func activitySummaryRemovesStreamingWhitespaceGaps() {
    #expect(ConversationActivity.readableSummary("  **Searching**\n\n\n\nReading  ") == "Searching\n\nReading")
}
