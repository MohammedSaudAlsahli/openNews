import SwiftUI

/// macOS presentations create a new hosting root. Bind their direction to the
/// selected app language rather than inheriting the system's initial direction.
private struct PresentationLocale: ViewModifier {
    @AppStorage("appLanguage") private var language = "ar"
    func body(content: Content) -> some View {
        content
            .environment(\.layoutDirection, language == "en" ? .leftToRight : .rightToLeft)
            .environment(\.locale, AppLanguage.current.locale)
            .multilineTextAlignment(.leading)
    }
}

extension View {
    func editorialPresentation() -> some View { modifier(PresentationLocale()) }
}
