import { SourceMedia } from "./source-media";
import { memo, useState, useEffect, useRef } from "react";
import {
  Copy,
  Check,
  FileText,
  ArrowUpRight,
  BookOpen,
  ChevronDown,
} from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { Markdown, Trace } from "./components";
import type { RecordData } from "./engine";
import { t, useLocale } from "./locale";
import {
  copyWithCitations,
  sourceAddress,
  type ChatCitation,
} from "./chat-citations";

export const ChatMessage = memo(function ChatMessage({
  message,
  onError,
  onDraft,
}: {
  message: RecordData;
  onError: (s: string) => void;
  onDraft: () => void;
}) {
  useLocale();
  const [copied, setCopied] = useState("");
  const copyRequest = useRef(0);
  const copyTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    setCopied("");
    return () => {
      ++copyRequest.current;
      clearTimeout(copyTimer.current);
    };
  }, [message.id, message.content]);
  async function copy(text: string, target: string) {
    const request = ++copyRequest.current;
    try {
      await navigator.clipboard.writeText(text);
      if (request !== copyRequest.current) return;
      clearTimeout(copyTimer.current);
      setCopied(target);
      copyTimer.current = setTimeout(() => setCopied(""), 1800);
    } catch (e) {
      if (request === copyRequest.current) onError(String(e));
    }
  }
  return (
    <article className={`message ${message.role}`}>
      {message.activity && <Trace data={message.activity} />}
      <Markdown
        text={message.content}
        citations={
          message.role === "assistant" ? message.citations || [] : undefined
        }
      />
      {message.role === "assistant" &&
        (message.citations || [])
          .flatMap((c: RecordData) =>
            (c.media || []).map((media: RecordData) => ({
              ...media,
              source_url: c.url,
            })),
          )
          .filter(
            (m: RecordData, i: number, all: RecordData[]) =>
              all.findIndex((x) => x.url === m.url) === i,
          )
          .slice(0, 4)
          .map((media: RecordData) => (
            <SourceMedia
              key={media.url}
              media={media}
              messageId={message.id}
              sourceUrl={media.source_url}
            />
          ))}
      {!!message.citations?.length && (
        <details className="citations">
          <summary>
            <BookOpen size={14} aria-hidden="true" />
            <span>
              {t("Sources")} · {message.citations.length}
            </span>
            <ChevronDown size={13} aria-hidden="true" />
          </summary>
          <div className="citation-list">
            {message.citations.map((c: ChatCitation, i: number) => (
              <button
                key={c.article_id || c.url || i}
                disabled={!sourceAddress(c)}
                onClick={() =>
                  void invoke("open_external", { address: c.url }).catch((e) =>
                    onError(String(e)),
                  )
                }
              >
                <span className="citation-number">{i + 1}</span>
                <span>
                  <span className="citation-title" dir="auto">
                    {c.title}
                  </span>
                  <small dir="ltr">{c.url}</small>
                </span>
                <ArrowUpRight size={14} />
              </button>
            ))}
          </div>
        </details>
      )}
      {message.outputs?.map((o: RecordData, i: number) => (
        <section className="draft-artifact" key={i}>
          <div className="artifact-heading">
            <FileText size={18} />
            <strong>{o.title || t("Saved draft")}</strong>
            <small>{o.format?.replaceAll("_", " ")}</small>
          </div>
          <Markdown text={o.text || ""} />
          <div className="reader-actions">
            <button onClick={onDraft}>
              {t("Open drafts")}
              <ArrowUpRight size={14} />
            </button>
            <button onClick={() => void copy(o.text || "", `draft:${i}`)}>
              {copied === `draft:${i}` && (
                <Check size={14} aria-hidden="true" />
              )}
              {t(copied === `draft:${i}` ? "Copied" : "Copy draft")}
            </button>
          </div>
        </section>
      ))}
      {message.role === "assistant" && message.content && (
        <div className="message-actions">
          <button
            className="icon-button"
            aria-label={t(copied === "response" ? "Copied" : "Copy response")}
            title={t(copied === "response" ? "Copied" : "Copy response")}
            onClick={() =>
              void copy(
                copyWithCitations(
                  message.content,
                  message.citations || [],
                  t("Sources"),
                  t("Source unavailable"),
                ),
                "response",
              )
            }
          >
            {copied === "response" ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>
      )}
    </article>
  );
});
