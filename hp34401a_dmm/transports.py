"""Transport abstraction, backed by scpi-driver-core (spec sections 5, 21).

Byte-level I/O, connection state, and SCPI text framing are delegated to
``scpi_driver_core`` (``Transport`` backends + ``ScpiClient``). This module
keeps only the driver-specific behavior that sits above that boundary:

  * the one-outstanding-query rule (a repeated query/write while a previous
    response is unread is refused rather than silently interleaved),
  * the ``FakeTransport`` test double,
  * dispatching device-clear to the right per-transport recovery sequence
    (see ``serial_transport.py`` for the RS-232 Ctrl-C variant).

Shared transport rules (21.1):
  * ASCII encoding by default.
  * Append the write terminator to commands.
  * Strip response terminators (raw text preserved by callers).
  * Serialize all traffic through a lock.
  * Enforce one outstanding query at a time.
  * Provide a clear() operation.
  * Expose a name/resource for logs.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from typing import Protocol, runtime_checkable

from scpi_driver_core.exceptions import ConfigurationError as _CoreConfigurationError
from scpi_driver_core.exceptions import NotConnectedError as _CoreNotConnectedError
from scpi_driver_core.exceptions import TransportError as _CoreTransportError
from scpi_driver_core.exceptions import TransportTimeoutError as _CoreTransportTimeoutError
from scpi_driver_core.scpi.client import ScpiClient
from scpi_driver_core.scpi.codec import ScpiTextCodec
from scpi_driver_core.simulation.scripted import ScriptedScpiTransport
from scpi_driver_core.transport.base import Transport as CoreTransport
from scpi_driver_core.transport.models import FlushDirection

from .enums import TransportType
from .errors import InstrumentConnectionError, InstrumentTimeoutError, ProtocolError, TransportError

_log = logging.getLogger("hp34401a_dmm.transport")


@runtime_checkable
class Transport(Protocol):
    """Low-level byte/line transport contract used by the driver."""

    @property
    def name(self) -> str: ...

    @property
    def transport_type(self) -> TransportType: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def is_open(self) -> bool: ...

    def write(self, command: str) -> None: ...

    def query(self, command: str) -> str: ...

    def read_raw(self) -> str: ...

    def write_raw(self, data: str) -> None: ...

    def clear(self) -> None: ...

    def set_timeout(self, timeout_s: float) -> None: ...


class BaseTransport:
    """Common locking, terminator handling and one-outstanding-query enforcement.

    Concrete transports implement ``_build_core_transport`` (returning a
    ``scpi_driver_core`` byte ``Transport``) and may override ``_do_clear``;
    this base owns the cross-cutting rules plus the scpi-driver-core
    ``ScpiClient`` that actually performs the I/O, so the behaviour is
    identical across serial, VISA and the fake test transport.
    """

    _transport_type: TransportType = TransportType.FAKE

    def __init__(
        self,
        *,
        read_termination: str = "\n",
        write_termination: str = "\n",
        encoding: str = "ascii",
        raw_traffic_log: bool = False,
    ) -> None:
        self._read_termination = read_termination
        self._write_termination = write_termination
        self._encoding = encoding
        self._raw_traffic_log = raw_traffic_log
        self._lock = threading.RLock()
        self._has_unread_output = False
        self._open = False
        self._timeout_s: float = 10.0
        self._core: CoreTransport | None = None
        self._client: ScpiClient | None = None

    # -- properties ---------------------------------------------------------
    @property
    def transport_type(self) -> TransportType:
        return self._transport_type

    @property
    def name(self) -> str:  # pragma: no cover - overridden
        return "base"

    def is_open(self) -> bool:
        return self._open

    # -- public API ---------------------------------------------------------
    def write(self, command: str) -> None:
        with self._lock:
            if self._has_unread_output:
                raise ProtocolError(
                    "Refusing to write a command while a previous query response "
                    "is unread (one-outstanding-query rule)."
                )
            self._log_traffic("WRITE", command)
            self._call(lambda: self._client.write(command, timeout_s=self._timeout_s))

    def query(self, command: str) -> str:
        with self._lock:
            if self._has_unread_output:
                raise ProtocolError(
                    "Refusing to send a query while a previous query response is "
                    "unread (one-outstanding-query rule)."
                )
            t0 = time.monotonic()
            self._has_unread_output = True
            try:
                response = self._call(lambda: self._client.query(command, timeout_s=self._timeout_s))
            except Exception:
                # A real instrument can still send the response after the PC-side
                # timeout. Keep the unread-output flag set until clear()/read_raw()
                # is used so the driver cannot accidentally send another query and
                # read stale data or create a query-interrupted condition.
                raise
            else:
                self._has_unread_output = False
            self._log_traffic("QUERY", command, response, time.monotonic() - t0)
            return response

    def read_raw(self) -> str:
        """Recovery-only raw read. Does not enforce the query rule."""
        with self._lock:
            request = self._client.response_request
            raw = self._call(lambda: self._core.read(request, timeout_s=self._timeout_s))
            self._has_unread_output = False
            return self._client.codec.decode_response(raw)

    def write_raw(self, data: str) -> None:
        """Recovery-only raw write (e.g. Ctrl-C). Does not append a terminator."""
        with self._lock:
            self._log_traffic("RAW", data)
            self._call(lambda: self._core.write(data.encode(self._encoding), timeout_s=self._timeout_s))

    def clear(self) -> None:
        with self._lock:
            self._call(self._do_clear)
            self._has_unread_output = False

    def open(self) -> None:
        with self._lock:
            core = None
            try:
                core = self._build_core_transport()
                core.open()
                client = ScpiClient(
                    core,
                    codec=ScpiTextCodec(
                        encoding=self._encoding,
                        command_terminator=self._write_termination.encode(self._encoding),
                        response_terminator=(
                            self._read_termination.encode(self._encoding)
                            if self._read_termination
                            else None
                        ),
                    ),
                )
            except Exception as exc:
                self._open = False
                self._has_unread_output = False
                if core is not None:
                    with contextlib.suppress(Exception):
                        core.close()
                raise self._map_open_error(exc) from exc
            self._core = core
            self._client = client
            self._open = True

    def close(self) -> None:
        with self._lock:
            try:
                if self._core is not None:
                    self._core.close()
            finally:
                self._open = False
                self._has_unread_output = False

    def set_timeout(self, timeout_s: float) -> None:
        with self._lock:
            # scpi-driver-core transports take their timeout per call rather than
            # as mutable state, so the effective value is threaded through every
            # ScpiClient/core-transport call as ``timeout_s=self._timeout_s``.
            self._timeout_s = timeout_s

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    # -- hooks (override) -----------------------------------------------------
    def _build_core_transport(self) -> CoreTransport:  # pragma: no cover - overridden
        raise NotImplementedError

    def _do_clear(self) -> None:
        """Default device-clear: flush both directions on the byte transport."""
        self._core.flush(FlushDirection.BOTH)

    # -- helpers ------------------------------------------------------------
    def _call(self, action):
        try:
            return action()
        except _CoreTransportTimeoutError as exc:
            raise InstrumentTimeoutError(str(exc)) from exc
        except (_CoreNotConnectedError, _CoreTransportError) as exc:
            raise TransportError(str(exc)) from exc

    @staticmethod
    def _map_open_error(exc: Exception) -> Exception:
        if isinstance(exc, _CoreTransportTimeoutError):
            return InstrumentTimeoutError(str(exc))
        if isinstance(exc, (_CoreTransportError, _CoreConfigurationError)):
            return InstrumentConnectionError(str(exc))
        return exc

    def _log_traffic(
        self, kind: str, command: str, response: str | None = None, dur: float | None = None
    ) -> None:
        if not self._raw_traffic_log:
            return
        if response is None:
            _log.debug("[%s] %s -> %r", self.name, kind, command)
        else:
            _log.debug(
                "[%s] %s %r => %r (%.3fs)", self.name, kind, command, response, dur or 0.0
            )


class FakeTransport(BaseTransport):
    """Scriptable, deterministic transport for unit tests (spec sections 2, 29).

    Internally backed by ``scpi_driver_core.simulation.scripted.ScriptedScpiTransport``
    (the same simulator infrastructure real hardware tests build on), while
    keeping the exact public surface the existing test suite depends on:

    * ``responses`` maps an exact command string to a canned response.
    * ``default_response`` is returned for any unmatched query.
    * ``error_queue`` simulates the instrument FIFO error queue; SYSTem:ERRor?
      pops from it (returning '+0,"No error"' when empty).
    * ``history`` records every command written/queried in order so tests can
      assert on exact SCPI sequencing.
    * ``timeout_on`` is a set of commands that raise InstrumentTimeoutError to
      exercise recovery paths.
    """

    _transport_type = TransportType.FAKE

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        *,
        default_response: str = "",
        error_queue: list[str] | None = None,
        idn: str = "HEWLETT-PACKARD,34401A,0,11-05-01",
        raw_traffic_log: bool = False,
    ) -> None:
        super().__init__(raw_traffic_log=raw_traffic_log)
        self.responses = dict(responses or {})
        self.default_response = default_response
        self.error_queue: list[str] = list(error_queue or [])
        self.idn = idn
        self.history: list[str] = []
        self.write_history: list[str] = []
        self.query_history: list[str] = []
        self.response_history: list[tuple[str, str]] = []
        self.clear_count = 0
        self.raw_writes: list[str] = []
        self.timeout_on: set[str] = set()

    @property
    def name(self) -> str:
        return "fake"

    def _build_core_transport(self) -> CoreTransport:
        # No catch-all rule here: a plain (non-query) write of a command that
        # matches nothing must produce no queued reply at all, or it would
        # sit in the read buffer and be returned by the *next* query instead
        # of that query's own reply. Unmatched queries are resolved to
        # `default_response` explicitly in `query()` below, without ever
        # reaching this transport.
        scripted = ScriptedScpiTransport(unknown_command_error=None)
        # Registration order matters: later registrations for the same exact
        # command win (scpi_driver_core.ScriptedScpiTransport.on() overwrites),
        # so user-supplied `responses` are registered first and the built-in
        # *IDN?/error-queue handlers are registered last to guarantee they take
        # precedence, matching the historical FakeTransport._respond() order.
        for command, reply in self.responses.items():
            scripted.on(command, reply)
        scripted.on("*IDN?", lambda _cmd: self.idn)
        scripted.on("SYSTem:ERRor?", lambda _cmd: self._pop_error_queue())
        return scripted

    def _pop_error_queue(self) -> str:
        return self.error_queue.pop(0) if self.error_queue else '+0,"No error"'

    def _is_known_query(self, command: str) -> bool:
        key = command.strip().casefold()
        if key in ("*idn?", "system:error?"):
            return True
        return any(key == cmd.strip().casefold() for cmd in self.responses)

    # The fake overrides write/query directly (it tracks history/timeout_on
    # itself and never fails to open), rather than reusing BaseTransport's
    # locking wrappers verbatim.
    def write(self, command: str) -> None:
        with self._lock:
            if self._has_unread_output:
                raise ProtocolError("Write while query response unread (fake).")
            self.history.append(command)
            self.write_history.append(command)
            if command in self.timeout_on:
                raise InstrumentTimeoutError(f"Fake timeout on {command!r}")
            self._client.write(command)

    def query(self, command: str) -> str:
        with self._lock:
            if self._has_unread_output:
                raise ProtocolError("Query while previous response unread (fake).")
            self.history.append(command)
            self.query_history.append(command)
            if command in self.timeout_on:
                # Model a real timeout: response stays 'outstanding' until cleared.
                self._has_unread_output = True
                raise InstrumentTimeoutError(f"Fake timeout on {command!r}")
            if self._is_known_query(command):
                response = self._client.query(command)
            else:
                # Nothing was registered to answer this on the wire, so no reply
                # is queued anywhere; resolve straight to default_response
                # rather than asking the transport to read a reply that will
                # never arrive.
                response = self.default_response
            self.response_history.append((command, response))
            return response

    def read_raw(self) -> str:
        with self._lock:
            self._has_unread_output = False
            return self.default_response

    def write_raw(self, data: str) -> None:
        with self._lock:
            self.raw_writes.append(data)

    def clear(self) -> None:
        with self._lock:
            self.clear_count += 1
            self._has_unread_output = False

    def open(self) -> None:
        core = self._build_core_transport()
        core.open()
        self._core = core
        self._client = ScpiClient(
            core,
            codec=ScpiTextCodec(
                encoding=self._encoding,
                command_terminator=self._write_termination.encode(self._encoding),
                response_terminator=self._read_termination.encode(self._encoding),
            ),
        )
        self._open = True

    def close(self) -> None:
        if self._core is not None:
            self._core.close()
        self._open = False
        self._has_unread_output = False

    def set_timeout(self, timeout_s: float) -> None:
        pass
