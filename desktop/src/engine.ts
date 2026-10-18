import { invoke } from "@tauri-apps/api/core";
export type RecordData = Record<string, any>;
export async function call<T = RecordData>(
  command: string,
  payload: RecordData = {},
): Promise<T> {
  return invoke<T>("engine_call", { command, payload });
}
export const active = (state?: string) =>
  state === "queued" || state === "running";
export function language(text: string) {
  return /[\u0600-\u06ff]/.test(text) ? "ar" : "en";
}
export function duration(seconds: number) {
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}
// Aggregators often use the description for navigation rather than an excerpt.
export function articleExcerpt(text = "") {
  if (/^\s*Article URL:/i.test(text)) return "";
  return text
    .replace(/<[^>]*>/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .slice(0, 190);
}
