import Foundation
import Darwin

struct EngineError: LocalizedError {
    let message: String
    var errorDescription: String? { L(message) }
}

enum SocketTransport {
    static let maximumFrame = 1024 * 1024
    static func exchange(path: String, data: Data) throws -> Data {
        guard data.count <= maximumFrame else { throw EngineError(message: L("النص أكبر من حد الرسالة.")) }
        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { throw EngineError(message: L("تعذر إنشاء اتصال المحرك.")) }
        defer { Darwin.close(fd) }
        var noSignal: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &noSignal, socklen_t(MemoryLayout<Int32>.size))
        var timeout = timeval(tv_sec: 130, tv_usec: 0)
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        var address = sockaddr_un()
        address.sun_family = sa_family_t(AF_UNIX)
        let bytes = Array(path.utf8CString)
        guard bytes.count <= MemoryLayout.size(ofValue: address.sun_path) else { throw EngineError(message: L("مسار الاتصال أطول من المسموح.")) }
        withUnsafeMutableBytes(of: &address.sun_path) { buffer in
            for (index, byte) in bytes.enumerated() { buffer[index] = UInt8(bitPattern: byte) }
        }
        let connected = withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }
        guard connected == 0 else { throw EngineError(message: L("المحرك غير متصل. أعد تشغيله من الشريط الجانبي.")) }
        try data.withUnsafeBytes { buffer in
            var sent = 0
            while sent < data.count {
                let n = Darwin.send(fd, buffer.baseAddress!.advanced(by: sent), data.count-sent, 0)
                if n < 0 && errno == EINTR { continue }
                guard n > 0 else { throw EngineError(message: L("انقطع الاتصال بالمحرك.")) }
                sent += n
            }
        }
        var answer = Data(), buffer = [UInt8](repeating: 0, count: 8192)
        while !answer.contains(10) {
            let n = Darwin.recv(fd, &buffer, buffer.count, 0)
            if n < 0 && errno == EINTR { continue }
            guard n > 0 else { throw EngineError(message: L("لم يصل رد المحرك ضمن المهلة.")) }
            answer.append(contentsOf: buffer.prefix(n))
            guard answer.count <= maximumFrame else { throw EngineError(message: L("نتيجة أكبر من حد الاتصال.")) }
        }
        return answer
    }
}

struct IPCRequest: Encodable {
    let schemaVersion = 1
    let requestID: UUID
    let command: String
    enum CodingKeys: String, CodingKey { case schemaVersion = "schema_version", requestID = "request_id", command }
}

struct Health: Decodable {
    let engineVersion: String
    let schemaVersion: Int
    let sqliteVec: String?
    let workspaceId: String
}
struct Source: Decodable, Identifiable, Hashable {
    let id, title, canonicalUri, author, rightsStatus, currentVersionId, text: String
    let versionNo, analyses: Int
    let purpose: String?
}
struct TechniqueCard: Decodable, Identifiable {
    let id, name, description, applicability, method, status, evidenceText, sourceTitle, canonicalUri: String
    let itemId, itemVersionId: String?
    let excerptStart, excerptEnd: Int
    // Python evidence offsets count Unicode code points, not Swift grapheme clusters.
    var excerpt: String { String(String.UnicodeScalarView(evidenceText.unicodeScalars.dropFirst(excerptStart).prefix(excerptEnd-excerptStart))) }
}
struct DNARule: Decodable, Identifiable { let id, statement, status: String }
struct DNAVersion: Decodable { let id, rulesJson, createdAt: String }
struct ProviderProfile: Decodable, Identifiable {
    let id, providerKey, modelId, keychainRef: String
    let label: String?
    let autoRefresh: Bool?
    let connection: ProviderConnectionStatus?
    var displayName: String { label.flatMap { $0.isEmpty ? nil : $0 } ?? providerKey }
}
struct Draft: Decodable, Identifiable, Hashable {
    let id, topic, format, language, text, currentVersionId, warningsJson: String
}
struct Job: Decodable, Identifiable {
    let id, type, state: String
    let errorCode: String?
    var active: Bool { state == "queued" || state == "running" }
}
struct Snapshot: Decodable {
    let workspaceId: String
    let sources: [Source]
    let techniques: [TechniqueCard]
    let drafts: [Draft]
    let rules: [DNARule]
    let dnaVersion: DNAVersion
    let profiles: [ProviderProfile]
    let assignments: [AgentAssignment]?
    let subscriptions: [NewsSubscription]?
    let articles: [NewsArticle]?
    let newsDigest: NewsDigestStatus?
    let newsSearch: NewsSearchStatus?
    let jobs: [Job]
}
struct NewsSearchStatus: Decodable, Equatable {
    let enabled: Bool
    let model, phase, currentTitle: String
    let indexed, semantic, pending: Int
}
struct NewsDigestStatus: Decodable, Equatable {
    var engine: String? = nil
    var localModel: String? = nil
    var currentId: String? = nil
    let enabled: Bool
    let language: String
    let prepared, pending: Int
    let dailyLimit, usedToday: Int?
    let phase: String?
    let currentTitle: String
}
struct Provider: Decodable, Identifiable {
    let id, name, status, defaultModel, credential, note: String
    let fields: [String]
    let credentialFields: [String]?
    let defaultBaseUrl: String?
    var ready: Bool { status == "ready" }
}
struct ProviderCatalog: Decodable { let agnoVersion: String; let providers: [Provider] }
struct Evidence: Decodable, Identifiable { let id, text: String }
struct ClaimViewData: Decodable, Identifiable {
    let id, text, claimType, verdict, rationale: String
    let evidence: [Evidence]
}
struct DraftVersion: Decodable, Identifiable {
    let id, text, createdAt, warningsJson, alternativesJson: String
}
struct DraftDetail: Decodable { let versions: [DraftVersion]; let claims: [ClaimViewData]; let newsEvidence: [DraftNewsEvidence]? }
struct DraftNewsEvidence: Decodable, Identifiable {
    let articleId, title, url, excerpt: String
    let publishedAt: String?
    var id: String { articleId }
}

