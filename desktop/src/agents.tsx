import { useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Bot, Check, LoaderCircle, Plus, Trash2, X } from "lucide-react";
import { t } from "./locale";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { useUnsavedChanges } from "./unsaved-changes";

const blank = { name: "", instructions: "", profile: "", model: "" };
export function Agents({
  snapshot,
  refresh,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [agents, setAgents] = useState<RecordData[]>([]);
  const [id, setId] = useState(""),
    [form, setForm] = useState(blank);
  const [baseline, setBaseline] = useState(JSON.stringify(blank));
  const [editing, setEditing] = useState(false),
    [preview, setPreview] = useState(false);
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false);
  const [models, setModels] = useState<RecordData[]>([]),
    [loadingModels, setLoadingModels] = useState(false);
  const [notice, setNotice] = useState(""),
    [deleting, setDeleting] = useState(false);
  const inFlight = useRef(false);
  const dirty = editing && JSON.stringify(form) !== baseline;
  const guard = useUnsavedChanges(dirty, save);
  useEffect(() => {
    let live = true;
    call("agents.list")
      .then((r) => {
        if (live) setAgents(r.agents || []);
      })
      .catch((e) => {
        if (live) onError(String(e));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    let live = true;
    setModels([]);
    if (!form.profile) {
      setLoadingModels(false);
      return;
    }
    setLoadingModels(true);
    call("providers.models", { profile_id: form.profile })
      .then((r) => {
        if (!live) return;
        setModels(r.models || []);
        if (r.error) onError(r.error);
      })
      .catch((e) => {
        if (live) onError(String(e));
      })
      .finally(() => {
        if (live) setLoadingModels(false);
      });
    return () => {
      live = false;
    };
  }, [form.profile]);

  function edit(row?: RecordData) {
    const value = row
      ? {
          name: row.name,
          instructions: row.instructions,
          profile: row.profile_id,
          model: row.model_id,
        }
      : blank;
    setId(row?.id || "");
    setForm(value);
    setBaseline(JSON.stringify(value));
    setEditing(true);
    setPreview(false);
    setNotice("");
  }
  function change(key: keyof typeof blank, value: string) {
    setForm((previous) => ({ ...previous, [key]: value }));
    setNotice("");
  }
  async function save() {
    if (inFlight.current) return false;
    if (
      !form.name.trim() ||
      !form.instructions.trim() ||
      !form.profile ||
      !form.model
    ) {
      onError(t("Add a name, instructions and a model before saving."));
      return false;
    }
    inFlight.current = true;
    setBusy(true);
    setNotice("");
    try {
      const payload = {
        ...(id ? { id } : {}),
        name: form.name,
        instructions: form.instructions,
        profile_id: form.profile,
        model_id: form.model,
      };
      const result = await call("agents.save", payload);
      const savedId = result.agent_id || id;
      setId(savedId);
      setBaseline(JSON.stringify(form));
      setNotice(t("Assistant saved."));
      setAgents((previous) => [
        { ...payload, id: savedId },
        ...previous.filter((a) => a.id !== savedId),
      ]);
      // A refresh failure must not turn an acknowledged save into a duplicate create.
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
  async function remove() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      await call("agents.delete", { agent_id: id });
      setAgents((previous) => previous.filter((a) => a.id !== id));
      setDeleting(false);
      setEditing(false);
      setForm(blank);
      setBaseline(JSON.stringify(blank));
      setId("");
      await refresh().catch((e) => onError(String(e)));
    } catch (e) {
      onError(String(e));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  return (
    <section className="assistant-library">
      {guard.dialog}
      <div className="editor-header">
        <h3>{t("Specialized assistants")}</h3>
        <button disabled={busy} onClick={() => guard.confirm(() => edit())}>
          <Plus size={15} />
          {t("New assistant")}
        </button>
      </div>
      {loading ? (
        <p className="muted" role="status">
          <LoaderCircle size={15} className="spin" />
          {t("Loading assistants…")}
        </p>
      ) : agents.length > 0 ? (
        <div className="assistant-list">
          {agents.map((a) => (
            <button
              key={a.id}
              disabled={busy}
              aria-pressed={id === a.id && editing}
              onClick={() => guard.confirm(() => edit(a))}
            >
              <Bot size={18} />
              <span>
                <strong dir="auto">{a.name}</strong>
                <small dir="auto">{a.model_id}</small>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">
          {t(
            "No specialized assistants yet. Your general assistant is ready to use.",
          )}
        </p>
      )}
      {editing && (
        <div className="assistant-editor">
          <div className="editor-header">
            <h3>{t(id ? "Edit assistant" : "New assistant")}</h3>
            <button
              disabled={busy}
              className="icon-button"
              aria-label={t("Close editor")}
              onClick={() => guard.confirm(() => setEditing(false))}
            >
              <X size={16} />
            </button>
          </div>
          <fieldset disabled={busy} className="plain-fieldset">
            <label className="field">
              {t("Name")}
              <input
                autoFocus
                dir="auto"
                value={form.name}
                maxLength={120}
                onChange={(e) => change("name", e.target.value)}
              />
            </label>
            <div className="form-grid">
              <label className="field">
                {t("Connection")}
                <select
                  value={form.profile}
                  onChange={(e) => {
                    setForm((previous) => ({
                      ...previous,
                      profile: e.target.value,
                      model: "",
                    }));
                    setNotice("");
                  }}
                >
                  <option value="">{t("Select connection")}</option>
                  {(snapshot.profiles || []).map((p: RecordData) => (
                    <option key={p.id} value={p.id}>
                      {p.label || p.provider_key}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                {t("Model")}
                <select
                  value={form.model}
                  disabled={!form.profile || loadingModels}
                  onChange={(e) => change("model", e.target.value)}
                >
                  <option value="">
                    {t(loadingModels ? "Loading models…" : "Select model")}
                  </option>
                  {form.model && !models.some((m) => m.id === form.model) && (
                    <option value={form.model}>{form.model}</option>
                  )}
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name || m.id}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="editor-header">
              <h4>{t("Instructions")}</h4>
              <div className="segments">
                <button
                  type="button"
                  aria-pressed={!preview}
                  onClick={() => setPreview(false)}
                >
                  {t("Write")}
                </button>
                <button
                  type="button"
                  aria-pressed={preview}
                  onClick={() => setPreview(true)}
                >
                  {t("Preview")}
                </button>
              </div>
            </div>
            {preview ? (
              <div className="markdown-preview">
                <Markdown text={form.instructions} />
              </div>
            ) : (
              <textarea
                className="editor"
                dir="auto"
                aria-label={t("Assistant instructions")}
                maxLength={12000}
                value={form.instructions}
                onChange={(e) => change("instructions", e.target.value)}
              />
            )}
          </fieldset>
          <div className="save-row">
            <span className="muted" role="status">
              {notice ||
                t(dirty ? "Unsaved changes" : id ? "Saved" : "Not saved")}
            </span>
            <div className="reader-actions">
              {id && (
                <button
                  className="danger-text"
                  disabled={busy}
                  onClick={() => setDeleting(true)}
                >
                  <Trash2 size={15} />
                  {t("Delete assistant")}
                </button>
              )}
              <button
                className="primary"
                disabled={
                  busy ||
                  !dirty ||
                  !form.name.trim() ||
                  !form.instructions.trim() ||
                  !form.model
                }
                onClick={() => void save()}
              >
                {busy ? (
                  <LoaderCircle size={15} className="spin" />
                ) : (
                  <Check size={15} />
                )}{" "}
                {t("Save assistant")}
              </button>
            </div>
          </div>
        </div>
      )}
      <Dialog.Root
        open={deleting}
        onOpenChange={(open) => {
          if (!busy) setDeleting(open);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-panel">
            <Dialog.Title>{t("Delete this assistant?")}</Dialog.Title>
            <Dialog.Description>
              {t(
                "Its preset and instructions will be removed. Saved conversations stay in your workspace.",
              )}
            </Dialog.Description>
            <p dir="auto">
              <strong>{form.name}</strong>
            </p>
            <div className="dialog-actions">
              <button disabled={busy} onClick={() => setDeleting(false)}>
                {t("Cancel")}
              </button>
              <button
                className="danger-button"
                disabled={busy}
                onClick={() => void remove()}
              >
                {t(busy ? "Deleting…" : "Delete assistant")}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
