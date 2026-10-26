import * as Popover from "@radix-ui/react-popover";
import { ArrowUpRight, X } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { useState } from "react";
import { sourceAddress, type ChatCitation } from "./chat-citations";
import { t, useLocale } from "./locale";

export function CitationReference({
  source,
  number,
}: {
  source?: ChatCitation;
  number?: number;
}) {
  const locale = useLocale();
  const [error, setError] = useState(false);
  const address = sourceAddress(source);
  const published = source?.published_at
    ? new Date(source.published_at)
    : undefined;
  const label = source
    ? `${t("Source")} ${number}: ${source.title || address?.hostname || t("Sources")}`
    : t("Source unavailable");
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button className="inline-citation" aria-label={label} type="button">
          {number ? new Intl.NumberFormat(locale).format(number) : "?"}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="link-preview citation-preview"
          side="top"
          align="start"
          sideOffset={8}
          collisionPadding={16}
          aria-label={t("Source preview")}
          dir={locale === "ar" ? "rtl" : "ltr"}
        >
          <div className="link-preview-source">
            <bdi>{address?.hostname || t("Source unavailable")}</bdi>
            <Popover.Close
              className="citation-preview-close"
              aria-label={t("Close")}
            >
              <X size={16} aria-hidden="true" />
            </Popover.Close>
          </div>
          <h3 dir="auto">{source?.title || t("Source unavailable")}</h3>
          {published && Number.isFinite(published.getTime()) && (
            <time dateTime={source?.published_at}>
              {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
                published,
              )}
            </time>
          )}
          {source?.excerpt && (
            <p className="link-preview-excerpt" dir="auto">
              {source.excerpt}
            </p>
          )}
          <p className="link-preview-status">
            {source?.excerpt
              ? t("Saved source excerpt")
              : t("No saved excerpt is available for this reference.")}
          </p>
          {address && (
            <footer className="link-preview-footer">
              <a
                href={address.href}
                className="link-preview-open"
                onClick={(event) => {
                  event.preventDefault();
                  setError(false);
                  void invoke("open_external", { address: address.href }).catch(
                    () => setError(true),
                  );
                }}
              >
                {t("Open original")}
                <ArrowUpRight size={15} aria-hidden="true" />
              </a>
            </footer>
          )}
          {error && (
            <p className="link-preview-status" role="alert">
              {t("Could not open the source. Try again.")}
            </p>
          )}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
