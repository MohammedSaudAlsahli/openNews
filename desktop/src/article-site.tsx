import { useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";

// Serialize create/resize/close so rapid tab switches cannot leave an orphaned webview.
let operations: Promise<unknown> = Promise.resolve();
export function ArticleSite({ address, onError }: { address: string; onError: (message: string) => void }) {
  const host = useRef<HTMLDivElement>(null);
  const errorHandler = useRef(onError);
  errorHandler.current = onError;
  useEffect(() => {
    let active = true;
    let scheduled = 0;
    const update = () => {
      cancelAnimationFrame(scheduled);
      scheduled = requestAnimationFrame(() => {
        if (!active || !host.current) return;
        const { x, y, width, height } = host.current.getBoundingClientRect();
        if (width < 1 || height < 1) return;
        operations = operations.catch(() => {}).then(async () => {
          if (active) await invoke("open_article_site", { address, x, y, width, height });
        }).catch(e => { if (active) errorHandler.current(String(e)); });
      });
    };
    const observer = new ResizeObserver(update);
    if (host.current) observer.observe(host.current);
    window.addEventListener("resize", update);
    update();
    return () => {
      active = false;
      cancelAnimationFrame(scheduled);
      observer.disconnect();
      window.removeEventListener("resize", update);
      operations = operations.catch(() => {}).then(() => invoke("close_article_site")).catch(() => {});
    };
  }, [address]);
  return <div className="article-site-host" ref={host} />;
}
