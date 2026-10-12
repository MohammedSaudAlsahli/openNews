import Foundation
import Testing
@testable import EISApp

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
    #expect(chat.format == "discussion")
    #expect(chat.seconds == 60)
    #expect(chat.error == nil)
    #expect(chat.composerRevision != revision)
}

@MainActor @Test func newConversationCannotDetachAnActiveReply() {
    let chat = ChatSession()
    chat.conversationID = "active-chat"
    chat.composer = "Keep this"
    chat.sending = true
    chat.jobID = "running-job"
    chat.newConversation(StudioModel())
    #expect(chat.conversationID == "active-chat")
    #expect(chat.jobID == "running-job")
    #expect(chat.composer == "Keep this")
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
