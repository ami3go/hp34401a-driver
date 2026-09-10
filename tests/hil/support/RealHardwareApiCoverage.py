"""Runtime coverage/evidence helper for the real-hardware public-API suite."""

from __future__ import annotations

import csv
import json
import sys
import os
import platform
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from robot.api.deco import keyword, library

_SUPPORT_DIR = Path(__file__).resolve().parent
if str(_SUPPORT_DIR) not in sys.path:
    sys.path.insert(0, str(_SUPPORT_DIR))

from coverage_state import (
    STATE_ENV,
    configured_state_path,
    initialize_state,
    load_results,
    merge_record,
)


@library(scope="SUITE", auto_keywords=False)
class RealHardwareApiCoverage:
    """Observe nested Robot keyword execution and report every driver API status."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_AUTO_KEYWORDS = False
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[3]
        public_api = json.loads((root / "api" / "public_api.yaml").read_text(encoding="utf-8"))
        self._root = root
        self._keywords = {item["name"]: item for item in public_api["keywords"]}
        self._results: dict[str, dict[str, Any]] = {}
        self._output_dir: Path | None = None
        self._profile = "UNKNOWN"
        self._started_utc: str | None = None
        self._state_file: Path | None = None
        self.ROBOT_LIBRARY_LISTENER = self

    @keyword("Normalize Boolean Value")
    def normalize_boolean_value(self, value: Any, name: str = "value") -> bool:
        """Convert Robot CLI/profile Boolean values without Python expression evaluation.

        Robot command-line variables are strings. Values such as ``true`` and
        ``false`` must therefore be normalized before they are used by ``IF`` or
        ``Should Be True``. Invalid values fail closed instead of being treated as
        truthy strings.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in {0, 1}:
            return bool(value)
        normalized = str(value).strip().casefold()
        if normalized in {"true", "yes", "on", "1", "enabled"}:
            return True
        if normalized in {"false", "no", "off", "0", "disabled", "", "none", "null"}:
            return False
        raise AssertionError(
            f"{name} must be a Boolean value (true/false, yes/no, on/off, 1/0); "
            f"received {value!r}"
        )

    @keyword("Start Real Hardware API Coverage")
    def start_real_hardware_api_coverage(self, output_dir: str, profile: str = "FULL_API") -> None:
        self._output_dir = Path(output_dir).resolve()
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._profile = str(profile)
        self._started_utc = datetime.now(timezone.utc).isoformat()
        self._results.clear()
        self._state_file = self._output_dir / ".real_hardware_api_state.json"
        os.environ[STATE_ENV] = str(self._state_file)
        initialize_state(self._state_file)

    def end_keyword(self, data: Any, result: Any) -> None:
        name = str(getattr(result, "name", getattr(data, "name", "")))
        candidate = name
        if candidate not in self._keywords and "." in candidate:
            candidate = candidate.rsplit(".", 1)[-1]
        if candidate not in self._keywords:
            return
        status = str(getattr(result, "status", "UNKNOWN")).upper()
        record = {
            "keyword": candidate,
            "canonical_keyword": self._keywords[candidate]["canonical_name"],
            "status": status,
            "message": str(getattr(result, "message", "")),
            "elapsed_ms": int(getattr(result, "elapsedtime", 0) or 0),
            "device_facing": bool(self._keywords[candidate]["device_facing"]),
            "protocol_vector": self._keywords[candidate].get("protocol_vector"),
            "evidence": "output.xml/log.html/report.html",
        }
        self._results[candidate] = record
        merge_record(self._state_file or configured_state_path(), record)

    @keyword("Record Real Hardware Device Identity")
    def record_real_hardware_device_identity(
        self, identity: str, resource: str, transport: str = "VISA", alias: str = "default"
    ) -> dict[str, Any]:
        """Persist the connected device identity and selected transport resource."""
        if self._output_dir is None:
            raise AssertionError("Start Real Hardware API Coverage was not called")
        raw = str(identity).strip()
        parts = [part.strip() for part in raw.split(",")]
        record = {
            "captured_utc": datetime.now(timezone.utc).isoformat(),
            "raw_identity": raw,
            "manufacturer": parts[0] if len(parts) > 0 else "UNKNOWN",
            "model": parts[1] if len(parts) > 1 else "UNKNOWN",
            "serial_number": parts[2] if len(parts) > 2 else "UNKNOWN",
            "firmware_version": parts[3] if len(parts) > 3 else "UNKNOWN",
            "transport": str(transport),
            "resource": str(resource),
            "alias": str(alias),
        }
        (self._output_dir / "device_identity.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return record

    @keyword("Exclude Real Hardware API Keywords")
    def exclude_real_hardware_api_keywords(self, reason: str, *keyword_names: str) -> None:
        if not str(reason).strip():
            raise AssertionError("An explicit exclusion reason is mandatory")
        for name in keyword_names:
            text = str(name)
            if text not in self._keywords:
                raise AssertionError(f"Cannot exclude unknown public keyword {text!r}")
            if text in self._results and self._results[text].get("status") == "PASS":
                continue
            record = {
                "keyword": text,
                "canonical_keyword": self._keywords[text]["canonical_name"],
                "status": "EXCLUDED",
                "message": str(reason),
                "elapsed_ms": 0,
                "device_facing": bool(self._keywords[text]["device_facing"]),
                "protocol_vector": self._keywords[text].get("protocol_vector"),
                "evidence": "operator-declared HIL prerequisite",
            }
            self._results[text] = record
            merge_record(self._state_file or configured_state_path(), record)

    @keyword("Finalize Real Hardware API Coverage")
    def finalize_real_hardware_api_coverage(self, fail_on_exclusions: bool = False) -> dict[str, Any]:
        if self._output_dir is None:
            raise AssertionError("Start Real Hardware API Coverage was not called")
        persisted = load_results(self._state_file or configured_state_path())
        for name, record in persisted.items():
            self._results[name] = record
        rows: list[dict[str, Any]] = []
        for name in sorted(self._keywords):
            row = self._results.get(name)
            if row is None:
                item = self._keywords[name]
                row = {
                    "keyword": name,
                    "canonical_keyword": item["canonical_name"],
                    "status": "NOT RUN",
                    "message": "No Robot Framework invocation or approved exclusion was recorded",
                    "elapsed_ms": 0,
                    "device_facing": bool(item["device_facing"]),
                    "protocol_vector": item.get("protocol_vector"),
                    "evidence": None,
                }
            rows.append(row)
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        summary = {
            "schema_version": "1.0",
            "driver": "rf_hp34401a",
            "driver_version": "26.07",
            "profile": self._profile,
            "started_utc": self._started_utc,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "keyword_count": len(rows),
            "counts": counts,
            "complete_inventory": counts.get("NOT RUN", 0) == 0,
            "all_executed_passed": counts.get("FAIL", 0) == 0 and counts.get("NOT RUN", 0) == 0,
            "exclusions_present": counts.get("EXCLUDED", 0) > 0,
            "rows": rows,
        }
        (self._output_dir / "real_hardware_api_coverage.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with (self._output_dir / "real_hardware_api_coverage.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["keyword", "canonical_keyword", "status", "device_facing", "protocol_vector", "elapsed_ms", "message", "evidence"])
            writer.writeheader()
            writer.writerows(rows)
        environment = {
            "captured_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "operating_system": platform.platform(),
            "robot_framework_version": self._package_version("robotframework"),
            "driver_distribution_version": self._package_version("rf-hp34401a"),
            "driver_source_version": "26.07",
            "profile": self._profile,
        }
        (self._output_dir / "environment.json").write_text(
            json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        lines = [
            "# HP34401A real-hardware API verification",
            "",
            f"- Public keywords: {len(rows)}",
            f"- PASS: {counts.get('PASS', 0)}",
            f"- FAIL: {counts.get('FAIL', 0)}",
            f"- EXCLUDED: {counts.get('EXCLUDED', 0)}",
            f"- NOT RUN: {counts.get('NOT RUN', 0)}",
            "",
            "EXCLUDED is not hardware proof. A D2/P1 claim requires rerunning with the missing prerequisites and zero exclusions for the claimed scope.",
        ]
        (self._output_dir / "real_hardware_api_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        failures = [row for row in rows if row["status"] in {"FAIL", "NOT RUN"}]
        if fail_on_exclusions:
            failures.extend(row for row in rows if row["status"] == "EXCLUDED")
        compact = {key: value for key, value in summary.items() if key != "rows"}
        compact["fail_on_exclusions"] = bool(fail_on_exclusions)
        compact["acceptance_passed"] = not failures
        compact["failure_count"] = len(failures)
        compact["failure_keywords"] = [
            {"keyword": row["keyword"], "status": row["status"]} for row in failures
        ]
        return compact

    @keyword("Assert Real Hardware API Coverage")
    def assert_real_hardware_api_coverage(
        self, summary: dict[str, Any], fail_on_exclusions: bool = False
    ) -> None:
        """Fail only after the generated summary has been logged and persisted."""
        if not isinstance(summary, dict):
            raise AssertionError("Real-hardware API summary must be a dictionary")
        failures = list(summary.get("failure_keywords", []))
        if not failures and bool(summary.get("acceptance_passed", False)):
            return
        detail = "; ".join(
            f"{item.get('keyword')}={item.get('status')}" for item in failures[:20]
        )
        policy = "zero exclusions required" if fail_on_exclusions else "exclusions permitted"
        raise AssertionError(
            f"Real-hardware API coverage is incomplete ({policy}): {detail or 'unknown failure'}"
        )

    @staticmethod
    def _package_version(name: str) -> str:
        try:
            return version(name)
        except PackageNotFoundError:
            return "NOT_INSTALLED"
