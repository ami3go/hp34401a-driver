"""Production logging: CSV measurements, JSONL events (spec section 25).

Resume-safe append logging with header creation, per-row flush, and optional
fsync for high-integrity stations.  Uses the stdlib only.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .measurement import MeasurementReading, TestStepResult

_log = logging.getLogger("hp34401a_dmm.production")

CSV_COLUMNS = [
    "timestamp_utc", "monotonic_s", "station_id", "dut_id", "step_name",
    "transport_type", "resource", "instrument_idn", "instrument_serial",
    "software_version", "git_commit", "function", "value", "unit", "is_valid",
    "is_overload", "was_retried", "retry_count", "reconnect_count",
    "range_value", "nplc", "aperture_s", "terminal", "raw_response",
    "pass_fail", "lower_limit", "upper_limit", "error_code", "error_message",
]


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return str(obj)


class CsvMeasurementLog:
    """Append-mode CSV log with a fixed column set."""

    def __init__(self, path: str | Path, *, fsync: bool = False) -> None:
        self.path = Path(path)
        self.fsync = fsync
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_header_if_needed()

    def _write_header_if_needed(self) -> None:
        if self.path.exists() and self.path.stat().st_size > 0:
            return
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(CSV_COLUMNS)
            fh.flush()
            if self.fsync:
                os.fsync(fh.fileno())

    def write_row(self, row: dict[str, Any]) -> None:
        ordered = [_cell(row.get(col)) for col in CSV_COLUMNS]
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(ordered)
            fh.flush()  # flush every row by default for production
            if self.fsync:
                os.fsync(fh.fileno())


class JsonlEventLog:
    """Append-mode JSON-lines structured event/error log."""

    def __init__(self, path: str | Path, *, fsync: bool = False) -> None:
        self.path = Path(path)
        self.fsync = fsync
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, default=_json_default)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            if self.fsync:
                os.fsync(fh.fileno())


def _cell(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def reading_to_csv_row(
    reading: MeasurementReading,
    *,
    station_id: str = "",
    dut_id: str = "",
    step_name: str = "",
    resource: str = "",
    instrument_idn: str = "",
    instrument_serial: str = "",
    software_version: str = "",
    git_commit: str = "",
    pass_fail: str = "",
    lower_limit: float | None = None,
    upper_limit: float | None = None,
    error_code: int | None = None,
    error_message: str = "",
) -> dict[str, Any]:
    return {
        "timestamp_utc": reading.timestamp_utc,
        "monotonic_s": reading.monotonic_s,
        "station_id": station_id,
        "dut_id": dut_id,
        "step_name": step_name,
        "transport_type": reading.transport.value if reading.transport else "",
        "resource": resource,
        "instrument_idn": instrument_idn,
        "instrument_serial": instrument_serial,
        "software_version": software_version,
        "git_commit": git_commit,
        "function": reading.function.value,
        "value": reading.value,
        "unit": reading.unit,
        "is_valid": reading.is_valid,
        "is_overload": reading.is_overload,
        "was_retried": reading.was_retried,
        "retry_count": reading.retry_count,
        "reconnect_count": reading.reconnect_count,
        "range_value": reading.range_value,
        "nplc": reading.nplc,
        "aperture_s": reading.aperture_s,
        "terminal": reading.terminal.value if reading.terminal else "",
        "raw_response": reading.raw,
        "pass_fail": pass_fail,
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "error_code": error_code,
        "error_message": error_message,
    }
