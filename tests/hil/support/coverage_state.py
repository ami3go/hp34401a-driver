"""File-backed state shared by the HIL library and Robot listener."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

STATE_ENV = "RF_HP34401A_HIL_COVERAGE_STATE"
_STATUS_PRIORITY = {
    "NOT RUN": 0,
    "SKIP": 1,
    "EXCLUDED": 2,
    "PASS": 3,
    "FAIL": 4,
}


def configured_state_path(default: Path | None = None) -> Path | None:
    raw = os.environ.get(STATE_ENV, "").strip()
    if raw:
        return Path(raw).resolve()
    return default.resolve() if default is not None else None


def initialize_state(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path, {"schema_version": "1.0", "results": {}})


def load_results(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    results = payload.get("results", {}) if isinstance(payload, dict) else {}
    if not isinstance(results, dict):
        return {}
    return {
        str(name): dict(record)
        for name, record in results.items()
        if isinstance(record, dict)
    }


def merge_record(path: Path | None, record: dict[str, Any]) -> None:
    if path is None:
        return
    results = load_results(path)
    name = str(record["keyword"])
    previous = results.get(name)
    if previous is None or _should_replace(previous, record):
        results[name] = dict(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path, {"schema_version": "1.0", "results": results})


def _should_replace(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    old_status = str(previous.get("status", "NOT RUN")).upper()
    new_status = str(current.get("status", "NOT RUN")).upper()
    return _STATUS_PRIORITY.get(new_status, 0) >= _STATUS_PRIORITY.get(old_status, 0)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
