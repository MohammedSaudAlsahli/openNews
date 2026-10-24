import { useEffect, useState, useRef } from "react";
import { Check, LoaderCircle, X } from "lucide-react";
import { call } from "./engine";
import { t, getLocale } from "./locale";
const intervals = [1, 5, 15, 30, 60, 180, 360, 720, 1440];
export function intervalLabel(minutes: number) {
  const hours = minutes >= 60 && minutes % 60 === 0;
  const days = minutes >= 1440 && minutes % 1440 === 0;
  return new Intl.NumberFormat(getLocale(), {
    style: "unit",
    unit: days ? "day" : hours ? "hour" : "minute",
    unitDisplay: "long",
  }).format(days ? minutes / 1440 : hours ? minutes / 60 : minutes);
}
export function RefreshInterval({
  id,
  title,
  minutes = 5,
  onSaved,
  onError,
  onClose,
}: {
  id: string;
  title: string;
  minutes?: number;
  onSaved: () => Promise<void>;
  onError: (message: string) => void;
  onClose?: () => void;
}) {
  const [value, setValue] = useState(minutes),
    [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(""),
    [error, setError] = useState("");
  const pending = useRef(false);
  useEffect(() => setValue(minutes), [minutes]);
  // Preserve a previously saved custom duration until the user chooses a preset.
  const options = intervals.includes(value)
    ? intervals
    : [...intervals, value].sort((a, b) => a - b);
  return (
    <div className="refresh-interval">
      <label>
        {t("Refresh interval")}
        <select
          value={value}
          disabled={saving}
          aria-busy={saving}
          aria-label={t("Refresh interval") + " " + title}
          onChange={async (e) => {
            const next = Number(e.target.value),
              previous = value;
            if (pending.current || next === previous || !options.includes(next))
              return;
            pending.current = true;
            setError("");
            setFeedback("");
            setValue(next);
            setSaving(true);
            try {
              await call("news.update", {
                subscription_id: id,
                interval_minutes: next,
              });
            } catch (reason) {
              setValue(previous);
              setError(String(reason).replace(/^Error:\s*/, ""));
              onError(String(reason));
              setSaving(false);
              pending.current = false;
              return;
            }
            setFeedback(t("Saved"));
            try {
              await onSaved();
            } catch {
              setFeedback(t("Saved. The list will update when you refresh."));
            } finally {
              setSaving(false);
              pending.current = false;
            }
          }}
        >
          {options.map((n) => (
            <option key={n} value={n}>
              {intervalLabel(n)}
            </option>
          ))}
        </select>
      </label>
      <span className="interval-feedback" role="status">
        {saving ? (
          <>
            <LoaderCircle size={13} className="spin" />
            {t("Saving…")}
          </>
        ) : feedback ? (
          <>
            <Check size={13} />
            {feedback}
          </>
        ) : null}
      </span>
      {onClose && (
        <button
          className="icon-button"
          aria-label={t("Close interval settings")}
          disabled={saving}
          onClick={onClose}
        >
          <X size={14} />
        </button>
      )}
      {error && (
        <p className="source-action-error" role="alert" dir="auto">
          {error}
        </p>
      )}
    </div>
  );
}
