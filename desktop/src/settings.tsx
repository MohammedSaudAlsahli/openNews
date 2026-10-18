import { Updates } from "./updates";
import { t, useLocale, setLocale } from "./locale";
import { invoke } from "@tauri-apps/api/core";
import { Agents } from "./agents";
import { WritingLibrary } from "./writing-library";
import { TaskInstructions } from "./task-instructions";
import { ModelLibrary } from "./model-library";
import { Connections } from "./connections";
import { useEffect, useState } from "react";
import {
  Check,
  SlidersHorizontal,
  Cpu,
  Calendar,
  BookOpen,
  Search,
  Sun,
  Moon,
  Shield,
  LoaderCircle,
} from "lucide-react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
export default function Settings({
  snapshot,
  refresh,
  theme,
  setTheme,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  theme: string;
  setTheme: (s: string) => void;
  onError: (s: string) => void;
}) {
  const locale = useLocale();
  const [tab, setTab] = useState(
      sessionStorage.getItem("settings-tab") || "instructions",
    ),
    [data, setData] = useState<RecordData>({}),
    [section, setSection] = useState("role"),
    [instructionScope, setInstructionScope] = useState("general"),
    [skill, setSkill] = useState("research"),
    [preview, setPreview] = useState(false),
    [busy, setBusy] = useState(false),
    [saved, setSaved] = useState(false),
    [indexedArticles, setIndexedArticles] = useState<RecordData[]>([]);
  const statusLabels: Record<string, string> = {
    enabled: "Background processing",
    language: "Explanation language",
    prepared: "Articles explained",
    pending: "Articles waiting",
    current_title: "Working on",
    phase: "Current status",
    daily_limit: "Daily request limit",
    used_today: "Requests used today",
    local_model: "Explanation model",
    model: "Search model",
    indexed: "Articles searchable by text",
    semantic: "Articles searchable by meaning",
  };
  const phases: Record<string, string> = {
    disabled: "Off",
    needs_model: "Choose a model to begin",
    needs_download: "Model download required",
    summarizing: "Explaining an article",
    daily_limit: "Daily limit reached",
    waiting_model: "Waiting for the model",
    ready: "Up to date",
    waiting_articles: "Waiting for articles",
    retrying: "Waiting before retry",
    queued: "Ready to start",
    idle: "Idle",
    indexing: "Indexing articles",
  };
  const sections: Record<string, string> = {
    role: "Role & expertise",
    instructions: "Working instructions",
    style: "Writing style",
    knowledge: "Sources & knowledge",
    examples: "Examples",
    output: "Response format",
    system_prompt: "System prompt",
    developer_prompt: "Developer prompt",
  };
  useEffect(() => {
    let live = true;
    setSaved(false);
    setData({});
    const command = (
      {
        instructions: "assistant.get",
        daily: "daily.get",
        search: "news.search.status",
        summaries: "news.digest.status",
      } as Record<string, string>
    )[tab];
    if (!command) return;
    setBusy(true);
    call(
      command,
      tab === "instructions"
        ? {
            scope: instructionScope === "general" ? "general" : "agent",
            target_id: instructionScope === "general" ? "" : instructionScope,
          }
        : {},
    )
      .then((r) => {
        if (live) {
          setData(r);
        }
      })
      .catch((e) => onError(String(e)))
      .finally(() => {
        if (live) setBusy(false);
      });
    return () => {
      live = false;
    };
  }, [tab, instructionScope]);
  useEffect(() => {
    if (tab !== "search" && tab !== "summaries") return;
    let live = true,
      inFlight = false;
    const timer = setInterval(async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const result = await call(
          tab === "search" ? "news.search.status" : "news.digest.status",
        );
        if (live) setData(result);
      } catch {
      } finally {
        inFlight = false;
      }
    }, 5000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [tab]);
  async function save() {
    setBusy(true);
    setSaved(false);
    try {
      if (tab === "instructions")
        await call("assistant.save", {
          scope: instructionScope === "general" ? "general" : "agent",
          target_id: instructionScope === "general" ? "" : instructionScope,
          settings: data.settings,
        });
      if (tab === "daily")
        await call("daily.set", { ...data.settings, consent: true });
      setSaved(true);
      await refresh();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  function setting(key: string, value: unknown) {
    setData((d) => ({ ...d, settings: { ...d.settings, [key]: value } }));
    setSaved(false);
  }
  return (
    <div className="settings-layout">
      <aside className="settings-nav">
        <p className="eyebrow">{t("MAKE IT YOURS")}</p>
        <h1>{t("Settings")}</h1>
        {[
          [SlidersHorizontal, "instructions", "Assistant instructions"],
          [Cpu, "connections", "Model connections"],
          [SlidersHorizontal, "agents", "Assistants"],
          [BookOpen, "writing", "Writing & references"],
          [BookOpen, "skills", "Writing skills"],
          [BookOpen, "summaries", "Article explanations"],
          [Search, "search", "News memory"],
          [Calendar, "daily", "Daily report"],
          [Sun, "appearance", "Appearance"],
          [Shield, "privacy", "Privacy & updates"],
        ].map(([Icon, id, title]) => {
          const I = Icon as typeof Sun;
          return (
            <button
              key={id as string}
              className={tab === id ? "selected" : ""}
              onClick={() => setTab(id as string)}
            >
              <I size={16} />
              {t(title as string)}
            </button>
          );
        })}
      </aside>
      <div className="settings-content">
        {busy && <LoaderCircle className="spin busy-indicator" size={17} />}{" "}
        {tab === "instructions" ? (
          <>
            <h2>{t("Give your assistant a little direction.")}</h2>
            <p className="muted">
              {t(
                "These are the instructions it actually uses. Read them, make them yours, and save.",
              )}
            </p>
            <label className="field">
              {t("Applies to")}
              <select
                value={instructionScope}
                onChange={(e) => setInstructionScope(e.target.value)}
              >
                <option value="general">
                  {t("All assistants and conversations")}
                </option>
                <option value="writer">{t("Writing assistant")}</option>
                <option value="analyst">{t("Analysis assistant")}</option>
              </select>
            </label>
            <div className="instruction-tabs">
              {Object.entries(sections).map(([k, v]) => (
                <button
                  key={k}
                  className={section === k ? "selected" : ""}
                  onClick={() => setSection(k)}
                >
                  {t(v)}
                </button>
              ))}
            </div>
            <div className="editor-header">
              <h3>{t(sections[section])}</h3>
              <div className="segments">
                <button
                  className={!preview ? "selected" : ""}
                  onClick={() => setPreview(false)}
                >
                  {t("Write")}
                </button>
                <button
                  className={preview ? "selected" : ""}
                  onClick={() => setPreview(true)}
                >
                  {t("Preview")}
                </button>
              </div>
            </div>
            {preview ? (
              <div className="markdown-preview">
                <Markdown
                  text={
                    data.settings?.[section] || "No additional instructions."
                  }
                />
              </div>
            ) : (
              <textarea
                className="editor"
                dir="auto"
                aria-label={t(sections[section])}
                value={data.settings?.[section] || ""}
                onChange={(e) => setting(section, e.target.value)}
              />
            )}
            <div className="save-row">
              <small>{t("Saved locally · Applied to new responses")}</small>
              <button
                className="primary"
                disabled={busy}
                onClick={() => void save()}
              >
                {saved ? (
                  <>
                    <Check size={15} />
                    {t("Saved")}
                  </>
                ) : (
                  "Save instructions"
                )}
              </button>
            </div>
          </>
        ) : tab === "skills" ? (
          <>
            <h2>{t("Writing skills")}</h2>
            <p className="muted">
              {t(
                "Use a / command or describe what you need. The assistant can select the relevant writing guide from your request.",
              )}
            </p>
            <label className="field">
              {t("Skill")}
              <select value={skill} onChange={(e) => setSkill(e.target.value)}>
                {[
                  "research",
                  "summarize",
                  "x",
                  "thread",
                  "linkedin",
                  "youtube",
                  "shorts",
                  "rewrite",
                  "plan",
                  "hooks",
                ].map((id) => (
                  <option key={id} value={id}>
                    /{id}
                  </option>
                ))}
              </select>
            </label>
            <TaskInstructions
              key={skill}
              id={"skill:" + skill}
              title={"Instructions for /" + skill}
              onError={onError}
            />
          </>
        ) : tab === "agents" ? (
          <Agents snapshot={snapshot} refresh={refresh} onError={onError} />
        ) : tab === "writing" ? (
          <WritingLibrary
            snapshot={snapshot}
            refresh={refresh}
            onError={onError}
          />
        ) : tab === "connections" ? (
          <Connections
            snapshot={snapshot}
            refresh={refresh}
            onError={onError}
          />
        ) : tab === "daily" ? (
          <>
            <h2>{t("Your day, explained.")}</h2>
            <p className="muted">
              {t("Choose when to prepare a report from your sources.")}
            </p>
            <div className="settings-group">
              <label className="setting-row">
                {t("Daily report")}
                <input
                  type="checkbox"
                  checked={!!data.settings?.enabled}
                  onChange={(e) => setting("enabled", e.target.checked)}
                />
              </label>
              <label className="setting-row">
                {t("Report time")}
                <input
                  type="time"
                  value={`${String(data.settings?.hour ?? 22).padStart(2, "0")}:${String(data.settings?.minute ?? 0).padStart(2, "0")}`}
                  onChange={(e) => {
                    const [hour, minute] = e.target.value
                      .split(":")
                      .map(Number);
                    setData((d) => ({
                      ...d,
                      settings: { ...d.settings, hour, minute },
                    }));
                  }}
                />
              </label>
              <label className="setting-row">
                {t("Time zone")}
                <input
                  value={data.settings?.timezone || "Asia/Riyadh"}
                  onChange={(e) => setting("timezone", e.target.value)}
                />
              </label>
              <label className="setting-row">
                {t("Language")}
                <select
                  value={data.settings?.language || "ar"}
                  onChange={(e) => setting("language", e.target.value)}
                >
                  <option value="ar">العربية</option>
                  <option value="en">{t("English")}</option>
                </select>
              </label>
            </div>
            <button className="primary" onClick={() => void save()}>
              {t(saved ? t("Saved") : t("Save schedule"))}
            </button>
            <p className="notice">
              {t(
                "Reports run while OpenStudio is open, including with its window closed. If your Mac sleeps, the report is prepared when you return. Enable OpenStudio notifications in macOS System Settings.",
              )}
            </p>
            <TaskInstructions
              id="daily-report"
              title={t("Daily report instructions")}
              onError={onError}
            />
            {(data.reports || []).map((r: RecordData) => (
              <details key={r.id || r.day}>
                <summary>{r.day}</summary>
                <Markdown text={r.body || ""} />
              </details>
            ))}
          </>
        ) : tab === "appearance" ? (
          <>
            <h2>{t("A calmer place to work.")}</h2>
            <p className="muted">
              {t("A focused workspace, in the light that suits you.")}
            </p>
            <label className="setting-row">
              {t("Interface language")}
              <select
                value={locale}
                onChange={(e) => setLocale(e.target.value as "ar" | "en")}
              >
                <option value="en">English</option>
                <option value="ar">العربية</option>
              </select>
            </label>
            <div className="theme-options">
              <button
                aria-pressed={theme === "light"}
                className={theme === "light" ? "selected" : ""}
                onClick={() => setTheme("light")}
              >
                <Sun size={28} />
                <strong>{t("Daylight")}</strong>
                <small>{t("Warm paper and soft contrast")}</small>
              </button>
              <button
                aria-pressed={theme === "dark"}
                className={theme === "dark" ? "selected" : ""}
                onClick={() => setTheme("dark")}
              >
                <Moon size={28} />
                <strong>{t("After hours")}</strong>
                <small>{t("Quiet charcoal, readable text")}</small>
              </button>
            </div>
          </>
        ) : tab === "privacy" ? (
          <>
            <h2>{t("On your Mac. Under your control.")}</h2>
            <Updates onError={onError} />
            <p className="muted">
              {t(
                "This preview has its own workspace. Your current app and its data remain separate.",
              )}
            </p>
            <section className="notice">
              <h3>{t("Bring your original workspace")}</h3>
              <p>
                {t(
                  "Quit the original OpenStudio first. Import copies your articles, conversations, credentials, models and cached images. Your current preview workspace is backed up; the original stays intact. Automatic explanations, indexing and reports are paused until you enable them again.",
                )}
              </p>
              <div className="reader-actions">
                <button
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await invoke("transfer_workspace", { restore: false });
                      window.location.reload();
                    } catch (e) {
                      onError(String(e));
                      setBusy(false);
                    }
                  }}
                >
                  {t("Import original workspace")}
                </button>
                <button
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await invoke("transfer_workspace", { restore: true });
                      window.location.reload();
                    } catch (e) {
                      onError(String(e));
                      setBusy(false);
                    }
                  }}
                >
                  {t("Restore previous workspace")}
                </button>
              </div>
            </section>
            <div className="settings-group">
              <div className="setting-row">
                {t("Storage")}
                <span>{t("Local SQLite")}</span>
              </div>
              <div className="setting-row">
                {t("Engine")}
                <span>{t("Python + Agno")}</span>
              </div>
              <div className="setting-row">
                {t("Preview updates")}
                <span>{t("Signed preview channel")}</span>
              </div>
            </div>
            <p>
              {t(
                "Your original workspace remains unchanged. The Tauri update channel must be published and tested before this preview replaces the original app.",
              )}
            </p>
          </>
        ) : (
          <>
            <h2>
              {tab === "search"
                ? t("A memory for your news.")
                : t("Understand the whole story.")}
            </h2>
            <p className="muted">
              {tab === "search"
                ? t(
                    "Search uses your saved articles. Indexing and explanations are separate tasks.",
                  )
                : t(
                    "Explanations use the summary model selected in your workspace.",
                  )}
            </p>
            <label className="setting-row">
              {tab === "search"
                ? t("Search by meaning")
                : t("Automatic explanations")}
              <input
                type="checkbox"
                checked={!!data.enabled}
                onChange={async (e) => {
                  try {
                    setData(
                      await call(
                        tab === "search"
                          ? "news.search.set"
                          : "news.digest.set",
                        { enabled: e.target.checked },
                      ),
                    );
                  } catch (error) {
                    onError(String(error));
                  }
                }}
              />
            </label>
            {tab === "summaries" && (
              <>
                <label className="setting-row">
                  {t("Language")}
                  <select
                    value={data.language || "ar"}
                    onChange={async (e) => {
                      try {
                        setData(
                          await call("news.digest.set", {
                            enabled: !!data.enabled,
                            language: e.target.value,
                          }),
                        );
                      } catch (error) {
                        onError(String(error));
                      }
                    }}
                  >
                    <option value="ar">العربية</option>
                    <option value="en">{t("English")}</option>
                  </select>
                </label>
                <label className="setting-row">
                  {t("Explanation source")}
                  <select
                    value={data.engine || "provider"}
                    onChange={async (e) => {
                      try {
                        setData(
                          await call("news.digest.set", {
                            enabled: false,
                            engine: e.target.value,
                          }),
                        );
                      } catch (error) {
                        onError(String(error));
                      }
                    }}
                  >
                    <option value="provider">{t("Connected provider")}</option>
                    <option value="local">{t("Local model")}</option>
                  </select>
                </label>
              </>
            )}
            <div className="settings-group">
              {Object.entries(data)
                .filter(([k, v]) => k in statusLabels && v !== "" && v != null)
                .map(([k, v]) => (
                  <div className="setting-row" key={k}>
                    <span>{t(statusLabels[k])}</span>
                    <span>
                      {k === "phase"
                        ? t(phases[String(v)] || String(v).replaceAll("_", " "))
                        : k === "language"
                          ? v === "ar"
                            ? "العربية"
                            : t("English")
                          : typeof v === "boolean"
                            ? v
                              ? t("On")
                              : t("Off")
                            : String(v)}
                    </span>
                  </div>
                ))}
            </div>
            <ModelLibrary
              key={tab}
              embedding={tab === "search"}
              onError={onError}
            />
            {tab === "search" && (
              <details
                onToggle={(e) => {
                  if (e.currentTarget.open)
                    void call("news.search.inspect")
                      .then((r) => setIndexedArticles(r.articles))
                      .catch((e) => onError(String(e)));
                }}
              >
                <summary>{t("Index details")}</summary>
                {indexedArticles.map((a) => (
                  <div className="notice" key={a.id}>
                    <strong dir="auto">{a.title}</strong>
                    <p>
                      {t("Text segments")}: {a.segments} ·{" "}
                      {t("Embedded segments")}: {a.embedded}
                    </p>
                  </div>
                ))}
              </details>
            )}
            {tab === "summaries" && (
              <TaskInstructions
                id="article-summary"
                title={t("Article explanation instructions")}
                onError={onError}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
