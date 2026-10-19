export type ArticleIncident = { title: string; url: string; source: string; articleId: string; stage: string; elapsedMs: number; bodyStatus: string; errorCode?: string };
export function articleIncidentText(incident: ArticleIncident) {
  // Strip credentials, query parameters and fragments which can contain private tokens.
  let address = "";
  try { const url = new URL(incident.url); if (["http:", "https:"].includes(url.protocol)) { url.username=""; url.password=""; url.search=""; url.hash=""; address=url.href; } } catch {}
  const clean = (value: string) => String(value || "").replace(/[\r\n`]/g, " ").slice(0, 300);
  return `## Article context\nTitle: ${clean(incident.title)}\nURL (without query): ${address.slice(0, 1000)}\nSource: ${clean(incident.source)}\nArticle ID: ${clean(incident.articleId)}\nStage: ${clean(incident.stage)}\nElapsed: ${Math.round(incident.elapsedMs)} ms\nBody status: ${clean(incident.bodyStatus)}\nError code: ${clean(incident.errorCode || "none")}\n`;
}
// Only allowlisted technical codes and locally generated diagnostics enter the URL.
export function issueUrl(report: string, code = "", article?: ArticleIncident) {
  const safeCode = /^[A-Z][A-Z_]{3,50}$/.test(code) ? code : "USER_REPORT";
  const body = `## What happened?\n${safeCode}\n\n${article ? articleIncidentText(article) + "\n" : ""}## Steps to reproduce (optional)\n\n## Diagnostics\n\`\`\`text\n${report.slice(-4500)}\n\`\`\`\n`;
  return "https://github.com/MohammedSaudAlsahli/openStudio/issues/new?" + new URLSearchParams({title: `[openNews] ${safeCode}`, body}).toString();
}
