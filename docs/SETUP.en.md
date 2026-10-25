# Install and get started

[العربية](SETUP.md) · [Documentation](README.en.md)

## Install

Download the Apple Silicon ZIP from the [latest release](https://github.com/MohammedSaudAlsahli/openNews/releases/latest), unzip it and move `openNews.app` to Applications. The declared minimum is macOS 14; this does not claim testing on every macOS version. Python and Node are not needed, and no AI model is bundled.

The current package is ad-hoc signed, not Apple-notarized. Verify the repository, release and supplied SHA-256 checksum. If you choose to trust the app and macOS blocks it, follow [Apple's instructions for apps from unidentified developers](https://support.apple.com/en-us/102445). Do not disable system protections. A checksum verifies matching published bytes; it does not replace Apple notarization.

## First use

1. Choose Arabic or English and your preferred appearance.
2. Open Sources, add an RSS feed or a supported public website, and check retrieval status.
3. Read an article or attach it to a conversation. Reading and keyword search do not need a model.
4. When needed, connect an account in AI model settings or select a local Ollama model. Review shared context and your provider's costs.
5. Use `/` for skills and `@` for references. Generated content remains a draft for your review.

## Models and skills

Model settings present a shared Ollama library and downloaded inventory. Capability labels determine whether a model can embed search content or generate explanations; being in Ollama does not make every model suitable for every task. Changing the embedding model rebuilds the semantic index without deleting articles.

Assistant & writing lets you edit instructions and discover skills. Review the source and text before adding a skill. Imports use instructions only and never execute repository scripts. A skill may require unavailable tools, so import does not guarantee its complete functionality.

## Upgrade or migrate from Swift

Open Privacy & updates, choose Check for updates, then Install and restart. The app verifies the archive signature and signed version before replacement; data remains outside the application bundle. For manual installation, quit openNews and replace the app in Applications using [GitHub Releases](https://github.com/MohammedSaudAlsahli/openNews/releases/latest). Keep the data directory.

For the former Swift app, quit it before importing the original workspace from privacy settings. Import copies data into Tauri and backs up the current Tauri workspace; the original stays intact. Automatic tasks in the imported copy stay paused until enabled. Verify the result before removing an older installation.

The compatibility path is `~/Library/Application Support/com.editorialintelligence.studio.preview/default/`. This historical identifier is retained for data compatibility.

## Troubleshooting

- **No articles:** inspect source status, internet access and the feed URL. The site may refuse public retrieval.
- **Missing model:** refresh Ollama inventory and inspect its service state and capabilities; retry in the same page.
- **Indexing waits:** read the reason, such as battery, memory pressure or schedule. Keyword search stays available.
- **Internal update check fails:** check connectivity and retry. If it persists, use the official GitHub download. A failed connection does not prove you are up to date.
- **Need help:** open Help & diagnostics and review the report before sharing it. Remove keys, private content and personal paths.
