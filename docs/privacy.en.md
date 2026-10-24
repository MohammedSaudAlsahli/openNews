# Privacy and data

[العربية](privacy.md) · [Documentation](README.en.md)

SQLite, articles, conversations, drafts and preferences live in a local workspace outside the `.app` bundle. See the path in [getting started](SETUP.en.md). Do not upload it to GitHub. Replacing the app does not delete the workspace.

| Feature | Network boundary |
|---|---|
| Saved articles and drafts | Uses existing local data |
| News, original sites and images | Requests the source and necessary services |
| Source/skill discovery | Directory services such as RSS.mobi, skills.sh and GitHub receive the required query |
| Local models | Local Ollama; downloading the runtime/weights needs network access |
| Cloud model accounts | The chosen provider receives the selected request context, under its policies/pricing |
| Releases and diagnostics | GitHub when checking/browsing; review diagnostic reports before sharing |

Connection credentials use private files in the user's workspace. Do not assume separate at-rest encryption or describe cloud requests as local. Disabling Agno telemetry does not imply that the entire app has no network traffic.

Skills import as text instructions; source scripts are not executed and additional permissions are not granted automatically. Importing a Swift workspace copies connection data too; never share that backup.

Use the [security policy](../SECURITY.md) for vulnerabilities or leaks. Reproductions should not contain secrets or real databases.
