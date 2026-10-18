# Articles, reading and RSS discovery

OpenStudio has a dedicated Articles destination in the main window. The conversation's news list and citation previews also open articles there. The menu-bar reader uses the same reader and article cards in a compact layout.

## Reading

- Cards present a publisher image when available, the title, a short plain-text excerpt, publisher icon and date. Excerpts come from the feed; they are not presented as AI summaries.
- Reader and Original website are separate tabs. Reader uses native SwiftUI/AppKit text and images. Original website lazily opens the publisher in WKWebView, supports back/forward navigation and keeps its page position when switching tabs. Media is suspended when switching back to the Reader tab. No app bridge or injected scripts are installed. Publisher login/paywall behavior is unchanged.
- The main reading column is centered, with a warm light background and a matching dark appearance. Text direction follows the article content independently of the interface language. Reading options control font size and images.
- Headings, links, lists, blockquotes, inline code, fenced code with indentation and Markdown tables have distinct presentation. The extractor upgrades previously cached reader content once to preserve code and quotes.
- Articles support persistent bookmarks and a Bookmarks view. Opening an article marks it read. Returning to the feed preserves its mounted list and scroll position.
- AI summary explicitly uses the configured Writer model through the existing Agno route and the existing model permission. It produces three short points in the interface language, caches by article content/language/model, and does not create a conversation. Feed-only summaries are identified. It never runs automatically on article opening.
- Images retain proportions and captions. Lazy images, picture/srcset, RSS images and enclosures are supported; Open Graph is a fallback. Image requests use pinned public-network transport without cookies or scripts, validate raster signatures, and downsample before display. The image cache is bounded. Reader extraction errors preserve saved content.
- Site icons are retrieved from each public site's favicon endpoint with the existing public transport, signature/size validation, single-flight requests and bounded caching. Unavailable icons fall back to the site's initial.
- Conversation citations are grouped in an icon pill. Its popover lists each article and opens it inside the app. Inline citation previews remain available.

## Search and discovery

- Article search runs after a 250 ms typing pause and searches titles, publishers, excerpts and saved full text. Quoted phrases stay together; all terms must match. Source, time range, unread/bookmarked state and date ordering are available. Pagination accesses articles beyond the initial snapshot.
- Discover sources connects to the public [RSS.mobi directory](https://rss.mobi/api/v1/feeds). Search runs after a 350 ms typing pause and can be narrowed by category. Language, followed-only and alphabetical filters apply to the loaded results. Results can be followed directly through the existing subscription flow.
- The local catalog tab and explanatory footer were removed. Existing `sources.yml` files and subscriptions are preserved; removing the UI does not delete user data. RSS.mobi is a community directory, not publisher verification.
- Directory cache freshness is one hour, with up to seven-day stale fallback clearly labeled. Caches are bounded. Only search/category/pagination parameters are sent; model keys, writing and subscriptions are not sent to the directory.
- [RSS.mobi API implementation](https://github.com/dstengine/rss-mobi/blob/main/src/pages/api/v1/feeds/index.ts) documents the endpoint parameters. [Directory terms](https://rss.mobi/terms/).

## Other interaction changes

- Enter sends a chat message. Shift+Enter (or Option+Enter) inserts a newline. Active input-method composition is preserved.
- Agent settings use a padded, bounded detail column and labeled controls. The connection menu uses one direction-safe indicator. The confusing Discuss draft action was removed; draft context remains available from the composer's context controls.

## Verification — 2026-10-12

- 291 Python tests and 36 Swift tests passed (327 total). Coverage includes bookmark persistence/workspace isolation, full-text/phrase/filter/pagination search, code and quote extraction, summary permission/model/cache behavior, icon validation, native keyboard routing, tables and variable-length code fences.
- Direct native UI checks covered English/dark and Arabic/light; live source discovery without Return; article cards and hero images; full article code/tables; Reader/Original website switching; persistent bookmarks; grouped citation icons; and feed scroll restoration.
- A real configured Writer produced a three-point article summary. A separate short test conversation verified Enter sends and Shift+Enter adds a newline. No authentication settings or source subscriptions were changed by these tests. The test conversation is retained in local history.
- The compact menu-bar reader shares the verified renderer, supports the same tabs/bookmarks/summary, and compiles in the app. Opening its actual status-bar popover could not be independently automated in this pass; no claim of complete menu-bar UI verification is made.

- Final packaged app passed signature verification, relocated bundled-runtime checks, the four-format Agno smoke test against a mock provider, and DMG checksum verification. Final native checks confirmed hidden reader/feed/web content is absent from the accessibility tree, the Arabic connection menu has a single indicator, and English tables keep their column order in Arabic UI.

## Card and provider polish — 2026-10-13

- Every card reserves the same image area while loading, on failure and when no image exists. A neutral photo placeholder explicitly identifies missing images. Titles and excerpts reserve consistent line heights, and bookmarks are independent controls on the card.
- Card bookmark changes update both the main Articles page and the compact reader immediately, including removing entries from the Bookmarks filter.
- Agent assignment details and the settings sidebar no longer have inset rectangular background blocks. Connection controls, headings and spacing remain native.
- New and existing provider credentials use labeled secure input fields. Provider-specific multi-field credentials and Google service-account JSON remain supported; unrelated saved fields are preserved. Local and Ollama Cloud setup choices remain available.
- Delete connection clears its local credentials and removes it from selectable profiles and automatic refresh. Built-in assignments are cleared; custom agent definitions and conversation history remain, with a removed connection rejected until another is selected. Non-secret registration rows are archived internally to preserve historical references.
- The menu-bar options control suppresses the automatic menu indicator and reserves a 32×28 pt target, preventing the chevron/ellipsis overlap.
- 292 Python and 37 Swift tests passed (329 total). Direct packaged-app checks covered English/dark and Arabic/light card bookmarks, missing-image cards, credential editors, local/cloud switching, and creating/deleting temporary local connections in each language. Temporary bookmarks and connections were removed, and the original English/dark preferences restored.
- Native NSHostingView rendering checked the complete 470×700 compact reader in Arabic and English with both layout directions. Rendered footer icons have no extra chevron or overlap. This verifies the menu content layout; status-bar popover opening remains outside the automated interaction coverage.

## Automatic full-text recovery

The engine drains up to 20 incomplete articles per polling cycle, independently of the feed's refresh interval or HTTP 304 responses. It follows the saved publisher URL, retains full RSS content, and skips already complete articles and media-only descriptions. Direct fetch retries wait 5 minutes, 30 minutes, then 6 hours. Only active subscriptions participate. Per-article locks and conditional writes prevent a late failed fetch from overwriting successfully captured full text.

While the macOS app is running, a cookie-free WebKit pass can try one failed article every 30 seconds, with a 12-second timeout and one persisted attempt per article per 24 hours. This fallback runs only at nominal thermal state and outside Low Power Mode. It accepts article/main content, does not log in or solve access challenges, and saves extracted text through the existing reader capture path. Success notifies the article list immediately. Closing the app cancels the render pass; pending work survives through article state and retry timestamps.

These are recovery attempts, not a guarantee that every publisher permits extraction. Subscriber-only, removed, or blocked articles may remain incomplete. No model call is needed to fetch the article. The UI and model must not describe an excerpt as the full article.
