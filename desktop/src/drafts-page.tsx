import { useEffect, useState, useRef } from "react";
import {
  ArrowLeft,
  Copy,
  Download,
  Plus,
  Search,
  Check,
  FileText,
  X,
  ChevronRight,
  LoaderCircle,
} from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { t, getLocale } from "./locale";
import { useUnsavedChanges } from "./unsaved-changes";
import { settingsMessage } from "./settings-message";

export function DraftsPage({
  snapshot,
  onError,
  refresh,
}: {
  snapshot: RecordData;
  onError: (s: string) => void;
  refresh?: () => Promise<void>;
}) {
  const [selected, setSelected] = useState<RecordData>(),
    [creating, setCreating] = useState(false),
    [text, setText] = useState("");
  const [baseline, setBaseline] = useState(""),
    [title, setTitle] = useState(""),
    [preview, setPreview] = useState(false),
    [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [error, setError] = useState(""),
    [versionsError, setVersionsError] = useState(false),
    [versionsLoading, setVersionsLoading] = useState(false),
    [opening, setOpening] = useState(""),
    [exporting, setExporting] = useState(false),
    [version, setVersion] = useState("");
  const [rows, setRows] = useState<RecordData[]>(snapshot.drafts || []);
  const saving = useRef(false);
  const copyRequest = useRef(0);
  const [copiedText, setCopiedText] = useState<string>();
  const request = useRef(0);
  const exportingRef = useRef(false);
  useEffect(
    () => () => {
      request.current += 1;
      copyRequest.current += 1;
    },
    [],
  );
  useEffect(() => setRows(snapshot.drafts || []), [snapshot.drafts]);
  useEffect(() => {
    copyRequest.current += 1;
    setCopiedText(undefined);
  }, [text, selected?.id, creating]);
  useEffect(() => {
    if (copiedText === undefined) return;
    const timer = setTimeout(() => setCopiedText(undefined), 1800);
    return () => clearTimeout(timer);
  }, [copiedText]);
  const dirty =
    (Boolean(selected) || creating) &&
    (text !== baseline || (creating && Boolean(title.trim())));
  async function open(id: string) {
    const token = ++request.current;
    setOpening(id);
    setNotice("");
    setError("");
    setVersionsError(false);
    try {
      const result = await call("drafts.detail", { draft_id: id });
      if (request.current !== token) return;
      const current = result.versions?.find(
        (v: RecordData) => v.id === result.draft.current_version_id,
      );
      setSelected({ ...rows.find((r) => r.id === id), ...result, id });
      setText(current?.text || "");
      setBaseline(current?.text || "");
      setVersion(result.draft.current_version_id);
      setCreating(false);
      setPreview(false);
    } catch (e) {
      if (request.current === token) setError(settingsMessage(String(e)));
    } finally {
      if (request.current === token) setOpening("");
    }
  }
  async function save() {
    if (saving.current) return false;
    if (!dirty && selected) return true;
    if (!text.trim() || (!selected && !title.trim())) return false;
    saving.current = true;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      let id = selected?.id;
      if (!id) {
        id = (
          await call("drafts.create", {
            topic: title.trim(),
            text,
            language: /[\u0600-\u06ff]/.test(text) ? "ar" : "en",
          })
        ).draft_id;
        // Keep the acknowledged identity even if loading saved versions fails.
        // A retry must update this draft, not create a second copy.
        setSelected({ id, topic: title.trim(), format: "x_post" });
        setCreating(false);
      } else await call("drafts.save", { draft_id: id, text });
      setCreating(false);
      setBaseline(text);
      setNotice(t("Draft saved."));
      setRows((old) => [
        {
          ...old.find((r) => r.id === id),
          id,
          topic: selected?.topic || title.trim(),
          text,
          format: selected?.format || "x_post",
          updated_at: new Date().toISOString(),
        },
        ...old.filter((r) => r.id !== id),
      ]);
      setVersionsError(false);
      try {
        const result = await call("drafts.detail", { draft_id: id });
        setSelected({
          ...selected,
          ...result,
          id,
          topic: selected?.topic || title.trim(),
        });
        setVersion(result.draft.current_version_id);
      } catch {
        setVersionsError(true);
      }
      await refresh?.().catch((e) => onError(String(e)));
      return true;
    } catch (e) {
      setError(settingsMessage(String(e)));
      onError(String(e));
      return false;
    } finally {
      saving.current = false;
      setBusy(false);
    }
  }
  const guard = useUnsavedChanges(dirty, save);
  useEffect(() => {
    if (!selected && !creating) return;
    const key = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void save();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [selected, creating, text, title]);
  const formats: Record<string, string> = {
    x_post: "X",
    linkedin: "LinkedIn",
    youtube_long: "YouTube",
    shorts: t("Short video"),
    manual: t("Draft"),
    tiktok: "TikTok",
    reels: "Reels",
  };
  const results = rows.filter((row) =>
    `${row.topic || row.title} ${row.text || ""}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  function create() {
    request.current += 1;
    setOpening("");
    setSelected(undefined);
    setCreating(true);
    setText("");
    setBaseline("");
    setTitle("");
    setPreview(false);
    setNotice("");
    setError("");
    setVersionsError(false);
  }
  return (
    <div className="page drafts-page">
      {guard.dialog}
      {error && (
        <p className="context-feedback" role="alert">
          {error}
        </p>
      )}
      {selected || creating ? (
        <>
          <div className="draft-toolbar">
            <button
              disabled={busy || versionsLoading || exporting}
              onClick={() =>
                guard.confirm(() => {
                  setSelected(undefined);
                  setCreating(false);
                })
              }
            >
              <ArrowLeft size={16} className="back-arrow" />
              {t("All drafts")}
            </button>
            <span className="draft-save-state" role="status">
              {busy
                ? t("Saving…")
                : dirty
                  ? t("Unsaved changes")
                  : creating
                    ? t("New draft")
                    : t("Saved")}
            </span>
            <button
              className="primary"
              disabled={
                busy || !dirty || !text.trim() || (!selected && !title.trim())
              }
              onClick={() => void save()}
            >
              {busy ? (
                <LoaderCircle size={15} className="spin" />
              ) : (
                <Check size={15} />
              )}{" "}
              {t("Save draft")}
            </button>
          </div>
          {creating ? (
            <input
              className="draft-title-input"
              aria-label={t("Title")}
              autoFocus
              placeholder={t("Give your draft a title")}
              maxLength={300}
              disabled={busy}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          ) : (
            <h1>
              <bdi>
                {selected?.topic || selected?.draft?.topic || selected?.title}
              </bdi>
            </h1>
          )}
          <div className="draft-editor-tools">
            <div className="segments">
              <button aria-pressed={!preview} onClick={() => setPreview(false)}>
                {t("Write")}
              </button>
              <button aria-pressed={preview} onClick={() => setPreview(true)}>
                {t("Preview")}
              </button>
            </div>
            {selected?.versions?.length > 0 && (
              <label>
                {t("Saved versions")}
                <select
                  disabled={busy || versionsLoading}
                  aria-label={t("Saved versions")}
                  value={version}
                  onChange={(e) => {
                    const id = e.target.value;
                    guard.confirm(() => {
                      setVersion(id);
                      setText(
                        selected?.versions.find((v: RecordData) => v.id === id)
                          ?.text || "",
                      );
                    });
                  }}
                >
                  {selected?.versions.map((v: RecordData) => (
                    <option key={v.id} value={v.id}>
                      {new Date(v.created_at).toLocaleString(getLocale())}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button
              className="icon-button"
              aria-label={t(copiedText === text ? "Copied" : "Copy text")}
              title={t("Copy text")}
              disabled={!text.trim()}
              onClick={() => {
                const token = ++copyRequest.current;
                void navigator.clipboard
                  .writeText(text)
                  .then(() => {
                    if (token === copyRequest.current) setCopiedText(text);
                  })
                  .catch((e) => {
                    if (token === copyRequest.current)
                      setError(settingsMessage(String(e)));
                  });
              }}
            >
              {copiedText === text ? <Check size={16} /> : <Copy size={16} />}
            </button>
            {selected && (
              <button
                className="icon-button"
                disabled={busy || exporting || !text.trim()}
                title={t("Export Markdown")}
                aria-label={t("Export Markdown")}
                onClick={async () => {
                  if (exportingRef.current) return;
                  exportingRef.current = true;
                  setExporting(true);
                  setError("");
                  try {
                    if (dirty && !(await save())) return;
                    const path = await invoke<string>("export_draft", {
                      draftId: selected.id,
                    });
                    setNotice(t("Exported to") + " " + path);
                  } catch (e) {
                    setError(settingsMessage(String(e)));
                  } finally {
                    exportingRef.current = false;
                    setExporting(false);
                  }
                }}
              >
                {exporting ? (
                  <LoaderCircle size={16} className="spin" />
                ) : (
                  <Download size={16} />
                )}
              </button>
            )}
          </div>
          {notice && (
            <p className="inline-success" role="status">
              <Check size={15} />
              {notice}
            </p>
          )}
          {versionsError && (
            <div className="context-feedback" role="alert">
              <p>{t("Your draft is saved. Saved versions could not load.")}</p>
              <button
                disabled={busy || versionsLoading}
                onClick={async () => {
                  if (!selected) return;
                  const token = ++request.current;
                  setVersionsLoading(true);
                  try {
                    const result = await call("drafts.detail", {
                      draft_id: selected.id,
                    });
                    if (request.current !== token) return;
                    setSelected({ ...selected, ...result });
                    setVersion(result.draft.current_version_id);
                    setVersionsError(false);
                  } catch (e) {
                    if (request.current === token)
                      setError(settingsMessage(String(e)));
                  } finally {
                    if (request.current === token) setVersionsLoading(false);
                  }
                }}
              >
                {versionsLoading && <LoaderCircle size={15} className="spin" />}
                {t("Reload saved versions")}
              </button>
            </div>
          )}
          {preview ? (
            <div className="draft-preview">
              {text.trim() ? (
                <Markdown text={text} />
              ) : (
                <p className="muted">
                  {t("Your preview will appear here as you write.")}
                </p>
              )}
            </div>
          ) : (
            <textarea
              className="draft-editor"
              aria-label={t("Draft text")}
              placeholder={t("Start writing…")}
              dir="auto"
              value={text}
              maxLength={60000}
              onChange={(e) => setText(e.target.value)}
            />
          )}
          <footer className="draft-editor-footer">
            <span>
              {text.trim() ? text.trim().split(/\s+/).length : 0} {t("words")}
            </span>
            <small>⌘ S</small>
          </footer>
        </>
      ) : (
        <>
          <div className="page-title">
            <div>
              <h1>{t("Saved drafts")}</h1>
              <p className="page-description">
                {t("Ideas you are turning into something.")}
              </p>
            </div>
            <button className="primary" onClick={create}>
              <Plus size={16} />
              {t("New draft")}
            </button>
          </div>
          <div className="filters">
            <span className="muted">
              {rows.length.toLocaleString(getLocale())}{" "}
              {t(rows.length === 1 ? "draft" : "drafts")}
            </span>
            <label className="search">
              <Search size={16} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("Search drafts")}
                aria-label={t("Search drafts")}
              />
              {query && (
                <button
                  className="icon-button"
                  onClick={() => setQuery("")}
                  aria-label={t("Clear search")}
                >
                  <X size={14} />
                </button>
              )}
            </label>
          </div>
          <div className="draft-library">
            {results.map((row) => (
              <button
                className="draft-library-row"
                aria-busy={opening === row.id}
                key={row.id}
                onClick={() => void open(row.id)}
              >
                {opening === row.id ? (
                  <LoaderCircle size={19} className="spin" />
                ) : (
                  <FileText size={19} />
                )}
                <span>
                  <strong>
                    <bdi>{row.topic || row.title}</bdi>
                  </strong>
                  <small>
                    <bdi>
                      {String(row.text || "")
                        .replace(/[#*`>]/g, "")
                        .slice(0, 110)}
                    </bdi>
                  </small>
                </span>
                <span className="draft-format">
                  {formats[row.format] || row.format}
                </span>
                <ChevronRight size={16} className="related-arrow" />
              </button>
            ))}
          </div>
          {!results.length && (
            <div className="empty">
              <FileText size={28} />
              <h2>
                {t(
                  query
                    ? "No drafts match your search"
                    : "A place for your next idea",
                )}
              </h2>
              <p>
                {t(
                  "Write here or ask the assistant to turn an idea into a post. Your drafts stay editable.",
                )}
              </p>
              <button onClick={create}>{t("New draft")}</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
