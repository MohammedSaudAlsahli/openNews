import { useEffect, useState, useRef } from "react";
import { Play, Image, Music, ArrowUpRight, LoaderCircle } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { type RecordData } from "./engine";
import { useLocale } from "./locale";
import { sourceAddress } from "./chat-citations";

export function SourceMedia({
  media,
  articleId,
  messageId,
  sourceUrl,
}: {
  media: RecordData;
  articleId?: string;
  messageId?: string;
  sourceUrl?: string;
}) {
  const locale = useLocale(),
    ar = locale === "ar";
  const [data, setData] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    setData("");
    setError(false);
    setBusy(false);
    return () => {
      generation.current += 1;
    };
  }, [media.url, articleId, messageId]);
  const original = sourceAddress({
    article_id: "",
    url: sourceUrl || media.source_url,
  });
  const label =
    media.type === "image"
      ? ar
        ? "عرض الصورة"
        : "Show image"
      : media.type === "audio"
        ? ar
          ? "تحميل المقطع الصوتي"
          : "Load audio"
        : ar
          ? "تحميل الفيديو"
          : "Load video";
  async function load() {
    const request = generation.current;
    setBusy(true);
    setError(false);
    try {
      const result = await invoke<string>("source_media", {
        articleId: articleId || null,
        messageId: messageId || null,
        url: media.url,
      });
      if (request === generation.current) setData(result);
    } catch {
      if (request === generation.current) setError(true);
    } finally {
      if (request === generation.current) setBusy(false);
    }
  }
  return (
    <figure className="source-media">
      {media.title && <figcaption dir="auto">{media.title}</figcaption>}
      {data ? (
        media.type === "image" ? (
          <img src={data} alt={media.alt || ""} />
        ) : media.type === "audio" ? (
          <audio
            controls
            preload="none"
            src={data}
            onError={() => setError(true)}
          />
        ) : (
          <video
            controls
            playsInline
            preload="none"
            src={data}
            onError={() => setError(true)}
          />
        )
      ) : (
        media.type !== "embed" && (
          <button disabled={busy} onClick={() => void load()}>
            {busy ? (
              <LoaderCircle size={18} />
            ) : media.type === "image" ? (
              <Image size={18} />
            ) : media.type === "audio" ? (
              <Music size={18} />
            ) : (
              <Play size={18} />
            )}
            {busy ? (ar ? "جارٍ التحميل…" : "Loading…") : label}
          </button>
        )
      )}
      {error && (
        <p role="status">
          {ar
            ? "تعذّر تشغيل الوسائط هنا. قد يكون الملف كبيرًا أو غير مدعوم؛ افتح المصدر الأصلي."
            : "This media could not load here. It may be too large or unsupported; open the original source."}
        </p>
      )}
      {!data && !error && media.type !== "embed" && (
        <small>
          {ar
            ? "تحميل اختياري حتى ٤ ميغابايت؛ للمقاطع الأطول افتح المصدر."
            : "On-demand playback up to 4 MB. Open the source for longer clips."}
        </small>
      )}
      {media.caption && <figcaption dir="auto">{media.caption}</figcaption>}
      {original && (
        <button
          className="media-source"
          onClick={() =>
            void invoke("open_external", { address: original }).catch(() =>
              setError(true),
            )
          }
        >
          {ar ? "المصدر الأصلي" : "Original source"}
          <ArrowUpRight size={14} />
        </button>
      )}
    </figure>
  );
}
