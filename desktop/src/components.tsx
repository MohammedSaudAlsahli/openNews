import {
  useState,
  useEffect,
  memo,
  useId,
  useMemo,
  createContext,
  useContext,
} from "react";
import {
  LoaderCircle,
  ChevronDown,
  BookOpen,
  Search,
  Globe,
  FileText,
  MessageSquare,
  Check,
  CircleAlert,
  CircleStop,
} from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import { invoke } from "@tauri-apps/api/core";
import { language, type RecordData } from "./engine";
import { CodeBlock } from "./code-block";
import { t, useLocale } from "./locale";
import { PreviewLink } from "./link-preview";
import { CitationReference } from "./citation-reference";
import {
  citationFragment,
  remarkChatCitations,
  type ChatCitation,
} from "./chat-citations";
// Publisher HTML is untrusted. Keep semantic formatting, never scripts, styles,
// event handlers, remote embeds or arbitrary DOM attributes.
const proseSchema = {
  ...defaultSchema,
  strip: [...(defaultSchema.strip || []), "style", "iframe", "object", "embed"],
  tagNames: [
    ...(defaultSchema.tagNames || []),
    "u",
    "mark",
    "sub",
    "sup",
    "kbd",
    "caption",
  ],
};
const CitationContext = createContext<ChatCitation[] | undefined>(undefined);

