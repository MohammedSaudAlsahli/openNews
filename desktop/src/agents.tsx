import { t } from "./locale";
import { useEffect, useState } from "react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
export function Agents({
  snapshot,
  refresh,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [agents, setAgents] = useState<RecordData[]>([]),
    [id, setId] = useState(""),
    [name, setName] = useState(""),
    [instructions, setInstructions] = useState(""),
    [profile, setProfile] = useState(""),
    [model, setModel] = useState(""),
    [models, setModels] = useState<RecordData[]>([]),
    [preview, setPreview] = useState(false),
    [busy, setBusy] = useState(false);
  const load = () => call("agents.list").then((r) => setAgents(r.agents));
  useEffect(() => {
    void load().catch((e) => onError(String(e)));
  }, []);
  useEffect(() => {
    let live = true;
    setModels([]);
    if (profile)
      call("providers.models", { profile_id: profile })
        .then((r) => {
          if (live) setModels(r.models);
        })
        .catch((e) => onError(String(e)));
    return () => {
      live = false;
    };
  }, [profile]);
  async function save() {
    setBusy(true);
    try {
      await call("agents.save", {
        ...(id ? { id } : {}),
        name,
        instructions,
        profile_id: profile,
        model_id: model,
      });
      await load();
      await refresh();
      setId("");
      setName("");
      setInstructions("");
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <h2>{t("Assistants for the way you work.")}</h2>
      <p className="muted">
        {t(
          "Give each assistant its own instructions and model, then select it in the conversation.",
        )}
      </p>
      <div className="source-list">
        {agents.map((a) => (
          <button
            key={a.id}
            onClick={() => {
              setId(a.id);
              setName(a.name);
              setInstructions(a.instructions);
              setProfile(a.profile_id);
              setModel(a.model_id);
            }}
          >
            <strong>{a.name}</strong>
            <small>{a.model_id}</small>
          </button>
        ))}
      </div>
      <h3>{t(id ? t("Edit assistant") : t("New assistant"))}</h3>
      {id && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await call("agents.delete", { agent_id: id });
              setId("");
              setName("");
              setInstructions("");
              await load();
              await refresh();
            } catch (e) {
              onError(String(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          {t("Delete assistant")}
        </button>
      )}
      <label className="field">
        {t("Name")}
        <input
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className="field">
        {t("Connection")}
        <select
          value={profile}
          onChange={(e) => {
            setProfile(e.target.value);
            setModel("");
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
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          <option value="">{t("Select model")}</option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name || m.id}
            </option>
          ))}
        </select>
      </label>
      <div className="editor-header">
        <h3>{t("Instructions")}</h3>
        <button onClick={() => setPreview(!preview)}>
          {preview ? t("Write") : t("Preview")}
        </button>
      </div>
      {preview ? (
        <Markdown text={instructions} />
      ) : (
        <textarea
          className="editor"
          dir="auto"
          maxLength={12000}
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
        />
      )}
      <button
        className="primary"
        disabled={busy || !name.trim() || !instructions.trim() || !model}
        onClick={() => void save()}
      >
        {t("Save assistant")}
      </button>
    </>
  );
}
