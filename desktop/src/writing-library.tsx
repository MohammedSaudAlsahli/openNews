import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  Check,
  FileText,
  LoaderCircle,
  Plus,
  Search,
  X,
} from "lucide-react";
import { t } from "./locale";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { useUnsavedChanges } from "./unsaved-changes";

const empty = {
  title: "",
  text: "",
  author: "",
  uri: "",
  accessMethod: "user_paste",
  purpose: "reference",
  rights: "unknown",
};
export function WritingLibrary({
  snapshot,
  refresh,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [form, setForm] = useState(empty),
    [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState<RecordData>(),
    [loadingId, setLoadingId] = useState("");
  const [busy, setBusy] = useState(false),
    [query, setQuery] = useState(""),
    [notice, setNotice] = useState("");
  const detailRequest = useRef(0),
    importRequest = useRef(0),
    inFlight = useRef(false);
  useEffect(
    () => () => {
      detailRequest.current++;
      importRequest.current++;
    },
    [],
  );
  const dirty = adding && JSON.stringify(form) !== JSON.stringify(empty);
  const guard = useUnsavedChanges(dirty, save);
  const sources = (snapshot.sources || []).filter((s: RecordData) =>
    `${s.title} ${s.author || ""} ${s.text || ""}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  function change(key: keyof typeof empty, value: string) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }
  function closeEditor() {
    importRequest.current++;
    setAdding(false);
    setForm(empty);
  }
  async function save() {
    if (inFlight.current) return false;
    if (
      !form.title.trim() ||
      !form.text.trim() ||
      (form.purpose === "style" && form.rights === "unknown")
    ) {
      onError(
        t(
          "Add a title and text. Style examples also need ownership or permission.",
        ),
      );
      return false;
    }
    if (form.uri && !/^https?:\/\/\S+$/i.test(form.uri)) {
      onError(t("Enter a complete http or https link."));
      return false;
    }
    inFlight.current = true;
    setBusy(true);
    setNotice("");
    try {
      await call("sources.add", {
        title: form.title,
        text: form.text,
        purpose: form.purpose,
        author: form.author,
        canonical_uri: form.uri,
        access_method: form.accessMethod,
        rights_status: form.rights,
      });
      closeEditor();
      setNotice(t("Reference saved."));
      await refresh().catch((e) => onError(String(e)));
      return true;
    } catch (e) {
      onError(String(e));
      return false;
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function action(command: string, payload: RecordData) {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setNotice("");
    try {
      await call(command, payload);
      setNotice(
        t(
          command === "analysis.run"
            ? "Analysis started. Follow its progress in Background activity."
            : "Style rules updated.",
        ),
      );
      await refresh().catch((e) => onError(String(e)));
    } catch (e) {
      onError(String(e));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function show(row: RecordData) {
    const request = ++detailRequest.current;
    setLoadingId(row.id);
    setSelected(undefined);
    try {
      const result = await call("sources.detail", { item_id: row.id });
      if (request === detailRequest.current) setSelected({ ...row, ...result });
    } catch (e) {
      if (request === detailRequest.current) onError(String(e));
    } finally {
      if (request === detailRequest.current) setLoadingId("");
    }
  }
  return (
    <section className="writing-library">
      {guard.dialog}
      <div className="editor-header">
        <h2>{t("Examples & references")}</h2>
        <button disabled={busy} onClick={() => setAdding(true)}>
          <Plus size={15} />
          {t("Add writing")}
        </button>
      </div>
      <p className="muted">
        {t(
          "Keep reference material and examples of your own voice. Style examples require ownership or permission.",
        )}
      </p>
      {notice && (
        <p className="inline-success" role="status">
          <Check size={15} />
          {notice}
        </p>
      )}
      {adding && (
        <form
          className="reference-editor"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <div className="editor-header">
            <h3>{t("Add writing")}</h3>
            <button
              type="button"
              disabled={busy}
              className="icon-button"
              aria-label={t("Close editor")}
              onClick={() => guard.confirm(closeEditor)}
            >
              <X size={16} />
            </button>
          </div>
          <fieldset className="plain-fieldset" disabled={busy}>
            <label className="field">
              {t("Title")}
              <input
                autoFocus
                required
                dir="auto"
                maxLength={300}
                value={form.title}
                onChange={(e) => change("title", e.target.value)}
              />
            </label>
            <div className="form-grid">
              <label className="field">
                {t("Use as")}
                <select
                  value={form.purpose}
                  onChange={(e) => change("purpose", e.target.value)}
                >
                  <option value="reference">{t("Reference material")}</option>
                  <option value="style">{t("Writing style example")}</option>
                </select>
              </label>
              <label className="field">
                {t("Rights")}
                <select
                  value={form.rights}
                  onChange={(e) => change("rights", e.target.value)}
                >
                  <option value="unknown">
                    {t("Reference only / unknown")}
                  </option>
                  <option value="owned">{t("My own writing")}</option>
                  <option value="licensed">{t("I have permission")}</option>
                </select>
              </label>
            </div>
            {form.purpose === "style" && form.rights === "unknown" && (
              <p className="muted">
                {t(
                  "Choose ownership or permission to use this text as a style example.",
                )}
              </p>
            )}
            <div className="form-grid">
              <label className="field">
                {t("Author")}
                <input
                  dir="auto"
                  maxLength={200}
                  value={form.author}
                  onChange={(e) => change("author", e.target.value)}
                />
              </label>
              <label className="field">
                {t("Original link")}
                <input
                  type="url"
                  maxLength={2000}
                  dir="ltr"
                  value={form.uri}
                  onChange={(e) => change("uri", e.target.value)}
                />
              </label>
            </div>
            <label className="field">
              {t("Import text or Markdown")}
              <input
                type="file"
                accept=".txt,.md,.markdown,text/plain,text/markdown"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (!file) return;
                  const request = ++importRequest.current;
                  try {
                    if (file.size > 512000)
                      throw new Error(
                        t("Choose a text file smaller than 500 KB."),
                      );
                    const text = new TextDecoder("utf-8", {
                      fatal: true,
                    }).decode(await file.arrayBuffer());
                    if ([...text].length > 120000)
                      throw new Error(
                        t("Text must not exceed 120000 characters."),
                      );
                    if (request === importRequest.current)
                      setForm((previous) => ({
                        ...previous,
                        text,
                        title:
                          previous.title ||
                          file.name.replace(/\.[^.]+$/, "").slice(0, 300),
                        accessMethod: "user_file",
                      }));
                  } catch (e) {
                    if (request === importRequest.current) onError(String(e));
                  }
                }}
              />
            </label>
            <label className="field">
              {t("Writing text")}
              <textarea
                className="editor"
                required
                dir="auto"
                maxLength={120000}
                value={form.text}
                onChange={(e) => change("text", e.target.value)}
              />
            </label>
          </fieldset>
          <div className="save-row">
            <small className="muted">
              {form.text.length.toLocaleString()} / 120,000 {t("characters")}
            </small>
            <div className="reader-actions">
              <button
                type="button"
                disabled={busy}
                onClick={() => guard.confirm(closeEditor)}
              >
                {t("Cancel")}
              </button>
              <button
                type="submit"
                className="primary"
                disabled={
                  busy ||
                  !form.title.trim() ||
                  !form.text.trim() ||
                  (form.purpose === "style" && form.rights === "unknown")
                }
              >
                {busy && <LoaderCircle size={15} className="spin" />}
                {t("Save writing")}
              </button>
            </div>
          </div>
        </form>
      )}
      {(snapshot.sources || []).length > 0 && (
        <label className="search">
          <Search size={16} />
          <input
            aria-label={t("Search references")}
            placeholder={t("Search references")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      )}
      <div className="reference-list">
        {sources.map((s: RecordData) => {
          const cloudRestricted =
            s.rights_status === "unknown" &&
            snapshot.assignments?.some(
              (a: RecordData) => a.role === "analyst" && a.profile_id,
            );
          return (
            <div className="reference-row" key={s.id}>
              <button
                className="reference-open"
                onClick={() => void show(s)}
                aria-pressed={selected?.id === s.id}
              >
                {loadingId === s.id ? (
                  <LoaderCircle size={17} className="spin" />
                ) : (
                  <FileText size={17} />
                )}
                <span>
                  <strong dir="auto">{s.title}</strong>
                  <small>
                    {t(
                      s.purpose === "style"
                        ? "Writing style example"
                        : "Reference material",
                    )}
                    {s.author ? ` · ${s.author}` : ""}
                  </small>
                </span>
              </button>
              <button
                disabled={busy || cloudRestricted}
                title={
                  cloudRestricted
                    ? t(
                        "Confirm ownership or permission before sending this text to a model.",
                      )
                    : undefined
                }
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
          );
        })}
      </div>
      {!sources.length && (
        <div className="reference-empty">
          <BookOpen size={22} />
          <p>
            {t(
              query
                ? "No references match your search."
                : "Save an example of your writing or reference text to use in future responses.",
            )}
          </p>
        </div>
      )}
      {selected && (
        <section className="reference-preview">
          <div className="editor-header">
            <h3 dir="auto">{selected.title}</h3>
            <button
              className="icon-button"
              aria-label={t("Close preview")}
              onClick={() => {
                detailRequest.current++;
                setSelected(undefined);
              }}
            >
              <X size={16} />
            </button>
          </div>
          <Markdown text={selected.text || ""} />
        </section>
      )}
      {((snapshot.techniques || []).length > 0 ||
        (snapshot.rules || []).some(
          (r: RecordData) => r.status === "approved",
        )) && (
        <section className="writing-rules">
          <h3>{t("Writing style rules")}</h3>
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
        </section>
      )}
    </section>
  );
}
