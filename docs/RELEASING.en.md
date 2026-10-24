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

## Automatic updates and Swift history

GitHub publication is separate from the signed Tauri update channel. `desktop/scripts/package-update.py` creates a signed update locally using a private key outside the repository; it does not publish. Do not replace an existing channel key or expose it in CI/logs. A real two-version upgrade preserving data must pass before publishing its feed. The channel has not been activated; no delta-update claim is made. Leave the Swift appcast unchanged.

The [historical Swift procedure](legacy/RELEASING.md) is not the current release path.
