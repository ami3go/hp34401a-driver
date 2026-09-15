"""RS-232 transport using scpi-driver-core's SerialTransport (spec section 21.2).

``pyserial`` is imported lazily inside ``scpi_driver_core.transport.serial``,
so this module and the CLI ``--help`` work without pyserial installed and
without hardware.

Known deviation: ``scpi_driver_core.transport.serial.SerialTransport`` does not
expose pyserial's ``dsrdtr`` hardware-flow-control flag, so
``SerialRs232Config.use_dtr_dsr`` is currently accepted but not applied. See
``docs/scpi_driver_core_review.md`` for detail; this is called out rather than
worked around by reaching into scpi-driver-core's private serial resource.
"""

from __future__ import annotations

import logging

from scpi_driver_core.transport.base import Transport as CoreTransport
from scpi_driver_core.transport.models import FlushDirection
from scpi_driver_core.transport.serial import SerialTransport as CoreSerialTransport

from .config import SerialRs232Config
from .enums import TransportType
from .transports import BaseTransport

_log = logging.getLogger("hp34401a_dmm.transport")

# RS-232 device-clear character for the 34401A (spec section 21.1).
CTRL_C = "\x03"

_PARITY_MAP = {"none": "N", "even": "E", "odd": "O"}


class SerialRs232Transport(BaseTransport):
    _transport_type = TransportType.SERIAL_RS232

    def __init__(self, config: SerialRs232Config, *, raw_traffic_log: bool = False) -> None:
        super().__init__(
            read_termination=config.read_termination,
            write_termination=config.write_termination,
            encoding=config.encoding,
            raw_traffic_log=raw_traffic_log,
        )
        self.config = config

    @property
    def name(self) -> str:
        return f"serial:{self.config.port}@{self.config.baudrate}"

    def _build_core_transport(self) -> CoreTransport:
        return CoreSerialTransport(
            self.config.port,
            baudrate=self.config.baudrate,
            timeout_s=self.config.timeout_s,
            write_timeout_s=self.config.write_timeout_s,
            bytesize=self.config.data_bits,
            parity=_PARITY_MAP[self.config.parity],
            stopbits=self.config.stop_bits,
        )

    def _do_clear(self) -> None:
        """RS-232 device clear: send Ctrl-C and flush buffers (spec 21.1/21.2)."""
        core = self._require_core()
        core.write(CTRL_C.encode(self._encoding), timeout_s=self._timeout_s)
        core.flush(FlushDirection.BOTH)
