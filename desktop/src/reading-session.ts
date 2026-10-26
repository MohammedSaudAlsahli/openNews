const KEY = "reading-positions-v1";
export function readingPosition(id: string) {
  try {
    return Number(JSON.parse(localStorage.getItem(KEY) || "{}")[id]) || 0;
  } catch {
    return 0;
  }
}
export function saveReadingPosition(id: string, value: number) {
  try {
    const positions = JSON.parse(localStorage.getItem(KEY) || "{}");
    delete positions[id];
    positions[id] = Math.max(0, value);
    localStorage.setItem(
      KEY,
      JSON.stringify(Object.fromEntries(Object.entries(positions).slice(-200))),
    );
  } catch {
    /* Reading remains available when browser storage is full. */
  }
}

export function readingFilters(): Record<string, any> {
  try {
    const value = JSON.parse(localStorage.getItem("reading-filters-v1") || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}
export function saveReadingFilters(filters: Record<string, any>) {
  try {
    localStorage.setItem("reading-filters-v1", JSON.stringify(filters));
  } catch {
    /* Optional persistence. */
  }
}
