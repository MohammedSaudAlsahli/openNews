import Foundation

/// Format presentation metadata, never stored document/source text or wire values.
enum DisplayFormat {
    /// Change UI language while retaining the user's region and explicit locale overrides.
    static func locale(language: AppLanguage = .current, regionalLocale: Locale = .autoupdatingCurrent) -> Locale {
        var components = Locale.Components(identifier: regionalLocale.identifier)
        components.languageComponents.languageCode = Locale.LanguageCode(language.rawValue)
        components.languageComponents.script = nil
        components.region = regionalLocale.region
        components.calendar = regionalLocale.calendar.identifier
        components.hourCycle = regionalLocale.hourCycle
        return Locale(components: components)
    }

    static func integer(_ value: Int, language: AppLanguage = .current, regionalLocale: Locale = .autoupdatingCurrent) -> String {
        let formatter = NumberFormatter()
        formatter.locale = locale(language: language, regionalLocale: regionalLocale)
        formatter.numberStyle = .decimal
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? String(value)
    }

    /// Timestamp instants use the user's time zone. Date-only values retain their calendar day.
    /// Invalid or unknown input is preserved rather than turned into an invented date.
    static func date(_ value: String, language: AppLanguage = .current,
                     regionalLocale: Locale = .autoupdatingCurrent, timeZone: TimeZone = .autoupdatingCurrent) -> String {
        let formatter = DateFormatter()
        formatter.locale = locale(language: language, regionalLocale: regionalLocale)
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        if let day = calendarDay(value) {
            formatter.timeZone = TimeZone(secondsFromGMT: 0)
            return formatter.string(from: day)
        }
        // A malformed date-only string must not be normalized by the timestamp parser.
        guard value.range(of: #"^\d{4}-\d{2}-\d{2}$"#, options: .regularExpression) == nil else { return value }
        let parser = ISO8601DateFormatter()
        parser.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var instant = parser.date(from: value)
        if instant == nil {
            parser.formatOptions = [.withInternetDateTime]
            instant = parser.date(from: value)
        }
        guard let instant else { return value }
        formatter.timeZone = timeZone
        formatter.timeStyle = .short
        return formatter.string(from: instant)
    }

    /// Explicit opt-in for a technical token embedded in Arabic UI copy (URL, ID, path).
    /// FSI/PDI prevent its punctuation from reordering adjacent Arabic text; no storage mutation.
    static func isolated(_ value: String, language: AppLanguage = .current) -> String {
        language.isRightToLeft && !value.isEmpty ? "\u{2068}" + value + "\u{2069}" : value
    }

    private static func calendarDay(_ value: String) -> Date? {
        guard value.range(of: #"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"#, options: .regularExpression) != nil else { return nil }
        let parts = value.split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return nil }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        let components = DateComponents(year: parts[0], month: parts[1], day: parts[2], hour: 12)
        guard let date = calendar.date(from: components) else { return nil }
        let actual = calendar.dateComponents([.year, .month, .day], from: date)
        guard actual.year == parts[0], actual.month == parts[1], actual.day == parts[2] else { return nil }
        return date
    }
}
