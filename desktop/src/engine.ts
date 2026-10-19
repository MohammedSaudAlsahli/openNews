import { invoke } from "@tauri-apps/api/core";
export type RecordData = Record<string, any>;
export async function call<T = RecordData>(
  command: string,
  payload: RecordData = {},
): Promise<T> {
  try { return await invoke<T>("engine_call", { command, payload }); }
  catch (error) {
    if (String(error).includes("Engine is starting")) throw error;
    const code = String(error).match(/\b[A-Z][A-Z_]{3,50}\b/)?.[0] || "REQUEST_FAILED";
    void invoke("record_diagnostic", {operation:command,code}).catch(()=>{});
    throw error;
  }
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

window.addEventListener("error",()=>{void invoke("record_diagnostic",{operation:"frontend",code:"UNCAUGHT_ERROR"}).catch(()=>{})});
window.addEventListener("unhandledrejection",()=>{void invoke("record_diagnostic",{operation:"frontend",code:"UNHANDLED_REJECTION"}).catch(()=>{})});
