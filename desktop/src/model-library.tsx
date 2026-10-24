import { t } from "./locale";
import { useEffect, useId, useRef, useState } from "react";
import { call, type RecordData } from "./engine";
import { Check, LoaderCircle, Search, X, ArrowRight } from "lucide-react";
import { settingsMessage } from "./settings-message";
const bytes = (n?: number) =>
  typeof n === "number" && Number.isFinite(n)
    ? n >= 1e9
      ? `${(n / 1e9).toFixed(2)} GB`
      : `${(Math.max(0, n) / 1e6).toFixed(1)} MB`
    : t("Size not available");
const downloadLabels: Record<string, string> = {
  checking: "Checking requirements…",
  preparing: "Preparing download…",
  downloading: "Downloading model…",
  verifying: "Verifying download…",
  testing: "Testing the model…",
  ready: "Model ready",
  failed: "Download failed",
  cancelled: "Download cancelled",
};
export function ModelLibrary({
  embedding = false,
  onActivated,
  onPurposeChange,
  initialTab = "suggested",
  currentModels = {},
}: {
  embedding?: boolean;
  onError: (s: string) => void;
  onActivated?: () => void;
  onPurposeChange?: (embedding: boolean) => void;
  initialTab?: "suggested" | "library" | "installed";
  currentModels?: { embedding?: string; summary?: string };
}) {
  const [tab, setTab] = useState(initialTab),
    [query, setQuery] = useState(""),
    [rows, setRows] = useState<RecordData[]>([]),
    [page, setPage] = useState(1),
    [more, setMore] = useState(false),
    [variant, setVariant] = useState(""),
    [variants, setVariants] = useState<RecordData[]>([]),
    [plan, setPlan] = useState<RecordData>(),
    [download, setDownload] = useState<RecordData>({}),
    [busy, setBusy] = useState(false),
    [searchError, setSearchError] = useState(""),
    [selectedModel, setSelectedModel] = useState(""),
    [choosing, setChoosing] = useState(false),
    [inspecting, setInspecting] = useState(false),
    [planError, setPlanError] = useState(""),
    [planAttempt, setPlanAttempt] = useState(0),
    [activating, setActivating] = useState(false),
    [cancelling, setCancelling] = useState(false),
    [operationError, setOperationError] = useState(""),
    [statusError, setStatusError] = useState(false),
    [statusAttempt, setStatusAttempt] = useState(0),
    [language, setLanguage] = useState("ar");
  const operation = useRef(false);
  const resultList = useRef<HTMLDivElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const queryInput = useRef<HTMLInputElement>(null);
  const searchId = useId();
  const [inventoryVersion, setInventoryVersion] = useState(0);
  const refreshDownload = useRef("");
  const downloading = [
    "checking",
    "preparing",
    "downloading",
    "verifying",
    "testing",
  ].includes(download.phase);
  const generation = useRef(0),
    inspection = useRef(0);
  const retryAppend = useRef(false);
  useEffect(
    () => () => {
      ++inspection.current;
    },
    [],
  );
  const remoteQuery = tab === "library" ? query : "";
  async function search(append = false) {
    const token = ++generation.current;
    setBusy(true);
    setSearchError("");
    try {
      let result: RecordData, values: RecordData[];
      const next = append ? page + 1 : 1;
      if (tab === "library") {
        result = await call("news.local.search", {
          query,
          page: next,
          capability: "",
        });
        values = result.models || [];
      } else if (tab === "installed") {
        result = await call("news.local.available", {
          capability: "",
        });
        values = result.installed || [];
      } else {
        result = await call("news.local.status");
        values = [
          {
            id: "embeddinggemma-2:270m",
            name: "EmbeddingGemma 2 · 270M",
            description: "Multilingual search",
            capabilities: ["embedding"],
          },
          ...(result.models || []),
        ];
      }
      if (token !== generation.current) return;
      setRows((old) =>
        append
          ? [...old, ...values.filter((x) => !old.some((y) => y.id === x.id))]
          : values,
      );
      setMore(!!result.has_more);
      setPage(next);
      if (!append && resultList.current) resultList.current.scrollTop = 0;
    } catch (e) {
      if (token === generation.current) {
        retryAppend.current = append;
        setSearchError(settingsMessage(String(e)));
      }
    } finally {
      if (token === generation.current) setBusy(false);
    }
  }
  useEffect(() => {
    setRows([]);
    setMore(false);
    setPage(1);
    setBusy(true);
    const timer = setTimeout(() => void search(), 300);
    return () => {
      clearTimeout(timer);
      ++generation.current;
    };
  }, [tab, remoteQuery, inventoryVersion]);
  useEffect(() => {
    let live = true,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      let wait = 10000;
      try {
        const r = await call("news.local.status");
        if (live) {
          setDownload(r.download || {});
          const ready = r.download?.phase === "ready" ? r.download.model : "";
          if (ready && refreshDownload.current !== ready) {
            setInventoryVersion((value) => value + 1);
            onActivated?.();
          }
          refreshDownload.current = ready;
          setStatusError(false);
        }
        if (
          [
            "checking",
            "preparing",
            "downloading",
            "verifying",
            "testing",
          ].includes(r.download?.phase)
        )
          wait = 2000;
      } catch {
        if (live) setStatusError(true);
      }
      if (live) timer = setTimeout(poll, wait);
    }
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [statusAttempt, downloading]);
  async function choose(id: string) {
    if (operation.current) return;
    const token = ++inspection.current;
    setSelectedModel(id);
    setOperationError("");
    const row = rows.find((row) => row.id === id);
    if (
      onPurposeChange &&
      row?.capabilities?.includes("embedding") &&
      !row.capabilities.includes("completion")
    )
      onPurposeChange(true);
    else if (
      onPurposeChange &&
      row?.capabilities?.includes("completion") &&
      !row.capabilities.includes("embedding")
    )
      onPurposeChange(false);
    setChoosing(true);
    setPlanError("");
    setVariant("");
    setPlan(undefined);
    setVariants([]);
    try {
      const values = id.includes(":")
        ? [{ id }]
        : (await call("news.local.variants", { model: id })).variants;
      if (token !== inspection.current) return;
      setVariants(values);
      setVariant(values.find((v: RecordData) => !v.cloud)?.id || "");
    } catch (e) {
      if (token === inspection.current)
        setPlanError(settingsMessage(String(e)));
    } finally {
      if (token === inspection.current) setChoosing(false);
    }
  }
  useEffect(() => {
    let live = true;
    setPlan(undefined);
    setPlanError("");
    setInspecting(Boolean(variant));
    if (variant)
      call("news.local.inspect", { model: variant })
        .then((r) => {
          if (live) setPlan(r);
        })
        .catch((e) => {
          if (live) setPlanError(settingsMessage(String(e)));
        })
        .finally(() => {
          if (live) setInspecting(false);
        });
    return () => {
      live = false;
    };
  }, [variant, planAttempt]);
  useEffect(() => {
    if (selectedModel) detailHeading.current?.focus();
  }, [selectedModel]);
  const selectedRow = rows.find((row) => row.id === selectedModel);
  const capabilities =
    plan?.capabilities ??
    (tab === "installed" ? selectedRow?.capabilities : undefined);
  const compatible =
    !Array.isArray(capabilities) ||
    capabilities.includes(embedding ? "embedding" : "completion");
  const visibleRows =
    tab === "library"
      ? rows
      : rows.filter((row) =>
          `${row.name || row.id} ${row.id} ${row.description || ""}`
            .toLowerCase()
            .includes(query.toLowerCase()),
        );
  async function activate() {
    if (
      operation.current ||
      !variant ||
      !plan?.can_download ||
      !compatible ||
      downloading
    )
      return;
    operation.current = true;
    setActivating(true);
    setOperationError("");
    try {
      const result = await call("news.local.download", {
        model: variant,
        consent: true,
        purpose: embedding ? "embedding" : "summary",
        language,
      });
      setDownload(result.download || { phase: "checking", model: variant });
      onActivated?.();
    } catch (e) {
      setOperationError(settingsMessage(String(e)));
    } finally {
      operation.current = false;
      setActivating(false);
    }
  }
  return (
    <section className="model-browser" aria-label={t("Ollama model library")}>
      <p className="muted">
        {t(
          "Downloaded models are shared. Search models create embeddings; explanation models generate text.",
        )}
      </p>
      <div className="segments">
        {["suggested", "library", "installed"].map((tabId) => (
          <button
            key={tabId}
            disabled={activating}
            aria-pressed={tab === tabId}
            className={tab === tabId ? "selected" : ""}
            onClick={() => setTab(tabId as typeof tab)}
          >
            {tabId === "installed"
              ? t("Downloaded")
              : tabId === "library"
                ? t("Ollama library")
                : t("Suggested")}
          </button>
        ))}
      </div>
      <label className="model-search" htmlFor={searchId}>
        <Search size={16} aria-hidden="true" />
        <input
          id={searchId}
          ref={queryInput}
          type="search"
          aria-label={t("Search models")}
          placeholder={t(
            tab === "library"
              ? "Search Ollama by name…"
              : "Search downloaded or suggested models…",
          )}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {query && (
          <button
            type="button"
            className="icon-button"
            aria-label={t("Clear model search")}
            onClick={() => {
              setQuery("");
              queryInput.current?.focus();
            }}
          >
            <X size={14} />
          </button>
        )}
      </label>
      <div className="model-library">
        <div
          className="model-list"
          ref={resultList}
          aria-label={t("Model results")}
          aria-busy={busy}
        >
          {searchError && (
            <div className="context-feedback" role="alert">
              <p>{searchError}</p>
              <button
                disabled={busy}
                onClick={() => void search(retryAppend.current)}
              >
                {t("Retry")}
              </button>
            </div>
          )}
          {!visibleRows.length && !searchError && (
            <p className="muted" role="status">
              {t(
                busy
                  ? "Loading models…"
                  : tab === "installed"
                    ? "No downloaded models match. Browse the Ollama library to add one."
                    : "No models match your search.",
              )}
            </p>
          )}
          {visibleRows.map((r) => (
            <button
              key={r.id}
              aria-pressed={selectedModel === r.id}
              className="model-result"
              disabled={activating}
              onClick={() => void choose(r.id)}
            >
              <span className="model-result-copy">
                <strong>
                  <bdi>{r.name || r.id}</bdi>
                </strong>
                <small>
                  {r.description || (r.size ? bytes(r.size) : r.id)}
                </small>
                {tab === "installed" && (
                  <span className="model-result-meta">
                    {r.capabilities?.includes("embedding") && (
                      <span>{t("Semantic search")}</span>
                    )}
                    {r.capabilities?.includes("completion") && (
                      <span>{t("Text generation")}</span>
                    )}
                    {!r.capabilities && (
                      <span>
                        {t("Compatibility checked before activation")}
                      </span>
                    )}
                    {(r.id === currentModels.embedding ||
                      r.id === currentModels.summary) && (
                      <span>
                        <Check size={12} />
                        {t("In use")}
                      </span>
                    )}
                  </span>
                )}
              </span>
              {selectedModel === r.id ? (
                <Check size={15} />
              ) : (
                <ArrowRight size={14} className="model-result-arrow" />
              )}
            </button>
          ))}
          {more && (
            <button disabled={busy} onClick={() => void search(true)}>
              {t("Load more")}
            </button>
          )}
        </div>
        <section
          className="model-inspector"
          hidden={!selectedModel}
          aria-label={t("Selected model")}
        >
          <h3 ref={detailHeading} tabIndex={-1}>
            <bdi>{selectedModel}</bdi>
          </h3>
          <p className="muted">
            {t("Your library and search stay here while you choose.")}
          </p>
          {(choosing || inspecting) && (
            <p className="inline-loading" role="status">
              <LoaderCircle size={15} className="spin" />
              {t(
                choosing
                  ? "Loading model sizes…"
                  : "Checking space and memory…",
              )}
            </p>
          )}
          {planError && (
            <div className="context-feedback" role="alert">
              <p>{planError}</p>
              <button
                onClick={() =>
                  variant
                    ? setPlanAttempt((value) => value + 1)
                    : void choose(selectedModel)
                }
              >
                {t("Retry")}
              </button>
            </div>
          )}
          {selectedModel && !choosing && !variant && !planError && (
            <p className="muted">
              {t("No local sizes are available for this model.")}
            </p>
          )}
          {variants.length > 0 &&
            !(tab === "installed" && variants.length === 1) && (
              <label className="field">
                {t("Model size")}
                <select
                  disabled={activating}
                  value={variant}
                  onChange={(e) => setVariant(e.target.value)}
                >
                  {variants
                    .filter((v) => !v.cloud)
                    .map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.id}
                        {v.size ? ` · ${bytes(v.size)}` : ""}
                      </option>
                    ))}
                </select>
              </label>
            )}
          {plan && (
            <>
              <h3>
                <bdi dir="ltr">{bytes(plan.size)}</bdi>
              </h3>
              <p>
                {plan.fit === "fits"
                  ? t("Estimated to fit your Mac")
                  : plan.fit === "disk"
                    ? t(
                        "Not enough free storage. Choose a smaller model or free space.",
                      )
                    : t("This model needs more memory. Choose a smaller size.")}
              </p>
              {onPurposeChange && (
                <label className="field">
                  {t("Use for")}
                  <select
                    value={embedding ? "embedding" : "summary"}
                    disabled={activating}
                    onChange={(event) =>
                      onPurposeChange(event.target.value === "embedding")
                    }
                  >
                    <option
                      value="embedding"
                      disabled={
                        Array.isArray(capabilities) &&
                        !capabilities.includes("embedding")
                      }
                    >
                      {t("Article search")}
                    </option>
                    <option
                      value="summary"
                      disabled={
                        Array.isArray(capabilities) &&
                        !capabilities.includes("completion")
                      }
                    >
                      {t("Article explanations")}
                    </option>
                  </select>
                </label>
              )}
              {!compatible && (
                <p className="notice" role="status">
                  {t(
                    !capabilities?.includes(
                      embedding ? "completion" : "embedding",
                    )
                      ? "This model does not support the selected task."
                      : embedding
                        ? "This model generates text. Choose an embedding model for semantic search."
                        : "This model creates embeddings. Choose a text generation model for explanations.",
                  )}
                </p>
              )}
              {!embedding && (
                <label className="field">
                  {t("Explanation language")}
                  <select
                    disabled={activating}
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                  >
                    <option value="ar">العربية</option>
                    <option value="en">{t("English")}</option>
                  </select>
                </label>
              )}
              <button
                className="primary"
                disabled={
                  !plan.can_download || !compatible || activating || downloading
                }
                onClick={() => void activate()}
              >
                {activating && <LoaderCircle size={15} className="spin" />}
                {t(
                  activating
                    ? "Preparing model…"
                    : tab === "installed" ||
                        rows.find((row) => row.id === variant)?.installed
                      ? "Use this model"
                      : "Download and use",
                )}
              </button>
              <details className="model-capacity-details">
                <summary>{t("Storage and memory details")}</summary>{" "}
                <small>
                  {t("Free storage:")}{" "}
                  <bdi dir="ltr">{bytes(plan.free_disk)}</bdi>{" "}
                  {t("· Required:")}{" "}
                  <bdi dir="ltr">{bytes(plan.required_disk)}</bdi>{" "}
                  {t("· Estimated memory:")}{" "}
                  <bdi dir="ltr">{bytes(plan.estimated_memory)}</bdi>
                </small>
                <p className="muted">
                  {t(
                    "Arabic and English quality varies by model. These estimates do not guarantee speed or accuracy.",
                  )}
                </p>
              </details>
            </>
          )}
        </section>
      </div>
      {operationError && (
        <p className="context-feedback" role="alert">
          {operationError}
        </p>
      )}
      {statusError && download.phase && download.phase !== "idle" && (
        <div className="context-feedback" role="alert">
          <p>
            {t(
              "Model status could not refresh. Existing work may still be running.",
            )}
          </p>
          <button onClick={() => setStatusAttempt((value) => value + 1)}>
            {t("Retry")}
          </button>
        </div>
      )}
      {download.phase && download.phase !== "idle" && (
        <div className="notice" role="status">
          <strong>
            <bdi>{download.model}</bdi>
          </strong>
          <p>
            {downloading ? (
              <LoaderCircle size={14} className="spin" />
            ) : download.phase === "ready" ? (
              <Check size={14} />
            ) : null}{" "}
            {t(downloadLabels[download.phase] || "Preparing model…")}
          </p>
          {download.error && <p>{download.error}</p>}
          {download.total > 0 && (
            <>
              <progress
                aria-label={t("Model download progress")}
                max={download.total}
                value={download.completed || 0}
              />
              <small>
                <bdi dir="ltr">
                  {bytes(download.completed)} / {bytes(download.total)}
                </bdi>
              </small>
              {downloading &&
                Number.isFinite(download.bytes_per_second) &&
                download.bytes_per_second > 0 && (
                  <small className="download-transfer-rate">
                    <bdi dir="ltr">{bytes(download.bytes_per_second)}</bdi>{" "}
                    {t("per second")}
                    {Number.isFinite(download.seconds_left) &&
                      download.seconds_left > 0 && (
                        <span>
                          {" · "}
                          {download.seconds_left < 60
                            ? t("Less than a minute remaining")
                            : `${Math.ceil(download.seconds_left / 60).toLocaleString()} ${t("min remaining")}`}
                        </span>
                      )}
                  </small>
                )}
            </>
          )}
          {downloading && (
            <button
              disabled={cancelling}
              onClick={async () => {
                if (operation.current) return;
                operation.current = true;
                setCancelling(true);
                setOperationError("");
                try {
                  const result = await call("news.local.cancel");
                  setDownload(
                    result.download || { ...download, phase: "cancelled" },
                  );
                } catch (e) {
                  setOperationError(settingsMessage(String(e)));
                } finally {
                  operation.current = false;
                  setCancelling(false);
                }
              }}
            >
              {cancelling && <LoaderCircle size={14} className="spin" />}
              {t(cancelling ? "Stopping…" : "Cancel download")}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
