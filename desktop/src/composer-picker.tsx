import { useEffect, useId, useState, type RefObject } from "react";
import { LoaderCircle } from "lucide-react";
import { call, type RecordData } from "./engine";
import { t, useLocale } from "./locale";
export const commands = [
  ["research", "Research a topic with sources"],
  ["summarize", "Explain an article in detail"],
  ["x", "Write a post for X"],
  ["thread", "Turn an idea into a thread"],
  ["shorts", "Write a short video script"],
  ["hooks", "Suggest opening lines"],
  ["linkedin", "Write a LinkedIn post"],
  ["youtube", "Write a YouTube script"],
  ["rewrite", "Improve your writing"],
  ["plan", "Create a content plan"],
];
export type PickerActive = { list: string; option?: string } | undefined;
export function ComposerPicker({
  message,
  onMessage,
  onArticle,
  onActiveChange,
  enabled = true,
  editor,
}: {
  message: string;
  onMessage: (value: string) => void;
  onArticle: (row: RecordData) => void;
  onError: (message: string) => void;
  onActiveChange?: (active: PickerActive) => void;
  enabled?: boolean;
  editor?: RefObject<HTMLTextAreaElement | null>;
}) {
  const listId = useId();
  const locale = useLocale();
  const [customCommands, setCustomCommands] = useState<string[][]>([]);
  const slash = /^\/([\w-]*)$/.exec(message);
  const mention = /(?:^|\s)@([^@\n]*)$/.exec(message);
  const query = mention?.[1] || "";
  const [rows, setRows] = useState<RecordData[]>([]);
  const [busy, setBusy] = useState(false);
  const [index, setIndex] = useState(0);
  const [dismissed, setDismissed] = useState<string>();
  const [bookmarks, setBookmarks] = useState(false);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setIndex(0);
  }, [message, bookmarks]);
  useEffect(() => {
    if (!mention) return;
    let live = true;
    setBusy(true);
    setError(false);
    setRows([]);
    const timer = setTimeout(
      () =>
        void call("news.list", {
          query: query.slice(0, 200),
          limit: 12,
          ...(bookmarks ? { scope: "saved" } : {}),
        })
          .then((r) => {
            if (live) setRows(r.articles || []);
          })
          .catch(() => {
            if (live) setError(true);
          })
          .finally(() => {
            if (live) setBusy(false);
          }),
      200,
    );
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [query, Boolean(mention), bookmarks, attempt]);
  useEffect(() => {
    if (!slash || !enabled) return;
    let live = true;
    void Promise.resolve(call("skills.catalog"))
      .then((result) => {
        if (live)
          setCustomCommands(
            (result?.skills || [])
              .filter((row: RecordData) => row.origin === "custom")
              .map((row: RecordData) => [
                row.id,
                row[`title_${locale}`] || row.id,
              ]),
          );
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [Boolean(slash), enabled, locale]);
  const choices: RecordData[] = slash
    ? [...commands, ...customCommands]
        .filter(([name]) => name.startsWith(slash[1]))
        .map(([id, description]) => ({ id, title: `/${id}`, description }))
    : rows;
  const visible = enabled && Boolean(slash || mention) && dismissed !== message;
  const searching = Boolean(mention) && busy;
  function pick(row: RecordData) {
    if (slash) onMessage(`/${row.id} `);
    else {
      onArticle(row);
      onMessage(message.slice(0, message.lastIndexOf("@")).trimEnd());
    }
  }
  useEffect(() => {
    if (!visible) return;
    const handler = (e: KeyboardEvent) => {
      if (!(e.target instanceof HTMLTextAreaElement) || e.isComposing) return;
      if (editor && e.target !== editor.current) return;
      if (["ArrowDown", "ArrowUp", "Escape", "Enter"].includes(e.key)) {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (e.key === "Escape") setDismissed(message);
        else if (e.key === "Enter") {
          if (choices[index]) pick(choices[index]);
        } else
          setIndex((i) =>
            choices.length
              ? (i + (e.key === "ArrowDown" ? 1 : -1) + choices.length) %
                choices.length
              : 0,
          );
      }
    };
    window.addEventListener("keydown", handler, true);
    return () => window.removeEventListener("keydown", handler, true);
  }, [visible, message, index, choices, editor]);
  const activeId = visible && choices[index] ? `${listId}-${index}` : undefined;
  useEffect(() => {
    onActiveChange?.(visible ? { list: listId, option: activeId } : undefined);
    if (activeId)
      document.getElementById(activeId)?.scrollIntoView?.({ block: "nearest" });
  }, [visible, activeId, listId, onActiveChange]);
  useEffect(() => () => onActiveChange?.(undefined), [onActiveChange]);
  if (!visible) return null;
  return (
    <section
      className="composer-picker"
      aria-label={t(slash ? "Commands" : "Choose an article")}
    >
      <div className="picker-heading">
        <strong>{t(slash ? "Commands" : "Choose an article")}</strong>
        <small>↑ ↓ · Enter · Esc</small>
      </div>
      {mention && (
        <div className="segments">
          <button
            type="button"
            aria-pressed={!bookmarks}
            onClick={() => setBookmarks(false)}
          >
            {t("All")}
          </button>
          <button
            type="button"
            aria-pressed={bookmarks}
            onClick={() => setBookmarks(true)}
          >
            {t("Bookmarks")}
          </button>
        </div>
      )}
      <div
        className="picker-results"
        role="listbox"
        id={listId}
        aria-label={t(slash ? "Commands" : "Choose an article")}
        aria-busy={searching}
      >
        {choices.map((row, i) => (
          <button
            type="button"
            role="option"
            aria-selected={i === index}
            id={`${listId}-${i}`}
            key={row.id}
            onMouseEnter={() => setIndex(i)}
            onClick={() => pick(row)}
          >
            <strong>
              <bdi>{row.title}</bdi>
            </strong>
            <small>
              <bdi>{slash ? t(row.description) : row.source_title}</bdi>
            </small>
          </button>
        ))}
      </div>
      {mention && error ? (
        <div className="context-feedback" role="alert">
          <p>{t("Articles could not be loaded")}</p>
          <button onClick={() => setAttempt((value) => value + 1)}>
            {t("Retry")}
          </button>
        </div>
      ) : (
        !choices.length && (
          <p className="context-feedback" role="status">
            {searching && <LoaderCircle size={15} className="spin" />}
            {t(searching ? "Searching…" : "No matches")}
          </p>
        )
      )}
    </section>
  );
}
