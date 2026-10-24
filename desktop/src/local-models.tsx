import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  ArrowDown,
  Cpu,
  LoaderCircle,
  Search,
  Sparkles,
} from "lucide-react";
import { call, type RecordData } from "./engine";
import { t } from "./locale";
import { ModelLibrary } from "./model-library";
import { LocalProcessing } from "./local-processing";
import { ProcessingStatus } from "./processing-status";

export function LocalModels({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const [purpose, setPurpose] = useState<"summary" | "embedding">("summary");
  const [digest, setDigest] = useState<RecordData>({});
  const [search, setSearch] = useState<RecordData>({});
  const [runtime, setRuntime] = useState<RecordData>({});
  const [checking, setChecking] = useState(true),
    [failure, setFailure] = useState("");
  const libraryHeading = useRef<HTMLHeadingElement>(null);
  const live = useRef(true),
    inFlight = useRef(false);
  const refresh = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const [nextDigest, nextSearch, nextRuntime] = await Promise.all([
        call("news.digest.status"),
        call("news.search.status"),
        call("news.local.status"),
      ]);
      if (live.current) {
        setDigest(nextDigest);
        setSearch(nextSearch);
        setRuntime(nextRuntime);
        setFailure("");
      }
    } catch (error) {
      if (live.current) setFailure(String(error).replace(/^Error:\s*/, ""));
    } finally {
      inFlight.current = false;
      if (live.current) setChecking(false);
    }
  };
  useEffect(() => {
    live.current = true;
    void refresh();
    const timer = setInterval(() => {
      if (document.visibilityState !== "hidden") void refresh();
    }, 5000);
    return () => {
      live.current = false;
      clearInterval(timer);
    };
  }, []);
  const state = checking
    ? "Checking connection…"
    : failure
      ? "Could not verify"
      : runtime.runtime
        ? "Ready"
        : "Not running";
  const models = runtime.installed || [];
  return (
    <section className="local-models-settings">
      <header className="settings-section-heading">
        <div>
          <h2>{t("Local models")}</h2>
          <p className="muted">
            {t("Private search and explanations, on your Mac.")}
          </p>
        </div>
        <span
          role="status"
          className={`runtime-state ${checking ? "idle" : failure ? "failed" : runtime.runtime ? "ready" : "idle"}`}
        >
          {checking ? (
            <LoaderCircle size={13} className="spin" />
          ) : failure ? (
            <AlertCircle size={13} />
          ) : (
            <i />
          )}
          {t(state)}
        </span>
      </header>
      {failure && (
        <div className="settings-feedback" role="alert">
          <span>{failure}</span>
          <button
            disabled={checking}
            onClick={() => {
              setChecking(true);
              void refresh();
            }}
          >
            {t("Try again")}
          </button>
        </div>
      )}
      <section
        className="preference-section"
        aria-labelledby="local-model-roles"
      >
        <h3 id="local-model-roles">{t("Model assignments")}</h3>
        <div className="preference-group model-roles">
          {(["embedding", "summary"] as const).map((role) => {
            const name =
              role === "embedding" ? search.model : digest.local_model;
            const installed = models.find(
              (model: RecordData) => model.id === name,
            );
            const Icon = role === "embedding" ? Search : Sparkles;
            const expanded = purpose === role;
            return (
              <div className="model-role" key={role}>
                <button
                  className="model-role-trigger"
                  aria-pressed={expanded}
                  aria-controls="shared-local-library"
                  onClick={() => {
                    setPurpose(role);
                    libraryHeading.current?.focus();
                  }}
                >
                  <Icon size={19} strokeWidth={1.6} />
                  <span className="preference-copy">
                    <strong>
                      {t(
                        role === "embedding"
                          ? "Article search"
                          : "Article explanations",
                      )}
                    </strong>
                    <small>
                      {t(
                        role === "embedding"
                          ? "Find articles by meaning. Text search is always available."
                          : "Generate explanations with a separate language model.",
                      )}
                    </small>
                  </span>
                  <span className="model-role-value">
                    <bdi>
                      {name ||
                        t(
                          checking
                            ? "Checking model…"
                            : failure
                              ? "Model information unavailable"
                              : "No model selected",
                        )}
                    </bdi>
                    <small>
                      {installed?.size ? (
                        <bdi dir="ltr">
                          {installed.size < 1e9
                            ? `${Math.round(installed.size / 1e6)} MB`
                            : `${(installed.size / 1e9).toLocaleString(undefined, { maximumFractionDigits: 2 })} GB`}
                        </bdi>
                      ) : (
                        t(name ? "Check model availability" : "Choose a model")
                      )}
                    </small>
                  </span>
                  <span className="model-role-change">
                    {t("Change model")}
                    <ArrowDown size={14} />
                  </span>
                </button>
              </div>
            );
          })}
        </div>
        <div id="shared-local-library" className="shared-local-library">
          <h3 ref={libraryHeading} tabIndex={-1}>
            {t("Ollama models")}
          </h3>
          <ModelLibrary
            embedding={purpose === "embedding"}
            onPurposeChange={(embedding) =>
              setPurpose(embedding ? "embedding" : "summary")
            }
            initialTab="installed"
            currentModels={{
              embedding: search.model,
              summary: digest.local_model,
            }}
            onError={onError}
            onActivated={() => void refresh()}
          />
        </div>
        <p className="preference-footnote">
          <Cpu size={13} />
          {t("Models download once. Only one local model runs at a time.")}
        </p>
      </section>
      <LocalProcessing />
      <details className="preparation-details">
        <summary>
          <span>
            <strong>{t("Your article library")}</strong>
            <small>{t("Search coverage and explanation progress")}</small>
          </span>
          <ChevronDown size={16} className="disclosure-chevron" />
        </summary>
        <div className="preference-group library-coverage">
          <div>
            <h4>
              <Search size={15} />
              {t("Article search")}
            </h4>
            <ProcessingStatus
              data={search}
              search
              loading={checking && !search.phase}
              unavailable={Boolean(failure) && !search.phase}
            />
          </div>
          <div>
            <h4>
              <Sparkles size={15} />
              {t("Article explanations")}
            </h4>
            <ProcessingStatus
              data={digest}
              loading={checking && !digest.phase}
              unavailable={Boolean(failure) && !digest.phase}
            />
          </div>
        </div>
      </details>
    </section>
  );
}
