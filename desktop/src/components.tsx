import { useState, useEffect } from "react";
import { LoaderCircle, ChevronDown, BookOpen } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { invoke } from "@tauri-apps/api/core";
import { duration, language, type RecordData } from "./engine";
export function Markdown({ text }: { text: string }) {
  return (
    <div className="prose" dir={language(text) === "ar" ? "rtl" : "ltr"}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a
              href={href}
              onClick={(e) => {
                e.preventDefault();
                if (href)
                  void invoke("open_external", { address: href }).catch(
                    () => {},
                  );
              }}
            >
              {children}
            </a>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
export function Trace({
  data,
  running = false,
}: {
  data?: RecordData;
  running?: boolean;
}) {
  const [open, setOpen] = useState(running);
  useEffect(() => setOpen(running), [running]);
  if (!data) return null;
  const execution = data.execution || data;
  const summary = execution.reasoning_summary || "";
  const arabic = execution.summary_language === "ar";
  const labels: Record<string, string> = arabic
    ? {
        context: "تجهيز سياق المحادثة",
        library: "البحث في المقالات المحفوظة",
        reading: "قراءة مصدر",
        web: "البحث على الويب",
        history: "مراجعة المحادثة",
        skill: "تطبيق تعليمات المهمة",
        complete: "اكتمل",
      }
    : {
        library: "Searching saved articles",
        web: "Searching the web",
        history: "Reviewing conversation",
        skill: "Using task instructions",
        context: "Preparing context",
        search: "Searching articles",
        reading: "Reading a source",
        web_search: "Searching the web",
        web_read: "Reading a page",
        complete: "Completed",
      };
  const steps = execution.steps || [];
  return (
    <section className="trace">
      <button
        className="trace-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {running ? <LoaderCircle className="spin" size={14} /> : null}
        {arabic
          ? running
            ? "جارٍ العمل منذ"
            : "اكتمل العمل خلال"
          : running
            ? "Working for"
            : "Worked for"}{" "}
        {arabic
          ? `${Math.floor((data.elapsed_seconds || execution.elapsed_seconds || 0) / 60)} د ${(data.elapsed_seconds || execution.elapsed_seconds || 0) % 60} ث`
          : duration(data.elapsed_seconds || execution.elapsed_seconds || 0)}
        <ChevronDown size={14} className={open ? "rotated" : ""} />
      </button>
      {open && (
        <div className="trace-body">
          {typeof summary === "string" && summary && (
            <Markdown text={summary} />
          )}{" "}
          {steps.map((step: RecordData, i: number) => (
            <div className="trace-step" key={step.id || i}>
              <BookOpen size={15} />
              <span>
                {step.label ||
                  step.title ||
                  labels[step.kind] ||
                  step.kind ||
                  step.stage}
                {step.detail && <small>{step.detail}</small>}
              </span>
            </div>
          ))}
          {!summary && !steps.length && (
            <p>
              {arabic
                ? "جارٍ تجهيز الرد…"
                : data.activity || "Preparing the response…"}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
