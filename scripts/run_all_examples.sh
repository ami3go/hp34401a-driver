#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"; [[ -x "$PY" ]] || PY=python3
mkdir -p "$ROOT/results/examples"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m robot --exclude hardware --outputdir "$ROOT/results/examples" "$ROOT/examples"
