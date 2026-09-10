"""Frozen data models for identities, readings, errors and results (spec section 19)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from .enums import InputTerminal, MeasurementFunction, TransportType


@dataclass(frozen=True, slots=True)
class Identity:
    manufacturer: str
    model: str
    serial: str | None
    firmware: str | None
    raw: str


@dataclass(frozen=True, slots=True)
class SelfTestResult:
    passed: bool
    code: int
    raw: str
    message: str = ""


@dataclass(frozen=True, slots=True)
class ErrorRecord:
    code: int
    message: str
    raw: str

    @property
    def is_no_error(self) -> bool:
        return self.code == 0


@dataclass(frozen=True, slots=True)
class MeasurementReading:
    timestamp_utc: datetime
    monotonic_s: float
    function: MeasurementFunction
    value: float | None
    unit: str
    raw: str
    range_value: float | None = None
    nplc: float | None = None
    aperture_s: float | None = None
    is_overload: bool = False
    is_valid: bool = True
    was_retried: bool = False
    retry_count: int = 0
    reconnect_count: int = 0
    recovery_actions: tuple[str, ...] = ()
    terminal: InputTerminal | None = None
    transport: TransportType | None = None


@dataclass(frozen=True, slots=True)
class HealthReport:
    connected: bool
    identity: Identity | None
    error_queue_clean: bool
    pending_errors: tuple[ErrorRecord, ...]
    state: str
    timestamp_utc: datetime
    message: str = ""


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    succeeded: bool
    actions: tuple[str, ...]
    final_state: str
    message: str = ""


@dataclass(frozen=True, slots=True)
class StableMeasurementResult:
    stable: bool
    value: float | None
    unit: str
    samples: tuple[float, ...]
    stdev: float | None
    relative_stdev: float | None
    slope_relative_per_s: float | None
    elapsed_s: float
    reason: str
    reading: MeasurementReading | None = None


@dataclass(frozen=True, slots=True)
class TestStepResult:
    dut_id: str
    station_id: str
    step_name: str
    started_utc: datetime
    finished_utc: datetime
    reading: MeasurementReading | None
    pass_fail: Literal["PASS", "FAIL", "ERROR", "SKIPPED"]
    lower_limit: float | None
    upper_limit: float | None
    error: str | None
    retry_count: int
    reconnect_count: int


@dataclass(frozen=True, slots=True)
class TestSequenceResult:
    dut_id: str
    station_id: str
    started_utc: datetime
    finished_utc: datetime
    step_results: tuple[TestStepResult, ...]

    @property
    def pass_fail(self) -> Literal["PASS", "FAIL", "ERROR"]:
        if any(r.pass_fail == "ERROR" for r in self.step_results):
            return "ERROR"
        if any(r.pass_fail == "FAIL" for r in self.step_results):
            return "FAIL"
        return "PASS"


@dataclass(frozen=True, slots=True)
class InstrumentMetadata:
    identity: Identity
    scpi_version: str | None
    calibration_due_date: date | None
    station_id: str
    station_software_version: str
    git_commit: str | None = None
    operator_id: str | None = None
