#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"; [[ -x "$PY" ]] || PY=python3
mkdir -p "$ROOT/generated/libdoc"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m robot.libdoc rf_hp34401a.Hp34401ALibrary "$ROOT/generated/libdoc/Hp34401ALibrary.html"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m robot.libdoc -f XML rf_hp34401a.Hp34401ALibrary "$ROOT/generated/libdoc/Hp34401ALibrary.xml"
