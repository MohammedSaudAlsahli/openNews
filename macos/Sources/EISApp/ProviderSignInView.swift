import SwiftUI
import AppKit

private struct ProviderAuthStart: Decodable { let authId, authorizationUrl: String }
private struct ProviderAuthStatus: Decodable {
    let status: String
    let profileId: String?
    let error: String?
}

struct ProviderSignInView: View {
    @EnvironmentObject private var model: StudioModel
    var existingProfileID: String? = nil
    let onConnected: (String) -> Void
    @State private var authID = ""
    @State private var authorizationURL: URL?
    @State private var starting = false
    @State private var startGeneration = UUID()
    @State private var completed = false
    @State private var failure: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Label(L("تسجيل الدخول بحساب ChatGPT"), systemImage: "person.crop.circle.badge.checkmark")
                .font(.headline)
            Text(L("أكمل تسجيل الدخول والموافقة في متصفحك. تُحفظ بيانات الاتصال على جهازك، وتظهر النماذج المتاحة لحسابك بعد الربط."))
                .foregroundStyle(.secondary)
            if authID.isEmpty {
                Button(L("المتابعة في المتصفح")) { Task { await start() } }
                    .buttonStyle(.borderedProminent).disabled(starting || model.health == nil)
            } else {
                HStack { ProgressView().controlSize(.small); Text(L("بانتظار إكمال تسجيل الدخول…")) }
                if let authorizationURL {
                    Button(L("فتح المتصفح مجددًا")) { NSWorkspace.shared.open(authorizationURL) }
                }
                Button(L("إلغاء تسجيل الدخول")) { cancel() }
            }
            if starting { ProgressView().controlSize(.small) }
            if let failure { Text(L(failure)).foregroundStyle(.red).textSelection(.enabled) }
            Spacer(minLength: 0)
        }.padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .task(id: authID) { await poll() }
            .onDisappear { if !completed { cancel() } }
    }

    private func start() async {
        let generation = UUID()
        startGeneration = generation
        starting = true; failure = nil; completed = false
        defer { starting = false }
        do {
            var payload: [String: Any] = ["provider_key": "openai", "language": UserDefaults.standard.string(forKey: "appLanguage") ?? "ar"]
            if let existingProfileID { payload["profile_id"] = existingProfileID }
            let result = try await model.decoded("providers.auth.start", payload, as: ProviderAuthStart.self)
            guard generation == startGeneration else {
                _ = try? await model.call("providers.auth.cancel", ["auth_id": result.authId])
                return
            }
            guard let url = URL(string: result.authorizationUrl), url.scheme == "https", url.host == "auth.openai.com" else {
                _ = try? await model.call("providers.auth.cancel", ["auth_id": result.authId])
                throw EngineError(message: L("تعذّر بدء تسجيل الدخول الآمن."))
            }
            authorizationURL = url; authID = result.authId
            if !NSWorkspace.shared.open(url) { failure = L("تعذّر فتح المتصفح. استخدم زر فتح المتصفح مجددًا.") }
        } catch { failure = error.localizedDescription }
    }

    private func poll() async {
        let id = authID
        guard !id.isEmpty else { return }
        do {
            while !Task.isCancelled && authID == id {
                let result = try await model.decoded("providers.auth.status", ["auth_id": id], as: ProviderAuthStatus.self)
                guard !Task.isCancelled, authID == id else { return }
                if result.status == "complete", let profile = result.profileId {
                    completed = true
                    // The account is already saved even if refreshing another panel fails.
                    do { try await model.refresh() } catch { model.error = error.localizedDescription }
                    guard !Task.isCancelled, authID == id else { return }
                    onConnected(profile)
                    return
                }
                if result.status == "failed" || result.status == "cancelled" {
                    authID = ""; authorizationURL = nil
                    failure = result.error ?? L("لم يكتمل تسجيل الدخول. يمكنك المحاولة مجددًا.")
                    return
                }
                try await Task.sleep(nanoseconds: 1_500_000_000)
            }
        } catch is CancellationError {
        } catch {
            guard !Task.isCancelled, authID == id else { return }
            failure = error.localizedDescription
            cancel()
        }
    }

    private func cancel() {
        startGeneration = UUID()
        let id = authID
        authID = ""; authorizationURL = nil
        guard !id.isEmpty else { return }
        Task { _ = try? await model.call("providers.auth.cancel", ["auth_id": id]) }
    }
}
