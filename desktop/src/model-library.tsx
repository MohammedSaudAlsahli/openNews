import { t } from "./locale";
import { useEffect, useRef, useState } from "react";
import { call, type RecordData } from "./engine";
const bytes = (n: number) =>
  n ? `${(n / 1e9).toFixed(2)} GB` : "Size not available";
export function ModelLibrary({
  embedding = false,
  onError,
}: {
  embedding?: boolean;
  onError: (s: string) => void;
}) {
  const [tab, setTab] = useState("suggested"),
    [query, setQuery] = useState(""),
    [rows, setRows] = useState<RecordData[]>([]),
    [page, setPage] = useState(1),
    [more, setMore] = useState(false),
    [variant, setVariant] = useState(""),
    [variants, setVariants] = useState<RecordData[]>([]),
    [plan, setPlan] = useState<RecordData>(),
    [download, setDownload] = useState<RecordData>({}),
    [busy, setBusy] = useState(false),
    [language, setLanguage] = useState("ar");
  const downloading = [
    "checking",
    "preparing",
    "downloading",
    "verifying",
    "testing",
  ].includes(download.phase);
  const generation = useRef(0),
    inspection = useRef(0);
  async function search(append = false) {
    const token = ++generation.current;
    setBusy(true);
    try {
      let result: RecordData, values: RecordData[];
      const next = append ? page + 1 : 1;
      if (tab === "library") {
        result = await call("news.local.search", {
          query,
          page: next,
          capability: embedding ? "embedding" : "",
        });
        values = result.models || [];
      } else if (tab === "installed") {
        result = await call("news.local.available", {
          capability: embedding ? "embedding" : "completion",
        });
        values = result.installed || [];
      } else {
        result = await call("news.local.status");
        values = embedding
          ? [
              {
                id: "embeddinggemma-2:270m",
                name: "EmbeddingGemma 2 · 270M",
                description: "Multilingual search",
              },
            ]
          : result.models || [];
      }
      if (token !== generation.current) return;
      setRows((old) =>
        append
          ? [...old, ...values.filter((x) => !old.some((y) => y.id === x.id))]
          : values,
      );
      setMore(!!result.has_more);
      setPage(next);
    } catch (e) {
      if (token === generation.current) onError(String(e));
    } finally {
      if (token === generation.current) setBusy(false);
    }
  }
  useEffect(() => {
    const timer = setTimeout(() => void search(), 300);
    return () => {
      clearTimeout(timer);
      ++generation.current;
    };
  }, [tab, query, embedding]);
  useEffect(() => {
    let live = true,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const r = await call("news.local.status");
        if (live) setDownload(r.download || {});
      } catch {}
      if (live) timer = setTimeout(poll, 2000);
    }
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, []);
  async function choose(id: string) {
    const token = ++inspection.current;
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
      if (token === inspection.current) onError(String(e));
    }
  }
  useEffect(() => {
    let live = true;
    setPlan(undefined);
    if (variant)
      call("news.local.inspect", { model: variant })
        .then((r) => {
          if (live) setPlan(r);
        })
        .catch((e) => {
          if (live) onError(String(e));
        });
    return () => {
      live = false;
    };
  }, [variant]);
  async function activate() {
    setBusy(true);
    try {
      await call("news.local.download", {
        model: variant,
        consent: true,
        purpose: embedding ? "embedding" : "summary",
        language,
      });
      setDownload((await call("news.local.status")).download);
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h3>{embedding ? t("Search models") : t("Local explanation models")}</h3>
      <p className="muted">
        {t(
          "Download when needed. Space and memory are checked before downloading; the model is tested before activation.",
        )}
      </p>
      <div className="segments">
        {["suggested", "library", "installed"].map((tabId) => (
          <button
            key={tabId}
            className={tab === tabId ? "selected" : ""}
            onClick={() => setTab(tabId)}
          >
            {tabId === "installed"
              ? t("Downloaded")
              : tabId === "library"
                ? t("Ollama library")
                : t("Suggested")}
          </button>
        ))}
      </div>
      {tab === "library" && (
        <label className="field">
          {t("Search Ollama")}
          <input value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
      )}
      <div className="model-library">
        <div className="source-list">
          {rows.map((r) => (
            <button key={r.id} onClick={() => void choose(r.id)}>
              <span>
                <strong>{r.name || r.id}</strong>
                <small>
                  {r.description || (r.size ? bytes(r.size) : r.id)}
                </small>
              </span>
            </button>
          ))}
          {more && (
            <button disabled={busy} onClick={() => void search(true)}>
              {t("Load more")}
            </button>
          )}
        </div>
        <div>
          {variants.length > 0 && (
            <label className="field">
              {t("Model size")}
              <select
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
              <h2>{bytes(plan.size)}</h2>
              <p>
                {plan.fit === "fits"
                  ? t("Estimated to fit your Mac")
                  : plan.fit === "disk"
                    ? t(
                        "Not enough free storage. Choose a smaller model or free space.",
                      )
                    : t("This model needs more memory. Choose a smaller size.")}
              </p>
              <small>
                {t("Free storage:")}
                {bytes(plan.free_disk)}
                {t("· Required:")} {bytes(plan.required_disk)}
                {t("· Estimated memory:")} {bytes(plan.estimated_memory)}
              </small>
              <p className="muted">
                {t(
                  "Arabic and English quality varies by model. These estimates do not guarantee speed or accuracy.",
                )}
              </p>
              {!embedding && (
                <label className="field">
                  {t("Explanation language")}
                  <select
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
                disabled={!plan.can_download || busy || downloading}
                onClick={() => void activate()}
              >
                {t("Download / activate")}
              </button>
            </>
          )}
        </div>
      </div>
      {download.phase && download.phase !== "idle" && (
        <div className="notice" role="status">
          <strong>{download.model}</strong>
          <p>{download.error || download.phase}</p>
          {download.total > 0 && (
            <>
              <progress max={download.total} value={download.completed} />
              <small>
                {bytes(download.completed)} / {bytes(download.total)}
              </small>
            </>
          )}
          {downloading && (
            <button
              onClick={() =>
                void call("news.local.cancel").catch((e) => onError(String(e)))
              }
            >
              {t("Cancel download")}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
