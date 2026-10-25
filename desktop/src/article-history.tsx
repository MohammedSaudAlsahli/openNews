import { useEffect, useRef, useState } from "react";
import {
  History,
  ChevronDown,
  LoaderCircle,
  Minus,
  Plus,
  RefreshCw,
} from "lucide-react";
import { call, type RecordData } from "./engine";
import { Markdown } from "./components";
import { getLocale, t } from "./locale";

type ChangeLine = {
  kind: "added" | "removed" | "context";
  text: string;
  before?: number;
  after?: number;
};
type ChangeGroup = { field: string; lines: ChangeLine[] };
const fields: Record<string, string> = {
  title: "Title",
  text: "Article text",
  summary: "Excerpt",
  published_at: "Publication date",
  url: "Original link",
  body_status: "Retrieval status",
};

export function articleChanges(diff: string): ChangeGroup[] {
  const groups: ChangeGroup[] = [];
  let group: ChangeGroup | undefined,
    before = 0,
    after = 0;
  for (const line of diff.split("\n")) {
    const file =
      /^--- (title|text|summary|published_at|url|body_status) \(before\)$/.exec(
        line,
      );
    if (file) {
      group = { field: file[1], lines: [] };
      groups.push(group);
      continue;
    }
    if (!group || /^\+\+\+ .* \(after\)$/.test(line)) continue;
    const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(line);
    if (hunk) {
      before = Number(hunk[1]);
      after = Number(hunk[2]);
      continue;
    }
    if (line.startsWith("+"))
      group.lines.push({ kind: "added", text: line.slice(1), after: after++ });
    else if (line.startsWith("-"))
      group.lines.push({
        kind: "removed",
        text: line.slice(1),
        before: before++,
      });
    else if (line.startsWith(" "))
      group.lines.push({
        kind: "context",
        text: line.slice(1),
        before: before++,
        after: after++,
      });
  }
  return groups.filter((group) => group.lines.length > 0);
}
function capturedAt(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? t("Unknown date")
    : date.toLocaleString(getLocale());
}

function ChangeRows({
  lines,
  onSaved,
}: {
  lines: ChangeLine[];
  onSaved: () => void;
}) {
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set());
  const output = [];
  let before = 0,
    after = 0;
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    const omitted = Math.max(
      line.before === undefined ? 0 : line.before - before - 1,
      line.after === undefined ? 0 : line.after - after - 1,
    );
    if (omitted > 0) {
      output.push(
        <button
          key={`gap-${index}`}
          className="change-context-toggle"
          onClick={onSaved}
        >
          {omitted.toLocaleString(getLocale())}{" "}
          {t("unchanged lines outside this excerpt · Read saved article")}
        </button>,
      );
      before += omitted;
      after += omitted;
    }
    if (line.before !== undefined) before = line.before;
    if (line.after !== undefined) after = line.after;
    let end = index;
    if (
      line.kind === "context" &&
      (index === 0 ||
        lines[index - 1].kind !== "context" ||
        lines[index - 1].before! + 1 !== line.before)
    ) {
      while (
        end + 1 < lines.length &&
        lines[end + 1].kind === "context" &&
        lines[end + 1].before === lines[end].before! + 1
      )
        end++;
      if (end - index >= 2) {
        const start = index;
        const isExpanded = expanded.has(start);
        output.push(
          <button
            className="change-context-toggle"
            key={`context-${start}`}
            aria-expanded={isExpanded}
            onClick={() =>
              setExpanded((old) => {
                const next = new Set(old);
                if (next.has(start)) next.delete(start);
                else next.add(start);
                return next;
              })
            }
          >
            <ChevronDown size={14} aria-hidden="true" />
            {t(isExpanded ? "Hide" : "Show")}{" "}
            {(end - start + 1).toLocaleString(getLocale())}{" "}
            {t("unchanged lines")}
          </button>,
        );
        if (!isExpanded) {
          before = lines[end].before!;
          after = lines[end].after!;
          index = end;
          continue;
        }
      }
    }
    output.push(
      <div className={`change-row change-${line.kind}`} key={index}>
        <span className="change-number" aria-hidden="true">
          {line.before ?? ""}
        </span>
        <span className="change-number" aria-hidden="true">
          {line.after ?? ""}
        </span>
        <span
          className="change-mark"
          aria-label={t(
            line.kind === "added"
              ? "Added"
              : line.kind === "removed"
                ? "Removed"
                : "Unchanged",
          )}
        >
          {line.kind === "added" ? "+" : line.kind === "removed" ? "−" : " "}
        </span>
        <span className="change-text" dir="auto">
          {line.text || "\u00a0"}
        </span>
      </div>,
    );
  }
  return <div className="change-rows">{output}</div>;
}

