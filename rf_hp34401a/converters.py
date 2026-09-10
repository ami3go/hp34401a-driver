"""Central Robot-friendly argument conversion."""

from __future__ import annotations

import math
import re
from typing import Any, TypeVar

from hp34401a_dmm import (
    AcFilterHz,
    Aperture,
    AutoRange,
    AutozeroMode,
    InputTerminal,
    Nplc,
    TriggerSource,
)

from .exceptions import DriverValidationError

E = TypeVar("E")


def as_bool(value: Any, *, name: str = "value") -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "on", "1", "${true}"}:
        return True
    if text in {"false", "no", "off", "0", "${false}"}:
        return False
    raise DriverValidationError(f"{name} must be a Boolean value, got {value!r}")


def as_float(value: Any, *, name: str = "value") -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise DriverValidationError(f"{name} must be numeric, got {value!r}") from exc
    if not math.isfinite(result):
        raise DriverValidationError(f"{name} must be finite, got {value!r}")
    return result


def as_int(value: Any, *, name: str = "value") -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DriverValidationError(f"{name} must be an integer, got {value!r}") from exc
    if not math.isfinite(number) or not number.is_integer():
        raise DriverValidationError(f"{name} must be an integer, got {value!r}")
    return int(number)


def as_seconds(value: Any, *, name: str = "duration") -> float:
    """Convert a Robot/Python timeout to finite positive seconds."""

    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text = str(value).strip()
        try:
            from robot.utils import timestr_to_secs

            seconds = float(timestr_to_secs(text))
        except Exception:
            match = re.fullmatch(
                r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(ms|s|sec|secs|second|seconds|min|mins|minute|minutes|h|hr|hrs|hour|hours)?",
                text,
                re.IGNORECASE,
            )
            if not match:
                seconds = as_float(text, name=name)
            else:
                number = float(match.group(1))
                unit = (match.group(2) or "s").lower()
                factor = {
                    "ms": 0.001,
                    "s": 1.0,
                    "sec": 1.0,
                    "secs": 1.0,
                    "second": 1.0,
                    "seconds": 1.0,
                    "min": 60.0,
                    "mins": 60.0,
                    "minute": 60.0,
                    "minutes": 60.0,
                    "h": 3600.0,
                    "hr": 3600.0,
                    "hrs": 3600.0,
                    "hour": 3600.0,
                    "hours": 3600.0,
                }[unit]
                seconds = number * factor
    if not math.isfinite(seconds) or seconds <= 0:
        raise DriverValidationError(f"{name} must be a finite value > 0 seconds")
    return seconds


def as_optional_float(value: Any, *, name: str = "value") -> float | None:
    if value is None or str(value).strip().lower() in {"", "none", "${none}"}:
        return None
    return as_float(value, name=name)


def as_range(value: Any, *, name: str = "range") -> float | AutoRange:
    if isinstance(value, AutoRange):
        return value
    if isinstance(value, (int, float)):
        result = as_float(value, name=name)
        if result <= 0:
            raise DriverValidationError(f"{name} must be positive or AUTO/MIN/MAX/DEF")
        return result
    text = str(value).strip().upper()
    aliases = {"DEFAULT": "DEF", "AUTORANGE": "AUTO"}
    text = aliases.get(text, text)
    try:
        return AutoRange[text]
    except KeyError:
        result = as_float(value, name=name)
        if result <= 0:
            raise DriverValidationError(f"{name} must be positive or AUTO/MIN/MAX/DEF")
        return result


def as_nplc(value: Any) -> Nplc:
    number = as_float(value, name="nplc")
    for member in Nplc:
        if member.value == number:
            return member
    raise DriverValidationError("nplc must be one of 0.02, 0.2, 1, 10, 100")


def as_aperture(value: Any) -> Aperture:
    number = as_float(value, name="aperture")
    for member in Aperture:
        if member.value == number:
            return member
    raise DriverValidationError("aperture must be one of 0.01, 0.1, 1 seconds")


def as_ac_filter(value: Any) -> AcFilterHz:
    number = as_int(value, name="AC filter")
    for member in AcFilterHz:
        if member.value == number:
            return member
    raise DriverValidationError("AC filter must be one of 3, 20, 200 Hz")


def as_autozero(value: Any) -> AutozeroMode:
    if isinstance(value, AutozeroMode):
        return value
    text = str(value).strip().upper()
    try:
        return AutozeroMode[text]
    except KeyError as exc:
        raise DriverValidationError("autozero must be OFF, ONCE, or ON") from exc


def as_trigger_source(value: Any) -> TriggerSource:
    if isinstance(value, TriggerSource):
        return value
    text = str(value).strip().upper()
    aliases = {"IMM": "IMMEDIATE", "EXT": "EXTERNAL"}
    text = aliases.get(text, text)
    try:
        return TriggerSource[text]
    except KeyError as exc:
        raise DriverValidationError("trigger source must be IMMEDIATE, BUS, or EXTERNAL") from exc


def as_terminal(value: Any) -> InputTerminal:
    if isinstance(value, InputTerminal):
        return value
    text = str(value).strip().upper()
    if text not in {"FRONT", "REAR"}:
        raise DriverValidationError("terminal must be FRONT or REAR")
    return InputTerminal[text]
