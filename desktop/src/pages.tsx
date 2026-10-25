import { RefreshInterval } from "./refresh-interval";
import { RelativeTime } from "./relative-time";
import { SupportPanel } from "./support-panel";
import type { ArticleIncident } from "./support-report";
import { readerMarkdown, readerLayout } from "./reader-format";
import { ArticleSite } from "./article-site";
import { ArticleExplanation } from "./article-explanation";
import { ReaderLinkPreviews } from "./link-preview";
import { ArticleHistory } from "./article-history";
import { summaryModel } from "./summary-model";
import * as Popover from "@radix-ui/react-popover";
import { t, getLocale } from "./locale";
import { useEffect, useState, useRef } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Bookmark,
  Search,
  X,
  Plus,
  RefreshCw,
  LoaderCircle,
  Rss,
  Check,
  BookOpen,
  Type,
  Flag,
  ChevronRight,
} from "lucide-react";
import { call, articleExcerpt, type RecordData } from "./engine";
import { Markdown } from "./components";
import { invoke } from "@tauri-apps/api/core";

export function ArticleImage({
  article,
  id,
  cover = false,
}: {
  article: string;
  id?: string;
  cover?: boolean;
}) {
  const [src, setSrc] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [failed, setFailed] = useState(false);
  const placeholder = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let live = true;
    setSrc("");
    setExpanded(false);
    setFailed(false);
    if (!id) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        observer.disconnect();
        // The engine keeps the disk cache; only visible images enter webview memory.
        invoke<string>("article_image", { articleId: article, imageId: id })
          .then((value) => {
            if (live) {
              if (value) setSrc(value);
              else setFailed(true);
            }
          })
          .catch(() => {
            if (live) setFailed(true);
          });
      },
      { rootMargin: "300px" },
    );
    if (placeholder.current) observer.observe(placeholder.current);
    return () => {
      live = false;
      observer.disconnect();
    };
  }, [article, id]);
  return (
    <div
      ref={placeholder}
      className={cover ? "cover-frame" : ""}
      hidden={failed && !cover}
    >
      {!id || failed ? (
        <div className="cover-fallback">
          <BookOpen size={28} />
          <span>{t("No cover available")}</span>
        </div>
      ) : src ? (
        cover ? (
          <img
            className="article-image"
            src={src}
            alt=""
            loading="lazy"
            onError={() => setFailed(true)}
          />
        ) : (
          <button
            className={`reader-image-toggle${expanded ? " expanded" : ""}`}
            aria-expanded={expanded}
            aria-label={
              getLocale() === "ar"
                ? expanded
                  ? "تصغير الصورة"
                  : "تكبير الصورة"
                : expanded
                  ? "Reduce image"
                  : "Enlarge image"
            }
            onClick={() => setExpanded(!expanded)}
          >
            <img
              className="article-image"
              src={src}
              alt=""
              loading="lazy"
              onError={() => setFailed(true)}
            />
          </button>
        )
      ) : (
        <div className="image-placeholder" aria-hidden="true" />
      )}
    </div>
  );
}

