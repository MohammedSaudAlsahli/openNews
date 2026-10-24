import { useRef, useState } from "react";
import { Activity, Check, LoaderCircle } from "lucide-react";
import { active, call, type RecordData } from "./engine";
import { RelativeTime } from "./relative-time";
import { t } from "./locale";

const tasks: Record<string, string> = {
  "chat.send": "Conversation response",
  "draft.generate": "Writing a draft",
  "analysis.run": "Analyzing writing",
};
const states: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};
export function ActivityPage({
  jobs,
  refresh,
  onReport,
}: {
  jobs: RecordData[];
  refresh: () => Promise<void>;
  onReport: (code: string) => void;
}) {
  const [pending, setPending] = useState<string[]>([]),
    [requested, setRequested] = useState<string[]>([]),
    [notice, setNotice] = useState(""),
    [error, setError] = useState("");
  const requests = useRef(new Set<string>());
  async function stop(id: string) {
    if (requests.current.has(id)) return;
    requests.current.add(id);
    setPending((value) => [...value, id]);
    setError("");
    setNotice("");
    try {
      await call("jobs.cancel", { job_id: id });
      setRequested((old) => [...old, id]);
      await refresh().catch(() =>
        setNotice(
          t("Stop requested. The task list will refresh automatically."),
        ),
      );
    } catch (reason) {
      setError(String(reason).replace(/^Error:\s*/, ""));
    } finally {
      requests.current.delete(id);
      setPending((value) => value.filter((key) => key !== id));
    }
  }
  return (
    <div className="page activity-page">
      <div className="page-title">
        <div>
          <h1>{t("Background activity")}</h1>
          <p className="page-description">
            {t(
              "Work continues as you move between conversations and articles.",
            )}
          </p>
        </div>
      </div>
      {error && (
        <div className="settings-feedback" role="alert">
          <span>{error}</span>
          <button onClick={() => onReport("JOB_CANCEL_FAILED")}>
            {t("Report problem")}
          </button>
        </div>
      )}
      {notice && (
        <p className="settings-feedback" role="status">
          {notice}
        </p>
      )}
      {!jobs.length ? (
        <div className="empty">
          <Check size={28} />
          <h2>{t("All quiet for now")}</h2>
          <p>{t("Searches, reading and responses will appear here.")}</p>
        </div>
      ) : (
        <div
          className="activity-list"
          role="list"
          aria-label={t("Background activity")}
        >
          {jobs.map((job) => (
            <div key={job.id} role="listitem">
              {active(job.state) ? (
                <LoaderCircle size={17} className="spin" />
              ) : (
                <Activity size={17} />
              )}
              <span>
                <strong>{t(tasks[job.type] || "Background task")}</strong>
                <small>
                  {job.updated_at ? (
                    <RelativeTime value={job.updated_at} now={Date.now()} />
                  ) : (
                    "—"
                  )}
                  {job.error_code && (
                    <>
                      {" "}
                      · <span dir="ltr">{job.error_code}</span>
                    </>
                  )}
                </small>
              </span>
              <span className={"status " + job.state}>
                {t(states[job.state] || job.state)}
              </span>
              {active(job.state) && (
                <button
                  disabled={
                    pending.includes(job.id) || requested.includes(job.id)
                  }
                  onClick={() => void stop(job.id)}
                >
                  {t(
                    pending.includes(job.id)
                      ? "Stopping…"
                      : requested.includes(job.id)
                        ? "Stop requested"
                        : "Stop",
                  )}
                </button>
              )}
              {job.state === "failed" && (
                <button
                  onClick={() => onReport(job.error_code || "JOB_FAILED")}
                >
                  {t("Report problem")}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
