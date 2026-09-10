#!/usr/bin/env python3
"""Regression check for file-backed real-hardware API evidence state."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "tests" / "hil" / "support"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    state_module = _load("coverage_state", SUPPORT / "coverage_state.py")
    import sys
    sys.modules["coverage_state"] = state_module
    listener = _load("RealHardwareApiListener", SUPPORT / "RealHardwareApiListener.py")

    public_api = json.loads((ROOT / "api" / "public_api.yaml").read_text(encoding="utf-8"))
    names = [str(item["name"]) for item in public_api["keywords"]]
    with tempfile.TemporaryDirectory(prefix="rf_hp34401a_hil_state_") as temp:
        state_path = Path(temp) / "state.json"
        os.environ[state_module.STATE_ENV] = str(state_path)
        state_module.initialize_state(state_path)
        for name in names:
            item = next(item for item in public_api["keywords"] if item["name"] == name)
            state_module.merge_record(
                state_path,
                {
                    "keyword": name,
                    "canonical_keyword": item["canonical_name"],
                    "status": "EXCLUDED",
                    "message": "regression fixture",
                    "elapsed_ms": 0,
                    "device_facing": bool(item["device_facing"]),
                    "protocol_vector": item.get("protocol_vector"),
                    "evidence": "regression",
                },
            )
        result = SimpleNamespace(name="Connect", status="PASS", message="", elapsedtime=1)
        listener.end_keyword(result, result)
        results = state_module.load_results(state_path)
        if len(results) != len(names):
            raise SystemExit(f"Expected {len(names)} records, got {len(results)}")
        if results["Connect"]["status"] != "PASS":
            raise SystemExit("Listener PASS did not override the prior EXCLUDED record")
        not_run = [name for name in names if name not in results]
        if not_run:
            raise SystemExit(f"Unexpected NOT RUN records: {not_run}")
    print(f"HIL coverage-state validation PASSED: {len(names)}/{len(names)} records persisted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
