import { useEffect, useState } from "react";
import { BookOpen, LoaderCircle, RotateCcw } from "lucide-react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { t, useLocale } from "./locale";
import { PreviewLink } from "./link-preview";
import { invoke } from "@tauri-apps/api/core";
import { processingLabel } from "./processing-status";

// Mounted by article ID; late responses cannot replace another article's TL;DR.
export function ArticleExplanation({
  article,
  configured = true,
  phase = "",
  onConfigure,
}: {
  article: RecordData;
  configured?: boolean;
  phase?: string;
  onConfigure?: () => void;
}) {
  const locale = useLocale();
  const [result, setResult] = useState<RecordData>(
    article.prepared_summary || {},
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const blocked = [
    "paused",
    "stopping",
    "memory_pressure",
    "waiting_charger",
    "cooling",
    "low_power",
    "waiting_device",
  ].includes(phase);
  useEffect(() => {
    setResult(article.prepared_summary || {});
  }, [article.prepared_summary]);
  useEffect(() => {
    if ((result.summary && !result.needs_refresh) || busy || !configured)
      return;
    let live = true,
      polling = false;
    const timer = setInterval(async () => {
      if (polling || document.visibilityState === "hidden") return;
      polling = true;
      try {
        const next = await call("news.preview", { article_id: article.id });
        if (live && next.prepared_summary?.summary)
          setResult(next.prepared_summary);
      } catch {
        /* A transient refresh failure must not interrupt reading. */
      } finally {
        polling = false;
      }
    }, 10000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [article.id, result.summary, result.needs_refresh, busy, configured]);
  async function generate(regenerate = false) {
    setBusy(true);
    setError("");
    try {
      setResult(
        await call("news.summarize", {
          article_id: article.id,
          consent: true,
          ...(regenerate ? { regenerate: true } : {}),
        }),
      );
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="article-tldr"
      aria-label={t("TL;DR")}
      aria-busy={busy}
      onClick={(event) => {
        if (event.defaultPrevented) return;
        const link = (event.target as HTMLElement).closest("a");
        if (link) {
          event.preventDefault();
          void invoke("open_external", { address: link.href }).catch(() => {});
        }
      }}
    >
      <header>
        <BookOpen size={17} aria-hidden="true" />
        <h2>{t("TL;DR")}</h2>
        {result.summary && (
          <button
            className="tldr-regenerate"
            disabled={busy || blocked || !configured}
            title={
              blocked && configured
                ? `${t("Your saved summary is ready.")} ${processingLabel(phase)}`
                : t(
                    "Generate again with your current summary model. Your saved summary stays until the new one is ready.",
                  )
            }
            onClick={() => void generate(true)}
          >
            {busy ? (
              <LoaderCircle size={14} className="spin" aria-hidden="true" />
            ) : (
              <RotateCcw size={14} aria-hidden="true" />
            )}
            {t(busy ? "Regenerating…" : "Regenerate summary")}
          </button>
        )}
      </header>
      {busy && result.summary && (
        <p className="tldr-regeneration-status" role="status">
          {t(
            "Preparing a new summary with your current model. Your saved summary remains available.",
          )}
        </p>
      )}
      {result.summary ? (
        <>
          <p className="tldr-provenance">
            <span>{t("Saved on this Mac")}</span>
            {result.model ? (
              <span>
                {t("Summarized by")} <bdi>{result.model}</bdi>
              </span>
            ) : (
              <span>{t("Model not recorded")}</span>
            )}
            {result.generated_at &&
              !Number.isNaN(Date.parse(result.generated_at)) && (
                <time dateTime={result.generated_at}>
                  {new Intl.DateTimeFormat(locale, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }).format(new Date(result.generated_at))}
                </time>
              )}
          </p>
          <Markdown text={result.summary} />
          {!!result.quotes?.length && (
            <div className="tldr-quotes">
              <h3>{t("Source quotations")}</h3>
              {result.quotes.map((quote: RecordData, index: number) => (
                <figure key={index}>
                  <blockquote dir="auto">{quote.text}</blockquote>
                  <figcaption>
                    <PreviewLink href={quote.url}>
                      {quote.source_id} · {new URL(quote.url).hostname}
                    </PreviewLink>
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
          {!!result.sources?.length && (
            <div className="tldr-sources">
              <h3>{t("Sources checked")}</h3>
              <ul>
                {result.sources.map((source: RecordData) => (
                  <li key={source.id}>
                    <PreviewLink href={source.url}>
                      <bdi>
                        {source.id} · {new URL(source.url).hostname}
                      </bdi>
                    </PreviewLink>
                    <span>
                      {t(
                        source.status === "read"
                          ? source.truncated
                            ? "Excerpt read"
                            : "Read"
                          : "Could not read",
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {(result.coverage?.limited ||
            result.coverage?.unvisited_links > 0) && (
            <p className="muted tldr-coverage">
              {t(
                "Coverage is limited to the text and sources shown. Some content or additional links were not included.",
              )}
            </p>
          )}
        </>
      ) : (
        <div className="tldr-empty">
          {configured && blocked && (
            <p role="status">{processingLabel(phase)}</p>
          )}
          <p className="muted">
            {t(
              configured
                ? "Prepared in the background for new and older articles. Saved summaries appear here immediately."
                : "Choose a summary model to prepare TL;DR automatically.",
            )}
          </p>
          {configured ? (
            <button disabled={busy || blocked} onClick={() => void generate()}>
              {busy && (
                <LoaderCircle size={16} className="spin" aria-hidden="true" />
              )}
              {t(busy ? "Preparing TL;DR…" : "Prepare this summary")}
            </button>
          ) : (
            onConfigure && (
              <button onClick={onConfigure}>{t("Choose a model")}</button>
            )
          )}
        </div>
      )}
      {error && (
        <p className="notice" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
