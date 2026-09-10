"""Production test-line layer: steps, limits, pass/fail results (spec sections 8, 19)."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Callable

from .driver import Hp34401A
from .enums import AutoRange, InputTerminal, MeasurementFunction, Nplc
from .errors import Hp34401AError
from .measurement import MeasurementReading, TestStepResult, TestSequenceResult


@dataclass(frozen=True, slots=True)
class TestStep:
    name: str
    function: MeasurementFunction
    range_value: float | AutoRange = AutoRange.AUTO
    nplc: Nplc = Nplc.PLC10
    lower_limit: float | None = None
    upper_limit: float | None = None
    required_terminal: InputTerminal | None = None


@dataclass(frozen=True, slots=True)
class TestSequence:
    name: str
    steps: tuple[TestStep, ...]


def check_limits(
    value: float | None, lower: float | None, upper: float | None
) -> str:
    """Return PASS/FAIL for a numeric value against optional limits."""
    if value is None:
        return "FAIL"
    if lower is not None and value < lower:
        return "FAIL"
    if upper is not None and value > upper:
        return "FAIL"
    return "PASS"


_CONFIGURE_DISPATCH: dict[MeasurementFunction, str] = {
    MeasurementFunction.VOLT_DC: "measure_dc_voltage",
    MeasurementFunction.VOLT_AC: "measure_ac_voltage",
    MeasurementFunction.CURR_DC: "measure_dc_current",
    MeasurementFunction.RES_2W: "measure_2wire_resistance",
    MeasurementFunction.RES_4W: "measure_4wire_resistance",
}


def run_measurement_step(
    driver: Hp34401A, step: TestStep, dut_id: str, station_id: str
) -> TestStepResult:
    """Execute one step with limit checking and safe failure (spec section 4/18/23)."""
    started = _dt.datetime.now(_dt.timezone.utc)
    reading: MeasurementReading | None = None
    error: str | None = None
    pass_fail = "ERROR"

    try:
        if step.required_terminal is not None:
            driver.require_terminal(step.required_terminal)  # fails safely on mismatch

        method_name = _CONFIGURE_DISPATCH.get(step.function)
        if method_name is None:
            raise Hp34401AError(f"No measurement method for function {step.function}")

        if step.function in (
            MeasurementFunction.VOLT_AC,
            MeasurementFunction.CURR_AC,
        ):
            reading = getattr(driver, method_name)(step.range_value)
        else:
            reading = getattr(driver, method_name)(step.range_value, step.nplc)

        if reading.is_overload or not reading.is_valid:
            pass_fail = "FAIL"  # overload/unstable -> FAIL, never fabricated
        else:
            pass_fail = check_limits(reading.value, step.lower_limit, step.upper_limit)
    except (Hp34401AError, ValueError, OSError) as exc:
        error = str(exc)
        pass_fail = "ERROR"

    finished = _dt.datetime.now(_dt.timezone.utc)
    return TestStepResult(
        dut_id=dut_id,
        station_id=station_id,
        step_name=step.name,
        started_utc=started,
        finished_utc=finished,
        reading=reading,
        pass_fail=pass_fail,  # type: ignore[arg-type]
        lower_limit=step.lower_limit,
        upper_limit=step.upper_limit,
        error=error,
        retry_count=reading.retry_count if reading else 0,
        reconnect_count=reading.reconnect_count if reading else 0,
    )


def run_sequence(
    driver: Hp34401A, sequence: TestSequence, dut_id: str, station_id: str
) -> TestSequenceResult:
    started = _dt.datetime.now(_dt.timezone.utc)
    results: list[TestStepResult] = []
    for step in sequence.steps:
        results.append(run_measurement_step(driver, step, dut_id, station_id))
    finished = _dt.datetime.now(_dt.timezone.utc)
    return TestSequenceResult(
        dut_id=dut_id,
        station_id=station_id,
        started_utc=started,
        finished_utc=finished,
        step_results=tuple(results),
    )
