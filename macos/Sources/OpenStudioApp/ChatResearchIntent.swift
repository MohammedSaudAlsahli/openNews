import Foundation

enum ChatResearchIntent {
    static func requiresCurrentNews(_ message: String) -> Bool {
        let text = message.lowercased()
        return ["آخر خبر", "اخر خبر", "آخر أخبار", "اخر اخبار", "ابحث بالنت", "ابحث في الويب", "ابحث عن خبر سابق", "ابحث عن أخبار سابقة", "latest news", "newest news", "breaking news", "search the web", "find related coverage"].contains { text.contains($0) }
    }
}

struct ImportedArticle: Decodable {
    let articleId: String
    let title: String
}
