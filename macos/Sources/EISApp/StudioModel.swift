import Foundation
import AppKit

@MainActor final class StudioModel: ObservableObject {
    @Published var snapshot: Snapshot?
    @Published var customAgents: [CustomAgent] = []
    @Published var agentEditor = AgentEditorState()
    @Published var catalog: ProviderCatalog?
    @Published var health: Health?
    @Published var error: String?
    @Published var notice: String?
    @Published var hasUnsavedChanges = false
    @Published var busy = false
    @Published var connecting = false
    private var process: Process?
    private var socketDirectory: URL?
    private var socketPath = ""
    private var polling: Task<Void, Never>?
    let workspace: URL
    private let permissionDefaults: UserDefaults

    init(permissionDefaults: UserDefaults = .standard) {
        self.permissionDefaults = permissionDefaults
        workspace = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("com.editorialintelligence.studio/default", isDirectory: true)
    }

    func start() async {
        guard !connecting else { return }
        connecting = true
        defer { connecting = false }
        let previous = process
        let previousDirectory = socketDirectory
        stop()
        do {
            for _ in 0..<50 where previous?.isRunning == true { try await Task.sleep(nanoseconds: 100_000_000) }
            guard previous?.isRunning != true else { throw EngineError(message: L("لم يتوقف المحرك السابق بعد. حاول مرة أخرى.")) }
            if let previousDirectory { try? FileManager.default.removeItem(at: previousDirectory) }
            let resources = Bundle.main.resourceURL!
            let python = resources.appendingPathComponent("python/bin/python3.12")
            let entry = resources.appendingPathComponent("engine/bootstrap.py")
            guard FileManager.default.isExecutableFile(atPath: python.path) else {
                throw EngineError(message: L("هذه ليست الحزمة المستقلة. افتح تطبيق .app المبني بواسطة build_app.sh."))
            }
            let directory = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("eis-"+String(UUID().uuidString.prefix(8)))
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            socketDirectory = directory
            socketPath = directory.appendingPathComponent("engine.sock").path
            let child = Process()
            child.executableURL = python
            child.arguments = ["-I", "-B", entry.path, "--workspace", workspace.path, "--socket", socketPath]
            child.environment = ["PATH":"/usr/bin:/bin", "HOME":NSHomeDirectory(), "AGNO_TELEMETRY":"false", "LANG":"en_US.UTF-8"]
            child.standardOutput = FileHandle.nullDevice
            child.standardError = FileHandle.nullDevice
            try child.run()
            process = child
            for _ in 0..<100 {
                if !child.isRunning { throw EngineError(message: L("توقف المحرك عند الإقلاع. قد تكون مساحة العمل مفتوحة في نسخة أخرى.")) }
                if FileManager.default.fileExists(atPath: socketPath) { break }
                try await Task.sleep(nanoseconds: 100_000_000)
            }
            health = try await decoded("runtime.health", as: Health.self)
            catalog = try await decoded("providers.catalog", as: ProviderCatalog.self)
            try await refresh()
            polling = Task { [weak self] in
                var ticks = 0
                while !Task.isCancelled {
                    try? await Task.sleep(nanoseconds: 1_000_000_000)
                    guard !Task.isCancelled, let self else { break }
                    if self.process?.isRunning != true {
                        self.health = nil
                        self.error = L("توقف المحرك. أعد تشغيله لاستعادة المهام المحفوظة.")
                        break
                    }
                    ticks += 1
                    let syncing = self.snapshot?.subscriptions?.contains { $0.status == "syncing" } == true
                    if self.snapshot?.jobs.contains(where: \.active) == true || (syncing && ticks % 2 == 0) || ticks % 60 == 0 {
                        try? await self.refresh()
                    }
                }
            }
        } catch { self.error = error.localizedDescription }
    }

    func stop() {
        polling?.cancel(); polling = nil
        if let process, process.isRunning { process.terminate() }
        process = nil
        health = nil
        // Socket directories are private. The child removes its own socket on exit.
    }

    func call(_ command: String, _ payload: [String: Any] = [:]) async throws -> Data {
        // Recheck at dispatch, including actions from sheets opened before permission was revoked.
        if payload["consent"] as? Bool == true && !ModelPermission.allowed(in: permissionDefaults) {
            throw EngineError(message: L("فعّل استخدام النماذج من إعدادات الصلاحيات للمتابعة."))
        }
        let request = UUID().uuidString
        var data = try JSONSerialization.data(withJSONObject: ["schema_version":1,"request_id":request,"command":command,"payload":payload])
        data.append(10)
        let path = socketPath
        let response = try await Task.detached(priority: .userInitiated) { try SocketTransport.exchange(path: path, data: data) }.value
        guard let envelope = try JSONSerialization.jsonObject(with: response) as? [String:Any],
              envelope["schema_version"] as? Int == 1,
              (envelope["request_id"] as? String)?.lowercased() == request.lowercased() else {
            throw EngineError(message: L("رد محرك غير متوافق."))
        }
        if let failure = envelope["error"] as? [String:Any] {
            throw EngineError(message: L(failure["message"] as? String ?? L("فشل الطلب"))+" ("+(failure["code"] as? String ?? "ERROR")+")")
        }
        return try JSONSerialization.data(withJSONObject: envelope["result"] ?? [:])
    }

    func decoded<T: Decodable>(_ command: String, _ payload: [String: Any] = [:], as: T.Type) async throws -> T {
        try JSONDecoder.engine.decode(T.self, from: await call(command,payload))
    }
    func refresh() async throws {
        snapshot = try await decoded("workspace.snapshot",as: Snapshot.self)
        customAgents = try await decoded("agents.list", as: CustomAgentList.self).agents
    }

    func perform(_ command: String, _ payload: [String:Any] = [:], message: String? = nil) async {
        busy = true
        defer { busy = false }
        do {
            _ = try await call(command,payload)
            try await refresh()
            notice = message
        } catch { self.error = error.localizedDescription }
    }

    func export(_ draft: Draft) async {
        do {
            let data = try await call("drafts.export",["draft_id":draft.id])
            let result = try JSONSerialization.jsonObject(with: data) as! [String:Any]
            let panel = NSSavePanel()
            panel.nameFieldStringValue = "editorial-draft.md"
            panel.title = L("تصدير مسودة للمراجعة")
            guard panel.runModal() == .OK, let url = panel.url, let text = result["text"] as? String else { return }
            try text.write(to: url, atomically: true, encoding: .utf8)
            notice = L("تم تصدير المسودة مع تنبيهات المراجعة.")
        } catch { self.error = error.localizedDescription }
    }
}
