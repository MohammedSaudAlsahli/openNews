// Repair legacy newsletter list markers without changing ordinary paragraphs.
export function readerMarkdown(text: string): string {
  return text.replace(/^([ \t]*(?:[-*+]|\d+\.)[ \t]*)\n(?:[ \t]*\n)+(?=\S)/gm, "$1 ");
}

// Preserve publisher image identities when a CDN adds size/quality transforms.
function imageIdentity(url = ""): string {
  try {
    const decoded = decodeURIComponent(url);
    const embedded = decoded.lastIndexOf("https://");
    return new URL(decoded.slice(Math.max(0, embedded))).pathname;
  } catch { return url; }
}
export function readerLayout(blocks: Record<string, any>[], coverId?: string) {
  const cover = blocks.find(b => b.type === "image" && b.id === coverId)
    || blocks.find(b => b.type === "image" && ["cover", "feed-cover"].includes(b.id));
  // Confirmed publisher masthead, retained as a source badge rather than body art.
  const logo = blocks.find(b => b.type === "image" && (b.role === "logo" ||
    imageIdentity(b.url).includes("7440cfd1-2142-4f98-b793-e6c2e48fe23f_1950x750")));
  const body = blocks.filter(b => b !== logo && !(cover && b.type === "image" && imageIdentity(b.url) === imageIdentity(cover.url)));
  return { cover, logo, body };
}
