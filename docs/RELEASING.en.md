# Publish an official release

[العربية](RELEASING.md) · [Packaging](packaging.en.md)

## Version sources

`desktop/package.json` is primary. Keep its version synchronized with both package roots in `desktop/package-lock.json`, `desktop/src-tauri/tauri.conf.json`, and the application package in `Cargo.toml`/`Cargo.lock`. Root `VERSION`, `BUILD_VERSION` and `appcast.xml` are historical Swift artifacts. The Python engine has an independent internal package version.

## Release gates

1. Update application versions, `CHANGELOG.md` and bilingual `docs/releases/v<version>.md`. Official releases use no preview suffix.
2. Review changes, possible secrets and fixtures. Never publish local QA evidence, databases or keys.
3. Run `bash scripts/test.sh`, build the application and run Cargo tests. Push to `main` and require **openNews tests and Tauri bundle** to pass for that exact SHA.
4. Push an annotated `v<version>` tag at that SHA. Never move published tags or replace existing release assets.
5. Dispatch **Publish official Tauri release** with the tag and successful CI run ID. It validates SHA, event, branch and workflow identity, downloads that exact artifact, checks hashes and publishes an official release with `prerelease=false`.
6. Verify the release, tag and assets. Download the ZIP and check SHA-256. `build-info.json` records app version, SHA, CI URL, architecture and signing limitations.

Example from the repository root after successful CI:

```sh
git tag -a v0.3.0 -m 'openNews 0.3.0'
git push origin v0.3.0
gh workflow run release.yml -f tag=v0.3.0 -f run_id=CI_RUN_ID
```

Use the green CI artifact, not the installed user app. SHA-256 checks integrity; it is not independent publisher authentication. Current CI does not access user accounts or run a live model.

## Signed update channel

A ZIP release alone does not update installed clients. After publishing the successful official build, prepare an updater archive from that exact release using the original owner key outside the repository:

```sh
engine/.venv/bin/python desktop/scripts/package-update.py --version 0.3.0
engine/.venv/bin/python desktop/scripts/test-update.py --prepared build/updater/v0.3.0
```

The QA tool requires matching test-enabled Rust dependencies; run the native Cargo tests first on a new build machine. It upgrades two real bundles in temporary storage, rejects tampering and signed-version mismatch, then reopens the new packaged engine to verify synthetic persisted data.

After success, append `.app.tar.gz`, `.sig`, `updater-SHA256SUMS`, build metadata and validation evidence to the same GitHub release without replacing published assets. Then copy the generated `tauri-preview.json` to `updates/tauri-preview.json` and push `main`. **Publish assets before promoting the feed.** Verify afterward:

```sh
engine/.venv/bin/python desktop/scripts/test-update.py --prepared build/updater/v0.3.0 --public
```

The 0.3.0 channel is active. The historical filename, data identifier and key stay for installed-client compatibility; `preview` in these technical names does not classify the official release as experimental. The real 0.3.0-preview.1 to 0.3.0 upgrade is tested, including article, conversation, draft, settings and external credential/model sentinels. Never expose the private key in GitHub/CI/logs or replace it. No delta-download claim is made.

Tauri update authentication is independent of Apple notarization. Leave the separate Swift appcast unchanged. The [historical Swift procedure](legacy/RELEASING.md) is not the current release path.
