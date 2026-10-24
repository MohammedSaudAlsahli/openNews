import { createElement, memo, type ReactNode } from "react";
import { all, createLowlight } from "lowlight";
import type { Element, Root, Text } from "hast";

const highlighter = createLowlight(all);
const common = [
  "javascript",
  "typescript",
  "python",
  "bash",
  "json",
  "sql",
  "xml",
  "css",
  "rust",
  "go",
  "java",
  "cpp",
  "csharp",
  "swift",
  "ruby",
  "yaml",
];

function renderTokens(node: Root | Element | Text, key = "root"): ReactNode {
  if (node.type === "text") return node.value;
  if (node.type === "root")
    return node.children.map((child, i) =>
      renderTokens(child as Element | Text, `${key}-${i}`),
    );
  // Lowlight emits only spans and text. No source HTML is executed.
  return createElement(
    "span",
    {
      key,
      className: (node.properties.className as string[] | undefined)?.join(" "),
    },
    node.children.map((child, i) =>
      renderTokens(child as Element | Text, `${key}-${i}`),
    ),
  );
}

export default memo(function HighlightedCode({
  source,
  className = "",
}: {
  source: string;
  className?: string;
}) {
  const language = /language-([^\s]+)/i.exec(className)?.[1].toLowerCase();
  let content: ReactNode = source;
  // Very long blocks remain readable plain text rather than blocking the UI.
  if (source.length <= 50000) {
    try {
      if (language && highlighter.registered(language))
        content = renderTokens(highlighter.highlight(language, source));
      else if (!language && source.length <= 10000)
        content = renderTokens(
          highlighter.highlightAuto(source, { subset: common }),
        );
    } catch {
      /* Unknown or incomplete streamed code remains visible verbatim. */
    }
  }
  return (
    <code className={`hljs ${className}`} dir="ltr">
      {content}
    </code>
  );
});
