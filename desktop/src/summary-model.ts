import type { RecordData } from "./engine";

// Mirror the engine's news-role assignment, without implying model health.
export function summaryModel(
  snapshot: RecordData,
  status = snapshot.news_digest || {},
): string {
  return status.engine === "local"
    ? status.local_model || ""
    : snapshot.assignments?.find((row: RecordData) => row.role === "news")
        ?.model_id || "";
}
