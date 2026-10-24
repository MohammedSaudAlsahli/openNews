import { useEffect, useMemo, useRef, useState } from "react";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import {
  Search,
  Plus,
  Rss,
  MoreHorizontal,
  Pause,
  Play,
  RefreshCw,
  Check,
  X,
  LoaderCircle,
  ArrowUpRight,
  Clock3,
} from "lucide-react";
import { call, type RecordData } from "./engine";
import { t, getLocale, useLocale } from "./locale";
import { RefreshInterval, intervalLabel } from "./refresh-interval";
import { invoke } from "@tauri-apps/api/core";

function address(row: RecordData) {
  return row.feed_url || row.url || "";
}
function hostname(row: RecordData) {
  try {
    return new URL(
      row.publisher_url || row.url || row.feed_url,
    ).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}
export function SourcesPage({
  snapshot,
  refresh,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  useLocale();
  const [tab, setTab] = useState("following"),
    [query, setQuery] = useState(""),
    [category, setCategory] = useState("all");
  const [sourceLanguage, setSourceLanguage] = useState("all");
  const [visible, setVisible] = useState(36),
    [directoryLoaded, setDirectoryLoaded] = useState(false);
  const [catalog, setCatalog] = useState<RecordData[]>([]),
    [remote, setRemote] = useState<RecordData[]>([]),
    [cursor, setCursor] = useState<string>();
  const [loading, setLoading] = useState(false),
    [failure, setFailure] = useState(""),
    [adding, setAdding] = useState(false),
    [url, setUrl] = useState("");
  const [pending, setPending] = useState<string[]>([]),
    [notice, setNotice] = useState(""),
    [configured, setConfigured] = useState("");
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});
  const [catalogLoading, setCatalogLoading] = useState(true),
    [catalogError, setCatalogError] = useState("");
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const actionRequests = useRef(new Set<string>());
  const [added, setAdded] = useState<string[]>([]);
  const descriptions = useMemo(() => {
    const byAddress = new Map<string, RecordData>(),
      byTitle = new Map<string, RecordData>();
    for (const row of catalog) {
      if (!byAddress.has(address(row))) byAddress.set(address(row), row);
      if (!byTitle.has(row.title)) byTitle.set(row.title, row);
    }
    return { byAddress, byTitle };
  }, [catalog]);
  const generation = useRef(0);
  const subscriptions: RecordData[] = snapshot.subscriptions || [];
  useEffect(() => {
    let live = true;
    setCatalogLoading(true);
    setCatalogError("");
    call("news.curated")
      .then((r) => {
        if (live) setCatalog(r.feeds || []);
      })
      .catch((e) => {
        if (live) setCatalogError(String(e));
      })
      .finally(() => {
        if (live) setCatalogLoading(false);
      });
    return () => {
      live = false;
    };
  }, [catalogAttempt]);
  async function discover(append = false, token = ++generation.current) {
    setLoading(true);
    setFailure("");
    try {
      const result = await call("news.directory", {
        query: query.slice(0, 100),
        cursor: append ? cursor : undefined,
      });
      if (token !== generation.current) return;
      setRemote((old) =>
        append ? [...old, ...(result.feeds || [])] : result.feeds || [],
      );
      setCursor(result.next_cursor);
      setDirectoryLoaded(true);
    } catch (e) {
      if (token === generation.current) setFailure(String(e));
    } finally {
      if (token === generation.current) setLoading(false);
    }
  }
  useEffect(() => {
    const token = ++generation.current;
    setRemote([]);
    setCursor(undefined);
    setDirectoryLoaded(false);
    setLoading(false);
    setFailure("");
    if (tab !== "discover" || !query.trim()) return;
    const timer = setTimeout(() => void discover(false, token), 350);
    return () => {
      clearTimeout(timer);
      ++generation.current;
    };
  }, [tab, query]);
  async function perform(key: string, work: () => Promise<void>) {
    if (actionRequests.current.has(key)) return;
    actionRequests.current.add(key);
    setPending((old) => [...old, key]);
    setNotice("");
    setActionErrors((old) => ({ ...old, [key]: "" }));
    try {
      await work();
      try {
        await refresh();
      } catch {
        setNotice(
          t("Your change was saved. Refresh the page to update the list."),
        );
      }
    } catch (e) {
      setActionErrors((old) => ({
        ...old,
        [key]: String(e).replace(/^Error:\s*/, ""),
      }));
    } finally {
      actionRequests.current.delete(key);
      setPending((old) => old.filter((x) => x !== key));
    }
  }
  async function follow(row: RecordData) {
    await perform(address(row), async () => {
      await call("news.subscribe", { url: address(row) });
      setAdded((old) => [...new Set([...old, address(row)])]);
      setNotice(t("Source added. New articles will appear in your library."));
    });
  }
  function description(row: RecordData) {
    const saved =
      descriptions.byAddress.get(address(row)) ||
      descriptions.byTitle.get(row.title);
    const key = getLocale() === "ar" ? "description_ar" : "description_en";
    return (
      row[key] ||
      saved?.[key] ||
      row.description ||
      t("Articles from this publisher, collected in your library.")
    );
  }
  const categories = [
    ...new Set(catalog.map((s) => s.category).filter(Boolean)),
  ];
  const combined = useMemo(() => {
    const sources = new Map<string, RecordData>();
    for (const row of [...catalog, ...remote])
      if (!sources.has(address(row))) sources.set(address(row), row);
    return [...sources.values()];
  }, [catalog, remote]);
  useEffect(
    () => setVisible(36),
    [tab, query, category, sourceLanguage, remote],
  );
  const list = (tab === "following" ? subscriptions : combined).filter(
    (row) =>
      (category === "all" ||
        tab === "following" ||
        row.category === category) &&
      (tab === "following" ||
        sourceLanguage === "all" ||
        (row.language || "und").split("-")[0].toLowerCase() ===
          sourceLanguage) &&
      (!query.trim() ||
        `${row.title} ${description(row)} ${row.category || ""} ${hostname(row)}`
          .toLowerCase()
          .includes(query.toLowerCase())),
  );
  const filtered =
    Boolean(query.trim()) ||
    (tab === "discover" && (category !== "all" || sourceLanguage !== "all"));
  return (
    <div className="page sources-page">
      <div className="page-title">
        <div>
          <h1>{t("Sources")}</h1>
          <p className="page-description">
            {t("A reading list shaped by you.")}
          </p>
        </div>
        <button
          className="primary"
          disabled={pending.includes("add")}
          onClick={() => setAdding(!adding)}
          aria-expanded={adding}
        >
          <Plus size={16} />
          {t("Add a source")}
        </button>
      </div>
      {adding && (
        <form
          className="source-add-panel"
          onSubmit={(e) => {
            e.preventDefault();
            void perform("add", async () => {
              await call("news.subscribe", { url });
              setAdded((old) => [...new Set([...old, url.trim()])]);
              setUrl("");
              setAdding(false);
              setNotice(
                t("Source added. New articles will appear in your library."),
              );
            });
          }}
        >
          <div className="section-heading">
            <strong>{t("Follow a website or community")}</strong>
            <button
              type="button"
              className="icon-button"
              onClick={() => setAdding(false)}
              aria-label={t("Close")}
              disabled={pending.includes("add")}
            >
              <X size={16} />
            </button>
          </div>
          <p className="muted">
            {t(
              "Paste a website, RSS feed or Reddit community. We will find its articles.",
            )}
          </p>
          <div className="inline-form">
            <input
              autoFocus
              type="url"
              required
              aria-label={t("Source URL")}
              placeholder="https://…"
              value={url}
              dir="ltr"
              disabled={pending.includes("add")}
              aria-invalid={Boolean(actionErrors.add)}
              aria-describedby={
                actionErrors.add ? "source-add-error" : undefined
              }
              onChange={(e) => {
                setUrl(e.target.value);
                setActionErrors((old) => ({ ...old, add: "" }));
              }}
            />
            <button className="primary" disabled={pending.includes("add")}>
              {pending.includes("add") ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <Plus size={16} />
              )}{" "}
              {t("Follow")}
            </button>
          </div>
          {actionErrors.add && (
            <p
              className="source-action-error"
              id="source-add-error"
              role="alert"
              dir="auto"
            >
              {actionErrors.add}
            </p>
          )}
        </form>
      )}
      {notice && (
        <p className="inline-success" role="status">
          <Check size={16} />
          {notice}
        </p>
      )}
      <div className="filters">
        <div className="segments" role="group" aria-label={t("Sources")}>
          <button
            className={tab === "following" ? "selected" : ""}
            aria-pressed={tab === "following"}
            onClick={() => setTab("following")}
          >
            {t("Following")}
            <span>{subscriptions.length}</span>
          </button>
          <button
            className={tab === "discover" ? "selected" : ""}
            aria-pressed={tab === "discover"}
            onClick={() => setTab("discover")}
          >
            {t("Discover")}
          </button>
        </div>
        <label className="search">
          <Search size={16} />
          <input
            aria-label={t("Search sources or topics")}
            maxLength={100}
            placeholder={t("Search sources or topics")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
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
      {tab === "discover" && (
        <div className="source-discovery-filters">
          <div
            className="category-tabs"
            role="group"
            aria-label={t("Categories")}
          >
            {["all", ...categories].map((c) => (
              <button
                key={c}
                aria-pressed={category === c}
                className={category === c ? "selected" : ""}
                onClick={() => setCategory(c)}
              >
                {c === "all"
                  ? t("All topics")
                  : t(c.charAt(0).toUpperCase() + c.slice(1))}
              </button>
            ))}
          </div>
          <label className="source-language-filter">
            {t("Source language")}
            <select
              value={sourceLanguage}
              onChange={(e) => setSourceLanguage(e.target.value)}
            >
              <option value="all">{t("All languages")}</option>
              {[
                ...new Set(
                  combined.map((row) =>
                    (row.language || "und").split("-")[0].toLowerCase(),
                  ),
                ),
              ]
                .sort()
                .map((code) => {
                  let label = t("Not specified");
                  if (code !== "und") {
                    try {
                      label =
                        new Intl.DisplayNames([getLocale()], {
                          type: "language",
                        }).of(code) || code;
                    } catch {
                      label = code;
                    }
                  }
                  return (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  );
                })}
            </select>
          </label>
        </div>
      )}
      {tab === "discover" && (
        <div className="section-heading discovery-heading">
          <h2>{query ? t("Search results") : t("Find your next good read")}</h2>
          <small>
            {t("Independent publishers, communities and newsrooms")}
          </small>
        </div>
      )}
      {tab === "discover" && catalogError && (
        <div className="settings-feedback" role="alert">
          <span>
            {t(
              "Suggested sources could not load. You can still search the directory.",
            )}
          </span>
          <button onClick={() => setCatalogAttempt((value) => value + 1)}>
            {t("Retry")}
          </button>
        </div>
      )}
      {tab === "discover" && failure && (
        <div className="settings-feedback" role="status">
          <span>
            {t(
              "The directory is unavailable. Suggested sources are still here.",
            )}
          </span>
          <button disabled={loading} onClick={() => void discover()}>
            {t("Retry")}
          </button>
        </div>
      )}
      <div
        className={tab === "following" ? "subscription-list" : "discovery-grid"}
      >
        {(tab === "discover" ? list.slice(0, visible) : list).map((s) => {
          const following =
              added.includes(address(s)) ||
              subscriptions.some((x) => address(x) === address(s)),
            busy = pending.includes(s.id) || pending.includes(address(s));
          const status = !s.enabled ? "paused" : s.status || "ready";
          return (
            <section key={s.id || address(s)} className="source-card">
              <div className="source-card-heading">
                <span className="source-monogram" aria-hidden="true">
                  {s.title?.[0] || <Rss size={19} />}
                </span>
                <div>
                  <h3>
                    <bdi>{s.title}</bdi>
                  </h3>
                  <small>
                    <bdi dir="ltr">{hostname(s)}</bdi>
                  </small>
                </div>
                {tab === "following" ? (
                  <Dropdown.Root>
                    <Dropdown.Trigger
                      id={`source-actions-${s.id}`}
                      className="icon-button"
                      disabled={busy}
                      aria-label={t("Manage source") + ": " + s.title}
                    >
                      <MoreHorizontal size={18} />
                    </Dropdown.Trigger>
                    <Dropdown.Portal>
                      <Dropdown.Content
                        className="floating-panel action-menu"
                        align="end"
                        sideOffset={6}
                        collisionPadding={16}
                      >
                        <Dropdown.Item
                          onSelect={() =>
                            void perform(s.id, async () => {
                              await call("news.sync", {
                                subscription_id: s.id,
                              });
                              setNotice(
                                t(
                                  "Refresh requested. New articles will appear when it finishes.",
                                ),
                              );
                            })
                          }
                        >
                          <RefreshCw size={15} />
                          {t("Refresh source")}
                        </Dropdown.Item>
                        <Dropdown.Item
                          onSelect={() =>
                            void perform(s.id, async () => {
                              await call("news.update", {
                                subscription_id: s.id,
                                enabled: !s.enabled,
                              });
                            })
                          }
                        >
                          {s.enabled ? <Pause size={15} /> : <Play size={15} />}{" "}
                          {t(s.enabled ? "Pause" : "Resume")}
                        </Dropdown.Item>
                        <Dropdown.Item
                          onSelect={() =>
                            setConfigured(configured === s.id ? "" : s.id)
                          }
                        >
                          <Clock3 size={15} />
                          {t("Refresh interval")}
                        </Dropdown.Item>
                        <Dropdown.Separator />
                        <Dropdown.Item
                          className="destructive"
                          onSelect={() =>
                            void perform(s.id, async () => {
                              await call("news.unsubscribe", {
                                subscription_id: s.id,
                              });
                              setAdded((old) =>
                                old.filter((url) => url !== address(s)),
                              );
                              setNotice(
                                t(
                                  "Source unfollowed. Your saved articles are still available.",
                                ),
                              );
                            })
                          }
                        >
                          {t("Unfollow")}
                        </Dropdown.Item>
                      </Dropdown.Content>
                    </Dropdown.Portal>
                  </Dropdown.Root>
                ) : (
                  <button
                    className={following ? "followed-button" : "follow-button"}
                    disabled={following || busy}
                    onClick={() => void follow(s)}
                  >
                    {busy ? (
                      <LoaderCircle size={15} className="spin" />
                    ) : following ? (
                      <Check size={15} />
                    ) : (
                      <Plus size={15} />
                    )}{" "}
                    {t(following ? "Following" : "Follow")}
                  </button>
                )}
              </div>
              <p className="source-description" dir="auto">
                {description(s)}
              </p>
              {tab === "following" ? (
                <div className="source-card-footer">
                  <span className={`source-status ${status}`}>
                    <i />
                    {t(
                      status === "paused"
                        ? "Paused"
                        : (
                            {
                              ready: "Ready",
                              error: "Needs attention",
                              syncing: "Refreshing…",
                              pending: "Waiting for first refresh",
                            } as Record<string, string>
                          )[status] || "Ready",
                    )}
                  </span>
                  {busy && <LoaderCircle size={14} className="spin" />}
                  <small>
                    <Clock3 size={12} aria-hidden="true" />{" "}
                    {intervalLabel(s.interval_minutes ?? 5)}
                  </small>
                </div>
              ) : (
                <div className="source-card-footer">
                  <small>
                    {t(
                      s.category
                        ? s.category.charAt(0).toUpperCase() +
                            s.category.slice(1)
                        : "Publication",
                    )}
                  </small>
                  <button
                    className="icon-button"
                    title={t("Visit publisher")}
                    aria-label={t("Visit publisher") + ": " + s.title}
                    onClick={() =>
                      void invoke("open_external", {
                        address: s.publisher_url || s.url || s.feed_url,
                      }).catch((e) => onError(String(e)))
                    }
                  >
                    <ArrowUpRight size={14} />
                  </button>
                </div>
              )}
              {s.error && tab === "following" && (
                <details className="source-failure">
                  <summary>{t("Last refresh needs attention")}</summary>
                  <p dir="auto">{s.error}</p>
                </details>
              )}
              {actionErrors[s.id] || actionErrors[address(s)] ? (
                <p className="source-action-error" role="alert" dir="auto">
                  {actionErrors[s.id] || actionErrors[address(s)]}
                </p>
              ) : null}
              {configured === s.id && (
                <RefreshInterval
                  id={s.id}
                  title={s.title}
                  minutes={s.interval_minutes ?? 5}
                  onSaved={refresh}
                  onError={onError}
                  onClose={() => {
                    setConfigured("");
                    document.getElementById(`source-actions-${s.id}`)?.focus();
                  }}
                />
              )}
            </section>
          );
        })}
      </div>
      {!list.length && !loading && !(tab === "discover" && catalogLoading) && (
        <div className="empty">
          <Rss size={28} />
          <h2>
            {t(
              filtered
                ? "No sources match your search"
                : "Your sources belong here.",
            )}
          </h2>
          <p>
            {t(
              filtered
                ? "Try another name or add a source by URL."
                : "Follow a source or explore the directory.",
            )}
          </p>
          <button
            onClick={() => {
              if (!filtered) setTab("discover");
              setQuery("");
              setCategory("all");
              setSourceLanguage("all");
            }}
          >
            {t(filtered ? "Clear filters" : "Explore sources")}
          </button>
        </div>
      )}
      {loading && (
        <p className="inline-loading" role="status">
          <LoaderCircle size={16} className="spin" />
          {t("Searching the directory…")}
        </p>
      )}
      {tab === "discover" && catalogLoading && !list.length && (
        <p className="inline-loading" role="status">
          <LoaderCircle size={16} className="spin" />
          {t("Loading suggested sources…")}
        </p>
      )}
      {tab === "discover" && visible < list.length && (
        <div className="directory-pagination">
          <span className="muted">
            {Math.min(visible, list.length).toLocaleString(getLocale())}{" "}
            {t("of")} {list.length.toLocaleString(getLocale())}
          </span>
          <button onClick={() => setVisible((value) => value + 36)}>
            {t("Show more sources")}
          </button>
        </div>
      )}
      {tab === "discover" && (!directoryLoaded || cursor) && (
        <button
          className="load-more"
          disabled={loading}
          onClick={() => void discover(Boolean(cursor))}
        >
          {t(cursor ? "Discover more" : "Explore the full directory")}
        </button>
      )}
    </div>
  );
}
