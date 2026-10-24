import { useEffect, useState, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  issueUrl,
  articleIncidentText,
  type ArticleIncident,
} from "./support-report";
import { t } from "./locale";
import { LoaderCircle, X } from "lucide-react";
export function SupportPanel({
  onClose,
  incidentCode = "",
  article,
}: {
  onClose: () => void;
  onError: (error: string) => void;
  incidentCode?: string;
  article?: ArticleIncident;
}) {
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(true),
    [action, setAction] = useState("");
  const busy = Boolean(action);
  const [error, setError] = useState(""),
    [saved, setSaved] = useState("");
  const [includeArticle, setIncludeArticle] = useState(true),
    [attempt, setAttempt] = useState(0);
  const dialog = useRef<HTMLDialogElement>(null),
    lock = useRef(false);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError("");
    void invoke<string>("diagnostics_report")
      .then((value) => {
        if (live) setReport(value);
      })
      .catch((reason) => {
        if (live) setError(String(reason).replace(/^Error:\s*/, ""));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [attempt]);
  const included = article && includeArticle ? article : undefined;
  const content =
    (included ? articleIncidentText(included) + "\n" : "") +
    (incidentCode ? `Incident: ${incidentCode}\n` : "") +
    report;
  async function perform(action: "save" | "github") {
    if (lock.current || loading || !report) return;
    lock.current = true;
    setAction(action);
    setError("");
    try {
      if (action === "save")
        setSaved(await invoke<string>("export_diagnostics", { content }));
      else
        await invoke("open_external", {
          address: issueUrl(report, incidentCode, included),
        });
    } catch (reason) {
      setError(String(reason).replace(/^Error:\s*/, ""));
    } finally {
      lock.current = false;
      setAction("");
    }
  }
  return (
    <dialog
      ref={dialog}
      className="support-dialog"
      aria-labelledby="support-heading"
      onCancel={(event) => {
        if (busy) event.preventDefault();
        else onClose();
      }}
    >
      <div className="page-title">
        <h2 id="support-heading">{t("Help & diagnostics")}</h2>
        <button
          className="icon-button"
          autoFocus
          disabled={busy}
          onClick={onClose}
          aria-label={t("Close")}
        >
          <X size={18} />
        </button>
      </div>
      <p>
        {t(
          "Technical events stay on this Mac. Reports exclude messages, article contents, account names and credentials.",
        )}
      </p>
      {article && (
        <label className="report-article-option">
          <input
            type="checkbox"
            disabled={busy}
            checked={includeArticle}
            onChange={(event) => {
              setIncludeArticle(event.target.checked);
              setSaved("");
            }}
          />
          {t(
            "Include article title, public URL and loading details in this report",
          )}
        </label>
      )}
      {loading && (
        <p className="inline-loading" role="status">
          <LoaderCircle className="spin" size={15} />
          {t("Preparing report…")}
        </p>
      )}
      {error && (
        <div className="settings-feedback" role="alert">
          <span>{error}</span>
          {!report && (
            <button onClick={() => setAttempt((value) => value + 1)}>
              {t("Try again")}
            </button>
          )}
        </div>
      )}
      {report && (
        <details>
          <summary>{t("Review diagnostic report")}</summary>
          <pre dir="ltr">{content}</pre>
        </details>
      )}
      <div className="reader-actions">
        <button
          disabled={loading || busy || !report}
          onClick={() => void perform("save")}
        >
          {action === "save" && <LoaderCircle className="spin" size={15} />}
          {t(action === "save" ? "Saving report…" : "Save diagnostic report")}
        </button>
        <button
          disabled={loading || busy || !report}
          className="primary"
          onClick={() => void perform("github")}
        >
          {action === "github" && <LoaderCircle className="spin" size={15} />}{" "}
          {t(
            action === "github"
              ? "Opening GitHub…"
              : "Report a problem on GitHub",
          )}
        </button>
      </div>
      {saved && (
        <p className="saved-report" role="status">
          {t("Report saved")}: <span dir="ltr">{saved}</span>
        </p>
      )}
      <small>
        {t("GitHub opens a draft report. Review it and submit it yourself.")}
      </small>
      <details className="support-shortcuts">
        <summary>{t("Keyboard shortcuts")}</summary>
        <div className="shortcut-list">
          <span>{t("Settings")}</span>
          <kbd>⌘ ,</kbd>
          <span>{t("New conversation")}</span>
          <kbd>⌘ N</kbd>
          <span>{t("Toggle sidebar")}</span>
          <kbd>⌘ ⇧ B</kbd>
          <span>{t("Commands / articles")}</span>
          <kbd>/ · @</kbd>
          <span>{t("New line")}</span>
          <kbd>⇧ Enter</kbd>
        </div>
      </details>
    </dialog>
  );
}
