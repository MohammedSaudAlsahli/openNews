import { useEffect, useRef, useState, type ReactNode } from "react";
import * as Popover from "@radix-ui/react-popover";
import {
  ArrowUp,
  Square,
  Plus,
  SlidersHorizontal,
  Globe,
  Newspaper,
  Paperclip,
  AtSign,
  Check,
  ChevronDown,
  LoaderCircle,
} from "lucide-react";
import { ComposerPicker, type PickerActive } from "./composer-picker";
import { t, getLocale } from "./locale";
import type { RecordData } from "./engine";

export function ModelPicker({
  profiles,
  profile,
  model,
  models,
  loading = false,
  error = "",
  onRetry,
  onProfile,
  onModel,
  onSettings,
}: {
  profiles: RecordData[];
  profile: string;
  model: string;
  models: RecordData[];
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  onProfile: (id: string) => void;
  onModel: (id: string) => void;
  onSettings: () => void;
}) {
  const account = profiles.find((p) => p.id === profile);
  const displayModel =
    models.find((row) => row.id === model)?.name ||
    model ||
    t("Choose a model");
  return (
    <Popover.Root>
      <Popover.Trigger
        className="model-picker-trigger"
        aria-label={t("Choose model")}
      >
        <span dir="auto" title={displayModel}>
          {displayModel}
        </span>
        <ChevronDown size={15} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="floating-panel model-picker-panel"
          align="start"
          sideOffset={8}
          collisionPadding={16}
        >
          <h3>{t("Model")}</h3>
          <p className="muted">
            <bdi>
              {account?.label ||
                account?.provider_key ||
                t("Connect a model to start a conversation.")}
            </bdi>
          </p>
          <label className="field">
            {t("Model connection")}
            <select value={profile} onChange={(e) => onProfile(e.target.value)}>
              {!profiles.length && (
                <option value="">{t("No account connected")}</option>
              )}
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label || p.provider_key}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            {t("Model")}
            <select
              value={model}
              disabled={loading || !profile}
              onChange={(e) => onModel(e.target.value)}
            >
              {!models.some((m) => m.id === model) && (
                <option value={model}>{model || t("Choose a model")}</option>
              )}
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name || m.id}
                </option>
              ))}
            </select>
          </label>
          {loading ? (
            <p className="context-feedback" role="status">
              <LoaderCircle size={15} className="spin" />
              {t("Loading models…")}
            </p>
          ) : error ? (
            <div className="context-feedback" role="alert">
              <p>
                {t(
                  "The model list could not load. Your selected model is unchanged.",
                )}
              </p>
              {onRetry && <button onClick={onRetry}>{t("Retry")}</button>}
            </div>
          ) : (
            profile &&
            !models.length && (
              <p role="status">
                {t(
                  "No models were returned. Refresh the list or manage this connection.",
                )}
              </p>
            )
          )}
          <Popover.Close asChild>
            <button className="text-action" onClick={onSettings}>
              {t("Manage accounts & models")}
            </button>
          </Popover.Close>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

