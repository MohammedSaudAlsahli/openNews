# Article reader and RSS discovery

The reader was compared with the installed feeeed app on 2026-10-12: a centered reading column, prominent title and byline, full-width proportional photos, captions, readable spacing and a visible original-page action. OpenStudio implements these using SwiftUI/AppKit rather than embedding the publisher's active webpage.

## Reading behavior

- Workspace articles open a dedicated reading sheet. The menu-bar reader uses the same content renderer in a compact layout.
- Reading options change text size, show/hide images and reload a saved article. Photos open a larger preview on click. Sharing and opening the original page stay available in the toolbar.
- Content direction is detected independently from interface language. The reading column stays centered in Arabic and English. Appearance follows the application's light/dark setting.
- Article images preserve aspect ratios. Known captions and author metadata are retained. Lazy image attributes, picture/srcset, RSS images and media enclosures are supported; a publisher's Open Graph image is a fallback.
- Old saved articles load their text immediately, then fetch reading content on first opening. An explicit reload retries failed enrichment. Failures preserve the saved text and reading content.
- Images load through the engine's existing pinned public-network transport, without cookies, authentication or scripts. Only images attached to that workspace's article can be requested. Raster signatures are checked; native decoding bounds pixel counts and downsamples to 2048 pixels. Local image cache is capped at 100 MiB. Inaccessible or unsupported images have a retry state.
- Reader content is separate from the plain/Markdown evidence sent to the model. Agno configuration, prompts, tools and authentication are unchanged.

## Source directories

Discover sources now connects directly to the public [RSS.mobi API](https://rss.mobi/api/v1/feeds), alongside the editable `sources.yml` catalog. It does not connect a Feedly or Inoreader account.

- The default online tab searches the live directory by name/topic and category. Search is submitted explicitly (button or Return), with 30 results per page and a Load more action. RSS, Atom and RDF feeds are supported; JSON Feed entries are omitted because the subscription parser does not support them yet.
- Follow uses the existing subscription path, fetches the publisher's feed directly, and shows saved subscriptions and paused sources without duplicates. Browsing does not subscribe automatically.
- The local tab keeps the user's YAML unchanged and supports Arabic/English filtering and file editing. RSS.mobi descriptions stay in their source language; inclusion in the community directory is not publisher verification.
- Cached pages remain fresh for one hour; on network failure they can be shown for up to seven days with an explicit saved-results notice and original timestamp. The workspace cache is bounded to 40 pages. Refresh bypasses freshness. A directory outage never blocks the local catalog or existing subscriptions.
- Only the submitted query, selected topic and pagination timestamp are sent to RSS.mobi. Workspace content, model keys and subscriptions are not sent. Requests use the existing public-network transport with DNS pinning and response limits. Pagination never follows an untrusted next URL.
- Endpoint parameters (`q`, `tag`, `limit`, `before`) are taken from the [provider's public API implementation](https://github.com/dstengine/rss-mobi/blob/main/src/pages/api/v1/feeds/index.ts). No provider source code is embedded. Attribution and a link to RSS.mobi appear in the interface; publisher links accompany each result. [Directory terms](https://rss.mobi/terms/).

## Verification — 2026-10-12

- 273 Python tests and 34 Swift tests passed (307 total), including ordered images/captions, image allowlists, cached access, old-article backfill, offline preservation, malformed image rejection and native downsampling.
- Development app bundle passed signature verification, relocated runtime smoke and the existing four-format Agno conversation smoke against a mock provider.
- A real subscribed The Verge article extracted five photos and the author. All five images were fetched and rendered. Image enlargement and Arabic/light plus English/dark reader layouts were checked in the native app. The final build was also opened on another article with previously uncached images.
- Workspace reader received direct native UI verification. The compact menu-bar surface shares its renderer and builds successfully, but its menu-bar opening could not be independently automated in this pass.
- No new model requests or subscription changes were made during reader verification. Reading an article marks it read, as before.

## Directory integration verification — 2026-10-12

- 284 Python and 34 Swift tests passed (318 total). Directory coverage includes query encoding, page cursors, malicious/invalid next links, URL validation, unsupported formats, deduplication, bounded caching, offline/expired results, preserved YAML and the real subscribe dispatch path.
- Live API checks returned 30 initial entries, a matching The Verge result and a technology page. An isolated temporary workspace saved the returned feed, queued sync and fetched/parsed ten real publisher articles. The user's subscription list was not changed.
- Native UI checks covered English/dark and Arabic/light, searching, category selection, local catalog switching and the existing Following state. An accessibility scroll-to-end trap in SwiftUI's lazy rows was found during QA; the directory now uses eager rows. Scrolling to the end and loading the next live page succeeded (30 to 60 entries).
- The development bundle passed code-signature, relocated-runtime and bundled conversation smoke checks.
