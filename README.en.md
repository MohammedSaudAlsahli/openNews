# openNews

**Your news, sources and writing assistant, together on your Mac.**

[العربية — التوثيق الرئيسي](README.md) · [Getting started](docs/SETUP.en.md) · [Documentation](docs/README.en.md) · [Download the latest release](https://github.com/MohammedSaudAlsahli/openNews/releases/latest)

[![Checks and bundle](https://github.com/MohammedSaudAlsahli/openNews/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MohammedSaudAlsahli/openNews/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/MohammedSaudAlsahli/openNews)](https://github.com/MohammedSaudAlsahli/openNews/releases/latest)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

openNews is a macOS application for collecting, reading and discussing news and turning ideas into editable drafts. It supports Arabic and English, local models through Ollama, and cloud accounts you choose to connect.

**Tauri is the sole official, supported openNews application; `main` is its primary branch.** React renders the interface, Rust provides the native bridge, and an embedded Python engine uses SQLite. End users do not need Python or Node installed. The former SwiftUI application is retained only as an archive on [swift-legacy](https://github.com/MohammedSaudAlsahli/openNews/tree/swift-legacy), with no parallel supported app releases.

## What you can do

- **Read your sources:** RSS, Atom, Reddit and public websites, with an archive, an internal reader and article revision history.
- **Discuss and write:** news-linked conversations, `@` references, `/` skill commands and drafts with saved versions.
- **Search saved articles:** keyword search plus optional semantic search using a local embedding model.
- **Manage local models together:** one Ollama library shows downloaded models and their capabilities; choose search and explanation models according to their roles.
- **Customize the assistant:** editable instructions, writing examples and skills; discover skills through skills.sh and preview their original GitHub instructions before importing.
- **Control background work:** performance, battery and schedule settings, with visible download, indexing and daily-report states.

Skill imports add text instructions only; they do not install or run skill scripts. Semantic search and explanation are different tasks even when both use Ollama.

## Install

1. Download `openNews-<version>-macOS-arm64.dmg` from [official releases](https://github.com/MohammedSaudAlsahli/openNews/releases/latest).
2. Open the DMG, drag **openNews** to **Applications**, then launch it from Applications.
3. Add a source and start reading. Connecting an account or downloading a model is optional.

The current distribution targets **Apple Silicon**, with a declared minimum of **macOS 14**. It is ad-hoc signed and is **not Apple-notarized**; see [installation help](docs/SETUP.en.md) if Gatekeeper blocks it. This release does not include Intel, Windows or Linux builds.

## Data and connections

Articles, conversations and drafts are stored in a local workspace. A cloud account sends the required context to its provider. Fetching news and directories or downloading models needs internet access. Local storage does not make every feature offline. See [privacy](docs/privacy.en.md).

The data identifier remains `com.editorialintelligence.studio.preview` for compatibility. The historical word `preview` in this path does not describe the release status. Do not delete the workspace during an upgrade.

## Develop

Requirements: macOS, Xcode Command Line Tools, Node.js 22, stable Rust, and uv with CPython 3.12.13.

```sh
git clone https://github.com/MohammedSaudAlsahli/openNews.git
cd openNews
bash scripts/test.sh
bash scripts/build_app.sh
cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml
```

Output: `desktop/src-tauri/target/release/bundle/macos/openNews.app`. After staging the engine, launch development with `npm --prefix desktop run tauri -- dev`.

Read the [contribution guide](CONTRIBUTING.en.md), [architecture](docs/architecture.en.md) and [release process](docs/RELEASING.en.md). npm, Cargo and uv dependencies are locked. CI tests the engine, frontend and native bridge and builds the application.

## Scope and limitations

Review generated content yourself; a citation does not prove a claim is correct. The app does not publish content on your behalf. Some websites refuse public retrieval. Model speed, memory and heat depend on hardware and content; there is no general zero-heat or benchmark claim. Signed updates are available in app settings: check for an update, then choose Install and restart. Manual downloads from GitHub Releases remain available.

## Participate and license

[Report a bug or request a feature](https://github.com/MohammedSaudAlsahli/openNews/issues/new/choose) · [Private security reporting](SECURITY.md) · [Changelog](CHANGELOG.md)

Project code is [MIT-licensed](LICENSE). Dependencies, models and external content retain their separate terms; see [third-party notices](THIRD_PARTY_NOTICES.md). MIT permits commercial use, redistribution and sale with the required notices retained.
