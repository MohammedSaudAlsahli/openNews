import { SkillLibrary } from "./skill-library";
import { settingsCategories } from "./settings-navigation";
import { settingsMessage } from "./settings-message";
import { navigateSafely, useUnsavedChanges } from "./unsaved-changes";
import { Updates } from "./updates";
import { t, useLocale, setLocale } from "./locale";
import { invoke } from "@tauri-apps/api/core";
import { Agents } from "./agents";
import { WritingLibrary } from "./writing-library";
import { TaskInstructions } from "./task-instructions";
import { LocalModels } from "./local-models";
import { ModelLibrary } from "./model-library";
import { ProcessingStatus } from "./processing-status";
import { summaryModel } from "./summary-model";
import { Connections } from "./connections";
import { TimeZoneSelect } from "./time-zone-select";
import { IndexDetails } from "./index-details";
import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useRef, useState } from "react";
import {
  Check,
  Cpu,
  Calendar,
  Search,
  Sun,
  Moon,
  Shield,
  LoaderCircle,
  ChevronDown,
  X,
} from "lucide-react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import "./settings.css";
export default function Settings({
  snapshot,
  refresh,
  theme,
  setTheme,
  onError,
  onUseSkill,
  onRecommendSkills,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  theme: string;
  setTheme: (s: string) => void;
  onError: (s: string) => void;
  onUseSkill?: (id: string) => void;
  onRecommendSkills?: () => void;
}) {
  const locale = useLocale();
  const [pageError, setPageError] = useState("");
  useEffect(() => {
    onError("");
  }, []);
  const [tab, changeTab] = useState(
      ["agents", "writing"].includes(
        sessionStorage.getItem("settings-tab") || "",
      )
        ? "instructions"
        : sessionStorage.getItem("settings-tab") || "appearance",
    ),
    [data, setData] = useState<RecordData>({}),
    [section, setSection] = useState("role"),
    [instructionScope, setInstructionScope] = useState("general"),
    [preview, setPreview] = useState(false),
    [busy, setBusy] = useState(false),
    [saved, setSaved] = useState(false);
  const [customizationView, setCustomizationView] = useState("instructions");
  const [showAgents, setShowAgents] = useState(false);
  const [advancedInstructions, setAdvancedInstructions] = useState(false);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const [baseline, setBaseline] = useState("");
  const [settingsQuery, setSettingsQuery] = useState("");
  const [loadState, setLoadState] = useState("loading"),
    [loadAttempt, setLoadAttempt] = useState(0);
  const [changing, setChanging] = useState(false);
  const [transfer, setTransfer] = useState(""),
    [timeDraft, setTimeDraft] = useState<string>();
  const invalidTime =
    tab === "daily" &&
    timeDraft !== undefined &&
    !/^([01]\d|2[0-3]):[0-5]\d$/.test(timeDraft);
  const activeTab = useRef(tab),
    mutation = useRef(false),
    statusVersion = useRef(0);
  const saveLock = useRef(false);
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (content.current) content.current.scrollTop = 0;
    setModelPickerOpen(false);
    sessionStorage.setItem("settings-tab", tab);
  }, [tab]);
  activeTab.current = tab;
  const setTab = (next: string) => navigateSafely(() => changeTab(next));
  const chosenSummaryModel = summaryModel(snapshot, data);
  const dirty =
    Boolean(baseline) &&
    ["instructions", "daily"].includes(tab) &&
    (JSON.stringify(data.settings || {}) !== baseline || invalidTime);
  const guard = useUnsavedChanges(dirty, save);
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
  const category =
    settingsCategories.find((group) =>
      group.pages.some((page) => page.id === tab),
    ) || settingsCategories[0];
  const query = settingsQuery.trim().toLocaleLowerCase(locale);
  const searchResults = settingsCategories.flatMap((group) =>
    group.pages
      .filter((page) =>
        [group.title, group.description, page.title, ...page.keywords]
          .flatMap((value) => [value, t(value)])
          .some((value) => value.toLocaleLowerCase(locale).includes(query)),
      )
      .map((page) => ({ ...page, category: group.title, icon: group.icon })),
  );
  function openSetting(next: string) {
    navigateSafely(() => {
      changeTab(next);
      setSettingsQuery("");
      setPageError("");
      onError("");
    });
  }
  useEffect(() => {
    let live = true;
    setSaved(false);
    setTimeDraft(undefined);
    setPageError("");
    setLoadState("loading");
    setData({});
    setBaseline("");
    const command = (
      {
        instructions: "assistant.get",
        daily: "daily.get",
        search: "news.search.status",
        summaries: "news.digest.status",
      } as Record<string, string>
    )[tab];
    if (!command) {
      setBusy(false);
      setLoadState("ready");
      return;
    }
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
          setBaseline(JSON.stringify(r.settings || {}));
          setLoadState("ready");
        }
      })
      .catch((e) => {
        if (live) {
          setPageError(String(e));
          setLoadState("failed");
        }
      })
      .finally(() => {
        if (live) setBusy(false);
      });
    return () => {
      live = false;
    };
  }, [tab, instructionScope, loadAttempt]);
  useEffect(() => {
    if (tab !== "search" && tab !== "summaries") return;
    let live = true,
      inFlight = false;
    const timer = setInterval(async () => {
      if (inFlight || mutation.current || document.visibilityState === "hidden")
        return;
      inFlight = true;
      const version = statusVersion.current;
      try {
        const result = await call(
          tab === "search" ? "news.search.status" : "news.digest.status",
        );
        if (live && version === statusVersion.current && !mutation.current)
          setData(result);
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
  useEffect(() => {
    if (tab !== "daily") return;
    let live = true,
      inFlight = false;
    const timer = setInterval(async () => {
      if (inFlight || document.visibilityState === "hidden") return;
      inFlight = true;
      try {
        const result = await call("daily.get");
        if (live)
          setData((previous) => ({
            ...previous,
            reports: result.reports || [],
          }));
      } catch {
        /* Retain the last saved reports; the next scheduled read retries. */
      } finally {
        inFlight = false;
      }
    }, 15000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [tab]);
  async function changeProcessing(values: RecordData) {
    if (mutation.current) return;
    mutation.current = true;
    setChanging(true);
    const target = tab;
    ++statusVersion.current;
    try {
      const result = await call(
        target === "search" ? "news.search.set" : "news.digest.set",
        values,
      );
      if (activeTab.current === target) {
        setData(result);
        setPageError("");
      }
    } catch (error) {
      if (activeTab.current === target) setPageError(String(error));
    } finally {
      mutation.current = false;
      setChanging(false);
    }
  }
  async function save() {
    if (invalidTime) {
      setPageError(t("Choose a valid report time."));
      return false;
    }
    if (saveLock.current) return false;
    saveLock.current = true;
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
      setBaseline(JSON.stringify(data.settings || {}));
      try {
        await refresh();
      } catch {
        setPageError(
          t(
            "Settings saved. The workspace could not refresh; try reopening this page.",
          ),
        );
      }
      return true;
    } catch (e) {
      setPageError(String(e));
      return false;
    } finally {
      saveLock.current = false;
      setBusy(false);
    }
  }
  function setting(key: string, value: unknown) {
    setData((d) => ({ ...d, settings: { ...d.settings, [key]: value } }));
    setSaved(false);
  }
  return (
    <div className="settings-layout">
      {guard.dialog}
      <aside className="settings-nav" aria-label={t("Settings categories")}>
        <h1>{t("Settings")}</h1>
        <label className="settings-search">
          <Search size={14} />
          <input
            aria-label={t("Find a setting")}
            placeholder={t("Find a setting")}
            value={settingsQuery}
            onChange={(e) => setSettingsQuery(e.target.value)}
          />
          {settingsQuery && (
            <button
              className="icon-button"
              aria-label={t("Clear search")}
              onClick={() => setSettingsQuery("")}
            >
              <X size={14} />
            </button>
          )}
        </label>
        <label className="settings-category-picker">
          <span>{t("Settings categories")}</span>
          <select
            value={category.id}
            onChange={(event) => {
              const next = settingsCategories.find(
                (group) => group.id === event.target.value,
              );
              if (next) openSetting(next.pages[0].id);
            }}
          >
            {settingsCategories.map((group) => (
              <option key={group.id} value={group.id}>
                {t(group.title)}
              </option>
            ))}
          </select>
        </label>
        <nav
          className="settings-destinations"
          aria-label={t("Settings categories")}
        >
          {settingsCategories.map((group) => {
            const Icon = group.icon;
            return (
              <button
                key={group.id}
                aria-label={t(group.title)}
                aria-current={category.id === group.id ? "page" : undefined}
                className={category.id === group.id ? "selected" : ""}
                onClick={() =>
                  openSetting(
                    category.id === group.id ? tab : group.pages[0].id,
                  )
                }
              >
                <Icon size={18} strokeWidth={1.6} />
                <span>
                  <strong>{t(group.title)}</strong>
                  <small>{t(group.description)}</small>
                </span>
              </button>
            );
          })}
        </nav>
        <p className="settings-local-note">
          <Shield size={14} />
          {t("Your preferences stay on this Mac.")}
        </p>
      </aside>
      <div ref={content} className={`settings-content settings-tab-${tab}`}>
        <div className="settings-pane">
          {query && (
            <section
              className="settings-results"
              aria-label={t("Search results")}
            >
              <h2>{t("Search results")}</h2>
              <p className="muted">{t("Choose a setting to open it.")}</p>
              {searchResults.length ? (
                <div className="preference-group">
                  {searchResults.map((result) => {
                    const Icon = result.icon;
                    return (
                      <button
                        key={result.id}
                        className="settings-result"
                        aria-label={t(result.title)}
                        aria-describedby={`settings-result-group-${result.id}`}
                        onClick={() => openSetting(result.id)}
                      >
                        <Icon size={18} />
                        <span>
                          <strong>{t(result.title)}</strong>
                          <small id={`settings-result-group-${result.id}`}>
                            {t(result.category)}
                          </small>
                        </span>
                        <ChevronDown size={15} />
                      </button>
                    );
                  })}
                </div>
              ) : (
                <p role="status">{t("No settings match your search.")}</p>
              )}
            </section>
          )}
          <div className="settings-page-content" hidden={Boolean(query)}>
            {category.pages.length > 1 && (
              <nav
                className="settings-subnav"
                aria-label={t("Related settings")}
              >
                {category.pages.map((page) => (
                  <button
                    key={page.id}
                    aria-current={page.id === tab ? "page" : undefined}
                    onClick={() => openSetting(page.id)}
                  >
                    {t(page.title)}
                  </button>
                ))}
              </nav>
            )}
            {pageError && (
              <div className="settings-feedback" role="alert">
                <span>{settingsMessage(pageError)}</span>
                <button onClick={() => setPageError("")}>{t("Dismiss")}</button>
              </div>
            )}
            {busy && <LoaderCircle className="spin busy-indicator" size={17} />}{" "}
            {loadState !== "ready" ? (
              <div className="settings-load-state" role="status">
                {loadState === "loading" ? (
                  t("Loading settings…")
                ) : (
                  <button onClick={() => setLoadAttempt((value) => value + 1)}>
                    {t("Try again")}
                  </button>
                )}
              </div>
            ) : tab === "local-models" ? (
              <LocalModels onError={setPageError} />
            ) : tab === "instructions" ? (
              <>
                <h2>{t("Customize assistant")}</h2>
                <p className="muted">
                  {t(
                    "These are the instructions it actually uses. Read them, make them yours, and save.",
                  )}
                </p>
                <div
                  className="segments customization-tabs"
                  role="group"
                  aria-label={t("Customize assistant")}
                >
                  <button
                    aria-pressed={customizationView === "instructions"}
                    className={
                      customizationView === "instructions" ? "selected" : ""
                    }
                    onClick={() => setCustomizationView("instructions")}
                  >
                    {t("Instructions & style")}
                  </button>
                  <button
                    aria-pressed={customizationView === "references"}
                    className={
                      customizationView === "references" ? "selected" : ""
                    }
                    onClick={() => setCustomizationView("references")}
                  >
                    {t("Examples & references")}
                  </button>
                </div>
                <div hidden={customizationView !== "instructions"}>
                  <div className="instruction-setup">
                    <label className="field">
                      {t("Applies to")}
                      <select
                        value={instructionScope}
                        onChange={(e) => {
                          const next = e.target.value;
                          navigateSafely(() => setInstructionScope(next));
                        }}
                      >
                        <option value="general">
                          {t("All assistants and conversations")}
                        </option>
                        <option value="writer">{t("Writing assistant")}</option>
                        <option value="analyst">
                          {t("Analysis assistant")}
                        </option>
                      </select>
                    </label>
                    <label className="field instruction-section-select">
                      {t("What would you like to customize?")}
                      <select
                        value={section}
                        onChange={(event) => setSection(event.target.value)}
                      >
                        {Object.entries(sections)
                          .filter(
                            ([key]) =>
                              advancedInstructions ||
                              !["system_prompt", "developer_prompt"].includes(
                                key,
                              ),
                          )
                          .map(([key, label]) => (
                            <option key={key} value={key}>
                              {t(label)}
                            </option>
                          ))}
                      </select>
                    </label>
                  </div>
                  <button
                    className="advanced-instructions-toggle"
                    aria-expanded={advancedInstructions}
                    aria-controls="instruction-section"
                    onClick={() => {
                      setAdvancedInstructions(!advancedInstructions);
                      if (
                        advancedInstructions &&
                        ["system_prompt", "developer_prompt"].includes(section)
                      )
                        setSection("role");
                    }}
                  >
                    {t(
                      advancedInstructions
                        ? "Hide technical options"
                        : "Show technical options",
                    )}
                    <ChevronDown
                      size={14}
                      className={
                        advancedInstructions
                          ? "disclosure-chevron open"
                          : "disclosure-chevron"
                      }
                    />
                  </button>
                  {advancedInstructions && (
                    <p className="technical-options-note">
                      {t(
                        "System and developer prompts are now available in the section menu.",
                      )}
                    </p>
                  )}
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
                          data.settings?.[section] ||
                          t("No additional instructions.")
                        }
                      />
                    </div>
                  ) : (
                    <textarea
                      disabled={busy}
                      className="editor"
                      dir="auto"
                      aria-label={t(sections[section])}
                      value={data.settings?.[section] || ""}
                      onChange={(e) => setting(section, e.target.value)}
                    />
                  )}
                  <div className="save-row">
                    <small>
                      {t("Saved locally · Applied to new responses")}
                    </small>
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
                        t("Save instructions")
                      )}
                    </button>
                  </div>
                </div>
                <div hidden={customizationView !== "references"}>
                  <WritingLibrary
                    snapshot={snapshot}
                    refresh={refresh}
                    onError={setPageError}
                  />
                </div>
                <details
                  className="specialist-assistants"
                  onToggle={(e) => {
                    if (e.currentTarget.open) setShowAgents(true);
                  }}
                >
                  <summary>{t("Advanced: specialized assistants")}</summary>
                  <p className="muted">
                    {t(
                      "Optional. Create a separate assistant only when a task needs its own instructions or model.",
                    )}
                  </p>
                  {showAgents && (
                    <Agents
                      snapshot={snapshot}
                      refresh={refresh}
                      onError={setPageError}
                    />
                  )}
                </details>
              </>
            ) : tab === "skills" ? (
              <SkillLibrary
                onUse={onUseSkill}
                onRecommend={onRecommendSkills}
              />
            ) : tab === "connections" ? (
              <Connections
                snapshot={snapshot}
                refresh={refresh}
                onError={setPageError}
              />
            ) : tab === "daily" ? (
              <>
                <h2>{t("Daily report")}</h2>
                <p className="muted">
                  {t("Choose when to prepare a report from your sources.")}
                </p>
                <div className="settings-group">
                  <label className="setting-row">
                    {t("Daily report")}
                    <input
                      type="checkbox"
                      disabled={
                        busy ||
                        (!summaryModel(snapshot) && !data.settings?.enabled)
                      }
                      checked={!!data.settings?.enabled}
                      onChange={(e) => setting("enabled", e.target.checked)}
                    />
                  </label>
                  <label className="setting-row">
                    {t("Report time")}
                    <input
                      type="time"
                      disabled={busy}
                      value={
                        timeDraft ??
                        `${String(data.settings?.hour ?? 22).padStart(2, "0")}:${String(data.settings?.minute ?? 0).padStart(2, "0")}`
                      }
                      aria-invalid={invalidTime}
                      aria-describedby={
                        invalidTime ? "report-time-error" : undefined
                      }
                      onChange={(e) => {
                        setTimeDraft(e.target.value);
                        setSaved(false);
                        if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(e.target.value))
                          return;
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
                    <TimeZoneSelect
                      disabled={busy}
                      value={data.settings?.timezone || "Asia/Riyadh"}
                      onChange={(value) => setting("timezone", value)}
                    />
                  </label>
                  <label className="setting-row">
                    {t("Language")}
                    <select
                      disabled={busy}
                      value={data.settings?.language || "ar"}
                      onChange={(e) => setting("language", e.target.value)}
                    >
                      <option value="ar">العربية</option>
                      <option value="en">{t("English")}</option>
                    </select>
                  </label>
                </div>
                <button
                  className="primary"
                  disabled={busy || invalidTime || !dirty}
                  onClick={() => void save()}
                >
                  {busy && <LoaderCircle size={15} className="spin" />}
                  {t(busy ? "Saving…" : saved ? "Saved" : "Save schedule")}
                </button>
                {invalidTime && (
                  <p id="report-time-error" role="alert">
                    {t("Choose a valid report time.")}
                  </p>
                )}
                {!summaryModel(snapshot) && (
                  <p className="muted">
                    {t("Choose a model before scheduling reports.")}{" "}
                    <button onClick={() => setTab("summaries")}>
                      {t("Summary settings")}
                    </button>
                  </p>
                )}
                <p className="notice">
                  {t(
                    "Reports run while openNews is open, including with its window closed. If your Mac sleeps, the report is prepared when you return. Enable openNews notifications in macOS System Settings.",
                  )}
                </p>
                <h3>{t("Saved reports")}</h3>
                {!(data.reports || []).length && (
                  <p className="muted">
                    {t(
                      "Your report will appear here after the scheduled time.",
                    )}
                  </p>
                )}
                {(data.reports || []).map((r: RecordData) => (
                  <details className="saved-daily-report" key={r.id || r.day}>
                    <summary>
                      <Calendar size={16} />
                      <span>
                        <bdi>{r.day}</bdi> ·{" "}
                        {t(
                          r.state === "ready"
                            ? "Ready"
                            : r.state === "running"
                              ? "Preparing report…"
                              : "Failed",
                        )}
                      </span>
                      <ChevronDown size={15} className="disclosure-chevron" />
                    </summary>
                    {r.body ? (
                      <Markdown text={r.body} />
                    ) : (
                      <p>
                        {t(
                          r.state === "running"
                            ? "Preparing report…"
                            : "The report could not be prepared. Check your explanation model.",
                        )}
                      </p>
                    )}
                  </details>
                ))}
                <TaskInstructions
                  id="daily-report"
                  title={t("Daily report instructions")}
                  onError={setPageError}
                />
              </>
            ) : tab === "appearance" ? (
              <>
                <h2>{t("Appearance & language")}</h2>
                <p className="muted">
                  {t("A focused workspace, in the light that suits you.")}
                </p>
                <section className="preference-section">
                  <h3>{t("Language & appearance")}</h3>
                  <div className="preference-group">
                    <label className="setting-row">
                      <span className="preference-copy">
                        <strong>{t("Interface language")}</strong>
                        <small>
                          {t("Menus and controls follow this language.")}
                        </small>
                      </span>
                      <select
                        value={locale}
                        onChange={(e) =>
                          setLocale(e.target.value as "ar" | "en")
                        }
                      >
                        <option value="en">English</option>
                        <option value="ar">العربية</option>
                      </select>
                    </label>
                  </div>
                  <div className="appearance-choice">
                    <span className="preference-copy">
                      <strong>{t("Appearance")}</strong>
                      <small>
                        {t("Choose the look that feels comfortable to read.")}
                      </small>
                    </span>
                    <div
                      className="theme-options"
                      role="group"
                      aria-label={t("Appearance")}
                    >
                      <button
                        aria-pressed={theme === "light"}
                        className={theme === "light" ? "selected" : ""}
                        onClick={() => setTheme("light")}
                      >
                        <span
                          className="theme-preview light"
                          aria-hidden="true"
                        >
                          <i />
                          <span>
                            <b />
                            <b />
                            <b />
                          </span>
                        </span>
                        <span className="theme-label">
                          <Sun size={15} />
                          <strong>{t("Light")}</strong>
                          {theme === "light" && <Check size={15} />}
                        </span>
                      </button>
                      <button
                        aria-pressed={theme === "dark"}
                        className={theme === "dark" ? "selected" : ""}
                        onClick={() => setTheme("dark")}
                      >
                        <span className="theme-preview dark" aria-hidden="true">
                          <i />
                          <span>
                            <b />
                            <b />
                            <b />
                          </span>
                        </span>
                        <span className="theme-label">
                          <Moon size={15} />
                          <strong>{t("Dark")}</strong>
                          {theme === "dark" && <Check size={15} />}
                        </span>
                      </button>
                    </div>
                  </div>
                </section>
              </>
            ) : tab === "privacy" ? (
              <>
                <h2>{t("Privacy & updates")}</h2>
                <Updates onError={setPageError} />
                <p className="muted">
                  {t(
                    "Articles, conversations and drafts are saved on this Mac. Selected model providers receive the content needed for your requests.",
                  )}
                </p>
                <details className="notice">
                  <summary>{t("Advanced: import a legacy workspace")}</summary>
                  <p>
                    {t(
                      "Quit the Swift app before importing. This copies its articles, conversations, credentials, models and cached images. Your current workspace is backed up and the original stays intact. Automatic processing is paused after import until you enable it again.",
                    )}
                  </p>
                  <div className="reader-actions">
                    <button
                      disabled={busy}
                      onClick={() => setTransfer("import")}
                    >
                      {t("Import original workspace")}
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => setTransfer("restore")}
                    >
                      {t("Restore previous workspace")}
                    </button>
                  </div>
                </details>
                <Dialog.Root
                  open={Boolean(transfer)}
                  onOpenChange={(open) => {
                    if (!open && !busy) setTransfer("");
                  }}
                >
                  <Dialog.Portal>
                    <Dialog.Overlay className="dialog-overlay" />
                    <Dialog.Content className="dialog-panel">
                      <Dialog.Title>
                        {t(
                          transfer === "restore"
                            ? "Restore previous workspace?"
                            : "Import legacy workspace?",
                        )}
                      </Dialog.Title>
                      <Dialog.Description>
                        {t(
                          "This changes the workspace used by openNews. Your current workspace is backed up before replacement.",
                        )}
                      </Dialog.Description>
                      <div className="dialog-actions">
                        <button disabled={busy} onClick={() => setTransfer("")}>
                          {t("Cancel")}
                        </button>
                        <button
                          disabled={busy}
                          className="primary"
                          onClick={async () => {
                            setBusy(true);
                            try {
                              await invoke("transfer_workspace", {
                                restore: transfer === "restore",
                              });
                              window.location.reload();
                            } catch (reason) {
                              setTransfer("");
                              setPageError(String(reason));
                              setBusy(false);
                            }
                          }}
                        >
                          {t(
                            busy
                              ? "Working…"
                              : transfer === "restore"
                                ? "Restore previous workspace"
                                : "Import original workspace",
                          )}
                        </button>
                      </div>
                    </Dialog.Content>
                  </Dialog.Portal>
                </Dialog.Root>
              </>
            ) : (
              <>
                <h2>
                  {tab === "search"
                    ? t("Article search")
                    : t("TL;DR")}
                </h2>
                <p className="muted">
                  {tab === "search"
                    ? t(
                        "Search uses your saved articles. Indexing and summaries are separate tasks.",
                      )
                    : t(
                        "New and older articles are summarized in the background using your selected model.",
                      )}
                </p>
                {tab === "summaries" && (
                  <div className="summary-model-choice">
                    <div>
                      <strong>{t("Summary model")}</strong>
                      <span dir="auto">
                        {chosenSummaryModel || t("No model selected")}
                      </span>
                    </div>
                    <button
                      onClick={() =>
                        setTab(
                          data.engine === "local"
                            ? "local-models"
                            : "connections",
                        )
                      }
                    >
                      {t(
                        chosenSummaryModel ? "Change model" : "Choose a model",
                      )}
                    </button>
                    {!chosenSummaryModel && (
                      <p className="muted">
                        {t("Choose a model before enabling automatic summaries.")}
                      </p>
                    )}
                  </div>
                )}
                <label className="setting-row">
                  {tab === "search"
                    ? t("Search by meaning")
                    : t("Automatic summaries")}
                  <input
                    type="checkbox"
                    disabled={
                      changing ||
                      (tab === "summaries" &&
                        !chosenSummaryModel &&
                        !data.enabled)
                    }
                    checked={!!data.enabled}
                    onChange={(e) =>
                      void changeProcessing({ enabled: e.target.checked })
                    }
                  />
                </label>
                {tab === "summaries" && (
                  <>
                    <label className="setting-row">
                      {t("Language")}
                      <select
                        disabled={changing}
                        value={data.language || "ar"}
                        onChange={(e) =>
                          void changeProcessing({
                            enabled: !!data.enabled,
                            language: e.target.value,
                          })
                        }
                      >
                        <option value="ar">العربية</option>
                        <option value="en">{t("English")}</option>
                      </select>
                    </label>
                    <label className="setting-row">
                      {t("Summary source")}
                      <select
                        disabled={changing}
                        value={data.engine || "provider"}
                        onChange={(e) =>
                          void changeProcessing({
                            enabled: false,
                            engine: e.target.value,
                          })
                        }
                      >
                        <option value="provider">
                          {t("Connected provider")}
                        </option>
                        <option value="local">{t("Local model")}</option>
                      </select>
                    </label>
                  </>
                )}
                {changing && (
                  <p className="inline-loading" role="status">
                    <LoaderCircle size={14} className="spin" />
                    {t("Saving changes…")}
                  </p>
                )}
                <ProcessingStatus data={data} search={tab === "search"} />
                {(tab === "search" || data.engine === "local") && (
                  <button
                    className="manage-local-models"
                    aria-expanded={modelPickerOpen}
                    aria-controls="article-model-picker"
                    onClick={() => setModelPickerOpen((open) => !open)}
                  >
                    <Cpu size={17} />
                    <span>
                      {t("Change model")}
                      <small>
                        <bdi>
                          {tab === "search" ? data.model : data.local_model}
                        </bdi>
                      </small>
                    </span>
                    <ChevronDown
                      size={15}
                      className={modelPickerOpen ? "open" : ""}
                    />
                  </button>
                )}
                {modelPickerOpen &&
                  (tab === "search" || data.engine === "local") && (
                    <div
                      id="article-model-picker"
                      className="inline-model-picker"
                    >
                      <ModelLibrary
                        embedding={tab === "search"}
                        initialTab="installed"
                        onError={setPageError}
                        onActivated={() => {
                          const target = tab;
                          void call(
                            target === "search"
                              ? "news.search.status"
                              : "news.digest.status",
                          )
                            .then((result) => {
                              if (activeTab.current === target) setData(result);
                            })
                            .catch((error) => {
                              if (activeTab.current === target)
                                setPageError(String(error));
                            });
                        }}
                      />
                    </div>
                  )}
                {tab === "search" && <IndexDetails />}
                {tab === "summaries" && (
                  <TaskInstructions
                    id="article-summary"
                    title={t("TL;DR instructions")}
                    onError={setPageError}
                  />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
