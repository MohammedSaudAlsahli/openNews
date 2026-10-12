import SwiftUI
import WebKit

/// A real publisher page, loaded only after the user chooses the Website tab.
struct ArticleWebsite: View {
    let url: URL
    var active = true
    @StateObject private var browser = ArticleBrowser()
    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Button { browser.webView.goBack() } label: { Image(systemName: "chevron.backward") }
                    .disabled(!browser.canGoBack).help(L("السابق"))
                Button { browser.webView.goForward() } label: { Image(systemName: "chevron.forward") }
                    .disabled(!browser.canGoForward).help(L("التالي"))
                Text(browser.address.isEmpty ? (url.host ?? "") : browser.address)
                    .font(.caption).foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle)
                    .environment(\.layoutDirection, .leftToRight)
                Spacer(minLength: 0)
                if browser.loading { ProgressView().controlSize(.small) }
            }.buttonStyle(.borderless).padding(12)
            if let failure = browser.failure {
                HStack { Text(failure).font(.caption); Spacer(); Button(L("إعادة المحاولة")) { browser.load(url) } }.padding(12)
            }
            WebsiteSurface(browser: browser, active: active).frame(maxWidth: .infinity, maxHeight: .infinity)
        }.onAppear { if browser.webView.url == nil { browser.load(url) } }
            .onChange(of: active) { _, value in browser.webView.setAllMediaPlaybackSuspended(!value, completionHandler: nil) }
    }
}

@MainActor final class ArticleBrowser: NSObject, ObservableObject, WKNavigationDelegate, WKUIDelegate {
    let webView: WKWebView
    @Published var loading = false
    @Published var failure: String?
    @Published var address = ""
    @Published var canGoBack = false
    @Published var canGoForward = false
    override init() {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.preferences.javaScriptCanOpenWindowsAutomatically = false
        webView = WKWebView(frame: .zero, configuration: config)
        super.init()
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
    }
    func load(_ url: URL) {
        guard RichTextLinks.allowed(url) else { return }
        failure = nil
        webView.load(URLRequest(url: url))
    }
    private func update() {
        address = webView.url?.host ?? ""
        canGoBack = webView.canGoBack; canGoForward = webView.canGoForward
    }
    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) { loading = true; failure = nil; update() }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { loading = false; update() }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { failed(error) }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { failed(error) }
    private func failed(_ error: Error) {
        guard (error as NSError).code != NSURLErrorCancelled else { return }
        loading = false; failure = L("تعذّر فتح الموقع. تحقق من الاتصال أو عُد إلى القارئ."); update()
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(action.request.url.map(RichTextLinks.allowed) == true ? .allow : .cancel)
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if action.targetFrame == nil, let url = action.request.url { load(url) }
        return nil
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) { loading = false; failure = L("تعذّر فتح الموقع. تحقق من الاتصال أو عُد إلى القارئ.") }
}

private struct WebsiteSurface: NSViewRepresentable {
    @ObservedObject var browser: ArticleBrowser
    let active: Bool
    func makeNSView(context: Context) -> WKWebView { browser.webView }
    func updateNSView(_ nsView: WKWebView, context: Context) {
        nsView.isHidden = !active
        nsView.setAccessibilityHidden(!active)
    }
}
