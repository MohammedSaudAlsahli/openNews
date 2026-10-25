# openNews: repository workflow

- `main` is the official production application. Start feature, fix and UI work on `develop`; do not edit or push production directly. Promote tested `develop` through a pull request into `main`.
- The default local build (`bash scripts/build_app.sh`) and `npm --prefix desktop run app:dev` use **openNews Dev**, identifier `com.opennews.development`. Its workspace, credentials, settings and WebKit storage are separate. Never point it at the official workspace or import production data without explicit user authorization.
- `/Applications/openNews.app` is the sole daily-use installation. Do not replace it with a local development build. Official builds use `bash scripts/build_app.sh --release` on `main`; publish only the verified successful main CI artifact.
- Keep the official identifier `com.editorialintelligence.studio.preview`, updater public key, endpoint and workspace location unchanged for compatibility. Development and QA apps cannot install official updates.
- Only `main` and `develop` are permanent branches. Dependency branches are temporary, target `develop`, require passing tests, and are deleted after merge. Never force an untested dependency/security update into production; repair failed checks first.
- Keep Arabic documentation primary with an English counterpart. Run `bash scripts/test.sh` and relevant native tests. Never commit keys, user databases, model weights, app bundles or personal QA evidence.