export function ArticleHistory({ articleId }: { articleId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="summary-section article-history"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>
        <History size={15} aria-hidden="true" />
        <span>{t("Article history")}</span>
        <ChevronDown
          size={14}
          className="disclosure-chevron"
          aria-hidden="true"
        />
      </summary>
      {open && <HistoryPanel key={articleId} articleId={articleId} />}
    </details>
  );
}
function HistoryPanel({ articleId }: { articleId: string }) {
  const [rows, setRows] = useState<RecordData[]>([]),
    [revision, setRevision] = useState<RecordData>();
  const [loading, setLoading] = useState(true),
    [reading, setReading] = useState(false);
  const [error, setError] = useState(""),
    [selected, setSelected] = useState<number | string>();
  const [reload, setReload] = useState(0),
    [limit, setLimit] = useState(400);
  const [view, setView] = useState<"changes" | "saved">("changes");
  const savedView = useRef<HTMLButtonElement>(null);
  const request = useRef(0),
    live = useRef(true);
  async function choose(id: number | string) {
    const token = ++request.current;
    setSelected(id);
    setRevision(undefined);
    setReading(true);
    setError("");
    setLimit(400);
    setView("changes");
    try {
      const result = await call("news.revision", {
        article_id: articleId,
        revision_id: id,
      });
      if (live.current && token === request.current) setRevision(result);
    } catch (e) {
      if (live.current && token === request.current)
        setError(String(e).replace(/^Error:\s*/, ""));
    } finally {
      if (live.current && token === request.current) setReading(false);
    }
  }
  useEffect(() => {
    let current = true;
    live.current = true;
    setLoading(true);
    setReading(false);
    setError("");
    setRows([]);
    setRevision(undefined);
    setSelected(undefined);
    ++request.current;
    call("news.history", { article_id: articleId })
      .then((result) => {
        if (!current) return;
        const revisions = result.revisions || [];
        setRows(revisions);
        if (revisions.length) void choose(revisions[0].id);
      })
      .catch((e) => {
        if (current) setError(String(e).replace(/^Error:\s*/, ""));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
      live.current = false;
      ++request.current;
    };
  }, [articleId, reload]);
  const groups = articleChanges(revision?.diff || "");
  const lines = groups.flatMap((group) => group.lines);
  const additions = lines.filter((line) => line.kind === "added").length;
  const removals = lines.filter((line) => line.kind === "removed").length;
  let remaining = limit;
  return (
    <div className="history-panel">
      <div className="history-intro">
        <p>{t("Saved versions show what changed in the article over time.")}</p>
        <button
          className="icon-button"
          disabled={loading}
          aria-label={t("Refresh article history")}
          title={t("Refresh article history")}
          onClick={() => setReload((value) => value + 1)}
        >
          <RefreshCw size={15} className={loading ? "spin" : undefined} />
        </button>
      </div>
      {loading && (
        <p role="status" className="muted">
          <LoaderCircle size={15} className="spin" />{" "}
          {t("Loading saved versions…")}
        </p>
      )}
      {!loading && !error && !rows.length && (
        <p className="muted">
          {t(
            "No saved versions yet. Versions appear when article content changes.",
          )}
        </p>
      )}
      {rows.length > 0 && (
        <div
          className="history-versions"
          role="group"
          aria-label={t("Saved versions")}
        >
          {rows.map((row, index) => (
            <button
              className="history-version"
              key={row.id}
              aria-pressed={selected === row.id}
              disabled={reading && selected === row.id}
              onClick={() => void choose(row.id)}
            >
              <History size={15} />
              <span>
                <strong>
                  {t(
                    index === 0
                      ? "Latest saved version"
                      : index === rows.length - 1
                        ? "First saved version"
                        : "Earlier saved version",
                  )}
                </strong>
                <time dateTime={row.captured_at}>
                  {capturedAt(row.captured_at)}
                </time>
              </span>
            </button>
          ))}
        </div>
      )}
      {reading && (
        <p role="status" className="muted">
          <LoaderCircle size={15} className="spin" /> {t("Loading changes…")}
        </p>
      )}
      {error && (
        <div className="history-error" role="alert">
          <p>{error}</p>
          <button
            onClick={() =>
              selected === undefined
                ? setReload((value) => value + 1)
                : void choose(selected)
            }
          >
            {t("Try again")}
          </button>
        </div>
      )}
      {revision && (
        <section
          className="history-comparison"
          aria-label={t(
            revision.previous_id
              ? "Changes from the previous saved version"
              : "First saved version",
          )}
        >
          <header>
            <div>
              <strong>
                {t(
                  revision.previous_id
                    ? "Changes from the previous saved version"
                    : "First saved version",
                )}
              </strong>
              <small>
                {t(
                  revision.previous_id
                    ? "Compared with the preceding capture"
                    : rows.length === 1
                      ? "Only one version is saved. Changes appear after the article is updated."
                      : "Starting point for later comparisons.",
                )}
              </small>
            </div>
            {revision.previous_id && lines.length > 0 && (
              <div className="history-counts">
                <span className="change-added">
                  <Plus size={14} />
                  {additions.toLocaleString(getLocale())} {t("added lines")}
                </span>
                <span className="change-removed">
                  <Minus size={14} />
                  {removals.toLocaleString(getLocale())} {t("removed lines")}
                </span>
              </div>
            )}
          </header>
          {revision.previous_id && (
            <div className="history-tools">
              <div
                className="history-view"
                role="group"
                aria-label={t("History view")}
              >
                <button
                  aria-pressed={view === "changes"}
                  onClick={() => setView("changes")}
                >
                  {t("Changes")}
                </button>
                <button
                  ref={savedView}
                  aria-pressed={view === "saved"}
                  onClick={() => setView("saved")}
                >
                  {t("Saved article")}
                </button>
              </div>
              {view === "changes" && (
                <span className="history-context-key">
                  {t("Unmarked lines are unchanged")}
                </span>
              )}
            </div>
          )}
          {!revision.previous_id || view === "saved" ? (
            <div className="history-snapshot">
              <strong dir="auto">{revision.content?.title}</strong>
              <Markdown
                text={
                  revision.content?.text ||
                  revision.content?.summary ||
                  t("No article text was saved in this version.")
                }
              />
            </div>
          ) : !groups.length ? (
            <p className="history-unchanged">{t("No text changes")}</p>
          ) : (
            <div className="history-changes">
              {groups.map((group) => {
                const shown = group.lines.slice(0, Math.max(0, remaining));
                remaining -= shown.length;
                if (!shown.length) return null;
                return (
                  <section className="history-field" key={group.field}>
                    <div className="history-field-heading">
                      <h4>{t(fields[group.field] || group.field)}</h4>
                      <span className="history-field-counts" dir="ltr">
                        <span className="change-added">
                          +
                          {
                            group.lines.filter((line) => line.kind === "added")
                              .length
                          }
                        </span>
                        <span className="change-removed">
                          −
                          {
                            group.lines.filter(
                              (line) => line.kind === "removed",
                            ).length
                          }
                        </span>
                      </span>
                    </div>
                    <div className="change-column-labels" aria-hidden="true">
                      <span>{t("Before")}</span>
                      <span>{t("After")}</span>
                    </div>
                    <ChangeRows
                      key={String(revision.id)}
                      lines={shown}
                      onSaved={() => {
                        setView("saved");
                        savedView.current?.focus();
                      }}
                    />
                  </section>
                );
              })}
              {lines.length > limit && (
                <button
                  className="history-show-more"
                  onClick={() => setLimit((value) => value + 400)}
                >
                  {t("Show more changes")}
                </button>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