export const Markdown = memo(function Markdown({
  text,
  citations,
}: {
  text: string;
  citations?: ChatCitation[];
}) {
  useLocale();
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  // Stable component identities keep completed code mounted while a response
  // streams. Otherwise each token resets code focus, scroll and copy state.
  const components = useMemo<Components>(
    () => ({
      p: ({ children }) => <p dir="auto">{children}</p>,
      pre: ({ node }) => <CodeBlock node={node} />,
      code: ({ children }) => <code dir="ltr">{children}</code>,
      table: ({ children }) => (
        <div
          className="markdown-table"
          tabIndex={0}
          role="region"
          aria-label={t("Table")}
        >
          <table dir="auto">{children}</table>
        </div>
      ),
      a: function MarkdownLink({ href, children, node: _node, ...attributes }) {
        const citations = useContext(CitationContext);
        if (citations && href?.startsWith(citationFragment)) {
          const identifier = href.slice(citationFragment.length);
          const index = citations.findIndex(
            (source) => source.article_id?.toLowerCase() === identifier,
          );
          return (
            <CitationReference
              source={citations[index]}
              number={index >= 0 ? index + 1 : undefined}
            />
          );
        }
        return (
          <PreviewLink
            {...attributes}
            href={href}
            onClick={(e) => {
              e.preventDefault();
              if (href?.startsWith("#")) {
                const localId = href.slice(1);
                const target =
                  document.getElementById(`${id}-${localId}`) ||
                  document.getElementById(localId);
                if (
                  target?.closest(".prose") ===
                  e.currentTarget.closest(".prose")
                ) {
                  target.scrollIntoView?.({ block: "center" });
                  if (!target.hasAttribute("tabindex")) target.tabIndex = -1;
                  target.focus({ preventScroll: true });
                }
                return;
              }
              if (href)
                void invoke("open_external", { address: href }).catch(() => {});
            }}
          >
            {children}
          </PreviewLink>
        );
      },
    }),
    [id],
  );
  return (
    <div className="prose" dir={language(text) === "ar" ? "rtl" : "ltr"}>
      <CitationContext.Provider value={citations}>
        <ReactMarkdown
          remarkPlugins={
            citations
              ? [remarkGfm, remarkChatCitations(citations)]
              : [remarkGfm]
          }
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, { ...proseSchema, clobberPrefix: `${id}-` }],
          ]}
          remarkRehypeOptions={{
            clobberPrefix: "",
            footnoteLabel: t("Footnotes"),
            footnoteBackLabel: t("Back to reference"),
          }}
          components={components}
        >
          {text}
        </ReactMarkdown>
      </CitationContext.Provider>
    </div>
  );
});
export function Trace({
  data,
  running = false,
}: {
  data?: RecordData;
  running?: boolean;
}) {
  const locale = useLocale();
  const panelId = useId();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [running]);
  if (!data) return null;
  const execution = data.execution || data;
  const translated = execution.reasoning_summaries?.[locale];
  const stored =
    typeof execution.reasoning_summary === "string"
      ? execution.reasoning_summary
      : "";
  // UI language is independent of the answer and search queries. Older records
  // without a declared language can safely use their detected text language.
  const summary =
    typeof translated === "string" && translated.trim()
      ? translated
      : (execution.summary_language || language(stored)) === locale
        ? stored
        : "";
  const missingTranslation =
    !summary &&
    Boolean(
      stored ||
      execution.summary_translation_state ||
      Object.keys(execution.reasoning_summaries || {}).length,
    );

  const labels: Record<string, string> = {
    library: "Searching saved articles",
    search: "Searching saved articles",
    web: "Searching the web",
    web_search: "Searching the web",
    reading: "Reading a source",
    web_read: "Reading a source",
    history: "Reviewing conversation",
    skill: "Using task instructions",
    context: "Preparing context",
    complete: "Completed",
  };
  const icons = {
    context: MessageSquare,
    history: MessageSquare,
    library: Search,
    search: Search,
    web: Globe,
    web_search: Globe,
    reading: BookOpen,
    web_read: BookOpen,
    skill: FileText,
    complete: Check,
  };
  const steps: RecordData[] = Array.isArray(execution.steps)
    ? execution.steps.filter(
        (step: unknown) => step && typeof step === "object",
      )
    : [];
  const elapsed = Number(
    data.elapsed_seconds ?? execution.elapsed_seconds ?? 0,
  );
  const seconds = Number.isFinite(elapsed)
    ? Math.max(0, Math.floor(elapsed))
    : 0;
  const format = (value: number) =>
    new Intl.NumberFormat(locale, { useGrouping: false }).format(value);
  const minutes = Math.floor(seconds / 60);
  const time =
    locale === "ar"
      ? minutes
        ? `${format(minutes)} د${seconds % 60 ? ` ${format(seconds % 60)} ث` : ""}`
        : `${format(seconds)} ث`
      : minutes
        ? `${minutes}m${seconds % 60 ? ` ${seconds % 60}s` : ""}`
        : `${seconds}s`;
  const state = String(
    data.state || execution.state || (running ? "running" : "completed"),
  );
  const failed = state === "failed",
    stopped = state === "cancelled";
  const working = running && !failed && !stopped;
  const latest = steps.at(-1);
  const heading = failed
    ? t("Work interrupted")
    : stopped
      ? t("Work stopped")
      : working
        ? t(labels[latest?.kind] || "Preparing the response…")
        : t("Work completed");
  const hasDetails = Boolean(summary || missingTranslation || steps.length);
  const StatusIcon = failed
    ? CircleAlert
    : stopped
      ? CircleStop
      : working
        ? LoaderCircle
        : Check;
  return (
    <section
      className="trace"
      dir={locale === "ar" ? "rtl" : "ltr"}
      data-state={state}
    >
      <button
        className="trace-toggle"
        onClick={() => setOpen(!open)}
        disabled={!hasDetails}
        aria-label={`${heading}${seconds > 0 ? ` · ${time}` : ""}`}
        aria-expanded={hasDetails ? open : undefined}
        aria-controls={hasDetails ? panelId : undefined}
      >
        <StatusIcon
          size={14}
          className={working ? "spin" : ""}
          aria-hidden="true"
        />
        <span className="trace-heading" role={working ? "status" : undefined}>
          {heading}
        </span>
        {seconds > 0 && <span className="trace-time">{time}</span>}
        {hasDetails && (
          <ChevronDown
            size={13}
            className={open ? "rotated" : ""}
            aria-hidden="true"
          />
        )}
      </button>
      {open && hasDetails && (
        <div
          className="trace-body"
          id={panelId}
          role="region"
          aria-label={t("Work steps")}
          tabIndex={0}
        >
          {summary && (
            <div className="trace-summary">
              <Markdown text={summary} />
            </div>
          )}
          {missingTranslation && (
            <p className="trace-translation-status">
              {t(
                working &&
                  ["pending", "translating"].includes(
                    execution.summary_translation_state,
                  )
                  ? "Preparing activity in your interface language…"
                  : "Activity summary is unavailable in this language.",
              )}
            </p>
          )}
          {!!steps.length && (
            <ol className="trace-steps" aria-label={t("Work steps")}>
              {steps.map((step, i) => {
                const StepIcon =
                  icons[step.kind as keyof typeof icons] || FileText;
                return (
                  <li
                    className="trace-step"
                    key={step.id || i}
                    data-current={
                      working && i === steps.length - 1 ? "true" : undefined
                    }
                  >
                    <StepIcon size={14} aria-hidden="true" />
                    <div className="trace-step-copy">
                      <span dir="auto">
                        {t(labels[step.kind] || "Working…")}
                      </span>
                      {typeof step.detail === "string" && step.detail && (
                        <p dir="auto">{step.detail}</p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}
