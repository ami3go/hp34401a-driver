"""Enumerations, literals and validation tables for the HP 34401A (spec sections 9, 10)."""

from __future__ import annotations

import enum
from typing import Final


class MeasurementFunction(str, enum.Enum):
    VOLT_DC = "VOLT:DC"
    VOLT_DC_RATIO = "VOLT:DC:RATIO"
    VOLT_AC = "VOLT:AC"
    CURR_DC = "CURR:DC"
    CURR_AC = "CURR:AC"
    RES_2W = "RES"
    RES_4W = "FRES"
    FREQ = "FREQ"
    PERIOD = "PER"
    CONTINUITY = "CONT"
    DIODE = "DIOD"

    @property
    def unit(self) -> str:
        return _FUNCTION_UNITS[self]


_FUNCTION_UNITS: Final[dict[MeasurementFunction, str]] = {
    MeasurementFunction.VOLT_DC: "V",
    MeasurementFunction.VOLT_DC_RATIO: "",
    MeasurementFunction.VOLT_AC: "V",
    MeasurementFunction.CURR_DC: "A",
    MeasurementFunction.CURR_AC: "A",
    MeasurementFunction.RES_2W: "Ohm",
    MeasurementFunction.RES_4W: "Ohm",
    MeasurementFunction.FREQ: "Hz",
    MeasurementFunction.PERIOD: "s",
    MeasurementFunction.CONTINUITY: "Ohm",
    MeasurementFunction.DIODE: "V",
}

# Functions that accept NPLC (spec section 3 / 12).
NPLC_FUNCTIONS: Final[frozenset[MeasurementFunction]] = frozenset(
    {
        MeasurementFunction.VOLT_DC,
        MeasurementFunction.CURR_DC,
        MeasurementFunction.RES_2W,
        MeasurementFunction.RES_4W,
    }
)


class Nplc(float, enum.Enum):
    PLC0_02 = 0.02
    PLC0_2 = 0.2
    PLC1 = 1.0
    PLC10 = 10.0
    PLC100 = 100.0


class Aperture(float, enum.Enum):
    APER0_01 = 0.01
    APER0_1 = 0.1
    APER1 = 1.0


class AcFilterHz(int, enum.Enum):
    HZ3 = 3
    HZ20 = 20
    HZ200 = 200


class TriggerSource(str, enum.Enum):
    IMMEDIATE = "IMMediate"
    BUS = "BUS"
    EXTERNAL = "EXTernal"


class AutozeroMode(str, enum.Enum):
    OFF = "OFF"
    ONCE = "ONCE"
    ON = "ON"


class InputTerminal(str, enum.Enum):
    FRONT = "FRONT"
    REAR = "REAR"
    UNKNOWN = "UNKNOWN"


class TransportType(str, enum.Enum):
    SERIAL_RS232 = "SERIAL_RS232"
    VISA_GPIB = "VISA_GPIB"
    PROLOGIX_GPIB = "PROLOGIX_GPIB"
    FAKE = "FAKE"


class AutoRange(str, enum.Enum):
    """Sentinel range values accepted by CONFigure."""

    AUTO = "AUTO"
    MIN = "MIN"
    MAX = "MAX"
    DEF = "DEF"


class CommandState(str, enum.Enum):
    """Driver command state machine (spec section 22)."""

    CLOSED = "CLOSED"
    CONNECTED_LOCAL = "CONNECTED_LOCAL"
    CONNECTED_REMOTE = "CONNECTED_REMOTE"
    CONFIGURED = "CONFIGURED"
    WAITING_FOR_TRIGGER = "WAITING_FOR_TRIGGER"
    MEASURING = "MEASURING"
    HAS_UNREAD_OUTPUT = "HAS_UNREAD_OUTPUT"
    ERROR_RECOVERY = "ERROR_RECOVERY"


# --- Exact manual range tables (spec section 10). ----------------------------
VOLTAGE_DC_RANGES: Final[tuple[float, ...]] = (0.1, 1.0, 10.0, 100.0, 1000.0)
VOLTAGE_AC_RANGES: Final[tuple[float, ...]] = (0.1, 1.0, 10.0, 100.0, 750.0)
RESISTANCE_RANGES: Final[tuple[float, ...]] = (
    100.0, 1e3, 10e3, 100e3, 1e6, 10e6, 100e6,
)
CURRENT_DC_RANGES: Final[tuple[float, ...]] = (0.01, 0.1, 1.0, 3.0)
CURRENT_AC_RANGES: Final[tuple[float, ...]] = (1.0, 3.0)

RANGE_TABLES: Final[dict[MeasurementFunction, tuple[float, ...]]] = {
    MeasurementFunction.VOLT_DC: VOLTAGE_DC_RANGES,
    MeasurementFunction.VOLT_AC: VOLTAGE_AC_RANGES,
    MeasurementFunction.RES_2W: RESISTANCE_RANGES,
    MeasurementFunction.RES_4W: RESISTANCE_RANGES,
    MeasurementFunction.CURR_DC: CURRENT_DC_RANGES,
    MeasurementFunction.CURR_AC: CURRENT_AC_RANGES,
}

# Internal reading-memory depth (spec section 3 / 14.4).
MAX_INTERNAL_READINGS: Final[int] = 512
# Trigger/sample count instrument bounds (verified against manual).
MAX_COUNT: Final[int] = 50000
# Valid HP-IB primary addresses (R10): 0..30; 31 is talk-only.
MIN_GPIB_ADDRESS: Final[int] = 0
MAX_GPIB_ADDRESS: Final[int] = 30
TALK_ONLY_GPIB_ADDRESS: Final[int] = 31
# Overload magnitude returned by the instrument (spec section 3).
OVERLOAD_VALUE: Final[float] = 9.9e37
OVERLOAD_THRESHOLD: Final[float] = 9.8e37
