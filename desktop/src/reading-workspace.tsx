import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Search, X, Plus } from "lucide-react";
import { call, type RecordData } from "./engine";
import { useLocale } from "./locale";

export function ReadingWorkspace({
  onOpen,
  onError,
}: {
  onOpen: (id: string) => void;
  onError: (error: string) => void;
}) {
  const ar = useLocale() === "ar";
  const [view, setView] = useState(""),
    [state, setState] = useState<RecordData>({}),
    [articles, setArticles] = useState<RecordData[]>([]),
    [topic, setTopic] = useState(""),
    [busy, setBusy] = useState(false);
  const version = useRef(0);
  async function load(next = view, query = topic) {
    const token = ++version.current;
    setBusy(true);
    try {
      const data = await call("reading.workspace", {
        action: next === "quotes" ? "get" : "briefing",
        view: next,
        topic: query,
      });
      if (token !== version.current) return;
      setState(data.state || data);
      setArticles(data.articles || []);
    } catch (e) {
      if (token === version.current) onError(String(e));
    } finally {
      if (token === version.current) setBusy(false);
    }
  }
  useEffect(() => {
    if (view) void load();
    return () => {
      ++version.current;
    };
  }, [view]);
  async function action(payload: RecordData) {
    setBusy(true);
    try {
      await call("reading.workspace", payload);
      await load();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const tabs = [
    ["catchup", ar ? "وش فاتني؟" : "Catch me up"],
    ["five", ar ? "عندي ٥ دقائق" : "I have 5 minutes"],
    ["queue", ar ? "قائمة القراءة" : "Reading queue"],
    ["topic", ar ? "متابعة القصص" : "Following stories"],
    ["updates", ar ? "تغيّر منذ قراءتي" : "Updated since reading"],
    ["quotes", ar ? "اقتباساتي" : "My quotes"],
  ];
  return (
    <section
      className="reading-workspace"
      aria-label={ar ? "مساحة القراءة" : "Reading workspace"}
    >
      <div className="reading-workspace-tabs">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            aria-pressed={view === id}
            onClick={() => setView(view === id ? "" : id)}
          >
            {label}
          </button>
        ))}
      </div>
      {view && (
        <div className="reading-workspace-content" aria-busy={busy}>
          <header>
            <h2>{tabs.find((x) => x[0] === view)?.[1]}</h2>
            <button
              aria-label={ar ? "إغلاق" : "Close"}
              onClick={() => setView("")}
            >
              <X size={16} />
            </button>
          </header>
          <p className="muted">
            {ar
              ? "من آخر ٥٠٠ مقال محفوظ. تُستخدم الملخصات الموجودة دون تشغيل المودل؛ وقت القراءة تقديري."
              : "From the latest 500 saved articles. Uses existing summaries without running a model; reading times are estimates."}
          </p>
          {view === "topic" && (
            <>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void load("topic", topic);
                }}
                className="reading-topic-search"
              >
                <label>
                  <Search size={16} />
                  <input
                    aria-label={ar ? "موضوع القصة" : "Story topic"}
                    placeholder={
                      ar ? "شركة، حدث، أو عبارة…" : "Company, event, or phrase…"
                    }
                    value={topic}
                    maxLength={100}
                    onChange={(e) => setTopic(e.target.value)}
                  />
                </label>
                <button disabled={busy || !topic.trim()}>
                  {ar ? "بحث" : "Search"}
                </button>
                <button
                  type="button"
                  disabled={busy || !topic.trim()}
                  onClick={() => void action({ action: "topic", topic })}
                >
                  <Plus size={15} />
                  {ar ? "متابعة" : "Follow"}
                </button>
                <button
                  type="button"
                  disabled={busy || !topic.trim()}
                  onClick={() => void action({ action: "mute", topic })}
                >
                  {ar ? "إخفاء لأسبوع" : "Mute for a week"}
                </button>
              </form>
              <p className="muted">
                {ar
                  ? "تطابق كلمات العنوان والوصف؛ لا يفترض أن كل النتائج تتحدث عن الحدث نفسه."
                  : "Matches title and description words; results are not assumed to describe the same event."}
              </p>
              <div className="reading-workspace-tabs">
                {(state.topics || []).map((name: string) => (
                  <span key={name}>
                    <button
                      onClick={() => {
                        setTopic(name);
                        void load("topic", name);
                      }}
                    >
                      {name}
                    </button>
                    <button
                      aria-label={(ar ? "إلغاء متابعة " : "Unfollow ") + name}
                      onClick={() =>
                        void action({
                          action: "topic",
                          topic: name,
                          enabled: false,
                        })
                      }
                    >
                      <X size={13} />
                    </button>
                  </span>
                ))}
              </div>
              {(state.muted || [])
                .filter((m: RecordData) => m.until > new Date().toISOString())
                .map((m: RecordData) => (
                  <button
                    key={m.topic}
                    onClick={() =>
                      void action({
                        action: "mute",
                        topic: m.topic,
                        enabled: false,
                      })
                    }
                  >
                    {ar ? "إظهار مجددًا: " : "Unmute: "}
                    {m.topic}
                  </button>
                ))}
            </>
          )}
          {busy ? (
            <p role="status">{ar ? "جارٍ التحميل…" : "Loading…"}</p>
          ) : view === "quotes" ? (
            (state.quotes || []).map((q: RecordData) => (
              <div className="reading-brief" key={q.id}>
                <small>
                  {q.origin === "summary"
                    ? ar
                      ? "من الملخص الآلي"
                      : "From the AI summary"
                    : ar
                      ? "من المقال"
                      : "From the article"}
                </small>
                <blockquote dir="auto">{q.text}</blockquote>
                <button onClick={() => onOpen(q.article_id)} dir="auto">
                  {q.title}
                </button>
                <button
                  onClick={() =>
                    void action({ action: "remove_quote", id: q.id })
                  }
                >
                  {ar ? "حذف الاقتباس" : "Delete quote"}
                </button>
              </div>
            ))
          ) : (
            articles.map((a) => (
              <div className="reading-brief" key={a.id}>
                <button onClick={() => onOpen(a.id)} dir="auto">
                  <strong>{a.title}</strong>
                </button>
                <small>
                  {a.source_title} · {a.reading_minutes}{" "}
                  {ar ? "دقيقة تقريبًا" : "min estimated"}
                </small>
                <p dir="auto">
                  {(a.saved_summary || a.summary || "").slice(0, 700)}
                </p>
                {view === "queue" && (
                  <button
                    disabled={busy}
                    onClick={() =>
                      void action({
                        action: "queue",
                        article_id: a.id,
                        enabled: false,
                      })
                    }
                  >
                    {ar
                      ? "إنهاء وإزالة من القائمة"
                      : "Done · Remove from queue"}
                  </button>
                )}
              </div>
            ))
          )}
          {!busy &&
            (view === "quotes"
              ? !(state.quotes || []).length
              : !articles.length) && (
              <p>{ar ? "لا توجد عناصر هنا الآن." : "Nothing here yet."}</p>
            )}
          {view === "catchup" && articles.length > 0 && (
            <button
              disabled={busy}
              onClick={() =>
                void action({
                  action: "caught_up",
                  article_ids: articles.map((a) => a.id),
                })
              }
            >
              {ar ? "اطلعت على الموجز" : "Mark briefing seen"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

export function ReaderTools({
  article,
  onDiscuss,
  onError,
}: {
  article: RecordData;
  onDiscuss?: (article: RecordData) => void;
  onError: (e: string) => void;
}) {
  const ar = useLocale() === "ar";
  const [quoteOrigin, setQuoteOrigin] = useState("article");
  const [selected, setSelected] = useState(""),
    [query, setQuery] = useState(""),
    [matches, setMatches] = useState<HTMLElement[]>([]),
    [index, setIndex] = useState(0),
    [notice, setNotice] = useState(""),
    [queued, setQueued] = useState(false),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    void call("reading.workspace")
      .then((s) => {
        if (live) setQueued((s.queue || []).includes(article.id));
      })
      .catch(() => {});
    const selection = () => {
      const s = window.getSelection();
      const node = s?.anchorNode?.parentElement;
      setQuoteOrigin(node?.closest(".article-tldr") ? "summary" : "article");
      setSelected(
        node?.closest(".reader-content")
          ? s!.toString().trim().slice(0, 4000)
          : "",
      );
    };
    document.addEventListener("selectionchange", selection);
    return () => {
      live = false;
      document.removeEventListener("selectionchange", selection);
    };
  }, [article.id]);
  function search(value: string) {
    setQuery(value);
    const root = document.querySelector(".reader-content");
    const found = value.trim()
      ? Array.from(
          root?.querySelectorAll<HTMLElement>(
            ".prose p,.prose li,.prose h1,.prose h2,.prose h3",
          ) || [],
        ).filter((n) =>
          n.textContent
            ?.toLocaleLowerCase()
            .includes(value.toLocaleLowerCase()),
        )
      : [];
    setMatches(found);
    setIndex(0);
    found[0]?.scrollIntoView({ block: "center", behavior: "instant" });
  }
  async function save(action: RecordData) {
    setBusy(true);
    setNotice("");
    try {
      await call("reading.workspace", { ...action, article_id: article.id });
      if (action.action === "queue") setQueued(action.enabled);
      setNotice(ar ? "تم الحفظ" : "Saved");
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  function ask(kind: string) {
    onDiscuss?.({
      ...article,
      discussion_prompt: `${kind}\n\n${selected}\n\n${article.title}`,
    });
  }
  return (
    <div className="reader-tools">
      <div className="reader-tools-row">
        <label>
          <Search size={15} />
          <input
            aria-label={
              ar ? "بحث داخل المقال والملخص" : "Find in article and summary"
            }
            placeholder={
              ar ? "بحث داخل المقال والملخص" : "Find in article and summary"
            }
            value={query}
            onChange={(e) => search(e.target.value)}
          />
        </label>
        {query && (
          <>
            <span role="status">
              {matches.length ? index + 1 : 0}/{matches.length}
            </span>
            <button
              disabled={!matches.length}
              aria-label={ar ? "النتيجة السابقة" : "Previous result"}
              onClick={() => {
                const i = (index - 1 + matches.length) % matches.length;
                setIndex(i);
                matches[i].scrollIntoView({ block: "center" });
              }}
            >
              <ArrowLeft size={15} />
            </button>
            <button
              disabled={!matches.length}
              aria-label={ar ? "النتيجة التالية" : "Next result"}
              onClick={() => {
                const i = (index + 1) % matches.length;
                setIndex(i);
                matches[i].scrollIntoView({ block: "center" });
              }}
            >
              <ArrowRight size={15} />
            </button>
          </>
        )}
        <button
          disabled={busy}
          aria-pressed={queued}
          onClick={() => void save({ action: "queue", enabled: !queued })}
        >
          {queued
            ? ar
              ? "إزالة من قائمة القراءة"
              : "Remove from queue"
            : ar
              ? "اقرأه لاحقًا في الجلسة"
              : "Add to reading queue"}
        </button>
      </div>
      {selected && (
        <div className="reader-selection-actions">
          <span>{ar ? "النص المحدد" : "Selected text"}</span>
          <button
            onMouseDown={(e) => e.preventDefault()}
            onClick={() =>
              void save({
                action: "quote",
                text: selected,
                origin: quoteOrigin,
              })
            }
          >
            {ar ? "حفظ اقتباس" : "Save quote"}
          </button>
          {onDiscuss && (
            <>
              <button
                onMouseDown={(e) => e.preventDefault()}
                onClick={() =>
                  ask(
                    ar
                      ? "اشرح النص المحدد بالاستناد إلى المقال."
                      : "Explain this selected passage using the article.",
                  )
                }
              >
                {ar ? "اشرح لي" : "Explain"}
              </button>
              <button
                onMouseDown={(e) => e.preventDefault()}
                onClick={() =>
                  ask(
                    ar
                      ? "ترجم النص المحدد إلى العربية."
                      : "Translate this selected passage into English.",
                  )
                }
              >
                {ar ? "ترجمة" : "Translate"}
              </button>
              <button
                onMouseDown={(e) => e.preventDefault()}
                onClick={() =>
                  ask(
                    ar
                      ? "لدي سؤال حول هذا النص:"
                      : "I have a question about this passage:",
                  )
                }
              >
                {ar ? "اسأل الشات" : "Ask chat"}
              </button>
            </>
          )}
        </div>
      )}
      {notice && <span role="status">{notice}</span>}
    </div>
  );
}

export function SourceComparison({
  article,
  related,
  onError,
}: {
  article: RecordData;
  related: RecordData[];
  onError: (e: string) => void;
}) {
  const ar = useLocale() === "ar";
  const [result, setResult] = useState<RecordData>(),
    [busy, setBusy] = useState(false);
  const request = useRef(0);
  useEffect(() => {
    setResult(undefined);
    return () => {
      ++request.current;
    };
  }, [article.id]);
  async function compare(id: string) {
    const token = ++request.current;
    setBusy(true);
    try {
      const r = await call("reading.workspace", {
        action: "comparison",
        article_id: article.id,
        other_id: id,
      });
      if (token === request.current) setResult(r);
    } catch (e) {
      if (token === request.current) onError(String(e));
    } finally {
      if (token === request.current) setBusy(false);
    }
  }
  return related.length ? (
    <details className="source-comparison">
      <summary>
        {ar ? "ماذا يختلف عن تغطية أخرى؟" : "What differs from another source?"}
      </summary>
      <p className="muted">
        {ar
          ? "مقارنة نصية للمقتطفات المحفوظة، وليست حكمًا بأن كل اختلاف معلومة جديدة أو أن المقالين عن الحدث نفسه."
          : "Compares saved text excerpts. Different wording does not prove a new fact or that both articles cover the same event."}
      </p>
      <select
        aria-label={ar ? "المقال للمقارنة" : "Article to compare"}
        defaultValue=""
        disabled={busy}
        onChange={(e) => void compare(e.target.value)}
      >
        <option value="" disabled>
          {ar ? "اختر تغطية مرتبطة" : "Choose related coverage"}
        </option>
        {related.map((a) => (
          <option key={a.id} value={a.id}>
            {a.title}
          </option>
        ))}
      </select>
      {busy && <p role="status">{ar ? "جارٍ المقارنة…" : "Comparing…"}</p>}
      {result && (
        <div>
          <p dir="auto">{result.against.title}</p>
          {result.excerpts.length ? (
            result.excerpts.map((s: string, i: number) => (
              <blockquote dir="auto" key={i}>
                {s}
              </blockquote>
            ))
          ) : (
            <p>
              {ar
                ? "لم نعثر على مقتطفات مختلفة."
                : "No different excerpts found."}
            </p>
          )}
        </div>
      )}
    </details>
  ) : null;
}
