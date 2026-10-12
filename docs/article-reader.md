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

The current local source catalog remains hand-curated and editable as YAML; this change does not connect a new external directory.

- [Feedly Discover documentation](https://docs.feedly.com/article/287-how-to-find-and-add-follow-sources): search and follow sources using Feedly's discovery interface.
- [RSS.mobi](https://rss.mobi/): browsable RSS directory with feed addresses and links to readers.
- [Inoreader source types](https://www.inoreader.com/help/basic/feeds-sources/what-types-of-sources-can-i-follow): feed discovery and subscription options.

A future directory integration should use a documented API or licensed catalog, record its provenance and validate individual feeds. Directory browsing access alone does not establish redistribution rights.

## Verification — 2026-10-12

- 273 Python tests and 34 Swift tests passed (307 total), including ordered images/captions, image allowlists, cached access, old-article backfill, offline preservation, malformed image rejection and native downsampling.
- Development app bundle passed signature verification, relocated runtime smoke and the existing four-format Agno conversation smoke against a mock provider.
- A real subscribed The Verge article extracted five photos and the author. All five images were fetched and rendered. Image enlargement and Arabic/light plus English/dark reader layouts were checked in the native app. The final build was also opened on another article with previously uncached images.
- Workspace reader received direct native UI verification. The compact menu-bar surface shares its renderer and builds successfully, but its menu-bar opening could not be independently automated in this pass.
- No new model requests or subscription changes were made during reader verification. Reading an article marks it read, as before.
