# OpenStudio mark

A single open rounded loop. The opening suggests an open workspace; its silhouette
remains legible in the sidebar and menu bar. No lettering, sparkle or gradients.

- Application tile: warm white `#F4F1EB`, ink `#202321`.
- Interface mark: `currentColor`, adapts to the existing light/dark themes.
- Menu bar: transparent black template, tinted by macOS.
- Keep the opening and generous clear space; do not add detail at small sizes.

Sources: `app-icon.svg`, `mark.svg`. The React `BrandMark` uses the same path.
Generate platform assets with the existing Tauri CLI (run from `desktop`):

```
npm run tauri -- icon brand/app-icon.svg -o /tmp/openstudio-icon-generated
npm run tauri -- icon brand/mark.svg -p 32 -o /tmp/openstudio-mark
```

Copy `icon.png`, `icon.icns` into `src-tauri/icons`; copy `32x32.png` as `tray.png`.
The native app's original assets remain separate while Tauri is a preview.
