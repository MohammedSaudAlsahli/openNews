import { t, getLocale } from "./locale";
import { useEffect, useState, useRef } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Bookmark,
  Search,
  Plus,
  RefreshCw,
  LoaderCircle,
  Rss,
  Check,
  BookOpen,
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
  id: string;
  cover?: boolean;
}) {
  const [src, setSrc] = useState("");
  const [failed, setFailed] = useState(false);
  const placeholder = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let live = true;
    setSrc("");
    setFailed(false);
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        observer.disconnect();
        // The engine keeps the disk cache; only visible images enter webview memory.
        invoke<string>("article_image", { articleId: article, imageId: id })
          .then((value) => {
            if (live) setSrc(value);
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
      {failed ? (
        <div className="cover-fallback">
          <BookOpen size={28} />
          <span>{t("No cover available")}</span>
        </div>
      ) : src ? (
        <img
          className="article-image"
          src={src}
          alt=""
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="image-placeholder" aria-hidden="true" />
      )}
    </div>
  );
}

type Props = { onError: (e: string) => void };
const date = (v: string) =>
  v
    ? new Date(v).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      })
    : "";
export function Articles({
  onError,
  snapshot,
}: Props & { snapshot: RecordData }) {
  const [articles, setArticles] = useState<RecordData[]>([]),
    [query, setQuery] = useState(""),
    [scope, setScope] = useState("all"),
    [source, setSource] = useState(""),
    [order, setOrder] = useState("newest"),
    [history, setHistory] = useState<RecordData[]>([]),
    [revision, setRevision] = useState<RecordData>(),
    [more, setMore] = useState(false),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState<RecordData>(),
    [reading, setReading] = useState(false),
    [related, setRelated] = useState<RecordData[]>([]),
    [states, setStates] = useState<RecordData>({});
  const request = useRef(0),
    selection = useRef(0);
  async function load(append = false) {
    const token = ++request.current;
    setBusy(true);
    try {
      const r = await call("news.list", {
        query,
        scope,
        source_id: source,
        order,
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
      const s = await call("news.summary.states", {
        ids: r.articles.map((a: RecordData) => a.id),
      });
      if (token === request.current)
        setStates((old) => ({ ...old, ...s.states }));
    } catch (e) {
      if (token === request.current) onError(String(e));
    } finally {
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
  }, [query, scope, source, order]);
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
    setReading(true);
    setRelated([]);
    setHistory([]);
    setRevision(undefined);
    try {
      const article = await call("news.article", { article_id: id });
      if (token !== selection.current) return;
      setSelected(article);
      const r = await call("news.reader", { article_id: id, refresh });
      if (token !== selection.current) return;
      setSelected({ ...article, ...r });
      const related = await call("news.related", { article_id: id });
      if (token === selection.current) setRelated(related.articles || []);
    } catch (e) {
      if (token === selection.current) onError(String(e));
    } finally {
      if (token === selection.current) setReading(false);
    }
  }
  async function bookmark(a: RecordData) {
    try {
      await call("news.bookmark", {
        article_id: a.id,
        saved: !a.is_bookmarked,
      });
      setArticles((old) =>
        old.map((x) =>
          x.id === a.id ? { ...x, is_bookmarked: !x.is_bookmarked } : x,
        ),
      );
      if (selected?.id === a.id)
        setSelected({ ...selected, is_bookmarked: !a.is_bookmarked });
    } catch (e) {
      onError(String(e));
    }
  }
  if (selected)
    return (
      <div className="reader" key={selected.id}>
        <div className="reader-toolbar">
          <button
            onClick={() => {
              ++selection.current;
              setSelected(undefined);
              setReading(false);
              void load();
            }}
          >
            <ArrowLeft size={16} />
            {t("Articles")}
          </button>
          <span />
          {reading && <LoaderCircle className="spin" size={16} />}
          <button
            title={t("Refresh article")}
            disabled={reading}
            onClick={() => void open(selected.id, true)}
          >
            <RefreshCw size={17} />
          </button>
          <button title={t("Bookmark")} onClick={() => void bookmark(selected)}>
            <Bookmark
              size={17}
              fill={selected.is_bookmarked ? "currentColor" : "none"}
            />
          </button>
        </div>
        <div className="reader-content">
          <p className="eyebrow">
            {selected.source_title} · {date(selected.published_at)}
          </p>
          <h1 dir="auto">{selected.title}</h1>
          {selected.body_status !== "full" && (
            <p className="notice">
              {reading
                ? t("Retrieving article text…")
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
              <button
                onClick={() =>
                  void invoke("open_external", { address: selected.url }).catch(
                    (e) => onError(String(e)),
                  )
                }
              >
                {t("Read original")}
                <ArrowUpRight size={15} />
              </button>
            </div>
          )}
          {selected.body_status === "full" &&
          selected.reader?.blocks?.length ? (
            selected.reader.blocks.map((b: RecordData, i: number) =>
              b.type === "image" ? (
                <ArticleImage key={i} article={selected.id} id={b.id} />
              ) : (
                <Markdown key={i} text={b.text || ""} />
              ),
            )
          ) : (
            <Markdown
              text={
                selected.body_status === "full"
                  ? selected.text || ""
                  : articleExcerpt(selected.summary || "") ||
                    "This feed contains a link, rather than article text."
              }
            />
          )}
          <details
            className="summary-section"
            onToggle={(e) => {
              if (e.currentTarget.open && !history.length)
                void call("news.history", { article_id: selected.id })
                  .then((r) => setHistory(r.revisions))
                  .catch((e) => onError(String(e)));
            }}
          >
            <summary>{t("Article history")}</summary>
            {history.map((r) => (
              <button
                key={r.id}
                onClick={() =>
                  void call("news.revision", {
                    article_id: selected.id,
                    revision_id: r.id,
                  })
                    .then(setRevision)
                    .catch((e) => onError(String(e)))
                }
              >
                {new Date(r.captured_at).toLocaleString()}
              </button>
            ))}
            {revision && (
              <>
                <p>{t("Changes from the previous saved version")}</p>
                <pre className="revision-diff">
                  {revision.diff || "No text changes"}
                </pre>
              </>
            )}
          </details>
          <details className="summary-section">
            <summary>{t("Article explanation")}</summary>
            {selected.prepared_summary ? (
              <Markdown text={selected.prepared_summary.summary} />
            ) : (
              <button
                disabled={reading}
                onClick={async () => {
                  setReading(true);
                  try {
                    const summary = await call("news.summarize", {
                      article_id: selected.id,
                      consent: true,
                    });
                    setSelected({ ...selected, prepared_summary: summary });
                  } catch (e) {
                    onError(String(e));
                  } finally {
                    setReading(false);
                  }
                }}
              >
                {t("Generate explanation with my model")}
              </button>
            )}
          </details>
          {related.length > 0 && (
            <section>
              <h2>{t("Related reading")}</h2>
              {related.map((a) => (
                <button
                  className="related"
                  key={a.id}
                  onClick={() => void open(a.id)}
                >
                  {a.title}
                  <ArrowUpRight size={15} />
                </button>
              ))}
            </section>
          )}
        </div>
      </div>
    );
  return (
    <div className="page">
      <p className="eyebrow">{t("READ. UNDERSTAND. CONNECT.")}</p>
      <div className="page-title">
        <h1>{t("Your reading room")}</h1>
        <button
          title={t("Refresh")}
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
              onClick={() => setScope(s)}
            >
              {s === "saved" ? t("Bookmarks") : s[0].toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <label className="search">
          <Search size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("Search your articles")}
          />
        </label>
      </div>
      <div className="reader-actions">
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
      </div>
      {articles.length === 0 && !busy ? (
        <div className="empty">
          <BookOpen size={28} />
          <h2>{t("A little curiosity goes a long way.")}</h2>
          <p>{t("Add sources to start building your reading room.")}</p>
        </div>
      ) : (
        <div className="article-grid">
          {articles.map((a) => (
            <article className="article-card" key={a.id}>
              {a.cover_image_id && (
                <ArticleImage article={a.id} id={a.cover_image_id} cover />
              )}
              <p className="eyebrow">{a.source_title}</p>
              <button
                className="article-title"
                onClick={() => void open(a.id)}
                dir="auto"
              >
                {a.title}
              </button>
              <p dir="auto">{articleExcerpt(a.summary)}</p>
              <footer>
                <span>
                  {date(a.published_at)} ·{" "}
                  {states[a.id] === "ready"
                    ? t("Explained")
                    : a.body_status === "full"
                      ? t("Ready to read")
                      : t("Excerpt only")}
                </span>
                <button title={t("Bookmark")} onClick={() => void bookmark(a)}>
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
          {t("Load more stories")}
        </button>
      )}
    </div>
  );
}
export function Sources({
  snapshot,
  refresh,
  onError,
}: Props & { snapshot: RecordData; refresh: () => Promise<void> }) {
  const [tab, setTab] = useState("following"),
    [query, setQuery] = useState(""),
    [items, setItems] = useState<RecordData[]>([]),
    [cursor, setCursor] = useState<string>(),
    [busy, setBusy] = useState(false),
    [url, setUrl] = useState(""),
    [adding, setAdding] = useState(false);
  async function discover(append = false) {
    setBusy(true);
    try {
      const r = await call("news.directory", {
        query,
        cursor: append ? cursor : undefined,
      });
      setItems((old) =>
        append ? [...old, ...(r.feeds || [])] : r.feeds || [],
      );
      setCursor(r.next_cursor);
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    if (tab === "discover") {
      const timer = setTimeout(() => void discover(), 300);
      return () => clearTimeout(timer);
    }
  }, [tab, query]);
  async function add(address: string) {
    setBusy(true);
    try {
      await call("news.subscribe", { url: address });
      setUrl("");
      setAdding(false);
      await refresh();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const list =
    tab === "following"
      ? (snapshot.subscriptions || []).filter((s: RecordData) =>
          s.title.toLowerCase().includes(query.toLowerCase()),
        )
      : items;
  return (
    <div className="page">
      <p className="eyebrow">{t("A BETTER SIGNAL")}</p>
      <div className="page-title">
        <h1>{t("Follow what matters.")}</h1>
        <button className="primary" onClick={() => setAdding(!adding)}>
          <Plus size={16} />
          {t("Add a source")}
        </button>
      </div>
      <p className="muted">
        {t("Newsletters, publications and communities. All in one place.")}
      </p>
      {adding && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            void add(url);
          }}
        >
          <input
            type="url"
            required
            placeholder={t("Paste a website, RSS, subreddit or X RSS link")}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button disabled={busy} className="primary">
            {t("Follow")}
          </button>
        </form>
      )}
      <div className="filters">
        <div className="segments">
          {["following", "discover"].map((tabId) => (
            <button
              key={tabId}
              className={tab === tabId ? "selected" : ""}
              onClick={() => setTab(tabId)}
            >
              {t(tabId === "following" ? t("Following") : t("Discover"))}
            </button>
          ))}
        </div>
        <label className="search">
          <Search size={16} />
          <input
            placeholder={t("Search sources or topics")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>
      <div className="source-list">
        {list.map((s: RecordData) => (
          <div key={s.id || s.url}>
            <span className="source-monogram">
              {s.title?.[0] || <Rss size={17} />}
            </span>
            <div>
              <strong>{s.title}</strong>
              <p>
                {(getLocale() === "ar"
                  ? s.description_ar || s.description_en
                  : s.description_en || s.description_ar) ||
                  s.error ||
                  s.url ||
                  s.feed_url}
              </p>
              {s.status && <small>{s.status}</small>}
              {tab === "following" && (
                <div className="reader-actions">
                  <button
                    onClick={async () => {
                      try {
                        await call("news.update", {
                          subscription_id: s.id,
                          enabled: !s.enabled,
                        });
                        await refresh();
                      } catch (e) {
                        onError(String(e));
                      }
                    }}
                  >
                    {t(s.enabled ? t("Pause") : t("Resume"))}
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        await call("news.sync", { subscription_id: s.id });
                        await refresh();
                      } catch (e) {
                        onError(String(e));
                      }
                    }}
                  >
                    {t("Refresh source")}
                  </button>
                  <label>
                    {t("Refresh interval")}
                    <select
                      aria-label={t("Refresh interval") + " " + s.title}
                      value={s.interval_minutes || 60}
                      onChange={async (e) => {
                        try {
                          await call("news.update", {
                            subscription_id: s.id,
                            interval_minutes: Number(e.target.value),
                          });
                          await refresh();
                        } catch (error) {
                          onError(String(error));
                        }
                      }}
                    >
                      {[15, 30, 60, 180, 360, 720, 1440].map((n) => (
                        <option key={n} value={n}>
                          {n} {t("Minutes")}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              )}
            </div>
            {tab === "following" ? (
              <button
                onClick={async () => {
                  try {
                    await call("news.unsubscribe", { subscription_id: s.id });
                    await refresh();
                  } catch (e) {
                    onError(String(e));
                  }
                }}
              >
                {t("Unfollow")}
              </button>
            ) : (
              <button onClick={() => void add(s.feed_url || s.url)}>
                <Plus size={15} />
                {t("Follow")}
              </button>
            )}
          </div>
        ))}
      </div>
      {!list.length && !busy && (
        <div className="empty">
          <Rss size={30} />
          <h2>{t("Your sources belong here.")}</h2>
          <p>{t("Follow a source or explore the directory.")}</p>
        </div>
      )}
      {busy && <LoaderCircle className="spin" />}
      {cursor && tab === "discover" && (
        <button className="load-more" onClick={() => void discover(true)}>
          {t("Discover more")}
        </button>
      )}
    </div>
  );
}
export function Drafts({
  snapshot,
  onError,
}: Props & { snapshot: RecordData }) {
  const [selected, setSelected] = useState<RecordData>(),
    [text, setText] = useState(""),
    [preview, setPreview] = useState(false),
    [notice, setNotice] = useState(""),
    [topic, setTopic] = useState(""),
    [creating, setCreating] = useState(false);
  return (
    <div className="page">
      <p className="eyebrow">{t("WORK IN PROGRESS")}</p>
      <h1>{t("Saved drafts")}</h1>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {!selected && (
        <>
          <button onClick={() => setCreating(!creating)}>
            {t("New draft")}
          </button>
          {creating && (
            <section>
              <label className="field">
                {t("Title")}
                <input
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
              </label>
              <textarea
                className="editor"
                aria-label={t("New draft text")}
                dir="auto"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
              <button
                disabled={!topic.trim() || !text.trim()}
                onClick={async () => {
                  try {
                    const result = await call("drafts.create", {
                      topic,
                      text,
                      language: /[\u0600-\u06ff]/.test(text) ? "ar" : "en",
                    });
                    const detail = await call("drafts.detail", {
                      draft_id: result.draft_id,
                    });
                    setSelected({ id: result.draft_id, topic, ...detail });
                    setCreating(false);
                    setNotice("Draft created.");
                  } catch (e) {
                    onError(String(e));
                  }
                }}
              >
                {t("Create draft")}
              </button>
            </section>
          )}
        </>
      )}

      {selected ? (
        <>
          <button onClick={() => setSelected(undefined)}>
            <ArrowLeft size={16} />
            {t("All drafts")}
          </button>
          <h2>{selected.topic || selected.title}</h2>
          <label className="field">
            {t("Saved versions")}
            <select
              defaultValue={selected.draft?.current_version_id}
              onChange={(e) =>
                setText(
                  selected.versions?.find(
                    (v: RecordData) => v.id === e.target.value,
                  )?.text || "",
                )
              }
            >
              {(selected.versions || []).map((v: RecordData) => (
                <option key={v.id} value={v.id}>
                  {new Date(v.created_at).toLocaleString()}
                </option>
              ))}
            </select>
          </label>

          <div className="segments">
            <button onClick={() => setPreview(false)}>{t("Write")}</button>
            <button onClick={() => setPreview(true)}>{t("Preview")}</button>
          </div>
          {preview ? (
            <Markdown text={text} />
          ) : (
            <textarea
              className="editor"
              value={text}
              dir="auto"
              onChange={(e) => setText(e.target.value)}
            />
          )}
          <button
            className="primary"
            onClick={async () => {
              try {
                await call("drafts.save", { draft_id: selected.id, text });
                setNotice("Draft saved.");
              } catch (e) {
                onError(String(e));
              }
            }}
          >
            {t("Save draft")}
          </button>
          <button
            onClick={async () => {
              try {
                await call("drafts.save", { draft_id: selected.id, text });
                const path = await invoke<string>("export_draft", {
                  draftId: selected.id,
                });
                setNotice("Exported to " + path);
              } catch (e) {
                onError(String(e));
              }
            }}
          >
            {t("Export Markdown")}
          </button>
          <button
            onClick={() =>
              void navigator.clipboard
                .writeText(text)
                .then(() => setNotice("Copied."))
                .catch((e) => onError(String(e)))
            }
          >
            {t("Copy text")}
          </button>
        </>
      ) : (
        <div className="source-list">
          {(snapshot.drafts || []).map((d: RecordData) => (
            <button
              className="draft-row"
              key={d.id}
              onClick={async () => {
                try {
                  const r = await call("drafts.detail", { draft_id: d.id });
                  setSelected({ ...d, ...r });
                  setText(
                    r.versions?.find(
                      (v: RecordData) => v.id === r.draft.current_version_id,
                    )?.text || "",
                  );
                } catch (e) {
                  onError(String(e));
                }
              }}
            >
              <strong>{d.topic || d.title}</strong>
              <small>{d.format}</small>
              <ArrowUpRight size={16} />
            </button>
          ))}
          {!snapshot.drafts?.length && (
            <div className="empty">
              <h2>{t("Make something worth keeping.")}</h2>
              <p>
                {t(
                  "Ask the assistant to write a post or script. Saved drafts appear here.",
                )}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
