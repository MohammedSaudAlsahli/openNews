import { fromMarkdown } from "mdast-util-from-markdown";
import type { Nodes } from "mdast";

// Repair legacy newsletter list markers only in prose. A global replacement
// would change Markdown samples, shell commands or HTML <pre> contents.
export function readerMarkdown(text: string): string {
  const markers = /^([ \t]*(?:[-*+]|\d+\.)[ \t]*)\r?\n(?:[ \t]*\r?\n)+(?=\S)/gm;
  if (!markers.test(text)) return text;
  const protectedRanges: [number, number][] = [];
  function visit(node: Nodes) {
    const start = node.position?.start.offset;
    const end = node.position?.end.offset;
    if (["code", "inlineCode", "html"].includes(node.type)) {
      if (start !== undefined && end !== undefined)
        protectedRanges.push([start, end]);
    } else if ("children" in node) node.children.forEach(visit);
  }
  visit(fromMarkdown(text));
  return text.replace(markers, (match, marker: string, offset: number) =>
    protectedRanges.some(
      ([start, end]) => offset < end && offset + match.length > start,
    )
      ? match
      : `${marker} `,
  );
}

// Preserve publisher image identities when a CDN adds size/quality transforms.
function imageIdentity(url = ""): string {
  try {
    const decoded = decodeURIComponent(url);
    const embedded = decoded.lastIndexOf("https://");
    return new URL(decoded.slice(Math.max(0, embedded))).pathname;
  } catch {
    return url;
  }
}
export function readerLayout(blocks: Record<string, any>[], coverId?: string) {
  const cover =
    blocks.find((b) => b.type === "image" && b.id === coverId) ||
    blocks.find(
      (b) => b.type === "image" && ["cover", "feed-cover"].includes(b.id),
    );
  // Confirmed publisher masthead, retained as a source badge rather than body art.
  const logo = blocks.find(
    (b) =>
      b.type === "image" &&
      (b.role === "logo" ||
        imageIdentity(b.url).includes(
          "7440cfd1-2142-4f98-b793-e6c2e48fe23f_1950x750",
        )),
  );
  const body = blocks.filter(
    (b) =>
      b !== logo &&
      !(
        cover &&
        b.type === "image" &&
        imageIdentity(b.url) === imageIdentity(cover.url)
      ),
  );
  return { cover, logo, body };
}
