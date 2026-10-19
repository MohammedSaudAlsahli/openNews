#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
uv sync --project engine --frozen
engine/.venv/bin/python -m pytest engine/tests -q
npm --prefix desktop ci
npm --prefix desktop test
npm --prefix desktop run build
