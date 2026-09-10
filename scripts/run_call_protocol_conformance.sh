#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
PYTHON_BIN=${PYTHON_BIN:-python}
exec "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_call_protocol_conformance.py" "$@"
