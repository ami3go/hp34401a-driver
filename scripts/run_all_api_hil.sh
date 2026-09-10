#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 VISA_RESOURCE [additional robot arguments]" >&2
  exit 2
fi
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RESOURCE=$1
shift
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$ROOT/results/real_hardware_all_api/rf_hp34401a/$STAMP"
LISTENER="$ROOT/tests/hil/support/RealHardwareApiListener.py"
mkdir -p "$OUT"
RF_HP34401A_HIL_COVERAGE_STATE="$OUT/.real_hardware_api_state.json" \
robot --listener "$LISTENER" \
  --outputdir "$OUT" \
  --variable HIL_ENABLED:True \
  --variable "VISA_RESOURCE:$RESOURCE" \
  "$@" \
  "$ROOT/tests/hil/verify_all_public_api_real_hardware.robot"
