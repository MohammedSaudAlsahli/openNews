import { useMemo } from "react";
import { getLocale, t } from "./locale";

export function TimeZoneSelect({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  const locale = getLocale();
  const groups = useMemo(() => {
    const common = [
      ...new Set([
        value,
        Intl.DateTimeFormat().resolvedOptions().timeZone,
        "Asia/Riyadh",
        "Asia/Dubai",
        "Africa/Cairo",
        "Europe/London",
        "America/New_York",
        "UTC",
      ]),
    ];
    let zones: string[] = [];
    try {
      zones = Intl.supportedValuesOf("timeZone");
    } catch {
      /* Common zones remain available on older WebKit versions. */
    }
    return [common, zones.filter((zone) => !common.includes(zone))];
  }, [value, locale]);
  function label(zone: string) {
    const names: Record<string, string> = {
      "Asia/Riyadh": "Riyadh",
      "Asia/Dubai": "Dubai",
      "Africa/Cairo": "Cairo",
      "Europe/London": "London",
      "America/New_York": "New York",
    };
    const city = names[zone] ? t(names[zone]) : zone.replaceAll("_", " ");
    try {
      const offset = new Intl.DateTimeFormat(locale, {
        timeZone: zone,
        timeZoneName: "shortOffset",
      })
        .formatToParts(new Date())
        .find((part) => part.type === "timeZoneName")?.value;
      return offset ? `${city} · ${offset}` : city;
    } catch {
      return city;
    }
  }
  const labels = useMemo(
    () => Object.fromEntries(groups.flat().map((zone) => [zone, label(zone)])),
    [groups, locale],
  );
  return (
    <select
      aria-label={t("Time zone")}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    >
      {groups.map((zones, index) => (
        <optgroup
          key={index}
          label={t(index ? "Other time zones" : "Common time zones")}
        >
          {zones.map((zone) => (
            <option key={zone} value={zone}>
              {labels[zone]}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
