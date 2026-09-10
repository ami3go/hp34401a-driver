#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"; [[ -x "$PY" ]] || PY=python3
if [[ $# -lt 1 ]]; then echo "Usage: $0 <example.robot> [robot arguments...]"; exit 2; fi
EXAMPLE="$1"; shift
[[ "$EXAMPLE" = /* ]] || EXAMPLE="$ROOT/examples/$EXAMPLE"
mkdir -p "$ROOT/results"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m robot --outputdir "$ROOT/results" "$@" "$EXAMPLE"
