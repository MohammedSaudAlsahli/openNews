#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p build
uv sync --project engine --frozen
PYTHONPATH="$ROOT/engine" engine/.venv/bin/python scripts/generate_catalog.py
uv export --project engine --frozen --no-dev --no-emit-project --format requirements-txt --output-file build/requirements.lock >/dev/null
engine/.venv/bin/python desktop/scripts/stage-runtime.py
npm --prefix desktop ci
npm --prefix desktop run tauri -- build --bundles app
# Seal the complete app after Tauri has assembled its embedded resources.
# The arm64 executable's linker signature alone does not seal an app bundle.
APP="$ROOT/desktop/src-tauri/target/release/bundle/macos/openNews.app"
codesign --force --sign - "$APP"
codesign --verify --deep --strict "$APP"
