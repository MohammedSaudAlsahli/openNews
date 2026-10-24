import { useEffect, useRef, useState } from "react";
import { LoaderCircle, Pause, Play } from "lucide-react";
import { call, type RecordData } from "./engine";
import { t } from "./locale";
import { settingsMessage } from "./settings-message";

const reasons: Record<string, string> = {
  stopping: "Stopping background processing…",
  paused: "Background processing is paused",
  cooling: "Waiting for your Mac to cool down",
  low_power: "Paused in Low Power Mode",
  waiting_device: "Waiting for your Mac",
  waiting_power: "Waiting for a charger",
  waiting_charger: "Waiting for a charger",
  on_battery: "Waiting for a charger",
  memory_pressure: "Waiting for more available memory",
  resting: "Resting between tasks",
  waiting_model: "Another local task is running",
};

export function LocalProcessing() {
  const [policy, setPolicy] = useState<RecordData | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false),
    [saved, setSaved] = useState(false);
  const active = useRef(true),
    reading = useRef(false),
    writing = useRef(false),
    version = useRef(0);
  async function refresh() {
    if (reading.current || writing.current) return;
    const token = version.current;
    reading.current = true;
    try {
      const result = await call("news.local.policy");
      if (active.current && version.current === token) {
        setPolicy(result);
        setError("");
      }
    } catch (reason) {
      if (active.current && version.current === token)
        setError(settingsMessage(String(reason)));
    } finally {
      reading.current = false;
    }
  }
  useEffect(() => {
    active.current = true;
    void refresh();
    const timer = setInterval(() => {
      if (document.visibilityState !== "hidden") void refresh();
    }, 5000);
    return () => {
      active.current = false;
      clearInterval(timer);
    };
  }, []);
  async function change(values: RecordData) {
    if (writing.current || !policy) return;
    writing.current = true;
    ++version.current;
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const result = await call("news.local.policy.set", values);
      if (active.current) {
        setPolicy(result);
        setSaved(true);
      }
    } catch (reason) {
      if (active.current) setError(settingsMessage(String(reason)));
    } finally {
      writing.current = false;
      if (active.current) setSaving(false);
    }
  }
  const paused = policy?.paused === true;
  return (
    <section
      className="preference-section"
      aria-labelledby="background-preferences"
    >
      <div className="preference-section-title">
        <h3 id="background-preferences">{t("Background processing")}</h3>
        {saving ? (
          <span className="preference-save" role="status">
            <LoaderCircle size={12} className="spin" />
            {t("Saving changes…")}
          </span>
        ) : saved ? (
          <span className="preference-save" role="status">
            {t("Saved")}
          </span>
        ) : null}
      </div>
      <div className="preference-group">
        <div className="setting-row processing-pause">
          <span className="preference-copy">
            <strong>
              {t(
                policy?.phase === "stopping"
                  ? reasons.stopping
                  : paused
                    ? "Background processing is paused"
                    : reasons[policy?.phase] || "Automatic resource protection",
              )}
            </strong>
            <small>
              {t(
                policy
                  ? "Work pauses when your Mac is warm or memory is under pressure."
                  : "Loading processing preferences…",
              )}
            </small>
          </span>
          <button
            disabled={!policy || saving || policy.phase === "stopping"}
            onClick={() => void change({ paused: !paused })}
          >
            {paused ? <Play size={14} /> : <Pause size={14} />}
            {t(paused ? "Resume" : "Pause")}
          </button>
        </div>
        <label className="setting-row">
          <span className="preference-copy">
            <strong>{t("Performance")}</strong>
            <small>
              {t(
                policy?.mode === "balanced"
                  ? "Finish sooner, using more of your Mac’s resources."
                  : "Smaller work sessions, with more time for your Mac to rest.",
              )}
            </small>
          </span>
          <select
            disabled={!policy || saving}
            value={policy?.mode || "quiet"}
            onChange={(event) => void change({ mode: event.target.value })}
          >
            <option value="quiet">{t("Quiet")}</option>
            <option value="balanced">{t("Balanced")}</option>
          </select>
        </label>
        <label className="setting-row">
          <span className="preference-copy">
            <strong>{t("Process on battery power")}</strong>
            <small>
              {t(
                "When off, background preparation waits for a charger. Reading and search stay available.",
              )}
            </small>
          </span>
          <input
            type="checkbox"
            disabled={!policy || saving}
            checked={policy?.index_on_battery === true}
            onChange={(event) =>
              void change({ index_on_battery: event.target.checked })
            }
          />
        </label>
      </div>
      {error && (
        <div className="settings-feedback" role="alert">
          <span>{error}</span>
          <button disabled={saving} onClick={() => void refresh()}>
            {t("Retry")}
          </button>
        </div>
      )}
    </section>
  );
}
