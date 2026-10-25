#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CHANNEL="${1:---development}"
TAURI_CONFIG=()
case "$CHANNEL" in
  --development)
    TAURI_CONFIG=(--config src-tauri/tauri.dev.conf.json)
    APP_NAME="openNews Dev"
    ;;
  --release)
    if [[ "$(git branch --show-current)" != main && "${GITHUB_ACTIONS:-}" != true ]]; then
      echo 'Official builds require main. Use the default development build.' >&2
      exit 1
    fi
    if [[ "${GITHUB_ACTIONS:-}" == true && "${GITHUB_REF:-}" != refs/heads/main ]]; then
      echo 'Official CI bundles require main.' >&2
      exit 1
    fi
    APP_NAME="openNews"
    ;;
  *) echo 'Usage: bash scripts/build_app.sh [--development|--release]' >&2; exit 1 ;;
esac
mkdir -p build
uv sync --project engine --frozen
PYTHONPATH="$ROOT/engine" engine/.venv/bin/python scripts/generate_catalog.py
uv export --project engine --frozen --no-dev --no-emit-project --format requirements-txt --output-file build/requirements.lock >/dev/null
engine/.venv/bin/python desktop/scripts/stage-runtime.py
npm --prefix desktop ci
npm --prefix desktop run tauri -- build --bundles app "${TAURI_CONFIG[@]}"
# Seal the complete app after Tauri has assembled its embedded resources.
# The arm64 executable's linker signature alone does not seal an app bundle.
APP="$ROOT/desktop/src-tauri/target/release/bundle/macos/$APP_NAME.app"
codesign --force --sign - "$APP"
codesign --verify --deep --strict "$APP"
