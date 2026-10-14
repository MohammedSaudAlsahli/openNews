import SwiftUI
import Sparkle

@MainActor final class AppUpdates: ObservableObject {
    static let shared = AppUpdates()
    private let controller: SPUStandardUpdaterController?
    private init() {
        // Unit-test executables and unconfigured development bundles must not contact a feed.
        if Bundle.main.object(forInfoDictionaryKey: "SUPublicEDKey") != nil {
            controller = SPUStandardUpdaterController(startingUpdater: true, updaterDelegate: nil, userDriverDelegate: nil)
        } else { controller = nil }
    }
    func check() { controller?.checkForUpdates(nil) }
    var available: Bool { controller != nil }
}

struct UpdateSettings: View {
    @AppStorage("SUEnableAutomaticChecks") private var checks = true
    var body: some View {
        Section(L("تحديثات التطبيق")) {
            Toggle(L("التحقق تلقائيًا من التحديثات"), isOn: $checks)
            Button(L("التحقق من وجود تحديث…")) { AppUpdates.shared.check() }
                .disabled(!AppUpdates.shared.available)
            Text(L("يُنزل التحديث ويستبدل التطبيق بعد موافقتك. تبقى أخبارك ومسوداتك ونماذجك محفوظة على الجهاز."))
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}
