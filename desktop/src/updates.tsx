import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { t } from "./locale";
import { Markdown } from "./components";
import type { RecordData } from "./engine";
export function Updates({ onError }: { onError: (message: string) => void }) {
  const [busy, setBusy] = useState(false),
    [result, setResult] = useState<RecordData>(),
    [progress, setProgress] = useState<RecordData>();
  useEffect(() => {
    const handler = listen<RecordData>("update-progress", (event) =>
      setProgress(event.payload),
    );
    return () => {
      void handler.then((stop) => stop());
    };
  }, []);
  return (
    <section className="notice">
      <h3>{t("App updates")}</h3>
      <p>
        {t(
          "Tauri updates replace this app in place. Articles, accounts and downloaded models stay in your workspace. The preview channel is separate from the original app.",
        )}
      </p>
      <button
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            setResult(await invoke("check_update"));
          } catch (e) {
            onError(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {t(busy ? "Checking…" : "Check for updates")}
      </button>
      {result &&
        (result.update ? (
          <>
            <h4>{result.update.version}</h4>
            <Markdown text={result.update.notes || ""} />
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await invoke("install_update");
                } catch (e) {
                  onError(String(e));
                  setBusy(false);
                }
              }}
            >
              {t("Install and restart")}
            </button>
          </>
        ) : (
          <p role="status">{t("No newer version is available.")}</p>
        ))}
      {progress && (
        <p role="status">
          {(progress.downloaded / 1e6).toFixed(1)} MB{" "}
          {progress.total ? `/ ${(progress.total / 1e6).toFixed(1)} MB` : ""}
        </p>
      )}
    </section>
  );
}
