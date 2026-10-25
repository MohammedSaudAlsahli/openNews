import { settingsMessage } from "./settings-message";
import { t, getLocale } from "./locale";
import { useEffect, useRef, useState } from "react";
import { AlertCircle, Check, Circle, LoaderCircle } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { call, type RecordData } from "./engine";
import { useUnsavedChanges } from "./unsaved-changes";
const fieldNames: Record<string, string> = {
  api_key: "API key",
  service_account_info: "Service account JSON",
  aws_access_key_id: "AWS access key ID",
  aws_secret_access_key: "AWS secret access key",
  aws_session_token: "AWS session token",
  azure_management_token: "Azure management token",
  portkey_api_key: "Portkey API key",
  virtual_key: "Virtual key",
  host: "Server address",
  base_url: "Base URL",
  base_host_url: "Base URL",
  api_base: "API base URL",
  url: "URL",
  account_id: "Account ID",
  account_name: "Account name",
  api_version: "API version",
  aws_region: "AWS region",
  azure_deployment: "Azure deployment",
  azure_endpoint: "Azure endpoint",
  gateway_id: "Gateway ID",
  location: "Location",
  project_id: "Project ID",
  region: "Region",
  resource: "Resource",
  resource_group: "Resource group",
  subscription_id: "Subscription ID",
  vertexai: "Use Vertex AI",
};
export function Connections({
  snapshot,
  refresh,
  onError,
}: {
  snapshot: RecordData;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [checking, setChecking] = useState("");
  const [checkFailures, setCheckFailures] = useState<Record<string, string>>(
    {},
  );
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [catalogLoading, setCatalogLoading] = useState(true),
    [catalogFailed, setCatalogFailed] = useState(false),
    [catalogAttempt, setCatalogAttempt] = useState(0),
    [authAttempt, setAuthAttempt] = useState(0),
    [authFailed, setAuthFailed] = useState(false),
    [authUrl, setAuthUrl] = useState(""),
    [credentialProfile, setCredentialProfile] = useState("");
  const operation = useRef(false),
    checkLock = useRef(false);
  const savedProfile = useRef("");
  const [verified, setVerified] = useState<Record<string, RecordData>>({});
  const [profileUpdates, setProfileUpdates] = useState<
    Record<string, RecordData>
  >({});
  const [assignments, setAssignments] = useState<Record<string, RecordData>>(
    {},
  );
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
  const dirty =
    (adding || !(snapshot.profiles || []).length) &&
    (credentialProfile
      ? Object.values(secrets).some(Boolean)
      : Boolean(
          label.trim() ||
          model.trim() ||
          Object.values(config).some(Boolean) ||
          Object.values(secrets).some(Boolean),
        ));
  const guard = useUnsavedChanges(dirty, save);
  useEffect(() => {
    let live = true;
    setCatalogLoading(true);
    setCatalogFailed(false);
    call("providers.catalog")
      .then((r) => {
        if (live) setCatalog(r.providers || []);
      })
      .catch(() => {
        if (live) setCatalogFailed(true);
      })
      .finally(() => {
        if (live) setCatalogLoading(false);
      });
    return () => {
      live = false;
    };
  }, [catalogAttempt]);
  async function refreshSaved() {
    await refresh().catch(() =>
      setNotice(
        t("Your change was saved. Refresh the page to update the list."),
      ),
    );
  }
  useEffect(() => {
    if (!auth) return;
    setAuthFailed(false);
    let live = true,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const r = await call("providers.auth.status", { auth_id: auth });
        if (!live) return;
        if (r.status === "complete") {
          setAuth("");
          setNotice(t("Signed in"));
          await refreshSaved();
          return;
        }
        if (r.status !== "waiting") {
          setAuth("");
          setError(r.error || t("Sign-in did not finish. Try again."));
          return;
        }
      } catch (e) {
        if (live) {
          setError(String(e));
          setAuthFailed(true);
        }
        return;
      }
      if (live) timer = setTimeout(poll, 1500);
    }
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [auth, authAttempt]);
  async function signIn(profile_id?: string) {
    if (operation.current || checkLock.current || auth) return;
    operation.current = true;
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
      setAuthUrl(r.authorization_url);
      await invoke("open_external", { address: r.authorization_url });
    } catch (e) {
      setError(String(e));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }
  async function save() {
    if (operation.current || checkLock.current || !entry) return false;
    operation.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      // Validate structured credentials before creating a durable account.
      const values = Object.fromEntries(
        Object.entries(secrets)
          .filter(([, value]) => value.trim())
          .map(([key, value]) => {
            if (key !== "service_account_info") return [key, value];
            try {
              const parsed = JSON.parse(value);
              if (
                !parsed ||
                typeof parsed !== "object" ||
                Array.isArray(parsed)
              )
                throw new Error();
              return [key, parsed];
            } catch {
              throw new Error(
                t(
                  "Service account JSON is invalid. Paste a valid JSON object.",
                ),
              );
            }
          }),
      );
      if (entry.credential === "api_key" && !Object.keys(values).length)
        throw new Error(t("Enter your API key before connecting."));
      if (
        savedProfile.current &&
        entry.credential_fields?.length &&
        !Object.keys(values).length
      )
        throw new Error(t("Enter the credentials you want to save."));
      let created = savedProfile.current;
      if (!created) {
        const r = await call("providers.save", {
          provider_key: provider,
          label,
          model_id: model || entry?.default_model || "",
          config: Object.fromEntries(
            Object.entries(config).filter(([, value]) => value.trim()),
          ),
        });
        created = r.profile_id;
        savedProfile.current = created;
        setCredentialProfile(created);
      }
      if (Object.keys(values).length)
        await invoke("save_credentials", {
          profileId: created,
          values,
        });
      setSecrets({});
      setLabel("");
      setModel("");
      setConfig({});
      savedProfile.current = "";
      setCredentialProfile("");
      setAdding(false);
      setNotice(
        t(credentialProfile ? "Credentials updated" : "Connection added"),
      );
      await refreshSaved();
      return true;
    } catch (e) {
      setError(String(e));
      if (savedProfile.current) await refresh().catch(() => {});
      return false;
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }
  async function loadModels(id: string) {
    if (operation.current || checkLock.current) return;
    operation.current = true;
    setBusy(true);
    setError("");
    try {
      const r = await call("providers.models", {
        profile_id: id,
        refresh: true,
      });
      if (r.error) setError(r.error);
      setModels((old) => ({ ...old, [id]: r.models || [] }));
      await refresh().catch(() =>
        setNotice(
          t("Models loaded. The account list will update when you refresh."),
        ),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }
  async function checkConnection(id: string) {
    if (checkLock.current || operation.current) return;
    checkLock.current = true;
    setChecking(id);
    setCheckFailures((old) => ({ ...old, [id]: "" }));
    try {
      const result = await call("providers.check", { profile_id: id });
      if (result.state) setVerified((old) => ({ ...old, [id]: result }));
      else if (result.error) throw new Error(result.error);
      await refresh().catch(() =>
        setNotice(
          t(
            "Connection checked. The account list will update when you refresh.",
          ),
        ),
      );
    } catch (e) {
      setCheckFailures((old) => ({ ...old, [id]: settingsMessage(String(e)) }));
      await refresh().catch(() => {});
    } finally {
      checkLock.current = false;
      setChecking("");
    }
  }
  async function action(command: string, p: RecordData) {
    if (operation.current || checkLock.current) return;
    operation.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await call(command, p);
      if (result.error) throw new Error(result.error);
      if (command === "providers.update")
        setProfileUpdates((old) => ({
          ...old,
          [p.profile_id]: { ...old[p.profile_id], model_id: p.model_id },
        }));
      if (command === "agents.assign")
        setAssignments((old) => ({ ...old, [p.role]: p }));
      if (command === "providers.disconnect" && result.state)
        setVerified((old) => ({ ...old, [p.profile_id]: result }));
      setNotice(
        t(command === "providers.check" ? "Connection checked" : "Saved"),
      );
      await refreshSaved();
    } catch (e) {
      setError(String(e));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }
  return (
    <>
      {guard.dialog}
      <div className="settings-section-heading">
        <div>
          <h2>{t("Accounts & models")}</h2>
          <p className="muted">
            {t("Choose the account your assistant uses.")}
          </p>
        </div>
        <button
          className="primary"
          disabled={busy || Boolean(auth)}
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
            disabled={busy}
            onClick={() =>
              void invoke("open_external", { address: authUrl }).catch((e) =>
                setError(String(e)),
              )
            }
          >
            {t("Open sign-in page")}
          </button>
          {authFailed && (
            <button onClick={() => setAuthAttempt((value) => value + 1)}>
              {t("Retry sign-in check")}
            </button>
          )}
          <button
            disabled={busy}
            onClick={async () => {
              if (operation.current) return;
              operation.current = true;
              setBusy(true);
              try {
                await call("providers.auth.cancel", { auth_id: auth });
                setAuth("");
              } catch (e) {
                setError(String(e));
              } finally {
                operation.current = false;
                setBusy(false);
              }
            }}
          >
            {t("Cancel sign-in")}
          </button>
        </div>
      )}
      <div className="connection-list">
        {(snapshot.profiles || []).map((profile: RecordData) => {
          const p = { ...profile, ...profileUpdates[profile.id] };
          return (
            <section key={p.id}>
              <div className="connection-heading">
                <div>
                  <h3>
                    <bdi>{p.label || p.provider_key}</bdi>
                  </h3>
                  <small>
                    <bdi>{p.model_id || t("Choose a model")}</bdi>
                  </small>
                </div>
                <span
                  className="usage-pill"
                  title={t(
                    "This is usage observed by OpenNews, not your provider bill or quota.",
                  )}
                >
                  {Number(p.usage_today || 0)} {t("requests today")}
                </span>
              </div>
              <ConnectionStatus
                connection={
                  p.connection?.checked_at &&
                  p.connection.checked_at >= (verified[p.id]?.checked_at || "")
                    ? p.connection
                    : verified[p.id] || p.connection
                }
                checking={checking === p.id}
                failure={checkFailures[p.id]}
              />
              <button
                className="connection-check"
                disabled={busy || Boolean(checking)}
                onClick={() => void checkConnection(p.id)}
              >
                {t(
                  checking === p.id
                    ? "Checking connection…"
                    : "Check connection",
                )}
              </button>
              <details className="connection-manage">
                <summary>{t("Manage account")}</summary>
                <div className="reader-actions">
                  <button
                    disabled={busy || Boolean(checking)}
                    onClick={() => void loadModels(p.id)}
                  >
                    {t("Refresh models")}
                  </button>
                  {p.provider_key === "openai-chatgpt" && (
                    <button
                      disabled={busy || Boolean(auth)}
                      onClick={() => void signIn(p.id)}
                    >
                      {t("Sign in again")}
                    </button>
                  )}
                  {p.provider_key !== "openai-chatgpt" &&
                    p.provider_key !== "ollama" && (
                      <button
                        disabled={busy || Boolean(checking)}
                        onClick={() =>
                          guard.confirm(() => {
                            savedProfile.current = p.id;
                            setCredentialProfile(p.id);
                            setProvider(p.provider_key);
                            setLabel(p.label || "");
                            setModel(p.model_id || "");
                            setConfig(p.config || {});
                            setSecrets({});
                            setAdding(true);
                            setError("");
                          })
                        }
                      >
                        {t("Update credentials")}
                      </button>
                    )}
                  <button
                    disabled={busy || Boolean(checking)}
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
                      disabled={busy || Boolean(checking)}
                      value={p.model_id}
                      onChange={(e) =>
                        void action("providers.update", {
                          profile_id: p.id,
                          model_id: e.target.value,
                        })
                      }
                    >
                      <option value="">{t("Choose a model")}</option>
                      {p.model_id &&
                        !models[p.id].some((row) => row.id === p.model_id) && (
                          <option value={p.model_id}>{p.model_id}</option>
                        )}
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
                    "Apply the selected model to a task. TL;DR can also use a local model in article settings.",
                  )}
                </p>
                <div className="reader-actions">
                  {["writer", "analyst", "news"].map((role) => (
                    <button
                      key={role}
                      disabled={busy || Boolean(checking) || !p.model_id}
                      aria-pressed={
                        (
                          assignments[role] ||
                          snapshot.assignments?.find(
                            (row: RecordData) => row.role === role,
                          )
                        )?.profile_id === p.id &&
                        (
                          assignments[role] ||
                          snapshot.assignments?.find(
                            (row: RecordData) => row.role === role,
                          )
                        )?.model_id === p.model_id
                      }
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
                          ? "TL;DR"
                          : role === "writer"
                            ? "Writing"
                            : "Analysis",
                      )}
                    </button>
                  ))}
                </div>
              </details>
            </section>
          );
        })}
      </div>
      {(adding || !(snapshot.profiles || []).length) && (
        <section className="connection-add">
          <div className="settings-section-heading">
            <h3>
              {t(credentialProfile ? "Update credentials" : "Add account")}
            </h3>
            {(snapshot.profiles || []).length > 0 && (
              <button
                disabled={busy}
                onClick={() =>
                  guard.confirm(() => {
                    setAdding(false);
                    setSecrets({});
                    setLabel("");
                    setModel("");
                    setConfig({});
                    savedProfile.current = "";
                    setCredentialProfile("");
                  })
                }
              >
                {t("Cancel")}
              </button>
            )}
          </div>
          <p className="muted">
            {t("Sign in to a provider, or connect Ollama on this Mac.")}
          </p>
          {catalogLoading && <p role="status">{t("Loading providers…")}</p>}
          {catalogFailed && (
            <div className="context-feedback" role="alert">
              <p>{t("Providers could not load.")}</p>
              <button onClick={() => setCatalogAttempt((value) => value + 1)}>
                {t("Retry")}
              </button>
            </div>
          )}
          {credentialProfile && (
            <p className="muted">
              {t(
                "This account is already saved. Retrying updates its credentials without adding another account.",
              )}
            </p>
          )}
          <label className="field">
            {t("Provider")}
            <select
              disabled={
                busy ||
                Boolean(auth) ||
                Boolean(credentialProfile) ||
                catalogLoading ||
                catalogFailed
              }
              value={provider}
              onChange={(e) => {
                const nextProvider = e.target.value;
                guard.confirm(() => {
                  setProvider(nextProvider);
                  setSecrets({});
                  setConfig({});
                  setModel("");
                });
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
              disabled={busy || Boolean(auth)}
              onClick={() => void signIn()}
            >
              {t("Sign in with ChatGPT")}
            </button>
          ) : (
            <>
              <label className="field">
                {t("Connection name (optional)")}
                <input
                  disabled={busy || Boolean(credentialProfile)}
                  maxLength={120}
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
                    disabled={busy || Boolean(credentialProfile)}
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
                      disabled={busy || Boolean(credentialProfile)}
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
                    {t(fieldNames[k] || k.replaceAll("_", " "))}
                    <input
                      disabled={busy || Boolean(credentialProfile)}
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
                    {t(fieldNames[k] || k.replaceAll("_", " "))}
                    {k === "service_account_info" ? (
                      <textarea
                        rows={5}
                        spellCheck={false}
                        disabled={busy}
                        value={secrets[k] || ""}
                        onChange={(e) =>
                          setSecrets((old) => ({ ...old, [k]: e.target.value }))
                        }
                      />
                    ) : (
                      <input
                        disabled={busy}
                        type="password"
                        autoComplete="off"
                        value={secrets[k] || ""}
                        onChange={(e) =>
                          setSecrets((old) => ({ ...old, [k]: e.target.value }))
                        }
                      />
                    )}
                  </label>
                ))}
              <button
                className="primary"
                disabled={busy || !entry || catalogLoading || catalogFailed}
                onClick={() => void save()}
              >
                {busy && <LoaderCircle size={15} className="spin" />}
                {t(
                  busy
                    ? "Saving…"
                    : credentialProfile
                      ? "Save credentials"
                      : "Connect",
                )}
              </button>
            </>
          )}
        </section>
      )}
    </>
  );
}

