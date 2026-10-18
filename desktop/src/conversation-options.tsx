import { useEffect, useState } from "react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { t } from "./locale";
export function ConversationOptions({
  conversation,
  selected,
  onSelect,
  onError,
}: {
  conversation: string;
  selected: RecordData[];
  onSelect: (rows: RecordData[]) => void;
  onError: (message: string) => void;
}) {
  const [tab, setTab] = useState("articles"),
    [query, setQuery] = useState(""),
    [url, setUrl] = useState(""),
    [rows, setRows] = useState<RecordData[]>([]),
    [busy, setBusy] = useState(false),
    [settings, setSettings] = useState<RecordData>({}),
    [preview, setPreview] = useState(false),
    [saved, setSaved] = useState(false);
  useEffect(() => {
    let live = true;
    const timer = setTimeout(() => {
      void call("news.list", { query, limit: 20 })
        .then((r) => {
          if (live) setRows(r.articles || []);
        })
        .catch((e) => {
          if (live) onError(String(e));
        });
    }, 250);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [query]);
  useEffect(() => {
    let live = true;
    setSettings({});
    setSaved(false);
    if (conversation)
      void call("assistant.get", {
        scope: "conversation",
        target_id: conversation,
      })
        .then((r) => {
          if (live) setSettings(r.settings);
        })
        .catch((e) => {
          if (live) onError(String(e));
        });
    return () => {
      live = false;
    };
  }, [conversation]);
  return (
    <section className="conversation-options">
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
          <div className="context-list">
            {rows.map((row) => (
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
            ))}
          </div>
          <label className="field">
            {t("Attach an article link")}
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
            />
          </label>
          <button
            disabled={busy || !url.trim() || selected.length >= 12}
            onClick={async () => {
              setBusy(true);
              try {
                const r = await call("news.import", { url });
                if (!selected.some((s) => s.id === r.article_id))
                  onSelect([...selected, { id: r.article_id, title: r.title }]);
                setUrl("");
              } catch (e) {
                onError(String(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            {t(busy ? "Reading…" : "Attach article")}
          </button>
        </>
      ) : (
        <>
          <p className="muted">
            {t(
              "These instructions apply only to this conversation, alongside your general instructions.",
            )}
          </p>
          <button onClick={() => setPreview(!preview)}>
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
              value={settings.instructions || ""}
              onChange={(e) => {
                setSettings({ ...settings, instructions: e.target.value });
                setSaved(false);
              }}
            />
          )}
          <button
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await call("assistant.save", {
                  scope: "conversation",
                  target_id: conversation,
                  settings,
                });
                setSaved(true);
              } catch (e) {
                onError(String(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            {t(saved ? "Saved" : "Save instructions")}
          </button>
        </>
      )}
    </section>
  );
}
