# Contributing to openNews

[العربية](CONTRIBUTING.md) · [Documentation](docs/README.en.md)

Contributions in Arabic and English are welcome. Describe the problem in an issue and discuss substantial changes before implementation. Small fixes can be submitted directly as pull requests. Follow the [community rules](CODE_OF_CONDUCT.md); report vulnerabilities through the [private channel](SECURITY.md).

## Development

Use macOS, Xcode Command Line Tools, Node.js 22, stable Rust and uv. `uv sync --project engine --frozen` prepares CPython 3.12.13 according to the lock. No SwiftUI application build is needed. After cloning:

```sh
git switch develop
bash scripts/test.sh
bash scripts/build_app.sh
cargo test --locked --manifest-path desktop/src-tauri/Cargo.toml
npm --prefix desktop run app:dev
```

The frontend lives in `desktop/src`, the native bridge in `desktop/src-tauri/src`, the engine in `engine/eis_engine`, and small macOS services in `desktop/native`. See [architecture](docs/architecture.en.md).

## Verification

Run the commands above. Add tests for changed behavior or contracts; simple copy/documentation edits need no ceremonial tests. For UI work inspect Arabic/English, RTL/LTR, both themes, keyboard navigation, focus and loading/error/empty states. Use the [isolated native QA workspace](desktop/qa/README.md) for actual Tauri flows; browser mocks do not establish bridge persistence.

Never test destructive changes on user data. Do not commit keys, databases, real conversation screenshots or backups. Use clearly synthetic fixtures.

## Pull requests

Keep scope focused. Explain the problem, resulting behavior, verification and limits. Update primary Arabic documentation and its English equivalent when changing documented behavior. Preserve lockfiles and leave version bumps to the [release process](docs/RELEASING.en.md).

Submitting a contribution means you have the right to provide it and agree to license it under [MIT](LICENSE). News sources and model licenses do not automatically become project property.

## Official and development applications

| Use | Branch | Application | Data and updates |
|---|---|---|---|
| Daily use | `main` | **openNews** | Existing workspace and official updates |
| Feature development | `develop` | **openNews Dev** | Separate workspace; official updates disabled |

Start changes on `develop`. `bash scripts/build_app.sh` defaults to development; `npm --prefix desktop run app:dev` launches interactive development. Official builds require `bash scripts/build_app.sh --release` on `main`, and publication uses only a successful main CI artifact. Never install development over the daily app.

Grouped security updates use temporary branches into `develop`; routine non-security version upgrades do not create automatic branches. GitHub security PRs initially targeting `main` are automatically retargeted to `develop`, tested and merged only after required checks pass; merged branches are deleted. Failed checks must be repaired, never bypassed. Promotion into `main` and official publication remain separate. Only `main` and `develop` are permanent branches.
