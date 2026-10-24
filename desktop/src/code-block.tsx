import {
  Component,
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Check, Copy } from "lucide-react";
import type { Element, RootContent } from "hast";
import { t, useLocale } from "./locale";

const HighlightedCode = lazy(() => import("./highlighted-code"));

// A failed optional chunk must never hide the article or interrupt a reply.
class HighlightBoundary extends Component<
  {
    children: ReactNode;
    fallback: ReactNode;
  },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function sourceText(node: RootContent): string {
  if (node.type === "text") return node.value;
  if (node.type === "element") {
    if (node.tagName === "br") return "\n";
    const text = node.children.map(sourceText).join("");
    return ["div", "p", "li"].includes(node.tagName) && !text.endsWith("\n")
      ? text + "\n"
      : text;
  }
  return "";
}

// Read the sanitized AST, not rendered children: single-line HTML <pre> and
// incomplete Markdown fences must behave exactly like other code blocks.
export function CodeBlock({ node }: { node?: Element }) {
  useLocale();
  const code = node?.children.find(
    (child): child is Element =>
      child.type === "element" && child.tagName === "code",
  );
  const source = (code?.children || node?.children || [])
    .map(sourceText)
    .join("");
  const classes =
    (
      (code?.properties.className || node?.properties.className) as
        string[] | undefined
    )?.join(" ") || "";
  const language = /language-([^\s]+)/i.exec(classes)?.[1] || "";
  const shouldHighlight =
    source.length > 0 &&
    source.length <= 50000 &&
    (language
      ? !["text", "txt", "plaintext", "none"].includes(language.toLowerCase())
      : source.length <= 10000);
  const plain = (
    <code className={classes} dir="ltr">
      {source}
    </code>
  );
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const latestSource = useRef(source);
  latestSource.current = source;
  const live = useRef(true);
  const timeout = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
      clearTimeout(timeout.current);
    };
  }, []);
  useEffect(() => {
    clearTimeout(timeout.current);
    setCopied(false);
    setFailed(false);
  }, [source]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(source);
      if (!live.current || latestSource.current !== source) return;
      setCopied(true);
      setFailed(false);
      clearTimeout(timeout.current);
      timeout.current = setTimeout(() => setCopied(false), 1800);
    } catch {
      if (live.current && latestSource.current === source) setFailed(true);
    }
  }

  return (
    <figure className="code-block" dir="ltr">
      <figcaption className="code-block-header">
        <span>{language || t("Code")}</span>
        <button
          type="button"
          onClick={() => void copy()}
          aria-label={t("Copy code")}
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          <span aria-live="polite">
            {failed
              ? t("Copy failed. Try again")
              : copied
                ? t("Copied")
                : t("Copy code")}
          </span>
        </button>
      </figcaption>
      <pre
        tabIndex={0}
        aria-label={language ? `${t("Code")}: ${language}` : t("Code")}
      >
        {shouldHighlight ? (
          <HighlightBoundary fallback={plain}>
            <Suspense fallback={plain}>
              <HighlightedCode source={source} className={classes} />
            </Suspense>
          </HighlightBoundary>
        ) : (
          plain
        )}
      </pre>
    </figure>
  );
}
