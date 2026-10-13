import Foundation
import WebKit

/// A short-lived, cookie-free render pass for public pages whose RSS excerpt has no body.
@MainActor final class PublicPageCapture: NSObject, WKNavigationDelegate {
    private var webView: WKWebView?
    private var finish: ((String) -> Void)?
    private var started = false
    private var timeout: Task<Void, Never>?

    func load(_ url: URL, completion: @escaping (String) -> Void) {
        guard !started, RichTextLinks.allowed(url) else { return }
        started = true
        finish = completion
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        let browser = WKWebView(frame: .zero, configuration: config)
        browser.navigationDelegate = self
        webView = browser
        browser.load(URLRequest(url: url, cachePolicy: .returnCacheDataElseLoad, timeoutInterval: 10))
        timeout = Task { [weak self] in
            do { try await Task.sleep(nanoseconds: 12_000_000_000) }
            catch { return }
            self?.stop()
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        Task { [weak self] in
            try? await Task.sleep(nanoseconds: 700_000_000)
            guard let self, self.webView === webView else { return }
            let script = "document.querySelector('article')?.outerHTML || document.querySelector('main')?.outerHTML || document.body?.outerHTML || ''"
            let html = (try? await webView.evaluateJavaScript(script)) as? String ?? ""
            if html.utf8.count <= 512 * 1024, html.count > 200 { self.finish?(html) }
            self.stop()
        }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { stop() }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { stop() }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(action.request.url.map(RichTextLinks.allowed) == true ? .allow : .cancel)
    }
    private func stop() {
        timeout?.cancel()
        timeout = nil
        webView?.stopLoading()
        webView?.navigationDelegate = nil
        webView = nil
        finish = nil
        started = false
    }
}
