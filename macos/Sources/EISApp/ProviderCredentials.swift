import Foundation
import Darwin

/// Credentials belong only to this workspace; provider secrets never cross IPC.
enum ProviderCredentials {
    static func fileURL(workspace: URL, profileID: String) throws -> URL {
        guard UUID(uuidString: profileID) != nil else { throw EngineError(message: L("معرّف اتصال غير صالح.")) }
        return workspace.appendingPathComponent(".providers", isDirectory: true).appendingPathComponent(profileID + ".json")
    }
    private static func directory(workspace: URL) throws -> Int32 {
        let url = workspace.appendingPathComponent(".providers", isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        let fd = Darwin.open(url.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard fd >= 0 else { throw EngineError(message: L("تعذّر فتح مجلد بيانات الاتصال بأمان.")) }
        guard fchmod(fd, 0o700) == 0 else { Darwin.close(fd); throw EngineError(message: L("تعذّر ضبط صلاحيات المجلد.")) }
        return fd
    }
    static func read(workspace: URL, profileID: String) throws -> String {
        let url = try fileURL(workspace: workspace, profileID: profileID)
        let dir = try directory(workspace: workspace); defer { Darwin.close(dir) }
        let fd = openat(dir, url.lastPathComponent, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        if fd < 0 && errno == ENOENT { return "{}" }
        guard fd >= 0 else { throw EngineError(message: L("تعذّر قراءة ملف الاتصال.")) }
        defer { Darwin.close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_mode & S_IFMT == S_IFREG, info.st_size <= 65536 else {
            throw EngineError(message: L("ملف الاتصال غير صالح أو أكبر من {0} كيلوبايت.", 64))
        }
        guard fchmod(fd, 0o600) == 0 else { throw EngineError(message: L("تعذّر ضبط صلاحيات الملف.")) }
        var data = Data(), buffer = [UInt8](repeating: 0, count: 4096)
        while true {
            let count = Darwin.read(fd, &buffer, buffer.count)
            if count < 0 && errno == EINTR { continue }
            guard count >= 0 else { throw EngineError(message: L("تعذّرت قراءة الملف.")) }
            if count == 0 { break }
            data.append(contentsOf: buffer.prefix(count))
            guard data.count <= 65536 else { throw EngineError(message: L("ملف الاتصال أكبر من الحد المسموح.")) }
        }
        guard let text = String(data: data, encoding: .utf8) else { throw EngineError(message: L("يجب أن يكون الملف بترميز UTF-8.")) }
        return text
    }
    static func saveJSON(_ text: String, workspace: URL, profileID: String) throws {
        let url = try fileURL(workspace: workspace, profileID: profileID)
        let data = Data(text.utf8)
        guard data.count <= 65536, (try? JSONSerialization.jsonObject(with: data)) is [String: Any] else {
            throw EngineError(message: L("أدخل كائن JSON صالحًا لا يتجاوز {0} كيلوبايت.", 64))
        }
        let dir = try directory(workspace: workspace); defer { Darwin.close(dir) }
        let temporary = "." + UUID().uuidString + ".tmp"
        let fd = openat(dir, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
        guard fd >= 0 else { throw EngineError(message: L("تعذّر إنشاء ملف الاتصال.")) }
        defer { Darwin.close(fd); unlinkat(dir, temporary, 0) }
        try data.withUnsafeBytes { bytes in
            var offset = 0
            while offset < data.count {
                let count = Darwin.write(fd, bytes.baseAddress!.advanced(by: offset), data.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw EngineError(message: L("تعذّر حفظ ملف الاتصال.")) }
                offset += count
            }
        }
        guard fsync(fd) == 0, renameat(dir, temporary, dir, url.lastPathComponent) == 0 else {
            throw EngineError(message: L("تعذّر تثبيت ملف الاتصال."))
        }
    }
    static func saveKey(_ key: String, workspace: URL, profileID: String) throws {
        let existing = try read(workspace: workspace, profileID: profileID)
        var object = (try? JSONSerialization.jsonObject(with: Data(existing.utf8))) as? [String: Any] ?? [:]
        object["api_key"] = key
        let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
        try saveJSON(String(decoding: data, as: UTF8.self), workspace: workspace, profileID: profileID)
    }
}
