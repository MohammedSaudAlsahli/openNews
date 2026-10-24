# Legacy Swift Markdown rendering

The article reader (workspace and menu bar) and conversations share `RichTextView`.
Inline code uses a smaller monospaced font and per-line rounded TextKit backgrounds,
without adding padding characters to the source. Plain URLs remain links; code literals
are not automatically linked. Paragraph direction is detected from prose rather than
embedded commands and URLs. Block quotes use a content-direction leading rule.

Fences retain their language and whitespace, including incomplete streaming fences.
`MarkdownCodeBlock` provides a native SwiftUI copy button and horizontal scrolling.
`CodeHighlighting` is a bounded lexical highlighter for Swift, Python, JS/TS, JSON,
YAML, CSS and shell; other languages remain plain text. This is lexical coloring,
not a full language parser. HTML article extraction retains language-/lang- classes
on pre/code blocks. Previously cached extracted content cannot recover a language
that was discarded before this change without refreshing the article.

Validation: 316 Python tests and 43 Swift tests passed; the additional Arabic prose
with long technical tokens regression passed separately. Visual inspection used the
production renderer in an isolated native harness: dark/light, wide/narrow, mixed
Arabic/English, links, inline commands, quotes, JSON/Python and copy interaction.

## Reading polish

Inline capsules use font ascender/descender and the actual line baseline, excluding
paragraph leading from their background height. Paragraphs have 18 pt separation;
article line spacing is 5 pt. Code blocks use an inset neutral surface, a quiet
header divider and 16 pt content padding. Verified in the native renderer with
mixed Arabic/English at wide and narrow widths in light and dark appearances.
