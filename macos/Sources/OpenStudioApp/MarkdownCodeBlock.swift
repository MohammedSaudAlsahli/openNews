import SwiftUI
import AppKit

struct MarkdownCodeBlock: View {
    @Environment(\.colorScheme) private var colorScheme
    @State private var copied = false
    let code: String
    let language: String
    let fontSize: CGFloat

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text(language.isEmpty ? "Code" : language).font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(code, forType: .string)
                    copied = true
                } label: {
                    Image(systemName: copied ? "checkmark" : "doc.on.doc")
                }
                .buttonStyle(.borderless)
                .help(L("نسخ")).accessibilityLabel(L("نسخ"))
            }.padding(.horizontal, 16).padding(.vertical, 9)
            Divider().opacity(0.4)
            ScrollView(.horizontal) {
                Text(CodeHighlighting.render(code, language: language, dark: colorScheme == .dark))
                    .font(.system(size: max(12, fontSize * 0.88), design: .monospaced))
                    .lineSpacing(4).textSelection(.enabled)
                    .fixedSize(horizontal: true, vertical: true)
                    .padding(16)
            }
        }
        .background((colorScheme == .dark ? Color.black.opacity(0.18) : Color.black.opacity(0.035)), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(Color.primary.opacity(0.07)))
        .environment(\.layoutDirection, .leftToRight)
        .task(id: copied) {
            guard copied else { return }
            try? await Task.sleep(for: .seconds(2))
            copied = false
        }
    }
}

/// A bounded lexical pass; unknown languages stay literal. No remote assets,
/// execution or conversion of source characters (including Arabic comments).
enum CodeHighlighting {
    static func render(_ code: String, language: String, dark: Bool) -> AttributedString {
        var result = AttributedString(code)
        let language = language.lowercased()
        let supported = ["swift", "python", "py", "javascript", "js", "typescript", "ts", "tsx", "jsx", "json", "yaml", "yml", "css", "bash", "sh", "shell"]
        guard supported.contains(language), code.utf16.count <= 120_000 else { return result }
        let hashComments = ["python", "py", "yaml", "yml", "bash", "sh", "shell"].contains(language)
        let comment = hashComments ? #"#[^\n]*"# : #"//[^\n]*|/\*[\s\S]*?\*/"#
        let pattern = #""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|"# + comment + #"|\b(?:import|from|export|class|struct|enum|func|def|async|await|return|let|var|const|if|else|for|while|in|private|public|true|false|null|None|True|False|throw|try|guard|switch|case)\b|\b\d+(?:\.\d+)?\b"#
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return result }
        let native = code as NSString
        for match in regex.matches(in: code, range: NSRange(location: 0, length: native.length)) {
            guard let range = Range(match.range, in: code),
                  let lower = AttributedString.Index(range.lowerBound, within: result),
                  let upper = AttributedString.Index(range.upperBound, within: result) else { continue }
            let token = native.substring(with: match.range)
            let color: Color
            if token.hasPrefix("//") || token.hasPrefix("/*") || (hashComments && token.hasPrefix("#")) {
                color = .secondary
            } else if token.hasPrefix("\"") || token.hasPrefix("'") || token.hasPrefix("`") {
                let rest = native.substring(from: NSMaxRange(match.range)).drop(while: { $0.isWhitespace })
                color = rest.first == ":" ? (dark ? Color.yellow.opacity(0.85) : Color(red: 0.45, green: 0.30, blue: 0.05)) : (dark ? Color(red: 0.55, green: 0.80, blue: 0.56) : Color(red: 0.15, green: 0.43, blue: 0.24))
            } else if token.first?.isNumber == true {
                color = dark ? Color(red: 0.77, green: 0.66, blue: 0.96) : .purple
            } else {
                color = dark ? Color(red: 0.91, green: 0.61, blue: 0.77) : Color(red: 0.60, green: 0.20, blue: 0.41)
            }
            result[lower..<upper].foregroundColor = color
        }
        return result
    }
}
