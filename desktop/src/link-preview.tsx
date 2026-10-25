import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type AnchorHTMLAttributes,
  type ReactNode,
} from "react";
import * as Popover from "@radix-ui/react-popover";
import { ArrowUpRight } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { call, type RecordData } from "./engine";
import { t, useLocale } from "./locale";

const ArticleContext = createContext<string | undefined>(undefined);
// Only opened previews consume IPC. Bound session memory and reuse in-flight work.
const previews = new Map<
  string,
  { expires: number; request: Promise<RecordData> }
>();
function loadPreview(article: string, url: string) {
  const key = `${article}:${url}`;
  const saved = previews.get(key);
  if (saved && saved.expires > Date.now()) return saved.request;
  const request = call("news.link.preview", { article_id: article, url }).catch(
    () => ({ status: "unavailable" }),
  );
  previews.delete(key);
  previews.set(key, { expires: Date.now() + 5 * 60_000, request });
  if (previews.size > 80) previews.delete(previews.keys().next().value!);
  return request;
}

export function ReaderLinkPreviews({
  articleId,
  children,
}: {
  articleId: string;
  children: ReactNode;
}) {
  return (
    <ArticleContext.Provider value={articleId}>
      {children}
    </ArticleContext.Provider>
  );
}

export function PreviewLink(props: AnchorHTMLAttributes<HTMLAnchorElement>) {
  const article = useContext(ArticleContext);
  let address: URL | undefined;
  try {
    address = new URL(props.href || "");
  } catch {
    /* Local fragments remain ordinary links. */
  }
  if (
    !article ||
    !props.href ||
    !address ||
    !["http:", "https:"].includes(address.protocol)
  )
    return <a {...props} />;
  return (
    <ReaderLink
      key={`${article}:${props.href}`}
      {...props}
      article={article}
      href={props.href}
    />
  );
}

function ReaderLink({
  article,
  href,
  children,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & {
  article: string;
  href: string;
}) {
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const trigger = useRef<HTMLAnchorElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const clear = () => {
    clearTimeout(timer.current);
  };
  const close = () => {
    clear();
    timer.current = setTimeout(() => {
      if (
        !panel.current?.contains(document.activeElement) &&
        document.activeElement !== trigger.current
      )
        setOpen(false);
    }, 180);
  };
  useEffect(() => () => clearTimeout(timer.current), []);
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <a
          {...props}
          href={href}
          ref={trigger}
          onPointerEnter={(event) => {
            props.onPointerEnter?.(event);
            if (event.pointerType === "touch") return;
            clear();
            timer.current = setTimeout(() => setOpen(true), 320);
          }}
          onPointerLeave={(event) => {
            props.onPointerLeave?.(event);
            close();
          }}
          onFocus={(event) => {
            props.onFocus?.(event);
            clear();
            setOpen(true);
          }}
          onBlur={(event) => {
            props.onBlur?.(event);
            close();
          }}
          onKeyDown={(event) => {
            props.onKeyDown?.(event);
            if (event.key === "ArrowDown" && !event.defaultPrevented) {
              event.preventDefault();
              setOpen(true);
              requestAnimationFrame(() =>
                panel.current
                  ?.querySelector<HTMLAnchorElement>(".link-preview-open")
                  ?.focus(),
              );
            }
          }}
          onClick={(event) => {
            props.onClick?.(event);
            if (!event.defaultPrevented) {
              event.preventDefault();
              void invoke("open_external", { address: href }).catch(() => {});
            }
            setOpen(false);
          }}
        >
          {children}
        </a>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          ref={panel}
          className="link-preview"
          side="top"
          align="start"
          sideOffset={10}
          collisionPadding={16}
          aria-label={t("Link preview")}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
          onEscapeKeyDown={() =>
            trigger.current?.focus({ preventScroll: true })
          }
          onPointerEnter={clear}
          onPointerLeave={close}
          onFocusCapture={clear}
          onBlurCapture={close}
        >
          <PreviewContent article={article} href={href} label={children} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function PreviewContent({
  article,
  href,
  label,
}: {
  article: string;
  href: string;
  label: ReactNode;
}) {
  const locale = useLocale();
  const [result, setResult] = useState<RecordData | null>(null);
  useEffect(() => {
    let live = true;
    setResult(null);
    void loadPreview(article, href).then((value) => {
      if (live) setResult(value);
    });
    return () => {
      live = false;
    };
  }, [article, href]);
  const host = new URL(href).hostname.replace(/^www\./, "");
  return (
    <div dir={locale === "ar" ? "rtl" : "ltr"}>
      <div className="link-preview-source">
        <bdi>{host}</bdi>
        <span>{t(result?.kind === "post" ? "Post" : "Linked source")}</span>
      </div>
      <h3 dir="auto">{result?.title || label || host}</h3>
      {!result ? (
        <p className="link-preview-status" role="status">
          {t("Loading preview…")}
        </p>
      ) : result.status === "read" && result.excerpt ? (
        <>
          <p className="link-preview-excerpt" dir="auto">
            {result.excerpt}
          </p>
          <p className="link-preview-status">
            {t(
              result.cached
                ? "Saved excerpt · No model used"
                : "Source excerpt · No model used",
            )}
          </p>
        </>
      ) : (
        <p className="link-preview-status" role="status">
          {t(
            "Preview unavailable. The source may require sign-in or block reading. You can open the original.",
          )}
        </p>
      )}
      <footer className="link-preview-footer">
        <a
          className="link-preview-open"
          href={href}
          onClick={(event) => {
            event.preventDefault();
            void invoke("open_external", { address: href }).catch(() => {});
          }}
        >
          {t("Open original")}
          <ArrowUpRight size={15} aria-hidden="true" />
        </a>
      </footer>
    </div>
  );
}
