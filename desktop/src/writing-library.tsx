import { t } from "./locale";
import { useState } from "react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
export function WritingLibrary({
  snapshot,
  refresh,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [title, setTitle] = useState(""),
    [text, setText] = useState(""),
    [author, setAuthor] = useState(""),
    [uri, setUri] = useState(""),
    [accessMethod, setAccessMethod] = useState("user_paste"),
    [purpose, setPurpose] = useState("reference"),
    [rights, setRights] = useState("unknown"),
    [selected, setSelected] = useState<RecordData>(),
    [busy, setBusy] = useState(false);
  async function action(command: string, payload: RecordData) {
    setBusy(true);
    try {
      await call(command, payload);
      await refresh();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <h2>{t("Your writing & references.")}</h2>
      <p className="muted">
        {t(
          "Keep reference material and examples of your own voice. Style examples require ownership or permission.",
        )}
      </p>
      <div className="source-list">
        {(snapshot.sources || []).map((s: RecordData) => (
          <div key={s.id}>
            <button
              onClick={async () => {
                try {
                  setSelected({
                    ...s,
                    ...(await call("sources.detail", { item_id: s.id })),
                  });
                } catch (e) {
                  onError(String(e));
                }
              }}
            >
              <strong>{s.title}</strong>
              <small>{s.purpose}</small>
            </button>
            <button
              disabled={busy}
              onClick={() =>
                void action("analysis.run", {
                  item_ids: [s.id],
                  mode: "incremental",
                  consent: true,
                  profile_id: snapshot.assignments?.find(
                    (a: RecordData) => a.role === "analyst",
                  )?.profile_id,
                  model_id: snapshot.assignments?.find(
                    (a: RecordData) => a.role === "analyst",
                  )?.model_id,
                  idempotency_key: crypto.randomUUID(),
                })
              }
            >
              {t("Analyze writing")}
            </button>
          </div>
        ))}
      </div>
      {selected && (
        <details open>
          <summary>{selected.title}</summary>
          <Markdown text={selected.text} />
        </details>
      )}
      <h3>{t("Add writing")}</h3>
      <label className="field">
        {t("Title")}
        <input value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label className="field">
        {t("Use as")}
        <select value={purpose} onChange={(e) => setPurpose(e.target.value)}>
          <option value="reference">{t("Reference material")}</option>
          <option value="style">{t("Writing style example")}</option>
        </select>
      </label>
      <label className="field">
        {t("Rights")}
        <select value={rights} onChange={(e) => setRights(e.target.value)}>
          <option value="unknown">{t("Reference only / unknown")}</option>
          <option value="owned">{t("My own writing")}</option>
          <option value="licensed">{t("I have permission")}</option>
        </select>
      </label>
      <label className="field">
        {t("Author")}
        <input value={author} onChange={(e) => setAuthor(e.target.value)} />
      </label>
      <label className="field">
        {t("Original link")}
        <input
          type="url"
          value={uri}
          onChange={(e) => setUri(e.target.value)}
        />
      </label>
      <label className="field">
        {t("Import text or Markdown")}
        <input
          type="file"
          accept=".txt,.md,.markdown,text/plain,text/markdown"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              if (file.size > 512000)
                throw new Error(t("Choose a text file smaller than 500 KB."));
              const content = new TextDecoder("utf-8", { fatal: true }).decode(
                await file.arrayBuffer(),
              );
              if ([...content].length > 120000)
                throw new Error(t("Text must not exceed 120000 characters."));
              setText(content);
              setAccessMethod("user_file");
              if (!title) setTitle(file.name.replace(/\.[^.]+$/, ""));
            } catch (error) {
              onError(String(error));
            }
            e.target.value = "";
          }}
        />
      </label>
      <textarea
        className="editor"
        dir="auto"
        aria-label={t("Writing text")}
        value={text}
        maxLength={120000}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        className="primary"
        disabled={
          busy ||
          !title.trim() ||
          !text.trim() ||
          (purpose === "style" && rights === "unknown")
        }
        onClick={async () => {
          setBusy(true);
          try {
            await call("sources.add", {
              title,
              text,
              purpose,
              author,
              canonical_uri: uri,
              access_method: accessMethod,
              rights_status: rights,
            });
            await refresh();
            setTitle("");
            setText("");
            setAuthor("");
            setUri("");
            setAccessMethod("user_paste");
          } catch (e) {
            onError(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {t("Save writing")}
      </button>
      <h3>{t("Suggested style rules")}</h3>
      {(snapshot.techniques || []).map((technique: RecordData) => (
        <div className="notice" key={technique.id}>
          <strong>{technique.name}</strong>
          <p>{technique.description}</p>
          <blockquote dir="auto">
            {technique.evidence_text?.slice(
              technique.excerpt_start,
              technique.excerpt_end,
            )}
          </blockquote>
          {technique.status !== "approved" && (
            <button
              disabled={busy}
              onClick={() =>
                void action("dna.approve", { technique_id: technique.id })
              }
            >
              {t("Use this style rule")}
            </button>
          )}
        </div>
      ))}
      <h3>{t("Approved style")}</h3>
      {(snapshot.rules || [])
        .filter((r: RecordData) => r.status === "approved")
        .map((r: RecordData) => (
          <div className="setting-row" key={r.id}>
            <span dir="auto">{r.statement}</span>
            <button
              disabled={busy}
              onClick={() => void action("dna.retire", { rule_id: r.id })}
            >
              {t("Retire")}
            </button>
          </div>
        ))}
    </>
  );
}
