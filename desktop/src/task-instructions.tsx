import { t } from "./locale";
import { useEffect, useState } from "react";
import { call } from "./engine";
import { Markdown } from "./components";
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
  useEffect(() => {
    let live = true;
    setBusy(true);
    call("instructions.get", { id })
      .then((r) => {
        if (live) setContent(r.content);
      })
      .catch((e) => onError(String(e)))
      .finally(() => {
        if (live) setBusy(false);
      });
    return () => {
      live = false;
    };
  }, [id]);
  async function save() {
    setBusy(true);
    try {
      await call("instructions.save", { id, content });
      setSaved(true);
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="task-instructions">
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
      {preview ? (
        <div className="markdown-preview">
          <Markdown text={content} />
        </div>
      ) : (
        <textarea
          className="editor"
          dir="auto"
          aria-label={title}
          disabled={busy}
          maxLength={16000}
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            setSaved(false);
          }}
        />
      )}
      <div className="save-row">
        <small>
          {content.length.toLocaleString()}
          {t("characters")}
        </small>
        <button
          className="primary"
          disabled={busy || !content.trim()}
          onClick={() => void save()}
        >
          {saved ? t("Saved") : t("Save instructions")}
        </button>
      </div>
    </section>
  );
}
