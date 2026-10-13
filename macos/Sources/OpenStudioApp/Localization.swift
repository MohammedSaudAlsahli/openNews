import Foundation

/// Interface copy only. Never pass document text, model output, titles supplied by users,
/// credentials or source excerpts through this lookup.
enum AppLanguage: String, CaseIterable {
    case arabic = "ar"
    case english = "en"
    static func resolve(_ value: String?) -> Self { Self(rawValue: value ?? "ar") ?? .arabic }
    static var current: Self { resolve(UserDefaults.standard.string(forKey: "appLanguage")) }
    var isRightToLeft: Bool { self == .arabic }
    var locale: Locale { DisplayFormat.locale(language: self) }
}

enum Localization {
    static func argument(_ value: Any, language: AppLanguage = .current, regionalLocale: Locale = .autoupdatingCurrent) -> String {
        if let integer = value as? Int { return DisplayFormat.integer(integer, language: language, regionalLocale: regionalLocale) }
        return String(describing: value)
    }
    static let english: [String: String] = load("en")
    static let arabic: [String: String] = load("ar")
    private static func load(_ language: String) -> [String: String] {
        // SwiftPM's generated bundle is bundled inside the app's Resources directory.
        let name = "OpenStudio_OpenStudioApp"
        let embedded = Bundle.main.url(forResource: name, withExtension: "bundle").flatMap(Bundle.init(url:))
        let bundles = embedded.map { [$0] } ?? [Bundle.module]
        for bundle in bundles.compactMap({ $0 }) {
            if let url = bundle.url(forResource: language, withExtension: "json"),
               let data = try? Data(contentsOf: url),
               let map = try? JSONDecoder().decode([String: String].self, from: data) { return map }
        }
        return [:]
    }
    static func text(_ key: String, arguments: [String] = [], language: AppLanguage = .current, structuredError: Bool = false) -> String {
        // Structured backend validation text uses a fixed file prefix and known templates.
        let filePrefix = "ملف sources.yml: "
        if key.hasPrefix(filePrefix) || key.hasPrefix("sources.yml: ") {
            let prefix = key.hasPrefix(filePrefix) ? filePrefix : "sources.yml: "
            return (language == .english ? "sources.yml: " : filePrefix) + text(String(key.dropFirst(prefix.count)), language: language, structuredError: true)
        }
        if structuredError, arguments.isEmpty, english[key] == nil, !english.values.contains(key) {
            for patternKey in english.keys where patternKey.contains("{0}") {
                guard let placeholder = try? NSRegularExpression(pattern: #"\{[0-9]+\}"#) else { continue }
                let original = patternKey as NSString
                var pattern = "^", offset = 0
                for token in placeholder.matches(in: patternKey, range: NSRange(location: 0, length: original.length)) {
                    pattern += NSRegularExpression.escapedPattern(for: original.substring(with: NSRange(location: offset, length: token.range.location - offset))) + "(.+?)"
                    offset = NSMaxRange(token.range)
                }
                pattern += NSRegularExpression.escapedPattern(for: original.substring(from: offset)) + "$"
                guard let matcher = try? NSRegularExpression(pattern: pattern),
                      let match = matcher.firstMatch(in: key, range: NSRange(key.startIndex..., in: key)), match.numberOfRanges > 1 else { continue }
                let input = key as NSString
                let values = (1..<match.numberOfRanges).map { input.substring(with: match.range(at: $0)) }
                return text(patternKey, arguments: values, language: language)
            }
        }
        let canonical = english[key] != nil ? key : english.first(where: { $0.value == key })?.key ?? key
        let template = language == .english ? (english[canonical] ?? key) : (arabic[canonical] ?? key)
        // Single-pass substitution: argument text containing {1} remains literal user data.
        guard let regex = try? NSRegularExpression(pattern: #"\{([0-9]+)\}"#) else { return template }
        let original = template as NSString
        let matches = regex.matches(in: template, range: NSRange(location: 0, length: original.length))
        var result = template
        for match in matches.reversed() {
            guard let index = Int(original.substring(with: match.range(at: 1))), arguments.indices.contains(index),
                  let range = Range(match.range, in: result) else { continue }
            result.replaceSubrange(range, with: arguments[index])
        }
        return result
    }
}

func L(_ key: String, _ arguments: Any...) -> String {
    Localization.text(key, arguments: arguments.map { Localization.argument($0) })
}
