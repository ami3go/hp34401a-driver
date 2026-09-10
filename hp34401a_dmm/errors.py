"""Driver-specific exceptions and SCPI error-code mapping for the HP 34401A.

Raw transport failures are converted to these exceptions with enough context for
troubleshooting (spec section 20). Communication errors are never silently
ignored.
"""

from __future__ import annotations

from typing import Final


class Hp34401AError(Exception):
    """Base class for all driver errors."""


class InstrumentConnectionError(Hp34401AError):
    """Connection could not be established or was lost."""


class InstrumentTimeoutError(Hp34401AError):
    """A command/query exceeded its finite timeout."""


class TransportError(Hp34401AError):
    """A raw transport-layer failure (serial/VISA)."""


class ProtocolError(Hp34401AError):
    """A driver-level protocol violation, e.g. interleaved queries."""


class ScpiError(Hp34401AError):
    """An error reported by the instrument's error queue."""

    def __init__(self, code: int, message: str, raw: str = "") -> None:
        self.code = code
        self.message = message
        self.raw = raw or f'{code},"{message}"'
        super().__init__(f"SCPI error {code}: {message}")


class CommandError(ScpiError):
    """Command-class SCPI error (codes -199..-100)."""


class ExecutionError(ScpiError):
    """Execution-class SCPI error (codes -299..-200)."""


class QueryError(ScpiError):
    """Query-class SCPI error (codes -499..-400)."""


class DeviceError(ScpiError):
    """Device-specific SCPI error (positive code) with structured code/message."""


class OverloadError(Hp34401AError):
    """A reading was an overload (9.9E37) and cannot be treated as numeric."""


class MeasurementNotStableError(Hp34401AError):
    """Stable-resistance measurement did not converge before max_wait_s."""


class SafetyError(Hp34401AError):
    """A safety-gated operation was attempted without explicit intent."""


class RecoveryError(Hp34401AError):
    """Recovery was attempted but the instrument did not return to a good state."""


ERROR_MESSAGES: Final[dict[int, str]] = {
    -101: "Invalid character",
    -102: "Syntax error",
    -103: "Invalid separator",
    -104: "Data type error",
    -108: "Parameter not allowed",
    -109: "Missing parameter",
    -112: "Program mnemonic too long",
    -113: "Undefined header",
    -121: "Invalid character in number",
    -123: "Numeric overflow",
    -124: "Too many digits",
    -131: "Invalid suffix",
    -138: "Suffix not allowed",
    -148: "Character data not allowed",
    -151: "Invalid string data",
    -158: "String data not allowed",
    -211: "Trigger ignored",
    -213: "Init ignored",
    -214: "Trigger deadlock",
    -221: "Settings conflict",
    -222: "Data out of range",
    -223: "Too much data",
    -224: "Illegal parameter value",
    -230: "Data stale",
    -330: "Self-test failed",
    -350: "Too many errors",
    -410: "Query interrupted",
    -420: "Query unterminated",
    -430: "Query deadlocked",
    -440: "Query unterminated after indefinite response",
    501: "Isolator UART framing error",
    502: "Isolator UART overrun error",
    511: "RS-232 framing error",
    512: "RS-232 overrun error",
    513: "RS-232 parity error",
    514: "Command allowed only with RS-232",
    521: "Input buffer overflow",
    522: "Output buffer overflow",
    531: "Insufficient memory",
    532: "Cannot achieve requested resolution",
    540: "Cannot use overload as math reference",
    550: "Command not allowed in local",
}


def scpi_error_for(code: int, message: str = "", raw: str = "") -> ScpiError:
    """Map a numeric error code to the most specific exception class."""
    msg = message or ERROR_MESSAGES.get(code, "Unknown error")
    if -199 <= code <= -100:
        return CommandError(code, msg, raw)
    if -299 <= code <= -200:
        return ExecutionError(code, msg, raw)
    if -499 <= code <= -400:
        return QueryError(code, msg, raw)
    if code > 0:
        return DeviceError(code, msg, raw)
    return ScpiError(code, msg, raw)