export function ChatComposer({
  message,
  onMessage,
  onSend,
  onStop,
  running,
  sending,
  stopping = false,
  ready,
  onArticles,
  onFile,
  onArticle,
  onError,
  includeNews,
  researchWeb,
  onNews,
  onWeb,
  agents,
  agent,
  onAgent,
  attachments,
}: {
  message: string;
  onMessage: (text: string) => void;
  onSend: () => void;
  onStop: () => void;
  running: boolean;
  sending: boolean;
  stopping?: boolean;
  ready: boolean;
  onArticles: () => void;
  onFile: () => void;
  onArticle: (row: RecordData) => void;
  onError: (s: string) => void;
  includeNews: boolean;
  researchWeb: boolean;
  onNews: (v: boolean) => void;
  onWeb: (v: boolean) => void;
  agents: RecordData[];
  agent: string;
  onAgent: (id: string) => void;
  attachments: ReactNode;
}) {
  const editor = useRef<HTMLTextAreaElement>(null);
  const [activePicker, setActivePicker] = useState<PickerActive>();
  const [suggestionsFocused, setSuggestionsFocused] = useState(false);
  const isSuggestionTarget = (target: EventTarget | null) =>
    target === editor.current ||
    (target instanceof Element && Boolean(target.closest(".composer-picker")));
  const focusAfterMenu = useRef<"editor" | "articles" | null>(null);
  useEffect(() => {
    const element = editor.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(200, Math.max(52, element.scrollHeight))}px`;
  }, [message]);
  return (
    <div
      className="composer"
      onFocusCapture={(event) =>
        setSuggestionsFocused(isSuggestionTarget(event.target))
      }
      onBlurCapture={(event) =>
        setSuggestionsFocused(isSuggestionTarget(event.relatedTarget))
      }
    >
      {attachments}
      <textarea
        ref={editor}
        aria-label={t("Message")}
        aria-autocomplete="list"
        aria-controls={activePicker?.list}
        aria-activedescendant={activePicker?.option}
        rows={1}
        placeholder={t("Ask about your news, or explore an idea…")}
        value={message}
        dir={message ? "auto" : getLocale() === "ar" ? "rtl" : "ltr"}
        onChange={(e) => onMessage(e.target.value)}
        onKeyDown={(e) => {
          if (
            e.key === "Enter" &&
            !e.shiftKey &&
            !e.nativeEvent.isComposing &&
            !e.defaultPrevented
          ) {
            e.preventDefault();
            if (ready && !sending && !running && message.trim()) onSend();
          }
        }}
      />
      <ComposerPicker
        message={message}
        onMessage={onMessage}
        onArticle={onArticle}
        onError={onError}
        onActiveChange={setActivePicker}
        enabled={suggestionsFocused}
        editor={editor}
      />
      <div className="composer-tools">
        <Popover.Root>
          <Popover.Trigger
            className="icon-button"
            title={t("Add to conversation")}
            aria-label={t("Add to conversation")}
          >
            <Plus size={21} />
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content
              className="floating-panel attachment-menu"
              side="top"
              align="start"
              sideOffset={12}
              collisionPadding={16}
              onCloseAutoFocus={(event) => {
                const target = focusAfterMenu.current;
                focusAfterMenu.current = null;
                if (!target) return;
                event.preventDefault();
                requestAnimationFrame(() => {
                  if (target === "editor") editor.current?.focus();
                  else
                    document
                      .querySelector<HTMLInputElement>(
                        ".conversation-options input",
                      )
                      ?.focus();
                });
              }}
            >
              <Popover.Close asChild>
                <button onClick={onFile}>
                  <Paperclip size={17} />
                  <span>
                    {t("Attach a file")}
                    <small>TXT, Markdown, CSV, JSON</small>
                  </span>
                </button>
              </Popover.Close>
              <Popover.Close asChild>
                <button
                  onClick={() => {
                    focusAfterMenu.current = "articles";
                    onArticles();
                  }}
                >
                  <Newspaper size={17} />
                  <span>
                    {t("Choose saved articles")}
                    <small>{t("Search your library or add a link")}</small>
                  </span>
                </button>
              </Popover.Close>
              <Popover.Close asChild>
                <button
                  onClick={() => {
                    focusAfterMenu.current = "editor";
                    onMessage(
                      message + (message && !/\s$/.test(message) ? " @" : "@"),
                    );
                    editor.current?.focus();
                  }}
                >
                  <AtSign size={17} />
                  {t("Mention an article")}
                </button>
              </Popover.Close>
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
        <Popover.Root>
          <Popover.Trigger
            className="composer-tool"
            aria-label={t("Conversation tools")}
          >
            <SlidersHorizontal size={16} />
            {t("Tools")}
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content
              className="floating-panel tools-menu"
              side="top"
              align="start"
              sideOffset={12}
              collisionPadding={16}
            >
              <h3>{t("Conversation tools")}</h3>
              <button
                role="switch"
                aria-checked={includeNews}
                onClick={() => onNews(!includeNews)}
              >
                <Newspaper size={17} />
                <span>
                  {t("Use saved news")}
                  <small>{t("Find relevant articles in your library")}</small>
                </span>
                {includeNews && <Check size={16} />}
              </button>
              <button
                role="switch"
                aria-checked={researchWeb}
                onClick={() => onWeb(!researchWeb)}
              >
                <Globe size={17} />
                <span>
                  {t("Allow web research")}
                  <small>{t("Look for current sources on the web")}</small>
                </span>
                {researchWeb && <Check size={16} />}
              </button>
              {agents.length > 0 && (
                <label className="field">
                  {t("Assistant")}
                  <select
                    value={agent}
                    onChange={(e) => onAgent(e.target.value)}
                  >
                    <option value="">{t("Default assistant")}</option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
        <span className="composer-context-hint">
          {t("/ commands · @ articles")}
        </span>
        <button
          className="send icon-button"
          aria-label={t(
            stopping
              ? "Stopping response…"
              : running
                ? "Stop response"
                : sending
                  ? "Sending message…"
                  : "Send message",
          )}
          title={t(
            stopping
              ? "Stopping response…"
              : running
                ? "Stop response"
                : sending
                  ? "Sending message…"
                  : "Send message",
          )}
          disabled={
            stopping || (!running && (!message.trim() || sending || !ready))
          }
          onClick={running ? onStop : onSend}
        >
          {stopping || (sending && !running) ? (
            <LoaderCircle size={19} className="spin" />
          ) : running ? (
            <Square size={16} fill="currentColor" />
          ) : (
            <ArrowUp size={20} />
          )}
        </button>
      </div>
    </div>
  );
}
