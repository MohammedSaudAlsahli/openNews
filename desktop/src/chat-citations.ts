import { fromMarkdown } from "mdast-util-from-markdown";
import type { Root } from "mdast";

export interface ChatCitation {
  article_id: string;
  title?: string;
  url?: string;
  excerpt?: string;
  published_at?: string;
}

const marker = /\[([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\]/gi;
export const citationFragment = "#opennews-source-";
type Node = {
  type: string;
  value?: string;
  url?: string;
  children?: Node[];
  position?: { start: { offset?: number }; end: { offset?: number } };
};
const protectedNodes = new Set([
  "code",
  "inlineCode",
  "link",
  "linkReference",
  "html",
]);

export function sourceAddress(citation?: ChatCitation) {
  try {
    const address = new URL(citation?.url || "");
    if (
      ["https:", "http:"].includes(address.protocol) &&
      !address.username &&
      !address.password
    )
      return address;
  } catch {
    /* Historical references may have no usable address. */
  }
  return undefined;
}

// Transform prose nodes, never code examples, existing links or publisher HTML.
export function remarkChatCitations(citations: ChatCitation[]) {
  return () => (tree: Root) => {
    function visit(node: Node) {
      if (protectedNodes.has(node.type) || !node.children) return;
      node.children = node.children.flatMap((child) => {
        if (child.type !== "text" || !child.value) {
          visit(child);
          return [child];
        }
        const parts: Node[] = [];
        let start = 0;
        for (const match of child.value.matchAll(marker)) {
          const index = match.index!;
          const number =
            citations.findIndex(
              (c) => c.article_id?.toLowerCase() === match[1].toLowerCase(),
            ) + 1;
          if (index > start)
            parts.push({
              type: "text",
              value: child.value.slice(start, index),
            });
          parts.push({
            type: "link",
            url: citationFragment + match[1].toLowerCase(),
            children: [{ type: "text", value: number ? String(number) : "?" }],
          });
          start = index + match[0].length;
        }
        if (!parts.length) return [child];
        if (start < child.value.length)
          parts.push({ type: "text", value: child.value.slice(start) });
        return parts;
      });
    }
    visit(tree);
  };
}

// Preserve Markdown and code exactly when copying; change only prose reference spans.
export function copyWithCitations(
  text: string,
  citations: ChatCitation[],
  sourcesLabel: string,
  unavailableLabel: string,
) {
  const replacements: { start: number; end: number; value: string }[] = [];
  const used = new Set<number>();
  function visit(node: Node) {
    if (protectedNodes.has(node.type)) return;
    if (node.type === "text" && node.position) {
      const { start, end } = node.position;
      if (start.offset === undefined || end.offset === undefined) return;
      const raw = text.slice(start.offset, end.offset);
      for (const match of raw.matchAll(marker)) {
        if (match.index! > 0 && raw[match.index! - 1] === "\\") continue;
        const number =
          citations.findIndex(
            (c) => c.article_id?.toLowerCase() === match[1].toLowerCase(),
          ) + 1;
        if (number) used.add(number);
        replacements.push({
          start: start.offset + match.index!,
          end: start.offset + match.index! + match[0].length,
          value: number ? `[${number}]` : `[${unavailableLabel}]`,
        });
      }
    }
    node.children?.forEach(visit);
  }
  visit(fromMarkdown(text));
  let result = text;
  for (const change of replacements.sort((a, b) => b.start - a.start))
    result =
      result.slice(0, change.start) + change.value + result.slice(change.end);
  if (used.size)
    result +=
      `\n\n${sourcesLabel}\n` +
      [...used]
        .sort((a, b) => a - b)
        .map((number) => {
          const source = citations[number - 1];
          return `[${number}] ${source.title || sourcesLabel}${sourceAddress(source) ? ` — ${source.url}` : ""}`;
        })
        .join("\n");
  return result;
}
