# Article images and cache audit — 2026-10-18

Scope: local workspace, 15 active sources and 953 archived articles. One available image per source was sampled; this is not a verification of every remote image.

## Changes

- Explicit RSS image enclosures/media take precedence over inline newsletter banners.
- Website Open Graph / Twitter covers take precedence over inline images. Images remain optional.
- Image-only hyperlinks are unwrapped before Markdown splitting.
- WordPress emoji and marked avatar/icon images are excluded from article images.
- Responsive image URLs retain CDN transformation commas.
- Disk-cache hits bypass network concurrency slots. A bounded pool of locks prevents simultaneous downloads of the same image.
- Card images decode to at most 800 pixels, site icons to 64, reader images retain 2048 pixels. Decoding stays off the main actor.
- Reader format version 3 upgrades previously extracted content on opening. Manual feed refresh reprocesses unchanged feeds; background polling retains conditional requests.

## Measurements

Local engine timings, not full rendered UI latency:

- Article list median over 15 runs: 14.92 ms.
- Sampled cached image requests: 0.09–0.46 ms.
- Successful uncached image requests: approximately 0.33–2.93 seconds, dependent on publisher/network.
- MarkTechPost article re-extraction: 2.944 seconds; subsequent saved reader request: 0.028 ms. Correct editorial cover recovered instead of navigation emoji.
- Image sampling: 14 sources succeeded, one Reddit preview failed. Remote availability cannot be guaranteed.

## Persistence and bounds

Articles remain in workspace SQLite. Image files are atomically written to the existing local image cache, capped at 100 MiB with oldest-access eviction. Evicted images may download again; article text is retained. Tests cover concurrent requests, no-network disk reuse after a new manager instance, rejected non-image payloads, image allowlisting, and preserved read/bookmark state.

Validation: 381 Python tests and 53 Swift tests passed; release Swift build and installed ad-hoc signature verification passed. No GitHub release published by this change.
