import { BrandMark } from "./brand";
import { Onboarding } from "./onboarding";
import { ConversationOptions } from "./conversation-options";
import { t, useLocale } from "./locale";
import { listen } from "@tauri-apps/api/event";
import React, {
  useEffect,
  useState,
  useCallback,
  useRef,
  lazy,
  Suspense,
} from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUp,
  Plus,
  Search,
  PanelLeftClose,
  PanelLeftOpen,
  MessageSquare,
  Newspaper,
  Compass,
  FileText,
  Settings as SettingsIcon,
  Activity,
  Circle,
  Check,
  Square,
  ChevronDown,
  ChevronLeft,
  BookOpen,
  LoaderCircle,
} from "lucide-react";
import { Markdown, Trace } from "./components";
import { call, active, duration, language, type RecordData } from "./engine";
import "./style.css";
import { invoke } from "@tauri-apps/api/core";
const Articles = lazy(() =>
  import("./pages").then((x) => ({ default: x.Articles })),
);
const Sources = lazy(() =>
  import("./pages").then((x) => ({ default: x.Sources })),
);
const Settings = lazy(() => import("./settings"));
const Drafts = lazy(() =>
  import("./pages").then((x) => ({ default: x.Drafts })),
);
function App() {
  useLocale();
  const [showWelcome, setShowWelcome] = useState(
    localStorage.getItem("welcome-dismissed") !== "true",
  );
  const [newVersion, setNewVersion] = useState("");
  const [options, setOptions] = useState(false);
  const [attachments, setAttachments] = useState<Record<string, RecordData[]>>(
    {},
  );
  const [includeNews, setIncludeNews] = useState(true),
    [researchWeb, setResearchWeb] = useState(true);
  const [availableModels, setAvailableModels] = useState<RecordData[]>([]);
  const [page, setPage] = useState("chat"),
    [sidebar, setSidebar] = useState(true),
    [ready, setReady] = useState(false),
    [error, setError] = useState("");
  const [agents, setAgents] = useState<RecordData[]>([]),
    [agent, setAgent] = useState("");
  const [snapshot, setSnapshot] = useState<RecordData>({}),
    [chats, setChats] = useState<RecordData[]>([]),
    [selected, setSelected] = useState(""),
    [detail, setDetail] = useState<RecordData>(),
    [progress, setProgress] = useState<Record<string, RecordData>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>(() => {
      try {
        return JSON.parse(localStorage.getItem("composer-drafts") || "{}");
      } catch {
        return {};
      }
    }),
    [profile, setProfile] = useState(""),
    [model, setModel] = useState(""),
    [search, setSearch] = useState(""),
    [sending, setSending] = useState(false),
    [consent, setConsent] = useState(
      localStorage.getItem("model-consent") === "true",
    );
  useEffect(() => {
    localStorage.setItem("composer-drafts", JSON.stringify(drafts));
  }, [drafts]);
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);
  useEffect(() => {
    const listener = listen<string>("navigate", (event) => {
      if (event.payload === "articles") setPage("articles");
      else if (event.payload === "reports") {
        sessionStorage.setItem("settings-tab", "daily");
        setPage("settings");
      } else setPage("chat");
    });
    return () => {
      void listener.then((unlisten) => unlisten());
    };
  }, []);
  useEffect(() => {
    const handler = listen<RecordData>("update-available", (event) =>
      setNewVersion(event.payload.version),
    );
    return () => {
      void handler.then((stop) => stop());
    };
  }, []);
  const refresh = useCallback(async () => {
    const [s, c] = await Promise.all([
      call("workspace.snapshot"),
      call("chat.list"),
    ]);
    setSnapshot(s);
    setAgents((await call("agents.list")).agents || []);
    setChats(c.conversations || []);
  }, []);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const boot = async () => {
      try {
        await call("runtime.health");
        if (!alive) return;
        setReady(true);
        setError("");
        await refresh();
      } catch (e) {
        if (alive) {
          if (!String(e).includes("Engine is starting")) setError(String(e));
          timer = setTimeout(boot, 1500);
        }
      }
    };
    void boot();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [refresh]);
  useEffect(() => {
    if (!ready) return;
    let busy = false;
    const timer = setInterval(
      async () => {
        if (busy) return;
        busy = true;
        try {
          await refresh();
          const running = chats.filter((c) => c.active_job_id);
          await Promise.all(
            running.map(async (c) => {
              const p = await call("chat.progress", {
                job_id: c.active_job_id,
              });
              setProgress((old) => ({ ...old, [c.id]: p }));
            }),
          );
        } catch (e) {
          setError(String(e));
        } finally {
          busy = false;
        }
      },
      chats.some((c) => c.active_job_id) ? 1200 : 10000,
    );
    return () => clearInterval(timer);
  }, [ready, refresh, chats.map((c) => c.active_job_id).join()]);
  const navigationVersion = useRef(0);
  const transcript = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const selectionRef = useRef(selected);
  selectionRef.current = selected;
  const running = chats.find((c) => c.id === selected)?.active_job_id;
  useEffect(() => {
    if (!selected) {
      setDetail(undefined);
      return;
    }
    let live = true;
    call("chat.detail", { conversation_id: selected })
      .then((d) => {
        if (live) setDetail(d);
      })
      .catch((e) => setError(String(e)));
    return () => {
      live = false;
    };
  }, [selected, running]);
  useEffect(() => {
    if (!profile && snapshot.profiles?.length) {
      const p = snapshot.profiles[0];
      setProfile(p.id);
      setModel(p.model_id);
    }
  }, [snapshot, profile]);
  useEffect(() => {
    let live = true;
    setAvailableModels([]);
    if (profile)
      void call("providers.models", { profile_id: profile })
        .then((r) => {
          if (live) setAvailableModels(r.models || []);
        })
        .catch((e) => {
          if (live) setError(String(e));
        });
    return () => {
      live = false;
    };
  }, [profile]);
  async function send() {
    const key = selected || "new",
      text = drafts[key]?.trim();
    if (!text || sending || running) return;
    if (!profile || !model) {
      setPage("settings");
      setError("Connect a model in Settings before sending.");
      return;
    }
    if (!consent) {
      setError(
        "Enable model access below. Your message and selected context will be sent to your chosen provider.",
      );
      return;
    }
    const startedAtNavigation = navigationVersion.current;
    setSending(true);
    setError("");
    try {
      let id = selected;
      if (!id) {
        id = (await call("chat.create", { title: text.slice(0, 80) }))
          .conversation_id;
        if (navigationVersion.current === startedAtNavigation) {
          selectionRef.current = id;
          setSelected(id);
        }
      }
      const result = await call("chat.send", {
        conversation_id: id,
        message: text,
        profile_id: profile,
        model_id: model,
        consent: true,
        idempotency_key: crypto.randomUUID(),
        format: "auto",
        article_ids: (attachments[key] || []).map((a) => a.id),
        include_news: includeNews,
        research_web: researchWeb,
        ...(agent ? { agent_id: agent } : {}),
      });
      setDrafts((d) => ({ ...d, [key]: "" }));
      setAttachments((a) => ({ ...a, [key]: [] }));
      setProgress((p) => ({
        ...p,
        [id]: { job_id: result.job_id, state: "queued" },
      }));
      await refresh();
      const updated = await call("chat.detail", { conversation_id: id });
      if (selectionRef.current === id) setDetail(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setSending(false);
    }
  }
  function choose(id: string) {
    navigationVersion.current += 1;
    followLatest.current = true;
    selectionRef.current = id;
    setSelected(id);
    setPage("chat");
    setDetail(undefined);
  }
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "n") {
        event.preventDefault();
        choose("");
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  useEffect(() => {
    if (followLatest.current && transcript.current) {
      transcript.current.scrollTop = transcript.current.scrollHeight;
    }
  }, [selected, detail, progress, page]);
  const message = drafts[selected || "new"] || "";
  const profiles = snapshot.profiles || [];
  return (
    <div className={`app ${sidebar ? "" : "collapsed"}`}>
      <aside className="sidebar">
        <div className="brand">
          <BrandMark className="brand-mark" />
          <strong>{t("OpenStudio")}</strong>
          <button title={t("Hide sidebar")} onClick={() => setSidebar(false)}>
            <PanelLeftClose size={17} />
          </button>
        </div>
        <button className="new-chat" onClick={() => choose("")}>
          <Plus size={17} />
          {t("New conversation")}
          <span>{t("⌘ N")}</span>
        </button>
        <nav>
          {[
            [Newspaper, "articles", "Articles"],
            [Compass, "sources", "Sources"],
            [FileText, "drafts", "Saved drafts"],
          ].map(([Icon, id, label]) => {
            const I = Icon as typeof Newspaper;
            return (
              <button
                key={id as string}
                className={page === id ? "selected" : ""}
                onClick={() => setPage(id as string)}
              >
                <I size={17} />
                {t(label as string)}
              </button>
            );
          })}
        </nav>
        <div className="chat-heading">{t("Conversations")}</div>
        <label className="sidebar-search">
          <Search size={14} />
          <input
            placeholder={t("Search conversations")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <div className="chat-list">
          {chats
            .filter((c) => c.title.toLowerCase().includes(search.toLowerCase()))
            .map((c) => (
              <button
                className={
                  selected === c.id && page === "chat" ? "selected" : ""
                }
                key={c.id}
                onClick={() => choose(c.id)}
              >
                <span dir="auto">{c.title}</span>
                {c.active_job_id && <LoaderCircle size={13} className="spin" />}
              </button>
            ))}
        </div>
        <div className="sidebar-bottom">
          <button onClick={() => setPage("activity")}>
            <Activity size={16} />
            {t("Background activity")}
            <span className="count">
              {
                (snapshot.jobs || []).filter((j: RecordData) => active(j.state))
                  .length
              }
            </span>
          </button>
          <button
            className={page === "settings" ? "selected" : ""}
            onClick={() => setPage("settings")}
          >
            <SettingsIcon size={16} />
            {t("Settings")}
          </button>
          <div className="preview-note">
            <Circle size={7} fill="currentColor" />
            {t("Tauri preview · Separate workspace")}
          </div>
        </div>
      </aside>
      <main>
        {newVersion && (
          <button
            className="update-banner"
            onClick={() => {
              sessionStorage.setItem("settings-tab", "privacy");
              setPage("settings");
            }}
          >
            {t("Update available")}: {newVersion}
          </button>
        )}
        {ready &&
          showWelcome &&
          !(snapshot.subscriptions?.length || snapshot.profiles?.length) && (
            <Onboarding
              go={setPage}
              close={() => {
                setShowWelcome(false);
                localStorage.setItem("welcome-dismissed", "true");
              }}
            />
          )}
        <header className="topbar">
          {!sidebar && (
            <button title={t("Show sidebar")} onClick={() => setSidebar(true)}>
              <PanelLeftOpen size={18} />
            </button>
          )}
          <span>
            {page === "chat"
              ? detail?.title || t("New conversation")
              : t(
                  {
                    articles: "Your reading room",
                    sources: "Sources",
                    drafts: "Saved drafts",
                    settings: "Settings",
                    activity: "Background activity",
                  }[page] || page,
                )}
          </span>
          <span className="connection">
            <i className={ready ? "online" : ""} />
            {ready ? t("Saved on this Mac") : t("Starting engine…")}
          </span>
        </header>
        {error && (
          <div className="error" role="alert">
            {error}
            <button onClick={() => setError("")}>{t("Dismiss")}</button>
          </div>
        )}
        <Suspense
          fallback={
            <div className="loading">
              <LoaderCircle className="spin" />
              {t("Opening…")}
            </div>
          }
        >
          {page === "chat" ? (
            <div className="chat">
              <div
                className="messages"
                ref={transcript}
                onScroll={(event) => {
                  const element = event.currentTarget;
                  followLatest.current =
                    element.scrollHeight -
                      element.scrollTop -
                      element.clientHeight <
                    100;
                }}
              >
                {!selected ? (
                  <div className="welcome">
                    <BrandMark className="welcome-symbol" />
                    <p className="eyebrow">
                      {t("YOUR SPACE TO THINK & CREATE")}
                    </p>
                    <h1>
                      {t("Good stories start")}
                      <br />
                      {t("with a little curiosity.")}
                    </h1>
                    <p>
                      {t(
                        "Explore your news. Connect the dots. Make it your own.",
                      )}
                    </p>
                    <div className="suggestions">
                      {[
                        "What’s happening in AI today?",
                        "Explain a story from my sources",
                        "Turn an idea into a post",
                      ].map((t) => (
                        <button
                          key={t}
                          onClick={() => setDrafts((d) => ({ ...d, new: t }))}
                        >
                          {t}
                          <span>↗</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="transcript">
                    {detail?.has_more && (
                      <button
                        onClick={async () => {
                          try {
                            const older = await call("chat.detail", {
                              conversation_id: selected,
                              before_message_id: detail.next_before_message_id,
                            });
                            setDetail({
                              ...older,
                              messages: [...older.messages, ...detail.messages],
                            });
                          } catch (e) {
                            setError(String(e));
                          }
                        }}
                      >
                        {t("Load earlier messages")}
                      </button>
                    )}
                    {detail?.messages?.map((m: RecordData) => (
                      <article key={m.id} className={"message " + m.role}>
                        {m.activity && <Trace data={m.activity} />}
                        <Markdown text={m.content} />
                        {m.citations?.length > 0 && (
                          <details className="citations">
                            <summary>
                              {t("Sources ·")}
                              {m.citations.length}
                            </summary>
                            {m.citations.map((c: RecordData) => (
                              <p key={c.id || c.url}>
                                {c.title}
                                <small>{c.url}</small>
                              </p>
                            ))}
                          </details>
                        )}
                        {m.outputs?.map((o: RecordData, i: number) => (
                          <div className="draft-artifact" key={i}>
                            <span>{o.format?.replaceAll("_", " ")}</span>
                            <Markdown text={o.text || ""} />
                            <button
                              onClick={() =>
                                navigator.clipboard.writeText(o.text || "")
                              }
                            >
                              {t("Copy draft")}
                            </button>
                          </div>
                        ))}
                      </article>
                    ))}
                    {running && (
                      <article className="message assistant">
                        <Trace data={progress[selected] || {}} running />
                        <Markdown text={progress[selected]?.message || ""} />
                      </article>
                    )}
                  </div>
                )}
              </div>
              <div className="composer-wrap">
                {options && (
                  <ConversationOptions
                    conversation={selected}
                    selected={attachments[selected || "new"] || []}
                    onSelect={(rows) =>
                      setAttachments((old) => ({
                        ...old,
                        [selected || "new"]: rows,
                      }))
                    }
                    onError={setError}
                  />
                )}
                <div className="composer">
                  {(attachments[selected || "new"] || []).length > 0 && (
                    <div className="attached-articles">
                      {(attachments[selected || "new"] || []).map((a) => (
                        <button
                          key={a.id}
                          onClick={() =>
                            setAttachments((old) => ({
                              ...old,
                              [selected || "new"]: (
                                old[selected || "new"] || []
                              ).filter((row) => row.id !== a.id),
                            }))
                          }
                          title={t("Remove attachment")}
                        >
                          {a.title} ×
                        </button>
                      ))}
                    </div>
                  )}
                  <textarea
                    aria-label={t("Message")}
                    rows={2}
                    placeholder={t("Ask a question, explore an idea…")}
                    value={message}
                    dir="auto"
                    onChange={(e) =>
                      setDrafts((d) => ({
                        ...d,
                        [selected || "new"]: e.target.value,
                      }))
                    }
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault();
                        void send();
                      }
                    }}
                  />
                  {message.startsWith("/") && (
                    <div className="slash-menu">
                      {[
                        "research",
                        "summarize",
                        "x",
                        "thread",
                        "shorts",
                        "hooks",
                        "linkedin",
                        "youtube",
                        "rewrite",
                        "plan",
                      ]
                        .filter((x) => x.startsWith(message.slice(1)))
                        .map((x) => (
                          <button
                            key={x}
                            onClick={() =>
                              setDrafts((d) => ({
                                ...d,
                                [selected || "new"]: "/" + x + " ",
                              }))
                            }
                          >
                            /{x}
                          </button>
                        ))}
                    </div>
                  )}
                  <div className="composer-tools">
                    <button
                      onClick={() => setOptions(!options)}
                      aria-expanded={options}
                      title={t("Articles and conversation instructions")}
                    >
                      <Plus size={18} />
                    </button>
                    <select
                      aria-label={t("Model connection")}
                      value={profile}
                      onChange={(e) => {
                        setAgent("");
                        setProfile(e.target.value);
                        setModel(
                          profiles.find(
                            (p: RecordData) => p.id === e.target.value,
                          )?.model_id || "",
                        );
                      }}
                    >
                      <option value="">{t("Select a model")}</option>
                      {profiles.map((p: RecordData) => (
                        <option key={p.id} value={p.id}>
                          {p.label || p.model_id || p.provider_key}
                        </option>
                      ))}
                    </select>
                    {availableModels.length > 0 && (
                      <select
                        aria-label={t("Model")}
                        value={model}
                        onChange={(e) => {
                          setAgent("");
                          setModel(e.target.value);
                        }}
                      >
                        {availableModels.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name || m.id}
                          </option>
                        ))}
                      </select>
                    )}
                    {agents.length > 0 && (
                      <select
                        aria-label={t("Assistant")}
                        value={agent}
                        onChange={(e) => {
                          setAgent(e.target.value);
                          const chosen = agents.find(
                            (a) => a.id === e.target.value,
                          );
                          if (chosen) {
                            setProfile(chosen.profile_id);
                            setModel(chosen.model_id);
                          }
                        }}
                      >
                        <option value="">{t("Default assistant")}</option>
                        {agents.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                          </option>
                        ))}
                      </select>
                    )}
                    <details className="context-options">
                      <summary>{t("Context")}</summary>
                      <label>
                        <input
                          type="checkbox"
                          checked={includeNews}
                          onChange={(e) => setIncludeNews(e.target.checked)}
                        />
                        {t("Use saved news")}
                      </label>
                      <label>
                        <input
                          type="checkbox"
                          checked={researchWeb}
                          onChange={(e) => setResearchWeb(e.target.checked)}
                        />
                        {t("Allow web research")}
                      </label>
                    </details>
                    <button
                      className="send"
                      title={t(
                        running ? t("Stop response") : t("Send message"),
                      )}
                      disabled={
                        !running && (!message.trim() || sending || !ready)
                      }
                      onClick={() => {
                        if (running)
                          void call("jobs.cancel", { job_id: running })
                            .then(refresh)
                            .catch((e) => setError(String(e)));
                        else void send();
                      }}
                    >
                      {running ? <Square size={16} /> : <ArrowUp size={18} />}
                    </button>
                  </div>
                </div>
                <div className="composer-hint">
                  {!consent ? (
                    <label>
                      <input
                        type="checkbox"
                        checked={consent}
                        onChange={(e) => {
                          setConsent(e.target.checked);
                          localStorage.setItem(
                            "model-consent",
                            String(e.target.checked),
                          );
                        }}
                      />
                      {t(
                        "Allow sending messages and context to my selected model.",
                      )}
                    </label>
                  ) : running ? (
                    "You can switch conversations. Your response will keep running."
                  ) : (
                    t("Your ideas stay here. Review sources before publishing.")
                  )}
                </div>
              </div>
            </div>
          ) : page === "articles" ? (
            <Articles
              snapshot={snapshot}
              onError={setError}
              onDiscuss={(article) => {
                navigationVersion.current += 1;
                setSelected("");
                setDetail(undefined);
                setPage("chat");
                setAttachments((old) => ({ ...old, new: [article] }));
                setDrafts((old) => ({
                  ...old,
                  new: t("Discuss this article with me") + ": " + article.title,
                }));
              }}
            />
          ) : page === "sources" ? (
            <Sources snapshot={snapshot} refresh={refresh} onError={setError} />
          ) : page === "drafts" ? (
            <Drafts snapshot={snapshot} onError={setError} />
          ) : page === "settings" ? (
            <Settings
              snapshot={snapshot}
              refresh={refresh}
              theme={theme}
              setTheme={setTheme}
              onError={setError}
            />
          ) : (
            <div className="page">
              <p className="eyebrow">{t("HAPPENING IN YOUR WORKSPACE")}</p>
              <h1>{t("Background activity")}</h1>
              <p className="muted">
                {t(
                  "Work continues as you move between conversations and articles.",
                )}
              </p>
              <div className="activity-list">
                {(snapshot.jobs || []).length === 0 ? (
                  <div className="empty">
                    <Check />
                    <h3>{t("All quiet for now")}</h3>
                    <p>
                      {t("Searches, reading and responses will appear here.")}
                    </p>
                  </div>
                ) : (
                  (snapshot.jobs || []).map((j: RecordData) => (
                    <div key={j.id}>
                      <Activity size={17} />
                      <span>
                        {j.type}
                        <small>{j.error_code || j.updated_at}</small>
                      </span>
                      <span className={"status " + j.state}>{j.state}</span>
                      {active(j.state) && (
                        <button
                          onClick={() =>
                            void call("jobs.cancel", { job_id: j.id }).then(
                              refresh,
                            )
                          }
                        >
                          {t("Stop")}
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </Suspense>
      </main>
    </div>
  );
}
function QuickReader() {
  useLocale();
  const [snapshot, setSnapshot] = useState<RecordData>({});
  const [error, setError] = useState("");
  useEffect(() => {
    document.documentElement.dataset.theme =
      localStorage.getItem("theme") || "light";
    let alive = true;
    const refresh = () =>
      void call("workspace.snapshot", {})
        .then((value) => {
          if (alive) setSnapshot(value);
        })
        .catch((e) => {
          if (alive) setError(String(e));
        });
    refresh();
    const timer = window.setInterval(refresh, 15000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);
  return (
    <main className="quick-reader">
      {error && <p role="alert">{error}</p>}
      <Suspense fallback={<p>{t("Retrieving article text…")}</p>}>
        <Articles snapshot={snapshot} onError={setError} />
      </Suspense>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(
  new URLSearchParams(window.location.search).has("reader") ? (
    <QuickReader />
  ) : (
    <App />
  ),
);
