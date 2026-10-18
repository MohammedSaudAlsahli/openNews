import AppKit
import WebKit

// A separate, short-lived browser process. No Tauri IPC, shared cookies, logins,
// popups or downloads. The engine still extracts and validates the returned HTML.
@MainActor final class PublicReader: NSObject, WKNavigationDelegate, WKUIDelegate {
    private var browser: WKWebView?
    private var finished = false
    func load(_ url: URL) {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let browser = WKWebView(frame: .zero, configuration: configuration)
        self.browser = browser
        browser.navigationDelegate = self
        browser.uiDelegate = self
        browser.load(URLRequest(url: url, timeoutInterval: 10))
        DispatchQueue.main.asyncAfter(deadline: .now() + 12) { self.finish("") }
    }
    static func allowed(_ url: URL?) -> Bool {
        guard let url, ["https", "http"].contains(url.scheme?.lowercased() ?? ""), url.user == nil, url.password == nil,
              let host = url.host?.lowercased(), !host.isEmpty, host != "localhost", !host.hasSuffix(".local"), !host.hasSuffix(".localhost") else { return false }
        // Public capture never navigates to IP literals or local single-label names.
        return host.contains(".") && host.contains(where: { $0.isLetter }) && !host.contains(":")
    }
    func webView(_ view: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(Self.allowed(action.request.url) && action.targetFrame?.isMainFrame == true ? .allow : .cancel)
    }
    func webView(_ view: WKWebView, didFinish navigation: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.7) {
            view.evaluateJavaScript("document.querySelector('article')?.outerHTML || document.querySelector('main')?.outerHTML || ''") { result, _ in
                let html = result as? String ?? ""
                self.finish(html.utf8.count <= 512 * 1024 ? html : "")
            }
        }
    }
    func webView(_ view: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { finish("") }
    func webView(_ view: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { finish("") }
    func webView(_ view: WKWebView, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        completionHandler(challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust ? .performDefaultHandling : .cancelAuthenticationChallenge, nil)
    }
    private func finish(_ html: String) {
        guard !finished else { return }
        finished = true
        browser?.stopLoading()
        if let data = try? JSONSerialization.data(withJSONObject: ["html":html]) { FileHandle.standardOutput.write(data) }
        exit(0)
    }
}
@main struct Main {
    @MainActor static func main() {
        guard CommandLine.arguments.count == 2, let url = URL(string: CommandLine.arguments[1]), PublicReader.allowed(url) else { exit(1) }
        let application = NSApplication.shared
        application.setActivationPolicy(.prohibited)
        let reader = PublicReader()
        reader.load(url)
        withExtendedLifetime(reader) { application.run() }
    }
}