extension JSONDecoder {
    static var engine: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }
}

struct SourceDetail: Decodable { let text, versionId: String; let techniques: [TechniqueCard] }
struct CreatedDraft: Decodable { let draftId, draftVersionId: String }
struct ImportedSource: Decodable { let itemId, versionId, status: String }

struct SubmittedJob: Decodable { let jobId: String }
struct JobDetail: Decodable { let state: String; let resultJson: String? }
struct GeneratedResult: Decodable { let draftId: String }

struct AgentAssignment: Decodable { let role, profileId, modelId: String }
struct ProviderModel: Decodable, Identifiable { let id, name: String; let available: Bool }
struct ProviderModels: Decodable {
    let models: [ProviderModel]
    let updatedAt: String?
    let error: String?
    let source: String
}
struct SavedConnection: Decodable { let profileId, keychainRef: String }

struct ConversationSummary: Decodable, Identifiable {
    let id, title, updatedAt: String
    var activeJobId: String? = nil
}
struct ConversationList: Decodable { let conversations: [ConversationSummary] }
struct CreatedConversation: Decodable { let conversationId: String }
struct ConversationDetail: Decodable {
    let id, title: String
    let messages: [ConversationMessage]
    let activeJobId: String?
    let lastJob: ConversationJob?
    let hasMore: Bool?
    let nextBeforeMessageId: String?
}
struct ConversationJob: Decodable { let id, state: String; let errorCode: String? }
struct ConversationMessage: Decodable, Identifiable {
    let id, role, content, createdAt: String
    let activity: ConversationExecution?
    let outputs: [ConversationOutput]?
    let citations: [ConversationCitation]?
}
struct ConversationOutput: Decodable, Identifiable {
    let draftId, title, format: String
    let text: String?
    var id: String { draftId }
}
struct ConversationCitation: Decodable, Identifiable {
    let articleId, title, url: String
    let publishedAt: String?
    var origin: String? = nil
    var excerpt: String? = nil
    var id: String { articleId }
}
struct NewsSubscription: Decodable, Identifiable {
    let id, title, url, feedUrl, kind: String
    let enabled: Bool
    let lastChecked, lastSuccess, error: String?
    let status: String
    let unreadCount: Int
}
struct NewsArticle: Decodable, Identifiable {
    let id, subscriptionId, sourceTitle, title, url, discoveredAt, summary, bodyStatus: String
    let publishedAt: String?
    var isRead: Bool?
    var isBookmarked: Bool? = nil
    var coverImageId: String? = nil
}
struct NewsArticlePage: Decodable { let articles: [NewsArticle]; let hasMore: Bool }
struct ArticleAISummary: Decodable { let summary, model: String; let cached: Bool }
struct NewsArticleDetail: Decodable {
    let isBookmarked: Bool?
    let text: String
    let title, url, bodyStatus, summary: String?
    let reader: ArticleReadingContent?
    let preparedSummary: ArticleAISummary?
}
struct ArticleReadingContent: Decodable {
    let blocks: [ArticleReadingBlock]?
    let author, origin, checkedAt: String?
    let refreshFailed: Bool?
}
struct ArticleReadingBlock: Decodable {
    let type: String
    let id, text, url, alt, caption: String?
}
struct ArticleImageFile: Decodable { let path: String }


struct CustomAgent: Decodable, Identifiable {
    let id, name, instructions, profileId, modelId, createdAt, updatedAt: String
}
struct CustomAgentList: Decodable { let agents: [CustomAgent] }
struct SavedCustomAgent: Decodable { let agentId: String }

struct ConversationContextInfo: Decodable {
    let totalMessages, includedMessages, historyBytes, historyBudgetBytes: Int
    let hasOlderContext: Bool
}
struct ConversationExecutionStep: Decodable, Identifiable {
    let id, kind, detail: String
    let elapsedSeconds: Int
}
struct ConversationExecution: Decodable {
    let steps: [ConversationExecutionStep]
    let reasoningSummary: String
    var reasoningSummaries: [String: String]? = nil
    var summaryLanguage: String? = nil
    var summaryTranslationState: String? = nil
    let elapsedSeconds: Int
    let contextInfo: ConversationContextInfo?
}
struct ConversationProgress: Decodable {
    let execution: ConversationExecution?
    let contextInfo: ConversationContextInfo?
    let jobId, state, stage, message: String
    let activity: String?
    let citations: [ConversationCitation]
    let elapsedSeconds: Int
}
