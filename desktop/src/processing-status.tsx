import { Check, LoaderCircle, Pause } from "lucide-react";
import { t } from "./locale";
import type { RecordData } from "./engine";
const labels: Record<string, string> = {
  paused: "Background processing is paused",
  stopping: "Stopping background processing…",
  waiting_idle: "Waiting until you are away",
  memory_pressure: "Waiting for more available memory",
  waiting_charger: "Waiting for a charger",
  disabled: "Paused",
  needs_model: "Choose a model to begin",
  needs_download: "Model download required",
  summarizing: "Preparing a summary",
  waiting_model: "Waiting for the model",
  ready: "Up to date",
  waiting_articles: "Waiting for articles",
  retrying: "Waiting before retry",
  queued: "Ready to start",
  idle: "Idle",
  indexing: "Indexing articles",
  preparing: "Preparing the model",
  unavailable: "Model unavailable",
  resting: "Resting between tasks",
  cooling: "Waiting for your Mac to cool down",
  low_power: "Paused in Low Power Mode",
  waiting_device: "Waiting for your Mac",
};
export function processingLabel(phase: string) {
  return t(labels[phase] || "Status unavailable");
}
export function ProcessingStatus({
  data,
  search = false,
  loading = false,
  unavailable = false,
}: {
  data: RecordData;
  search?: boolean;
  loading?: boolean;
  unavailable?: boolean;
}) {
  const count = (value: unknown) =>
    typeof value === "number" && Number.isFinite(value) && value >= 0
      ? value
      : null;
  const finished = count(search ? data.semantic : data.prepared),
    waiting = count(data.pending),
    total = finished !== null && waiting !== null ? finished + waiting : null;
  const phase = String(data.phase || ""),
    working = ["summarizing", "indexing", "preparing"].includes(phase);
  if (loading)
    return (
      <section
        className="processing-status processing-loading"
        role="status"
        aria-busy="true"
      >
        <span>{t("Loading library status…")}</span>
        <span className="processing-skeleton" />
        <span className="processing-skeleton short" />
      </section>
    );
  if (unavailable)
    return (
      <p className="processing-unavailable" role="status">
        {t("Library status could not be verified. Try again above.")}
      </p>
    );
  return (
    <section className="processing-status" aria-label={t("Current status")}>
      <div
        className={"processing-heading " + (phase === "ready" ? "ready" : "")}
      >
        {working ? (
          <LoaderCircle size={17} className="spin" />
        ) : phase === "ready" ? (
          <Check size={17} />
        ) : (
          <Pause size={16} />
        )}
        <strong>{processingLabel(phase)}</strong>
        {total !== null && total > 0 && (
          <span>
            {finished} / {total}
          </span>
        )}
      </div>
      {total !== null && total > 0 && (
        <progress
          value={finished!}
          max={total}
          aria-label={t(
            search ? "Articles searchable by meaning" : "Articles summarized",
          )}
        />
      )}
      <div className="processing-counts">
        <span>
          <strong>{finished ?? "—"}</strong>
          {t(search ? "Articles searchable by meaning" : "Articles summarized")}
        </span>
        <span>
          <strong>{waiting ?? "—"}</strong>
          {t("Articles waiting")}
        </span>
        {search ? (
          <span>
            <strong>{count(data.indexed) ?? "—"}</strong>
            {t("Articles searchable by text")}
          </span>
        ) : (
          <span>
            <strong>{count(data.requests_today) ?? "—"}</strong>
            {t("Requests sent today")}
          </span>
        )}
      </div>
      {data.current_title && (
        <p dir="auto">
          {t("Working on")}: {data.current_title}
        </p>
      )}
    </section>
  );
}
