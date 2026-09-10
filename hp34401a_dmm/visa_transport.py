"""VISA GPIB/USBTMC transport using scpi-driver-core's VisaTransport
(spec section 21.3, incorporating R9/R10).

``pyvisa`` is imported lazily inside ``scpi_driver_core.transport.visa``, so
this module and the CLI ``--help`` work without pyvisa installed and without
hardware.
"""

from __future__ import annotations

import logging
import re

from scpi_driver_core.transport.base import Transport as CoreTransport
from scpi_driver_core.transport.visa import VisaTransport as CoreVisaTransport

from .config import VisaGpibConfig
from .enums import (
    MAX_GPIB_ADDRESS,
    MIN_GPIB_ADDRESS,
    TALK_ONLY_GPIB_ADDRESS,
    TransportType,
)
from .errors import InstrumentConnectionError
from .transports import BaseTransport

_log = logging.getLogger("hp34401a_dmm.transport")

_GPIB_ADDR_RE = re.compile(r"GPIB\d*::(\d+)", re.IGNORECASE)


def validate_gpib_resource(resource: str) -> None:
    """R10: reject talk-only (31) and out-of-range GPIB primary addresses."""
    m = _GPIB_ADDR_RE.search(resource)
    if not m:
        return  # non-GPIB resource string; nothing to validate here
    addr = int(m.group(1))
    if addr == TALK_ONLY_GPIB_ADDRESS:
        raise InstrumentConnectionError(
            f"GPIB address {addr} selects talk-only mode and cannot be queried. "
            f"Use a primary address in {MIN_GPIB_ADDRESS}-{MAX_GPIB_ADDRESS}."
        )
    if not (MIN_GPIB_ADDRESS <= addr <= MAX_GPIB_ADDRESS):
        raise InstrumentConnectionError(
            f"GPIB primary address {addr} is out of range "
            f"({MIN_GPIB_ADDRESS}-{MAX_GPIB_ADDRESS})."
        )


class VisaGpibTransport(BaseTransport):
    """Drives GPIB, USBTMC, TCPIP INSTR/SOCKET and ASRL VISA resources.

    The name is historical (spec section 21.3 covers GPIB); the underlying
    ``scpi_driver_core.transport.visa.VisaTransport`` is resource-class
    agnostic, so this also drives a USBTMC instrument such as
    ``USB0::<VID>::<PID>::<SERIAL>::INSTR``.
    """

    _transport_type = TransportType.VISA_GPIB

    def __init__(self, config: VisaGpibConfig, *, raw_traffic_log: bool = False) -> None:
        super().__init__(
            read_termination=config.read_termination,
            write_termination=config.write_termination,
            raw_traffic_log=raw_traffic_log,
        )
        validate_gpib_resource(config.resource)  # R10, fail before opening
        self.config = config

    @property
    def name(self) -> str:
        return f"visa:{self.config.resource}"

    def _build_core_transport(self) -> CoreTransport:
        return CoreVisaTransport(
            self.config.resource,
            timeout_s=self.config.timeout_s,
            visa_library=self.config.visa_library or "",
        )

    # No _do_clear override needed: scpi_driver_core.VisaTransport.flush()
    # already calls the VISA session's clear() for any direction other than
    # OUTPUT-only, matching the previous self._inst.clear() behaviour.