type Props = { onError: (e: string) => void };
export function Articles({
  onError,
  snapshot,
  onDiscuss,
  onConfigureExplanations,
  onExploreSources,
  libraryRequest = 0,
}: Props & {
  snapshot: RecordData;
  onDiscuss?: (article: RecordData) => void;
  onConfigureExplanations?: () => void;
  onExploreSources?: () => void;
  libraryRequest?: number;
}) {
  const [articles, setArticles] = useState<RecordData[]>([]),
    [query, setQuery] = useState(""),
    [scope, setScope] = useState("all"),
    [source, setSource] = useState(""),
    [order, setOrder] = useState("newest"),
    [days, setDays] = useState(0),
    [digestStatus, setDigestStatus] = useState<RecordData>(),
    [fontSize, setFontSize] = useState(() =>
      Math.min(
        24,
        Math.max(14, Number(localStorage.getItem("reader-font-size")) || 17),
      ),
    ),
    [more, setMore] = useState(false),
    [busy, setBusy] = useState(true),
    [selected, setSelected] = useState<RecordData>(),
    [siteMode, setSiteMode] = useState(false),
    [reading, setReading] = useState(false),
    [related, setRelated] = useState<RecordData[]>([]),
    [states, setStates] = useState<RecordData>({});
  const [clock, setClock] = useState(Date.now);
  const [listError, setListError] = useState("");
  const appendRequest = useRef<number | null>(null);
  const [articleReport, setArticleReport] = useState<ArticleIncident>();
  const [bookmarking, setBookmarking] = useState<string[]>([]);
  const bookmarkRequests = useRef(new Set<string>());
  const [openStage, setOpenStage] = useState("idle");
  const openTiming = useRef({
    started: 0,
    finished: 0,
    stage: "idle",
    errorCode: "",
  });
  function phase(stage: string) {
    openTiming.current.stage = stage;
    setOpenStage(stage);
  }
  function reportArticle() {
    if (!selected) return;
    const timing = openTiming.current;
    setArticleReport({
      title: selected.title || "",
      url: selected.url || "",
      source: selected.source_title || "",
      articleId: selected.id,
      stage: timing.stage,
      elapsedMs: (timing.finished || performance.now()) - timing.started,
      bodyStatus: selected.body_status || "unknown",
      errorCode: timing.errorCode,
    });
  }
  const request = useRef(0),
    selection = useRef(0);
  useEffect(() => {
    let live = true,
      pending = false;
    async function status(initial = false) {
      if (pending || (!initial && document.visibilityState === "hidden")) return;
      pending = true;
      try {
        const result = await call("news.digest.status");
        if (live) setDigestStatus(result);
      } catch {
        /* The reader remains usable if background status is unavailable. */
      } finally {
        pending = false;
      }
    }
    void status(true);
    const timer = setInterval(() => void status(), 15000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, []);
  async function load(append = false) {
    if (append && appendRequest.current !== null) return;
    const token = ++request.current;
    appendRequest.current = append ? token : null;
    setBusy(true);
    setListError("");
    try {
      const r = await call("news.list", {
        query: query.slice(0, 200),
        scope,
        source_id: source,
        order,
        days,
        limit: 30,
        offset: append ? articles.length : 0,
      });
      if (token !== request.current) return;
      setArticles((old) =>
        append
          ? [
              ...old,
              ...r.articles.filter(
                (a: RecordData) => !old.some((x) => x.id === a.id),
              ),
            ]
          : r.articles,
      );
      setMore(r.has_more);
      void call("news.summary.states", {
        ids: r.articles.map((a: RecordData) => a.id),
      })
        .then((s) => {
          if (token === request.current)
            setStates((old) => ({ ...old, ...s.states }));
        })
        .catch(() => {});
    } catch (e) {
      if (token === request.current)
        setListError(String(e).replace(/^Error:\s*/, ""));
    } finally {
      if (appendRequest.current === token) appendRequest.current = null;
      if (token === request.current) setBusy(false);
    }
  }
  useEffect(() => {
    ++request.current;
    const timer = setTimeout(() => void load(), 250);
    return () => {
      clearTimeout(timer);
      ++request.current;
    };
  }, [query, scope, source, order, days]);
  function clearFilters() {
    setQuery("");
    setScope("all");
    setSource("");
    setOrder("newest");
    setDays(0);
  }
  const previousLibraryRequest = useRef(libraryRequest);
  useEffect(() => {
    if (previousLibraryRequest.current === libraryRequest) return;
    previousLibraryRequest.current = libraryRequest;
    ++selection.current;
    setSelected(undefined);
    setReading(false);
    setSiteMode(false);
    setRelated([]);
    setArticleReport(undefined);
    void load();
  }, [libraryRequest]);
  useEffect(() => {
    let live = true,
      pending = false;
    async function refreshVisible() {
      if (document.visibilityState === "hidden") return;
      setClock(Date.now());
      if (selected || busy || pending) return;
      pending = true;
      const token = request.current;
      try {
        const count = Math.max(30, articles.length);
        const pages = await Promise.all(
          Array.from({ length: Math.ceil(count / 100) }, (_, index) =>
            call("news.list", {
              query,
              scope,
              source_id: source,
              order,
              days,
              limit: Math.min(100, count - index * 100),
              offset: index * 100,
            }),
          ),
        );
        if (live && token === request.current) {
          setListError("");
          setArticles(pages.flatMap((page) => page.articles));
          setMore(pages[pages.length - 1].has_more);
        }
      } catch {
        /* Retain the displayed cache during temporary engine unavailability. */
      } finally {
        pending = false;
      }
    }
    const timer = setInterval(() => void refreshVisible(), 60000);
    const visible = () => {
      if (document.visibilityState === "visible") void refreshVisible();
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      live = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [query, scope, source, order, days, selected?.id, busy, articles.length]);
  useEffect(
    () => () => {
      ++selection.current;
    },
    [],
  );
  useEffect(() => {
    if (!selected || selected.body_status === "full" || reading) return;
    const id = selected.id;
    let live = true,
      busy = false,
      attempts = 0;
    const timer = setInterval(async () => {
      if (busy || ++attempts > 20) return;
      busy = true;
      try {
        const result = await call("news.preview", { article_id: id });
        if (live && result.body_status === "full")
          setSelected((old) => (old?.id === id ? { ...old, ...result } : old));
      } catch {
      } finally {
        busy = false;
      }
    }, 15000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [selected?.id, selected?.body_status, reading]);
  async function open(id: string, refresh = false) {
    const token = ++selection.current;
    openTiming.current = {
      started: performance.now(),
      finished: 0,
      stage: "local_cache",
      errorCode: "",
    };
    phase("local_cache");
    // Paint the reader immediately from the card; never wait on IPC/network to navigate.
    const card =
      articles.find((a) => a.id === id) ||
      related.find((a) => a.id === id) ||
      (selected?.id === id ? selected : undefined);
    setSelected(card || { id, title: t("Loading…"), body_status: "loading" });
    setReading(true);
    setSiteMode(false);
    setRelated([]);
    try {
      const article = await call("news.article", { article_id: id });
      if (token !== selection.current) return;
      setSelected(article);
      // Paint saved content first; repair an obsolete extraction in the background.
      if (
        refresh ||
        article.reader_upgrade_required ||
        !["full", "media_summary"].includes(article.body_status)
      ) {
        phase("fetching_text");
        let result = await call("news.reader", { article_id: id, refresh });
        if (token !== selection.current) return;
        setSelected({ ...article, ...result });
        if (!["full", "media_summary"].includes(result.body_status)) {
          phase("website_recovery");
          try {
            result = await invoke<RecordData>("recover_article", {
              articleId: id,
            });
          } catch (error) {
            openTiming.current.errorCode =
              String(error).match(/\b[A-Z][A-Z_]{3,50}\b/)?.[0] ||
              "RECOVERY_FAILED";
          }
          if (token !== selection.current) return;
          setSelected({ ...article, ...result });
        }
        phase(
          ["full", "media_summary"].includes(result.body_status)
            ? "ready"
            : "text_unavailable",
        );
      } else phase("cached_ready");
      openTiming.current.finished = performance.now();
      setReading(false);
      // Related stories must not keep the primary article in a loading state.
      void call("news.related", { article_id: id })
        .then((result) => {
          if (token === selection.current) setRelated(result.articles || []);
        })
        .catch(() => {});
    } catch (error) {
      if (token === selection.current) {
        openTiming.current.errorCode =
          String(error).match(/\b[A-Z][A-Z_]{3,50}\b/)?.[0] ||
          "ARTICLE_OPEN_FAILED";
        phase("failed");
        onError(String(error));
      }
    } finally {
      if (token === selection.current) {
        openTiming.current.finished = performance.now();
        setReading(false);
      }
    }
  }
  async function bookmark(a: RecordData) {
    if (bookmarkRequests.current.has(a.id)) return;
    bookmarkRequests.current.add(a.id);
    setBookmarking((old) => [...old, a.id]);
    const saved = !a.is_bookmarked;
    try {
      await call("news.bookmark", {
        article_id: a.id,
        saved,
      });
      setArticles((old) =>
        old.map((x) => (x.id === a.id ? { ...x, is_bookmarked: saved } : x)),
      );
      setSelected((current) =>
        current?.id === a.id ? { ...current, is_bookmarked: saved } : current,
      );
    } catch (e) {
      onError(String(e));
    } finally {
      bookmarkRequests.current.delete(a.id);
      setBookmarking((old) => old.filter((id) => id !== a.id));
    }
  }
  const layout = selected
    ? readerLayout(selected.reader?.blocks || [], selected.cover_image_id)
    : undefined;
  if (selected)
    return (
      <div
        className={`reader ${siteMode ? "reader-site-mode" : ""}`}
        key={selected.id}
      >
        {articleReport && (
          <SupportPanel
            incidentCode="ARTICLE_READING_PROBLEM"
            article={articleReport}
            onClose={() => setArticleReport(undefined)}
            onError={onError}
          />
        )}
        <div className="reader-toolbar">
          <button
            onClick={() => {
              ++selection.current;
              setSelected(undefined);
              setReading(false);
              void load();
            }}
          >
            <ArrowLeft className="back-arrow" size={16} />
            {t("Articles")}
          </button>
          <div className="segments" role="group" aria-label={t("Article view")}>
            <button
              aria-pressed={!siteMode}
              className={!siteMode ? "selected" : ""}
              onClick={() => setSiteMode(false)}
            >
              {t("Reading")}
            </button>
            <button
              aria-pressed={siteMode}
              className={siteMode ? "selected" : ""}
              onClick={() => setSiteMode(true)}
            >
              {t("Original website")}
            </button>
          </div>
          <span />
          {onDiscuss && (
            <button onClick={() => onDiscuss(selected)}>
              {t("Discuss article")}
            </button>
          )}
          <button
            title={t("Open in browser")}
            aria-label={t("Open in browser")}
            className="icon-button"
            onClick={() =>
              void invoke("open_external", { address: selected.url }).catch(
                (e) => onError(String(e)),
              )
            }
          >
            <ArrowUpRight size={17} />
          </button>
          <Popover.Root>
            <Popover.Trigger
              className="icon-button"
              title={t("Reading appearance")}
              disabled={siteMode}
              aria-label={t("Reading appearance")}
            >
              <Type size={18} />
            </Popover.Trigger>
            <Popover.Portal>
              <Popover.Content
                className="floating-panel reading-appearance"
                sideOffset={8}
                collisionPadding={16}
              >
                <h3>{t("Text size")}</h3>
                <div className="reading-size-control">
                  <button
                    aria-label={t("Smaller text")}
                    disabled={fontSize <= 14}
                    onClick={() => {
                      setFontSize(fontSize - 1);
                      localStorage.setItem(
                        "reader-font-size",
                        String(fontSize - 1),
                      );
                    }}
                  >
                    A−
                  </button>
                  <output aria-label={t("Text size")} aria-live="polite">
                    {fontSize} px
                  </output>
                  <button
                    aria-label={t("Larger text")}
                    disabled={fontSize >= 24}
                    onClick={() => {
                      setFontSize(fontSize + 1);
                      localStorage.setItem(
                        "reader-font-size",
                        String(fontSize + 1),
                      );
                    }}
                  >
                    A+
                  </button>
                </div>
              </Popover.Content>
            </Popover.Portal>
          </Popover.Root>
          {reading && <LoaderCircle className="spin" size={16} />}
          <button
            title={t("Refresh article")}
            aria-label={t("Refresh article")}
            className="icon-button"
            disabled={reading}
            onClick={() => void open(selected.id, true)}
          >
            <RefreshCw size={17} />
          </button>
          <button
            className="icon-button"
            title={t("Report this article")}
            aria-label={t("Report this article")}
            onClick={reportArticle}
          >
            <Flag size={16} />
          </button>
          <button
            title={t("Bookmark")}
            aria-label={t("Bookmark")}
            className="icon-button"
            aria-pressed={!!selected.is_bookmarked}
            disabled={bookmarking.includes(selected.id)}
            onClick={() => void bookmark(selected)}
          >
            <Bookmark
              size={17}
              fill={selected.is_bookmarked ? "currentColor" : "none"}
            />
          </button>
        </div>
        {siteMode && (
          <ArticleSite
            key={selected.id}
            address={selected.url}
            onError={onError}
          />
        )}
        <ReaderLinkPreviews articleId={selected.id}>
          <div
            hidden={siteMode}
            className="reader-content"
            style={{ "--reading-size": `${fontSize}px` } as React.CSSProperties}
          >
            <header
              className={`article-heading${layout?.cover ? " has-cover" : ""}`}
            >
              <div className="article-heading-copy">
                <div className="reader-source">
                  {layout?.logo && (
                    <div className="reader-source-logo">
                      <ArticleImage article={selected.id} id={layout.logo.id} />
                    </div>
                  )}
                  <span dir="auto">{selected.source_title}</span>
                  <span className="muted">
                    · <RelativeTime value={selected.published_at} now={clock} />
                  </span>
                </div>
                <h1 dir="auto">{selected.title}</h1>
              </div>
              {layout?.cover && (
                <figure className="reader-cover">
                  <ArticleImage article={selected.id} id={layout.cover.id} />
                  <figcaption>
                    {getLocale() === "ar" ? "غلاف المقالة" : "Article cover"}
                  </figcaption>
                </figure>
              )}
            </header>
            {selected.body_status !== "full" && (
              <p className="notice">
                {reading
                  ? t(
                      openStage === "local_cache"
                        ? "Opening saved article…"
                        : openStage === "website_recovery"
                          ? "Retrieving text from the original website…"
                          : "Retrieving article text…",
                    )
                  : t(
                      "The full article has not been retrieved yet. You can retry or read the original.",
                    )}
              </p>
            )}
            {selected.body_status !== "full" && (
              <div className="reader-actions">
                <button
                  disabled={reading}
                  onClick={() => void open(selected.id, true)}
                >
                  <RefreshCw size={15} />
                  {t("Retry full article")}
                </button>
                <button onClick={() => setSiteMode(true)}>
                  {t("Read original")}
                  <ArrowUpRight size={15} />
                </button>
              </div>
            )}
            {(selected.body_status === "full" ||
              selected.prepared_summary?.summary) && (
              <ArticleExplanation
                key={selected.id}
                article={selected}
                phase={(digestStatus || snapshot.news_digest)?.phase}
                configured={
                  !!summaryModel(snapshot, digestStatus || snapshot.news_digest)
                }
                onConfigure={onConfigureExplanations}
              />
            )}
            {selected.body_status === "full" &&
            selected.reader?.blocks?.length ? (
              layout!.body.map((b: RecordData, i: number) =>
                b.type === "image" ? (
                  <ArticleImage key={i} article={selected.id} id={b.id} />
                ) : (
                  <Markdown key={i} text={readerMarkdown(b.text || "")} />
                ),
              )
            ) : (
              <Markdown
                text={
                  selected.body_status === "full"
                    ? selected.text || ""
                    : articleExcerpt(selected.summary || "") || ""
                }
              />
            )}
            <ArticleHistory
              key={`history:${selected.id}`}
              articleId={selected.id}
            />
            {related.length > 0 && (
              <section className="related-reading">
                <h2>{t("Related reading")}</h2>
                {related.map((a) => (
                  <button
                    className="related"
                    key={a.id}
                    onClick={() => void open(a.id)}
                  >
                    <span className="related-copy">
                      <span dir="auto">{a.title}</span>
                      {(a.source_title || a.published_at) && (
                        <small>
                          {a.source_title && (
                            <span dir="auto">{a.source_title}</span>
                          )}
                          {a.published_at && (
                            <RelativeTime value={a.published_at} now={clock} />
                          )}
                        </small>
                      )}
                    </span>
                    <ChevronRight className="related-arrow" size={16} />
                  </button>
                ))}
              </section>
            )}
          </div>
        </ReaderLinkPreviews>
      </div>
    );
  return (
    <div className="page">
      <div className="page-title">
        <h1>{t("Articles")}</h1>
        <button
          title={t("Refresh")}
          className="icon-button"
          aria-label={t("Refresh articles")}
          disabled={busy}
          onClick={() => void load()}
        >
          <RefreshCw size={17} className={busy ? "spin" : ""} />
        </button>
      </div>
      <p className="muted">
        {t("The stories you follow, with room to focus.")}
      </p>
      <div className="filters">
        <div className="segments">
          {["all", "unread", "saved"].map((s) => (
            <button
              key={s}
              className={s === scope ? "selected" : ""}
              aria-pressed={s === scope}
              onClick={() => setScope(s)}
            >
              {s === "saved"
                ? t("Bookmarks")
                : t(s[0].toUpperCase() + s.slice(1))}
            </button>
          ))}
        </div>
        <label className="search">
          <Search size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("Search your articles")}
            aria-label={t("Search your articles")}
            maxLength={200}
          />
          {query && (
            <button
              className="icon-button"
              aria-label={t("Clear search")}
              onClick={() => setQuery("")}
            >
              <X size={14} />
            </button>
          )}
        </label>
      </div>
      <div className="article-filters">
        <label>
          {t("Source")}{" "}
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">{t("All sources")}</option>
            {(snapshot.subscriptions || []).map((s: RecordData) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("Order")}{" "}
          <select value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="newest">{t("Newest first")}</option>
            <option value="oldest">{t("Oldest first")}</option>
          </select>
        </label>
        <label>
          {t("Date")}{" "}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={0}>{t("All dates")}</option>
            <option value={1}>{t("Last 24 hours")}</option>
            <option value={7}>{t("Last 7 days")}</option>
            <option value={30}>{t("Last 30 days")}</option>
          </select>
        </label>
        {(days !== 0 ||
          source ||
          query ||
          order !== "newest" ||
          scope !== "all") && (
          <button onClick={clearFilters}>{t("Clear filters")}</button>
        )}
      </div>
      {listError && (
        <div className="settings-feedback article-list-error" role="alert">
          <div>
            <strong>{t("Articles could not be loaded")}</strong>
            <p dir="auto">{listError}</p>
          </div>
          <button disabled={busy} onClick={() => void load()}>
            {t("Retry")}
          </button>
        </div>
      )}
      {busy && articles.length > 0 && (
        <p className="inline-loading" role="status">
          <LoaderCircle size={14} className="spin" />
          {t("Updating articles…")}
        </p>
      )}
      {digestStatus && !digestStatus.enabled && (
        <div className="summary-status">
          <span>
            {t(
              "Automatic summaries are paused. Saved summaries remain available.",
            )}
          </span>
          {onConfigureExplanations && (
            <button onClick={onConfigureExplanations}>
              {t("Summary settings")}
            </button>
          )}
        </div>
      )}
      {articles.length === 0 && busy ? (
        <div
          className="article-grid article-skeletons"
          role="status"
          aria-label={t("Loading articles…")}
        >
          {[0, 1, 2].map((i) => (
            <div key={i}>
              <div className="skeleton-cover" />
              <div className="skeleton-line" />
              <div className="skeleton-line short" />
            </div>
          ))}
        </div>
      ) : articles.length === 0 && !listError ? (
        <div className="empty">
          <BookOpen size={28} />
          <h2>
            {t(
              query || source || days || scope !== "all"
                ? "No articles match these filters"
                : "Your reading starts here",
            )}
          </h2>
          <p>
            {t(
              query || source || days || scope !== "all"
                ? "Try a different search or clear your filters."
                : "Follow sources to bring their stories into your library.",
            )}
          </p>
          {query || source || days || scope !== "all" ? (
            <button onClick={clearFilters}>{t("Clear filters")}</button>
          ) : (
            onExploreSources && (
              <button className="primary" onClick={onExploreSources}>
                {t("Explore sources")}
              </button>
            )
          )}
        </div>
      ) : (
        <div className="article-grid" aria-busy={busy}>
          {articles.map((a) => (
            <article className="article-card" key={a.id}>
              <ArticleImage article={a.id} id={a.cover_image_id} cover />
              <p className="eyebrow">{a.source_title}</p>
              <button
                className="article-title article-open"
                onClick={() => void open(a.id)}
                dir="auto"
              >
                {a.title}
              </button>
              <p dir="auto">{articleExcerpt(a.summary)}</p>
              <footer>
                <span>
                  <RelativeTime value={a.published_at} now={clock} /> ·{" "}
                  {t(
                    (
                      {
                        ready: "Explained",
                        summarizing: "Preparing TL;DR…",
                        retrying: "Explanation will retry",
                        pending: "Not explained",
                        incomplete: "Excerpt only",
                      } as Record<string, string>
                    )[states[a.id]] || "Not explained",
                  )}
                </span>
                <button
                  title={t("Bookmark")}
                  aria-label={t("Bookmark") + ": " + a.title}
                  aria-pressed={!!a.is_bookmarked}
                  disabled={bookmarking.includes(a.id)}
                  onClick={() => void bookmark(a)}
                >
                  <Bookmark
                    size={16}
                    fill={a.is_bookmarked ? "currentColor" : "none"}
                  />
                </button>
              </footer>
            </article>
          ))}
        </div>
      )}
      {more && (
        <button
          className="load-more"
          disabled={busy}
          onClick={() => void load(true)}
        >
          {busy && <LoaderCircle size={14} className="spin" />}
          {t(busy ? "Loading…" : "Load more stories")}
        </button>
      )}
    </div>
  );
}
export { SourcesPage as Sources } from "./sources-page";
export { DraftsPage as Drafts } from "./drafts-page";
