# openNews identity and issue reporting

Display name and newspaper icon now use openNews. The bundle identifier, existing workspace and updater repository remain unchanged, preserving local data. The GitHub repository is still openStudio.

Help & diagnostics opens a reviewable GitHub issue draft containing version, platform, bounded technical events and the selected error code. The error banner has a Report problem action. Raw error messages, conversation contents, articles, paths and credentials are not added. User submits the issue on GitHub (sign-in may be required). Only the last 4,500 diagnostic characters are included in the URL; full diagnostics can be exported separately.

A session-active marker is written on startup and removed on normal Tauri Exit. If it remains, the next launch offers to report UNEXPECTED_EXIT. This indicates an interrupted session (including force quit or power loss), not proof of a native crash. Native stack traces/macOS crash dumps are not collected. Closing the window to the tray does not end the session. The first upgraded launch cannot detect exits of versions which did not write a marker.

Validation: 28 frontend tests passed; production Tauri bundle built and codesign verified. Existing runtime is preserved when replacing the local application.

## Article reading reports and opening latency

The reader navigates immediately using the clicked card, then reads local article data. Full cached text does not trigger a blocking publisher refresh; explicit Refresh still does. Related stories load independently. Incomplete articles continue text fetching and rendered-site recovery with visible stages.

Report this article is available even while loading. The user reviews an optional context section (title, source, article ID, sanitized public URL, body status, stage, elapsed milliseconds and safe error code). Credentials, query parameters and URL fragments are removed. Article context stays in component memory and is transmitted only when the user opens the reviewed GitHub draft. No issue is submitted automatically.

Regression validation: 31 frontend tests pass, including navigation before an unresolved IPC request, immediate cached body display without network recovery, and removal of URL secrets from issue context.

## Publication times and feed refresh

Article cards and reader headers show relative publication times, recalculated each minute while visible. Hover exposes full local date/time. Missing dates are labeled unavailable; future publisher dates are not falsely shown as past.

The visible article list checks local storage every minute and upon returning to the app, retaining filters and loaded page count. This does not change publisher fetch schedules: existing per-source intervals apply while the app is running. Feed polling checks due sources between sync passes; network/body extraction work may delay later checks. Regression suite: 34 frontend tests passed.

## Configurable refresh intervals

New sources default to 5 minutes, including discovered websites without RSS. The backend accepts whole minutes from 1 to 10080. Each source exposes a preset dropdown (1, 5, 15, 30 minutes; 1, 3, 6, 12 hours; 1 day), saved immediately on selection. Previously saved custom intervals remain visible. Failed saves restore the prior selection. Website discovery no longer overwrites a user-selected interval with 360 minutes. Existing installations retain saved choices; on this local installation the 15 active sources with former default 60/360-minute intervals were changed to 5 after a database backup.

Existing single sync lock, conditional feed requests and cached article bodies remain in use. The interval is a polling target while the application is running, not a strict delivery deadline; publisher delays, slow requests, sleep and source failures can postpone retrieval. Tests: 36 frontend and 42 news/page-feed backend passed.
