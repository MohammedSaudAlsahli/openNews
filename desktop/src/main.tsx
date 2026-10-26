import { ChatComposer, ModelPicker } from "./chat-composer";
import { ChatMessage } from "./chat-message";
import { ConversationList } from "./conversation-list";
import { navigateSafely } from "./unsaved-changes";
import { SupportPanel } from "./support-panel";
import { APP_NAME } from "./app-channel";
import { BrandMark } from "./brand";
import { NavigationRail } from "./navigation-rail";
import { Onboarding } from "./onboarding";
import { ActivityPage } from "./activity-page";
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
  ArrowDown,
  X,
  HelpCircle,
} from "lucide-react";
import { Markdown, Trace } from "./components";
import { call, active, duration, language, type RecordData } from "./engine";
import "./style.css";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
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
export function App() {
  const locale = useLocale();
  const [support, setSupport] = useState(false);
  const [reportCode, setReportCode] = useState("");
  const [uncleanExit, setUncleanExit] = useState(false);
  useEffect(() => {
    void invoke<boolean>("previous_unclean_exit")
      .then(setUncleanExit)
      .catch(() => {});
  }, []);
  const [files, setFiles] = useState<
    Record<string, { name: string; text: string }[]>
  >({});
  const fileInput = useRef<HTMLInputElement>(null);
  const diagnosticStates = useRef(new Map<string, string>());

  const [showWelcome, setShowWelcome] = useState(
    localStorage.getItem("welcome-dismissed") !== "true",
  );
  const [newVersion, setNewVersion] = useState("");
  const [options, setOptions] = useState(false);
  const [awayFromLatest, setAwayFromLatest] = useState(false);
  const [attachments, setAttachments] = useState<Record<string, RecordData[]>>(
    {},
  );
  const [includeNews, setIncludeNews] = useState(true),
    [researchWeb, setResearchWeb] = useState(true);
  const [availableModels, setAvailableModels] = useState<RecordData[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false),
    [modelsError, setModelsError] = useState(""),
    [modelsAttempt, setModelsAttempt] = useState(0);
  const [page, changePage] = useState("chat"),
    [sidebar, setSidebar] = useState(window.innerWidth > 1050),
    [ready, setReady] = useState(false),
    [error, setError] = useState("");
  const previousSidebar = useRef(sidebar);
  const [sidebarMotion, setSidebarMotion] = useState(false);
  useEffect(() => {
    if (previousSidebar.current === sidebar) return;
    previousSidebar.current = sidebar;
    const frame = requestAnimationFrame(() =>
      document
        .querySelector<HTMLButtonElement>(
          sidebar ? ".brand button" : ".navigation-rail button",
        )
        ?.focus(),
    );
    return () => cancelAnimationFrame(frame);
  }, [sidebar]);
  const [libraryRequest, setLibraryRequest] = useState(0);
  const setPage = (next: string) =>
    navigateSafely(() => {
      if (next === "articles") setLibraryRequest((value) => value + 1);
      changePage(next);
    });
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
    [stopping, setStopping] = useState(false),
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
    // Match native macOS chrome to the reader's explicitly chosen appearance.
    void (async () => {
      try {
        await getCurrentWindow().setTheme(theme === "dark" ? "dark" : "light");
      } catch {
        // Browser fixtures have no native window.
      }
    })();
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
    setChats(c.conversations || []);
  }, []);
  useEffect(() => {
    void call("agents.list")
      .then((r) => setAgents(r.agents || []))
      .catch(() => {});
  }, [page]);
  useEffect(() => {
    for (const row of [
      ...(snapshot.subscriptions || []),
      ...(snapshot.jobs || []),
    ]) {
      const failed = row.status === "error" || row.state === "failed";
      const stamp = `${row.status || row.state}:${row.last_checked || row.updated_at || ""}`;
      if (failed && diagnosticStates.current.get(row.id) !== stamp) {
        void invoke("record_diagnostic", {
          operation: row.status ? "feed.sync" : "background.job",
          code: row.status ? "SOURCE_FETCH_FAILED" : "JOB_FAILED",
        }).catch(() => {});
      }
      diagnosticStates.current.set(row.id, stamp);
    }
  }, [snapshot]);
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
  const sendLock = useRef(false);
  const stopLock = useRef(false);
  const pendingConversation = useRef<
    { id: string; navigation: number } | undefined
  >(undefined);
  const pendingSend = useRef<{ signature: string; key: string } | undefined>(
    undefined,
  );
  const transcript = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const selectionRef = useRef(selected);
  selectionRef.current = selected;
  const earlierRequest = useRef<object | null>(null);
  const [loadingEarlier, setLoadingEarlier] = useState(false);
  useEffect(() => {
    earlierRequest.current = null;
    setLoadingEarlier(false);
  }, [selected]);
  const running = chats.find((c) => c.id === selected)?.active_job_id;
  useEffect(() => {
    if (!selected) {
      setDetail(undefined);
      return;
    }
    let live = true;
    call("chat.detail", { conversation_id: selected })
      .then((d) => {
        if (live)
          setDetail((previous) => {
            if (!previous || previous.id !== d.id) return d;
            const incoming = new Set(
              (d.messages || []).map((m: RecordData) => m.id),
            );
            return {
              ...d,
              ...(previous.messages?.[0] &&
              !incoming.has(previous.messages[0].id)
                ? {
                    has_more: previous.has_more,
                    next_before_message_id: previous.next_before_message_id,
                  }
                : {}),
              messages: [
                ...(previous.messages || []).filter(
                  (m: RecordData) => !incoming.has(m.id),
                ),
                ...(d.messages || []),
              ],
            };
          });
      })
      .catch((e) => {
        if (live) setError(String(e));
      });
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
    setModelsError("");
    setModelsLoading(Boolean(profile));
    if (profile)
      void call("providers.models", { profile_id: profile })
        .then((r) => {
          if (live) {
            setAvailableModels(r.models || []);
            if (r.error) setModelsError(String(r.error));
          }
        })
        .catch((e) => {
          if (live) setModelsError(String(e));
        })
        .finally(() => {
          if (live) setModelsLoading(false);
        });
    return () => {
      live = false;
    };
  }, [profile, modelsAttempt]);
  async function send() {
    const key = selected || "new",
      original = drafts[key] || "",
      text = original.trim();
    if (!text || !ready || sendLock.current || running) return;
    if (!profile || !model) {
      setPage("settings");
      setError(t("Connect a model in Settings before sending."));
      return;
    }
    if (!consent) {
      setError(
        t(
          "Enable model access below. Your message and selected context will be sent to your chosen provider.",
        ),
      );
      return;
    }
    const sentFiles = files[key] || [],
      sentArticles = attachments[key] || [];
    const fileText = sentFiles
      .map(
        (f) => `

--- Attached file: ${f.name} ---
${f.text}
--- End attached file ---`,
      )
      .join("");
    if ((text + fileText).length > 12000) {
      setError(t("Message and files must fit within 12,000 characters."));
      return;
    }
    const startedAtNavigation = navigationVersion.current;
    sendLock.current = true;
    setSending(true);
    setError("");
    try {
      let id = selected;
      if (!id) {
        if (pendingConversation.current?.navigation === startedAtNavigation) {
          id = pendingConversation.current.id;
        } else {
          id = (await call("chat.create", { title: text.slice(0, 80) }))
            .conversation_id;
          pendingConversation.current = { id, navigation: startedAtNavigation };
        }
      }
      const payload = {
        conversation_id: id,
        message: text + fileText,
        ui_language: locale,
        profile_id: profile,
        model_id: model,
        consent: true,
        format: "auto",
        article_ids: sentArticles.map((a) => a.id),
        include_news: includeNews,
        research_web: researchWeb,
        ...(agent ? { agent_id: agent } : {}),
      };
      const signature = JSON.stringify(payload);
      if (pendingSend.current?.signature !== signature)
        pendingSend.current = { signature, key: crypto.randomUUID() };
      const result = await call("chat.send", {
        ...payload,
        idempotency_key: pendingSend.current.key,
      });
      pendingSend.current = undefined;
      const stillHere = navigationVersion.current === startedAtNavigation;
      if (key !== "new" || stillHere) {
        // Consume only the submitted content. A follow-up typed during this
        // request belongs to the composer, not to the acknowledged message.
        setDrafts((d) => ({
          ...d,
          [key]: "",
          [id]: d[key] === original ? "" : d[key] || "",
        }));
        setFiles((f) => ({
          ...f,
          [key]: [],
          [id]: (f[key] || []).filter((row) => !sentFiles.includes(row)),
        }));
        setAttachments((a) => ({
          ...a,
          [key]: [],
          [id]: (a[key] || []).filter((row) => !sentArticles.includes(row)),
        }));
      }
      if (!selected && stillHere) {
        selectionRef.current = id;
        setSelected(id);
      }
      setChats((old) => [
        {
          ...old.find((row) => row.id === id),
          id,
          title: text.slice(0, 80),
          active_job_id: result.job_id,
        },
        ...old.filter((row) => row.id !== id),
      ]);
      setProgress((p) => ({
        ...p,
        [id]: { job_id: result.job_id, state: "queued" },
      }));
      try {
        await refresh();
        const updated = await call("chat.detail", { conversation_id: id });
        if (selectionRef.current === id) setDetail(updated);
      } catch {
        setError(
          t(
            "Message sent. The conversation view could not refresh; it will retry automatically.",
          ),
        );
      }
    } catch (e) {
      setError(String(e));
    } finally {
      sendLock.current = false;
      setSending(false);
    }
  }
  function choose(id: string, skill?: string, starter?: string) {
    navigateSafely(() => {
      if (skill)
        setDrafts((old) => ({
          ...old,
          new: `/${skill} ${(old.new || "").replace(/^\/[\w-]+\s*/, "")}`,
        }));
      if (starter)
        setDrafts((old) => ({
          ...old,
          new: [old.new, starter].filter(Boolean).join("\n\n"),
        }));
      navigationVersion.current += 1;
      followLatest.current = true;
      selectionRef.current = id;
      setSelected(id);
      changePage("chat");
      setOptions(false);
      setDetail(undefined);
    });
  }
  async function stopResponse() {
    if (!running || stopLock.current) return;
    stopLock.current = true;
    setStopping(true);
    try {
      await call("jobs.cancel", { job_id: running });
      await refresh().catch(() =>
        setError(
          t(
            "Stop requested. The conversation view will refresh automatically.",
          ),
        ),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      stopLock.current = false;
      setStopping(false);
    }
  }
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === ",") {
        event.preventDefault();
        setPage("settings");
        return;
      }
      if (
        (event.metaKey || event.ctrlKey) &&
        event.shiftKey &&
        event.key.toLowerCase() === "b"
      ) {
        event.preventDefault();
        setSidebarMotion(false);
        setSidebar((s) => !s);
        return;
      }
      if (event.key === "Escape" && !event.defaultPrevented) {
        if (document.querySelector('dialog[open], [role="dialog"]')) return;
        navigateSafely(() => setOptions(false));
        setSupport(false);
      }
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
  function selectProfile(id: string) {
    setAgent("");
    setProfile(id);
    setModel(profiles.find((p: RecordData) => p.id === id)?.model_id || "");
  }
  function selectAgent(id: string) {
    setAgent(id);
    const choice = agents.find((a) => a.id === id);
    if (choice) {
      setProfile(choice.profile_id);
      setModel(choice.model_id);
    }
  }
  const key = selected || "new";
  const staged = attachments[key] || [];
  const stagedFiles = files[key] || [];
  function attachArticle(row: RecordData) {
    if (staged.some((a) => a.id === row.id)) return;
    if (staged.length >= 12) {
      setError(t("Attach up to 12 articles."));
      return;
    }
    setAttachments((old) => ({
      ...old,
      [key]: [...(old[key] || []), { id: row.id, title: row.title }],
    }));
  }
  async function attachFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0],
      draftKey = key;
    event.target.value = "";
    if (!file) return;
    try {
      if (!/\.(txt|md|csv|json)$/i.test(file.name) || file.size > 48000)
        throw new Error(
          t("Choose a text, Markdown, CSV or JSON file up to 48 KB."),
        );
      if (stagedFiles.length >= 3) throw new Error(t("Attach up to 3 files."));
      const text = await file.text();
      if (text.includes("\0") || text.length > 10000)
        throw new Error(
          t("Text files must contain at most 10,000 characters."),
        );
      setFiles((old) => ({
        ...old,
        [draftKey]: [...(old[draftKey] || []), { name: file.name, text }],
      }));
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <div
      className={`app ${sidebar ? "" : "collapsed"}`}
      data-sidebar-motion={sidebarMotion ? "pointer" : undefined}
    >
      <header className="window-chrome" data-tauri-drag-region>
        {!ready && (
          <span className="engine-starting" role="status">
            {t("Starting engine…")}
          </span>
        )}
      </header>
      {!sidebar && (
        <NavigationRail
          page={page}
          onNavigate={setPage}
          onNew={() => choose("")}
          onExpand={(pointer = false) => {
            setSidebarMotion(pointer);
            setSidebar(true);
          }}
          onHelp={() => {
            setReportCode("");
            setSupport(true);
          }}
          busy={
            (snapshot.jobs || []).filter((j: RecordData) => active(j.state))
              .length
          }
        />
      )}
      {support && (
        <SupportPanel
          incidentCode={reportCode}
          onClose={() => setSupport(false)}
          onError={setError}
        />
      )}
      <aside className="sidebar" hidden={!sidebar}>
        <div className="brand">
          <BrandMark className="brand-mark" />
          <strong>{APP_NAME}</strong>
          <button
            title={t("Hide sidebar")}
            aria-label={t("Hide sidebar")}
            onClick={(event) => {
              setSidebarMotion(event.detail > 0);
              setSidebar(false);
            }}
          >
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
        <ConversationList
          chats={chats}
          selected={page === "chat" ? selected : ""}
          search={search}
          onSearch={setSearch}
          onChoose={choose}
        />
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
          <button
            onClick={() => {
              setReportCode("");
              setSupport(true);
            }}
          >
            <HelpCircle size={16} />
            {t("Help & diagnostics")}
          </button>
          <div className="preview-note">
            <Circle size={7} fill="currentColor" />
            {APP_NAME}
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
        {uncleanExit && (
          <div className="error" role="alert">
            {t(
              "The previous session ended unexpectedly. You can review and report it.",
            )}
            <button
              onClick={() => {
                setReportCode("UNEXPECTED_EXIT");
                setSupport(true);
                setUncleanExit(false);
              }}
            >
              {t("Report problem")}
            </button>
            <button onClick={() => setUncleanExit(false)}>
              {t("Dismiss")}
            </button>
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
            <button
              onClick={() => {
                setReportCode(
                  error.match(/\b[A-Z][A-Z_]{3,50}\b/)?.[0] || "REQUEST_FAILED",
                );
                setSupport(true);
              }}
            >
              {t("Report problem")}
            </button>
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
            <div className={"chat " + (!selected ? "is-new" : "")}>
              <div className="chat-toolbar">
                <ModelPicker
                  profiles={profiles}
                  profile={profile}
                  model={model}
                  models={availableModels}
                  loading={modelsLoading}
                  error={modelsError}
                  onRetry={() => setModelsAttempt((value) => value + 1)}
                  onProfile={selectProfile}
                  onModel={setModel}
                  onSettings={() => {
                    sessionStorage.setItem("settings-tab", "connections");
                    setPage("settings");
                  }}
                />
                {selected && (
                  <span className="chat-toolbar-title" dir="auto">
                    {detail?.title ||
                      chats.find((c) => c.id === selected)?.title}
                  </span>
                )}
                <span className="local-scope">{t("Private workspace")}</span>
              </div>
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
                  setAwayFromLatest(!followLatest.current);
                }}
              >
                {!selected ? (
                  <div className="welcome">
                    <BrandMark className="welcome-symbol" />
                    {ready &&
                    showWelcome &&
                    !(
                      snapshot.subscriptions?.length ||
                      snapshot.profiles?.length
                    ) ? (
                      <Onboarding
                        go={setPage}
                        close={() => {
                          setShowWelcome(false);
                          localStorage.setItem("welcome-dismissed", "true");
                        }}
                      />
                    ) : (
                      <>
                        <h1>{t("What would you like to explore?")}</h1>
                        <p>
                          {t(
                            "Read your news, connect ideas, and make something of them.",
                          )}
                        </p>
                        <div className="suggestions">
                          {[
                            "What’s happening in AI today?",
                            "Explain a story from my sources",
                            "Turn an idea into a post",
                          ].map((prompt) => (
                            <button
                              key={prompt}
                              onClick={() =>
                                setDrafts((d) => ({ ...d, new: t(prompt) }))
                              }
                            >
                              {t(prompt)}
                              <ArrowUp size={15} />
                            </button>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="transcript">
                    {!detail && (
                      <div
                        className="conversation-skeleton"
                        role="status"
                        aria-label={t("Opening conversation…")}
                      >
                        <div className="skeleton-line" />
                        <div className="skeleton-line short" />
                      </div>
                    )}
                    {detail?.has_more && (
                      <button
                        className="load-earlier"
                        disabled={loadingEarlier}
                        onClick={async () => {
                          if (earlierRequest.current) return;
                          const request = {};
                          earlierRequest.current = request;
                          setLoadingEarlier(true);
                          const conversationId = selected;
                          const atNavigation = navigationVersion.current;
                          try {
                            const height =
                              transcript.current?.scrollHeight || 0;
                            const top = transcript.current?.scrollTop || 0;
                            const older = await call("chat.detail", {
                              conversation_id: selected,
                              before_message_id: detail.next_before_message_id,
                            });
                            if (
                              selectionRef.current !== conversationId ||
                              earlierRequest.current !== request
                            )
                              return;
                            followLatest.current = false;
                            setDetail((current) => {
                              if (!current || current.id !== conversationId)
                                return current;
                              const known = new Set(
                                current.messages.map(
                                  (message: RecordData) => message.id,
                                ),
                              );
                              return {
                                ...current,
                                has_more: older.has_more,
                                next_before_message_id:
                                  older.next_before_message_id,
                                messages: [
                                  ...older.messages.filter(
                                    (message: RecordData) =>
                                      !known.has(message.id),
                                  ),
                                  ...current.messages,
                                ],
                              };
                            });
                            requestAnimationFrame(() => {
                              if (
                                transcript.current &&
                                selectionRef.current === conversationId &&
                                navigationVersion.current === atNavigation
                              )
                                transcript.current.scrollTop =
                                  top +
                                  transcript.current.scrollHeight -
                                  height;
                            });
                          } catch (e) {
                            if (earlierRequest.current === request)
                              setError(String(e));
                          } finally {
                            if (earlierRequest.current === request) {
                              earlierRequest.current = null;
                              setLoadingEarlier(false);
                            }
                          }
                        }}
                      >
                        {loadingEarlier && (
                          <LoaderCircle
                            size={14}
                            className="spin"
                            aria-hidden="true"
                          />
                        )}
                        {t(
                          loadingEarlier
                            ? "Loading earlier messages…"
                            : "Load earlier messages",
                        )}
                      </button>
                    )}
                    {detail?.messages?.map((m: RecordData) => (
                      <ChatMessage
                        key={m.id}
                        message={m}
                        onError={setError}
                        onDraft={() => setPage("drafts")}
                      />
                    ))}
                    {running && (
                      <article className="message assistant">
                        <Trace data={progress[selected] || {}} running />
                        <Markdown
                          text={progress[selected]?.message || ""}
                          citations={progress[selected]?.citations || []}
                        />
                      </article>
                    )}
                    {!running &&
                      ["failed", "cancelled"].includes(
                        detail?.last_job?.state,
                      ) && (
                        <article
                          className="message assistant response-notice"
                          role={
                            detail?.last_job?.state === "failed"
                              ? "alert"
                              : "status"
                          }
                        >
                          <Trace
                            data={{
                              ...progress[selected],
                              state: detail?.last_job?.state,
                            }}
                          />
                          <p>
                            {t(
                              detail?.last_job?.state === "failed"
                                ? "The response could not finish. Your message is saved. You can try again or report the problem."
                                : "The response was stopped. Your message is saved.",
                            )}
                          </p>
                          {detail?.last_job?.state === "failed" && (
                            <button
                              onClick={() => {
                                setReportCode(
                                  detail?.last_job?.error_code ||
                                    "CHAT_RESPONSE_FAILED",
                                );
                                setSupport(true);
                              }}
                            >
                              {t("Report problem")}
                            </button>
                          )}
                        </article>
                      )}
                  </div>
                )}
              </div>
              <div className="composer-wrap">
                {awayFromLatest && selected && (
                  <button
                    className="jump-latest icon-button"
                    aria-label={t("Jump to latest")}
                    onClick={() => {
                      followLatest.current = true;
                      transcript.current?.scrollTo({
                        top: transcript.current.scrollHeight,
                      });
                      setAwayFromLatest(false);
                    }}
                  >
                    <ArrowDown size={18} />
                  </button>
                )}
                {options && (
                  <ConversationOptions
                    onClose={() => setOptions(false)}
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
                <input
                  type="file"
                  ref={fileInput}
                  hidden
                  accept=".txt,.md,.csv,.json"
                  onChange={(e) => void attachFile(e)}
                />
                <ChatComposer
                  message={message}
                  onMessage={(value) =>
                    setDrafts((d) => ({ ...d, [key]: value }))
                  }
                  onSend={() => void send()}
                  onStop={() => void stopResponse()}
                  stopping={stopping}
                  running={Boolean(running)}
                  sending={sending}
                  ready={ready}
                  onArticles={() =>
                    navigateSafely(() => setOptions((value) => !value))
                  }
                  onFile={() => fileInput.current?.click()}
                  onArticle={attachArticle}
                  onError={setError}
                  includeNews={includeNews}
                  researchWeb={researchWeb}
                  onNews={setIncludeNews}
                  onWeb={setResearchWeb}
                  agents={agents}
                  agent={agent}
                  onAgent={selectAgent}
                  attachments={
                    <div className="attached-articles">
                      {staged.map((a) => (
                        <button
                          key={a.id}
                          title={t("Remove attachment")}
                          onClick={() =>
                            setAttachments((old) => ({
                              ...old,
                              [key]: (old[key] || []).filter(
                                (row) => row.id !== a.id,
                              ),
                            }))
                          }
                        >
                          <Newspaper size={14} />
                          <span>{a.title}</span>
                          <X size={13} />
                        </button>
                      ))}
                      {stagedFiles.map((f, i) => (
                        <button
                          key={i}
                          title={t("Remove attachment")}
                          onClick={() =>
                            setFiles((old) => ({
                              ...old,
                              [key]: (old[key] || []).filter((_, j) => j !== i),
                            }))
                          }
                        >
                          <FileText size={14} />
                          <span>{f.name}</span>
                          <X size={13} />
                        </button>
                      ))}
                    </div>
                  }
                />
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
                    t(
                      "You can switch conversations. Your response will keep running.",
                    )
                  ) : (
                    t("Your ideas stay here. Review sources before publishing.")
                  )}
                </div>
              </div>
            </div>
          ) : page === "articles" ? (
            <Articles
              libraryRequest={libraryRequest}
              snapshot={snapshot}
              onExploreSources={() => setPage("sources")}
              onError={setError}
              onConfigureExplanations={() => {
                sessionStorage.setItem("settings-tab", "summaries");
                setPage("settings");
              }}
              onDiscuss={(article) => {
                if (
                  (attachments.new || []).length >= 12 &&
                  !(attachments.new || []).some((row) => row.id === article.id)
                ) {
                  setError(t("Attach up to 12 articles."));
                  return;
                }
                navigateSafely(() => {
                  navigationVersion.current += 1;
                  selectionRef.current = "";
                  setSelected("");
                  setDetail(undefined);
                  setOptions(false);
                  changePage("chat");
                  setAttachments((old) => ({
                    ...old,
                    new: (old.new || []).some((row) => row.id === article.id)
                      ? old.new
                      : [...(old.new || []), article],
                  }));
                  setDrafts((old) => ({
                    ...old,
                    new: [
                      old.new,
                      article.discussion_prompt || t("Discuss this article with me") + ": " + article.title,
                    ]
                      .filter(Boolean)
                      .join("\n\n"),
                  }));
                });
              }}
            />
          ) : page === "sources" ? (
            <Sources snapshot={snapshot} refresh={refresh} onError={setError} />
          ) : page === "drafts" ? (
            <Drafts snapshot={snapshot} onError={setError} refresh={refresh} />
          ) : page === "settings" ? (
            <Settings
              onUseSkill={(id) => choose("", id)}
              onRecommendSkills={() =>
                choose(
                  "",
                  undefined,
                  t(
                    "Find useful writing and research skills for openNews. Search the directory, read the original instructions, and suggest a few with their sources and any missing requirements. Let me choose what to add.",
                  ),
                )
              }
              snapshot={snapshot}
              refresh={refresh}
              theme={theme}
              setTheme={setTheme}
              onError={setError}
            />
          ) : (
            <ActivityPage
              jobs={snapshot.jobs || []}
              refresh={refresh}
              onReport={(code) => {
                setReportCode(code);
                setSupport(true);
              }}
            />
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
const root =
  import.meta.hot?.data?.root ?? createRoot(document.getElementById("root")!);
if (import.meta.hot?.data) import.meta.hot.data.root = root;
root.render(
  new URLSearchParams(window.location.search).has("reader") ? (
    <QuickReader />
  ) : (
    <App />
  ),
);
