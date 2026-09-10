"""Deterministic parsing of instrument responses (spec sections 3, 29.2).

All functions here are pure and unit-tested with fixed vectors; they never touch
a transport.  Overload values are classified as overload rather than treated as
valid numeric measurements.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from .enums import OVERLOAD_THRESHOLD
from .errors import ProtocolError

# +0,"No error"  /  -113,"Undefined header"
_ERROR_RE = re.compile(r'^\s*([+-]?\d+)\s*,\s*"(.*)"\s*$')


class ParsedError(NamedTuple):
    code: int
    message: str
    raw: str


def is_overload(value: float) -> bool:
    """True if a numeric value is the 34401A overload sentinel (~9.9E37)."""
    return abs(value) >= OVERLOAD_THRESHOLD


def parse_float(raw: str) -> float:
    """Parse a single SCPI float response.

    Raises ProtocolError on empty/garbled input so callers never silently accept
    a bad reading.
    """
    text = raw.strip()
    if not text:
        raise ProtocolError("Empty response while a numeric value was expected")
    try:
        return float(text)
    except ValueError as exc:
        raise ProtocolError(f"Could not parse numeric response: {text!r}") from exc


def parse_reading_list(raw: str) -> list[float]:
    """Parse a comma-separated FETCh?/READ? response into floats.

    Handles single readings, multi-reading comma lists, and trailing terminators.
    Raises ProtocolError on empty or partial input.
    """
    text = raw.strip()
    if not text:
        raise ProtocolError("Empty response while readings were expected")
    if text.endswith(","):
        raise ProtocolError(f"Partial reading response with trailing comma: {raw!r}")
    parts = [p for p in (s.strip() for s in text.split(",")) if p]
    if not parts or len(parts) != len(text.split(",")):
        raise ProtocolError(f"Partial reading response: {raw!r}")
    try:
        return [float(p) for p in parts]
    except ValueError as exc:
        raise ProtocolError(f"Partial/garbled reading response: {raw!r}") from exc


def parse_error(raw: str) -> ParsedError:
    """Parse a SYSTem:ERRor? response of the form  <code>,"<message>".

    Raises ProtocolError on malformed responses.
    """
    text = raw.strip()
    m = _ERROR_RE.match(text)
    if not m:
        raise ProtocolError(f"Malformed SYSTem:ERRor? response: {raw!r}")
    return ParsedError(code=int(m.group(1)), message=m.group(2), raw=text)


def is_no_error(parsed: ParsedError) -> bool:
    return parsed.code == 0


def parse_identity(raw: str) -> tuple[str, str, str | None, str | None]:
    """Parse *IDN? -> (manufacturer, model, serial, firmware).

    Expected form: HEWLETT-PACKARD,34401A,0,XX-XX-XX
    The 34401A reports serial as "0", which we normalise to None.
    """
    text = raw.strip()
    fields = [f.strip() for f in text.split(",")]
    if len(fields) < 2:
        raise ProtocolError(f"Unrecognised *IDN? response: {raw!r}")
    manufacturer = fields[0]
    model = fields[1]
    serial = fields[2] if len(fields) > 2 else None
    firmware = fields[3] if len(fields) > 3 else None
    if serial in ("0", ""):
        serial = None
    return manufacturer, model, serial, firmware


_KNOWN_MODELS = ("34401A",)
_KNOWN_VENDORS = ("HEWLETT-PACKARD", "AGILENT", "KEYSIGHT")


def looks_like_34401a(raw: str) -> bool:
    """Heuristic used by the RS-232 connect path (R2) to detect a settings
    mismatch: a garbled/empty IDN does not look like a 34401A."""
    text = raw.strip().upper()
    if not text:
        return False
    has_model = any(m in text for m in _KNOWN_MODELS)
    has_vendor = any(v in text for v in _KNOWN_VENDORS)
    return has_model and has_vendor
