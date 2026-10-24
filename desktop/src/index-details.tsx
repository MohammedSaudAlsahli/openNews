import { useEffect, useState } from "react";
import { ChevronDown, LoaderCircle, Search } from "lucide-react";
import { call, type RecordData } from "./engine";
import { getLocale, t } from "./locale";
import { settingsMessage } from "./settings-message";

export function IndexDetails() {
  const [open, setOpen] = useState(false),
    [rows, setRows] = useState<RecordData[]>([]),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!open) return;
    let live = true;
    setLoading(true);
    setError("");
    void call("news.search.inspect")
      .then((result) => {
        if (live) setRows(result.articles || []);
      })
      .catch((reason) => {
        if (live) setError(settingsMessage(String(reason)));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [open, attempt]);
  const number = (value: unknown) =>
    typeof value === "number" ? value.toLocaleString(getLocale()) : "—";
  return (
    <details
      className="index-details"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        <Search size={16} />
        <span>{t("Index details")}</span>
        <ChevronDown size={15} className="disclosure-chevron" />
      </summary>
      <div aria-busy={loading}>
        {loading && (
          <p className="inline-loading" role="status">
            <LoaderCircle size={15} className="spin" />
            {t("Loading indexed articles…")}
          </p>
        )}
        {error && (
          <div className="context-feedback" role="alert">
            <p>{error}</p>
            <button onClick={() => setAttempt((value) => value + 1)}>
              {t("Retry")}
            </button>
          </div>
        )}
        {!loading && !error && !rows.length && (
          <p className="muted">{t("No articles have been indexed yet.")}</p>
        )}
        {rows.map((row) => (
          <div className="indexed-article" key={row.id}>
            <strong>
              <bdi>{row.title}</bdi>
            </strong>
            <dl>
              <div>
                <dt>{t("Text segments")}</dt>
                <dd>{number(row.segments)}</dd>
              </div>
              <div>
                <dt>{t("Embedded segments")}</dt>
                <dd>{number(row.embedded)}</dd>
              </div>
            </dl>
          </div>
        ))}
      </div>
    </details>
  );
}
