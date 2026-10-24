import { t } from "./locale";
import { useEffect, useRef, useState } from "react";
import { call } from "./engine";
import { Markdown } from "./components";
import { useUnsavedChanges } from "./unsaved-changes";
import { LoaderCircle } from "lucide-react";
export function TaskInstructions({
  id,
  title,
  onError,
}: {
  id: string;
  title: string;
  onError: (s: string) => void;
}) {
  const [content, setContent] = useState(""),
    [preview, setPreview] = useState(false),
    [busy, setBusy] = useState(true),
    [saved, setSaved] = useState(false);
  const [baseline, setBaseline] = useState("");
  const [limit, setLimit] = useState(16000);
  const [loadedFor, setLoadedFor] = useState(""),
    [attempt, setAttempt] = useState(0);
  const currentId = useRef(id),
    saving = useRef(false),
    mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  currentId.current = id;
  const guard = useUnsavedChanges(
    loadedFor === id && content !== baseline,
    save,
  );
  useEffect(() => {
    let live = true;
    setBusy(true);
    setSaved(false);
    setLoadedFor("");
    setContent("");
    setBaseline("");
    call("instructions.get", { id })
      .then((r) => {
        if (live) {
          if (typeof r.content !== "string")
            throw new Error(t("The instruction document could not be loaded."));
          setLimit(r.limit || 16000);
          setContent(r.content);
          setBaseline(r.content);
          setLoadedFor(id);
        }
      })
      .catch((e) => {
        if (live) onError(String(e));
      })
      .finally(() => {
        if (live) setBusy(false);
      });
    return () => {
      live = false;
    };
  }, [id, attempt]);
  async function save() {
    if (saving.current || loadedFor !== id) return false;
    saving.current = true;
    setBusy(true);
    onError("");
    try {
      await call("instructions.save", { id, content });
      if (mounted.current && currentId.current === id) {
        setSaved(true);
        setBaseline(content);
      }
      return true;
    } catch (e) {
      if (mounted.current && currentId.current === id) onError(String(e));
      return false;
    } finally {
      saving.current = false;
      if (mounted.current && currentId.current === id) setBusy(false);
    }
  }
  return (
    <section className="task-instructions">
      {guard.dialog}
      <div className="editor-header">
        <h3>{title}</h3>
        <div className="segments">
          <button aria-pressed={!preview} onClick={() => setPreview(false)}>
            {t("Write")}
          </button>
          <button aria-pressed={preview} onClick={() => setPreview(true)}>
            {t("Preview")}
          </button>
        </div>
      </div>
      <p className="muted">
        {t(
          "These are the actual instructions used for new results. Your edits survive updates.",
        )}
      </p>
      {loadedFor !== id ? (
        <div className="instruction-load-state" role="status">
          {busy ? (
            t("Loading instructions…")
          ) : (
            <>
              <p>{t("The instruction document could not be loaded.")}</p>
              <button
                onClick={() => {
                  onError("");
                  setAttempt((value) => value + 1);
                }}
              >
                {t("Try again")}
              </button>
            </>
          )}
        </div>
      ) : preview ? (
        <div className="markdown-preview">
          <Markdown text={content} />
        </div>
      ) : (
        <textarea
          className="editor"
          dir="auto"
          aria-label={title}
          disabled={busy}
          maxLength={limit}
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            setSaved(false);
          }}
        />
      )}
      <div className="save-row">
        <small>
          {content.length.toLocaleString()} {t("characters")}
        </small>
        <button
          className="primary"
          disabled={busy || loadedFor !== id || !content.trim()}
          onClick={() => void save()}
        >
          {saving.current && <LoaderCircle size={15} className="spin" />}
          {t(
            saving.current ? "Saving…" : saved ? "Saved" : "Save instructions",
          )}
        </button>
      </div>
    </section>
  );
}
