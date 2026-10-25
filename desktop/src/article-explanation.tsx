import { useEffect, useState } from "react";
import { BookOpen, LoaderCircle } from "lucide-react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { t } from "./locale";
import { invoke } from "@tauri-apps/api/core";

// Mounted by article ID; late responses cannot replace another article's TL;DR.
export function ArticleExplanation({
  article,
  configured = true,
  onConfigure,
}: {
  article: RecordData;
  configured?: boolean;
  onConfigure?: () => void;
}) {
  const [result, setResult] = useState<RecordData>(
    article.prepared_summary || {},
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setResult(article.prepared_summary || {});
  }, [article.prepared_summary]);
  useEffect(() => {
    if (result.summary || busy || !configured) return;
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
  }, [article.id, result.summary, busy, configured]);
  async function generate() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await call("news.summarize", { article_id: article.id, consent: true }),
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
      </header>
      {result.summary ? (
        <>
          <Markdown text={result.summary} />
          {!!result.quotes?.length && (
            <div className="tldr-quotes">
              <h3>{t("Source quotations")}</h3>
              {result.quotes.map((quote: RecordData, index: number) => (
                <figure key={index}>
                  <blockquote dir="auto">{quote.text}</blockquote>
                  <figcaption>
                    <a href={quote.url}>
                      {quote.source_id} · {new URL(quote.url).hostname}
                    </a>
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
                    <a href={source.url}>
                      <bdi>
                        {source.id} · {new URL(source.url).hostname}
                      </bdi>
                    </a>
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
          <p className="muted">
            {t(
              configured
                ? "Prepared in the background for new and older articles. Saved summaries appear here immediately."
                : "Choose a summary model to prepare TL;DR automatically.",
            )}
          </p>
          {configured ? (
            <button disabled={busy} onClick={() => void generate()}>
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
