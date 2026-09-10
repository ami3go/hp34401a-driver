#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"; [[ -x "$PY" ]] || PY=python3
mkdir -p "$ROOT/results/tests"
cd "$ROOT"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" scripts/validate_ai_contract.py
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" scripts/validate_call_protocol_conformance.py
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m pytest
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" scripts/run_call_protocol_conformance.py
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m robot --outputdir "$ROOT/results/tests" tests/robot
