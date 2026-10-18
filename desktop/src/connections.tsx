import { settingsMessage } from "./settings-message";
import { t, getLocale } from "./locale";
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { call, type RecordData } from "./engine";
export function Connections({
  snapshot,
  refresh,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [catalog, setCatalog] = useState<RecordData[]>([]),
    [provider, setProvider] = useState("ollama"),
    [label, setLabel] = useState(""),
    [model, setModel] = useState(""),
    [config, setConfig] = useState<Record<string, string>>({}),
    [secrets, setSecrets] = useState<Record<string, string>>({}),
    [busy, setBusy] = useState(false),
    [auth, setAuth] = useState(""),
    [models, setModels] = useState<Record<string, RecordData[]>>({});
  const entry = catalog.find((p) => p.id === provider);
  useEffect(() => {
    call("providers.catalog")
      .then((r) => setCatalog(r.providers))
      .catch((e) => setError(String(e)));
  }, []);
  useEffect(() => {
    if (!auth) return;
    let live = true,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const r = await call("providers.auth.status", { auth_id: auth });
        if (!live) return;
        if (r.status === "complete") {
          setAuth("");
          await refresh();
          return;
        }
        if (r.status !== "waiting") {
          setAuth("");
          if (r.error) setError(r.error);
          return;
        }
      } catch (e) {
        if (live) setError(String(e));
        return;
      }
      if (live) timer = setTimeout(poll, 1500);
    }
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [auth]);
  async function signIn(profile_id?: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await call("providers.auth.start", {
        provider_key: "openai-chatgpt",
        profile_id,
        language: getLocale(),
      });
      setAuth(r.auth_id);
      await invoke("open_external", { address: r.authorization_url });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    setBusy(true);
    setError("");
    setNotice("");
    let created = "";
    try {
      const r = await call("providers.save", {
        provider_key: provider,
        label,
        model_id: model || entry?.default_model || "",
        config: Object.fromEntries(
          Object.entries(config).filter(([, value]) => value.trim()),
        ),
      });
      created = r.profile_id;
      if (Object.values(secrets).some(Boolean))
        await invoke("save_credentials", {
          profileId: created,
          values: Object.fromEntries(
            Object.entries(secrets)
              .filter(([, v]) => v.trim())
              .map(([key, value]) => [
                key,
                key === "service_account_info" ? JSON.parse(value) : value,
              ]),
          ),
        });
      setSecrets({});
      setLabel("");
      setModel("");
      await refresh();
      await loadModels(created);
      setAdding(false);
      setNotice(t("Connection added"));
    } catch (e) {
      setError(String(e));
      if (created) await refresh();
    } finally {
      setBusy(false);
    }
  }
  async function loadModels(id: string) {
    setBusy(true);
    setError("");
    try {
      const r = await call("providers.models", {
        profile_id: id,
        refresh: true,
      });
      if (r.error) setError(r.error);
      setModels((old) => ({ ...old, [id]: r.models || [] }));
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function action(command: string, p: RecordData) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await call(command, p);
      if (result.error) throw new Error(result.error);
      setNotice(
        t(command === "providers.check" ? "Connection checked" : "Saved"),
      );
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="settings-section-heading">
        <div>
          <h2>{t("Accounts & models")}</h2>
          <p className="muted">
            {t("Choose the account your assistant uses.")}
          </p>
        </div>
        <button
          className="primary"
          onClick={() => {
            setAdding(true);
            setError("");
          }}
        >
          {t("Add account")}
        </button>
      </div>
      {error && (
        <div className="settings-feedback" role="alert">
          {settingsMessage(error)}
          <button onClick={() => setError("")}>{t("Dismiss")}</button>
        </div>
      )}
      {notice && (
        <p className="settings-feedback" role="status">
          {notice}
        </p>
      )}
      {auth && (
        <div className="notice" role="status">
          {t("Complete sign-in in your browser.")}
          <button
            onClick={async () => {
              await call("providers.auth.cancel", { auth_id: auth });
              setAuth("");
            }}
          >
            {t("Cancel sign-in")}
          </button>
        </div>
      )}
      <div className="connection-list">
        {(snapshot.profiles || []).map((p: RecordData) => (
          <section key={p.id}>
            <div className="connection-heading">
              <h3>{p.label || p.provider_key}</h3>
              <span>{p.model_id || t("Choose a model")}</span>
            </div>
            <details className="connection-manage">
              <summary>{t("Manage account")}</summary>
              <div className="reader-actions">
                <button
                  disabled={busy}
                  onClick={() =>
                    void action("providers.check", { profile_id: p.id })
                  }
                >
                  {t("Check connection")}
                </button>
                <button disabled={busy} onClick={() => void loadModels(p.id)}>
                  {t("Refresh models")}
                </button>
                {p.provider_key === "openai-chatgpt" && (
                  <button onClick={() => void signIn(p.id)}>
                    {t("Sign in again")}
                  </button>
                )}
                <button
                  disabled={busy}
                  onClick={() =>
                    void action("providers.disconnect", { profile_id: p.id })
                  }
                >
                  {t("Disconnect")}
                </button>
              </div>
              {models[p.id] && (
                <label className="field">
                  {t("Default model")}
                  <select
                    value={p.model_id}
                    onChange={(e) =>
                      void action("providers.update", {
                        profile_id: p.id,
                        model_id: e.target.value,
                      })
                    }
                  >
                    <option value="">{t("Choose a model")}</option>
                    {models[p.id].map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name || m.id}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <h4>{t("Use this model for")}</h4>
              <p className="muted">
                {t(
                  "Apply the selected model to a task. Article explanations can also use a local model in News settings.",
                )}
              </p>
              <div className="reader-actions">
                {["writer", "analyst", "news"].map((role) => (
                  <button
                    key={role}
                    disabled={busy || !p.model_id}
                    onClick={() =>
                      void action("agents.assign", {
                        role,
                        profile_id: p.id,
                        model_id: p.model_id,
                      })
                    }
                  >
                    {t(
                      role === "news"
                        ? "Article explanations"
                        : role === "writer"
                          ? "Writing"
                          : "Analysis",
                    )}
                  </button>
                ))}
              </div>
            </details>
          </section>
        ))}
      </div>
      {(adding || !(snapshot.profiles || []).length) && (
        <section className="connection-add">
          <div className="settings-section-heading">
            <h3>{t("Add account")}</h3>
            {(snapshot.profiles || []).length > 0 && (
              <button
                onClick={() => {
                  setAdding(false);
                  setSecrets({});
                }}
              >
                {t("Cancel")}
              </button>
            )}
          </div>
          <p className="muted">
            {t("Sign in to a provider, or connect Ollama on this Mac.")}
          </p>
          <label className="field">
            {t("Provider")}
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                setSecrets({});
                setConfig({});
                setModel("");
              }}
            >
              {catalog
                .filter((p) => p.status === "ready")
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name || p.id}
                  </option>
                ))}
            </select>
          </label>
          {entry?.credential === "oauth" ? (
            <button
              className="primary"
              disabled={busy}
              onClick={() => void signIn()}
            >
              {t("Sign in with ChatGPT")}
            </button>
          ) : (
            <>
              <label className="field">
                {t("Connection name (optional)")}
                <input
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                />
              </label>
              <details className="connection-advanced">
                <summary>{t("Advanced connection options")}</summary>
                <p className="muted">
                  {t(
                    "Defaults work for most accounts. Change these only for a custom server or model.",
                  )}
                </p>
                <label className="field">
                  {t("Initial model")}
                  <input
                    value={model}
                    placeholder={
                      entry?.default_model || "Choose after connecting"
                    }
                    onChange={(e) => setModel(e.target.value)}
                  />
                </label>
                {provider === "ollama" && (
                  <label className="field">
                    {t("Server address")}
                    <input
                      placeholder="http://127.0.0.1:11434"
                      value={config.host || ""}
                      onChange={(e) =>
                        setConfig((old) => ({ ...old, host: e.target.value }))
                      }
                    />
                  </label>
                )}
              </details>
              {(provider === "ollama" ? [] : entry?.fields || []).map(
                (k: string) => (
                  <label className="field" key={k}>
                    {k.replaceAll("_", " ")}
                    <input
                      value={config[k] || ""}
                      onChange={(e) =>
                        setConfig((old) => ({ ...old, [k]: e.target.value }))
                      }
                    />
                  </label>
                ),
              )}
              {entry?.credential !== "local_server" &&
                (entry?.credential_fields || []).map((k: string) => (
                  <label className="field" key={k}>
                    {k.replaceAll("_", " ")}
                    <input
                      type="password"
                      autoComplete="off"
                      value={secrets[k] || ""}
                      onChange={(e) =>
                        setSecrets((old) => ({ ...old, [k]: e.target.value }))
                      }
                    />
                  </label>
                ))}
              <button
                className="primary"
                disabled={busy || !entry}
                onClick={() => void save()}
              >
                {t("Connect")}
              </button>
            </>
          )}
        </section>
      )}
    </>
  );
}
