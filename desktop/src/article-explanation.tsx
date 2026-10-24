import { useEffect, useState } from "react";
import { BookOpen, ChevronDown, LoaderCircle } from "lucide-react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { t } from "./locale";

// Mounted by article ID: late results cannot replace another article's explanation.
export function ArticleExplanation({
  article,
  configured = true,
  onConfigure,
}: {
  article: RecordData;
  configured?: boolean;
  onConfigure?: () => void;
}) {
  const [summary, setSummary] = useState(
    article.prepared_summary?.summary || "",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setSummary(article.prepared_summary?.summary || "");
  }, [article.prepared_summary?.summary]);
  useEffect(() => {
    if (summary || busy) return;
    let live = true,
      polling = false;
    const timer = setInterval(async () => {
      if (polling || document.visibilityState === "hidden") return;
      polling = true;
      try {
        const result = await call("news.preview", { article_id: article.id });
        if (live && result.prepared_summary?.summary)
          setSummary(result.prepared_summary.summary);
      } catch {
        /* Temporary failures must not interrupt reading. */
      } finally {
        polling = false;
      }
    }, 10000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [article.id, summary, busy]);
  async function generate() {
    setBusy(true);
    setError("");
    try {
      const result = await call("news.summarize", {
        article_id: article.id,
        consent: true,
      });
      setSummary(result.summary);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="article-explanation">
      <summary>
        <BookOpen size={15} aria-hidden="true" />
        <span>{t("Article explanation")}</span>
        <ChevronDown
          size={14}
          className="disclosure-chevron"
          aria-hidden="true"
        />
      </summary>
      {summary ? (
        <Markdown text={summary} />
      ) : (
        <>
          <p className="muted">
            {t(
              configured
                ? "No explanation yet. Generate one using your selected summary model."
                : "Choose an explanation model to explain this article.",
            )}
          </p>
          {!configured ? (
            onConfigure && (
              <button onClick={onConfigure}>{t("Choose a model")}</button>
            )
          ) : (
            <button disabled={busy} onClick={() => void generate()}>
              {busy && <LoaderCircle size={16} className="spin" />}
              {t(
                busy
                  ? "Preparing explanation…"
                  : "Generate explanation with my model",
              )}
            </button>
          )}
        </>
      )}
      {error && (
        <p className="notice" role="alert">
          {error}
        </p>
      )}
    </details>
  );
}
