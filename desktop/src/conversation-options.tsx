import { useEffect, useRef, useState } from "react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { t } from "./locale";
import { Check, LoaderCircle, X } from "lucide-react";
import { useUnsavedChanges } from "./unsaved-changes";
import { settingsMessage } from "./settings-message";
export function ConversationOptions({
  conversation,
  selected,
  onSelect,
  onClose,
}: {
  conversation: string;
  selected: RecordData[];
  onSelect: (rows: RecordData[]) => void;
  onError: (message: string) => void;
  onClose?: () => void;
}) {
  const [tab, setTab] = useState("articles"),
    [query, setQuery] = useState(""),
    [url, setUrl] = useState(""),
    [rows, setRows] = useState<RecordData[]>([]),
    [busy, setBusy] = useState(false),
    [settings, setSettings] = useState<RecordData>({}),
    [preview, setPreview] = useState(false),
    [saved, setSaved] = useState(false),
    [baseline, setBaseline] = useState(""),
    [loadedFor, setLoadedFor] = useState<string>(),
    [instructionsError, setInstructionsError] = useState(""),
    [articlesError, setArticlesError] = useState(""),
    [importError, setImportError] = useState(""),
    [searching, setSearching] = useState(true),
    [attempt, setAttempt] = useState(0),
    [searchAttempt, setSearchAttempt] = useState(0);
  const current = useRef({ conversation, selected, onSelect });
  current.current = { conversation, selected, onSelect };
  const operation = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const loaded = loadedFor === conversation;
  const dirty = loaded && (settings.instructions || "") !== baseline;
  async function save() {
    if (!loaded || operation.current) return false;
    operation.current = true;
    setBusy(true);
    setInstructionsError("");
    const target = conversation;
    try {
      await call("assistant.save", {
        scope: "conversation",
        target_id: target,
        settings,
      });
      if (mounted.current && current.current.conversation === target) {
        setBaseline(settings.instructions || "");
        setSaved(true);
      }
      return true;
    } catch (e) {
      if (mounted.current && current.current.conversation === target)
        setInstructionsError(settingsMessage(String(e)));
      return false;
    } finally {
      operation.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  const guard = useUnsavedChanges(dirty, save);
  useEffect(() => {
    let live = true;
    setSearching(true);
    setArticlesError("");
    const timer = setTimeout(() => {
      void call("news.list", { query, limit: 20 })
        .then((r) => {
          if (live) setRows(r.articles || []);
        })
        .catch((e) => {
          if (live) setArticlesError(settingsMessage(String(e)));
        })
        .finally(() => {
          if (live) setSearching(false);
        });
    }, 250);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [query, searchAttempt]);
  useEffect(() => {
    let live = true;
    setSettings({});
    setSaved(false);
    setLoadedFor(undefined);
    setInstructionsError("");
    setBaseline("");
    setImportError("");
    if (conversation)
      void call("assistant.get", {
        scope: "conversation",
        target_id: conversation,
      })
        .then((r) => {
          if (live) {
            setSettings(r.settings || {});
            setBaseline(r.settings?.instructions || "");
            setLoadedFor(conversation);
          }
        })
        .catch((e) => {
          if (live) setInstructionsError(settingsMessage(String(e)));
        });
    return () => {
      live = false;
    };
  }, [conversation, attempt]);
  return (
    <section className="conversation-options">
      {guard.dialog}
      <div className="section-heading">
        <h3>{t("Conversation context")}</h3>
        {onClose && (
          <button
            className="icon-button"
            disabled={busy}
            onClick={() => guard.confirm(onClose)}
            aria-label={t("Close")}
          >
            <X size={16} />
          </button>
        )}
      </div>
      <div className="segments">
        <button
          onClick={() => setTab("articles")}
          aria-pressed={tab === "articles"}
        >
          {t("Articles")} · {selected.length}/12
        </button>
        {conversation && (
          <button
            onClick={() => setTab("instructions")}
            aria-pressed={tab === "instructions"}
          >
            {t("Conversation instructions")}
          </button>
        )}
      </div>
      {tab === "articles" ? (
        <>
          <label className="field">
            {t("Search your articles")}
            <input value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <div className="context-list" aria-busy={searching}>
            {articlesError ? (
              <div className="context-feedback" role="alert">
                <p>{t("Articles could not be loaded")}</p>
                <button onClick={() => setSearchAttempt((value) => value + 1)}>
                  {t("Retry")}
                </button>
              </div>
            ) : searching ? (
              <p className="context-feedback" role="status">
                <LoaderCircle size={15} className="spin" />
                {t("Searching…")}
              </p>
            ) : !rows.length ? (
              <p className="context-feedback" role="status">
                {t("No matches")}
              </p>
            ) : (
              rows.map((row) => (
                <label key={row.id}>
                  <input
                    type="checkbox"
                    checked={selected.some((s) => s.id === row.id)}
                    disabled={
                      !selected.some((s) => s.id === row.id) &&
                      selected.length >= 12
                    }
                    onChange={(e) =>
                      onSelect(
                        e.target.checked
                          ? [...selected, { id: row.id, title: row.title }]
                          : selected.filter((s) => s.id !== row.id),
                      )
                    }
                  />
                  <span dir="auto">{row.title}</span>
                </label>
              ))
            )}
          </div>
          <label className="field">
            {t("Attach an article link")}
            <input
              type="url"
              disabled={busy}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
            />
          </label>
          <button
            disabled={busy || !url.trim() || selected.length >= 12}
            onClick={async () => {
              if (operation.current) return;
              operation.current = true;
              const target = conversation;
              setBusy(true);
              setImportError("");
              try {
                const r = await call("news.import", { url });
                if (!mounted.current || current.current.conversation !== target)
                  return;
                const latest = current.current.selected;
                if (!latest.some((s) => s.id === r.article_id)) {
                  if (latest.length >= 12) {
                    setImportError(
                      t(
                        "Article saved to your library. Remove an attachment to add it here.",
                      ),
                    );
                    return;
                  }
                  current.current.onSelect([
                    ...latest,
                    { id: r.article_id, title: r.title },
                  ]);
                }
                setUrl("");
              } catch (e) {
                if (mounted.current && current.current.conversation === target)
                  setImportError(settingsMessage(String(e)));
              } finally {
                operation.current = false;
                if (mounted.current) setBusy(false);
              }
            }}
          >
            {t(busy ? "Reading…" : "Attach article")}
          </button>
          {importError && (
            <p className="context-feedback" role="alert">
              {importError}
            </p>
          )}
        </>
      ) : (
        <>
          <p className="muted">
            {t(
              "These instructions apply only to this conversation, alongside your general instructions.",
            )}
          </p>
          {!loaded && !instructionsError && (
            <p className="context-feedback" role="status">
              <LoaderCircle size={15} className="spin" />
              {t("Loading instructions…")}
            </p>
          )}
          {instructionsError && (
            <div className="context-feedback" role="alert">
              <p>{instructionsError}</p>
              {!loaded && (
                <button onClick={() => setAttempt((value) => value + 1)}>
                  {t("Retry")}
                </button>
              )}
            </div>
          )}
          <button disabled={!loaded} onClick={() => setPreview(!preview)}>
            {t(preview ? "Write" : "Preview")}
          </button>
          {preview ? (
            <Markdown text={settings.instructions || ""} />
          ) : (
            <textarea
              className="editor"
              aria-label={t("Conversation instructions")}
              dir="auto"
              maxLength={6000}
              disabled={!loaded}
              value={settings.instructions || ""}
              onChange={(e) => {
                setSettings({ ...settings, instructions: e.target.value });
                setSaved(false);
              }}
            />
          )}
          <button
            disabled={busy || !loaded || !dirty}
            onClick={() => void save()}
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : saved && !dirty ? (
              <Check size={15} />
            ) : null}
            {t(
              busy
                ? "Saving…"
                : saved && !dirty
                  ? "Saved"
                  : "Save instructions",
            )}
          </button>
        </>
      )}
    </section>
  );
}
