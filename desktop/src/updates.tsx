import { useEffect, useRef, useState } from "react";
import { LoaderCircle } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { t } from "./locale";
import { Markdown } from "./components";
import type { RecordData } from "./engine";
export function Updates({ onError }: { onError: (message: string) => void }) {
  const [action, setAction] = useState(""),
    [result, setResult] = useState<RecordData>(),
    [progress, setProgress] = useState<RecordData>();
  const pending = useRef(false);
  const busy = Boolean(action);
  useEffect(() => {
    const handler = listen<RecordData>("update-progress", (event) =>
      setProgress(event.payload),
    );
    return () => {
      void handler.then((stop) => stop()).catch(() => {});
    };
  }, []);
  return (
    <section className="notice">
      <h3>{t("App updates")}</h3>
      <p>
        {t(
          "Updates replace openNews in place. Your articles, accounts and downloaded models stay in your workspace.",
        )}
      </p>
      <button
        disabled={busy}
        onClick={async () => {
          if (pending.current) return;
          pending.current = true;
          setAction("check");
          setResult(undefined);
          onError("");
          try {
            const response = await invoke<RecordData>("check_update");
            if (!response || !("update" in response))
              throw new Error(
                t("The update check did not return a result. Try again."),
              );
            setResult(response);
          } catch (e) {
            onError(String(e));
          } finally {
            pending.current = false;
            setAction("");
          }
        }}
      >
        {action === "check" && <LoaderCircle size={14} className="spin" />}
        {t(action === "check" ? "Checking…" : "Check for updates")}
      </button>
      {result &&
        (result.update ? (
          <>
            <h4>{result.update.version}</h4>
            <Markdown text={result.update.notes || ""} />
            <button
              disabled={busy}
              onClick={async () => {
                if (pending.current) return;
                pending.current = true;
                setAction("install");
                onError("");
                setProgress(undefined);
                try {
                  await invoke("install_update");
                } catch (e) {
                  onError(String(e));
                } finally {
                  pending.current = false;
                  setAction("");
                }
              }}
            >
              {action === "install" && (
                <LoaderCircle size={14} className="spin" />
              )}
              {t(
                action === "install"
                  ? "Installing update…"
                  : "Install and restart",
              )}
            </button>
          </>
        ) : (
          <p role="status">{t("No newer version is available.")}</p>
        ))}
      {action === "install" && (
        <div className="update-progress" role="status">
          <progress
            aria-label={t("Downloading update")}
            max={progress?.total || undefined}
            value={
              progress?.total
                ? Math.min(progress.downloaded || 0, progress.total)
                : undefined
            }
          />
          {progress && (
            <span>
              {((progress.downloaded || 0) / 1e6).toFixed(1)} MB
              {progress.total
                ? ` / ${(progress.total / 1e6).toFixed(1)} MB`
                : ""}
            </span>
          )}
        </div>
      )}
    </section>
  );
}