const connectionStates: Record<string, [string, string, string]> = {
  connected: [
    "Ready",
    "Connection verified. This account is ready to use.",
    "ready",
  ],
  configured: [
    "Not checked yet",
    "Account saved. Check the connection before using it.",
    "neutral",
  ],
  unverified: [
    "Needs a fresh check",
    "The last verification is more than ten minutes old.",
    "neutral",
  ],
  needs_login: [
    "Sign-in required",
    "Sign in again from Manage account.",
    "warning",
  ],
  disconnected: [
    "Disconnected",
    "Reconnect this account to use it.",
    "neutral",
  ],
  network_error: [
    "Connection problem",
    "Check your internet connection or local model server, then retry.",
    "warning",
  ],
  service_error: [
    "Service unavailable",
    "The provider is unavailable. Try again shortly.",
    "warning",
  ],
  restricted: [
    "Access restricted",
    "Your account does not have permission for this service.",
    "warning",
  ],
  limited: [
    "Usage limit reached",
    "Check your provider usage limit or try again later.",
    "warning",
  ],
  check_failed: [
    "Could not verify",
    "Check the account settings and try again.",
    "warning",
  ],
};
function ConnectionStatus({
  connection,
  checking,
  failure,
}: {
  connection?: RecordData;
  checking: boolean;
  failure?: string;
}) {
  const [label, description, tone] = checking
    ? ["Checking connection…", "", "neutral"]
    : failure
      ? ["Could not verify", failure, "warning"]
      : connectionStates[connection?.state] || connectionStates.configured;
  const stamp = connection?.checked_at && new Date(connection.checked_at);
  return (
    <div
      className={`connection-status ${tone}`}
      role="status"
      aria-live="polite"
    >
      <strong>
        <span aria-hidden="true">
          {checking ? (
            <LoaderCircle size={15} className="spin" />
          ) : tone === "ready" ? (
            <Check size={15} />
          ) : tone === "warning" ? (
            <AlertCircle size={15} />
          ) : (
            <Circle size={12} />
          )}
        </span>{" "}
        {t(label)}
      </strong>
      {description && <p>{t(description)}</p>}
      {stamp && !Number.isNaN(stamp.getTime()) && (
        <small>
          {t("Last checked")}: {stamp.toLocaleString(getLocale())}
        </small>
      )}
    </div>
  );
}
