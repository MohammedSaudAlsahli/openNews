// Repair legacy newsletter list markers without changing ordinary paragraphs.
export function readerMarkdown(text: string): string {
  return text.replace(/^([ \t]*(?:[-*+]|\d+\.)[ \t]*)\n(?:[ \t]*\n)+(?=\S)/gm, "$1 ");
}
