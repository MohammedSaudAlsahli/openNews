import Foundation

enum ConversationPresentation {
    /// Resolve identifiers only against the frozen evidence for this reply.
    /// Never guess a URL, and never mutate the stored message or source text.
    static func markdown(_ text: String, citations: [ConversationCitation], partial: Bool = false) -> String {
        let pattern = #"\[([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\]"#
        guard let expression = try? NSRegularExpression(pattern: pattern) else { return text }
        let original = text as NSString
        let result = NSMutableString(string: text)
        for match in expression.matches(in: text, range: NSRange(location: 0, length: original.length)).reversed() {
            let identifier = original.substring(with: match.range(at: 1))
            let replacement: String
            if let index = citations.firstIndex(where: { $0.articleId.caseInsensitiveCompare(identifier) == .orderedSame }),
               let url = URL(string: citations[index].url), RichTextLinks.allowed(url) {
                // Angle brackets protect parentheses in source URLs in Markdown.
                let address = url.absoluteString.replacingOccurrences(of: "<", with: "%3C").replacingOccurrences(of: ">", with: "%3E")
                replacement = "[\(index + 1)](<\(address)>)"
            } else { replacement = L("[مرجع غير متاح]") }
            result.replaceCharacters(in: match.range, with: replacement)
        }
        if partial {
            return (result as String).replacingOccurrences(of: #"\[[0-9a-fA-F-]{1,36}$"#, with: "", options: .regularExpression)
        }
        return result as String
    }
}
