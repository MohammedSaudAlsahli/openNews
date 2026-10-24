> Historical Swift documentation. For the supported Tauri application, start at [the documentation index](../README.md).

# Publishing experimental updates

Use `VERSION` and a strictly increasing numeric `BUILD_VERSION`. Update the engine
package/version and run `uv lock --project engine`. Write `docs/releases/vVERSION.md`,
run tests, review all changes, commit, push main, and verify GitHub CI is green.

Then run on the release Mac:

```sh
uv run --project engine python scripts/publish_release.py
```

Use the project Python (3.12+) rather than macOS system Python, which may be older.

This re-tests, builds, signs the update archive using the existing Sparkle key in
login Keychain, creates an immutable annotated tag, uploads a draft GitHub prerelease,
publishes it, then commits/pushes the appcast **after** assets are available. It stops
if the source is dirty, main is not pushed, a tag exists, or the public key differs.
Do not overwrite old release assets or tags. If interrupted after tagging/upload,
inspect the draft and published feed manually before resuming; the script deliberately
refuses to overwrite an existing tag.

The app reads the HTTPS `appcast.xml` on main. Checks run periodically (one hour)
and on startup according to Sparkle scheduling, with a manual command available.
Users approve installation. Uploading an arbitrary file through GitHub without
updating the signed appcast does not notify installed clients.

The private signing key stays in Keychain account `com.editorialintelligence.studio`.
Back it up through a secure offline procedure; never commit it or print/export it
into logs. `release-config.json` contains only the public key. Future CI publishing
needs a deliberately provisioned signing secret; current CI tests/builds only.

No Apple Developer ID/notarization is configured. Keep releases marked experimental,
Apple Silicon only, and clearly disclose first-launch Gatekeeper restrictions.
Sparkle authenticates update archives with EdDSA; it does not grant Apple notarization.
Application data lives outside the bundle, under Application Support. Preserve the
bundle identifier and data location across versions.
