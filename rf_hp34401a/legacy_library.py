"""Explicit Robot Framework keyword library for the HP 34401A.

Every public keyword is wrapped (see ``_evidenced`` below) with an RFDS-008
evidence operation record — arguments, duration, result/failure, correlated
with the literal SCPI traffic that operation caused on whichever transport
carried it. See ``hp34401a_dmm/evidence.py`` for what gets recorded and where;
pass ``evidence_enabled=False`` to disable it. This complements, and does not
replace, the existing ``tests/hil/`` real-hardware conformance suite and
``tests/conformance/`` RFDS-019 protocol-vector suite, which remain the
keyword/protocol coverage authority — this layer is about explaining one
session's failure after the fact, not proving coverage.
"""

from __future__ import annotations

import functools
import inspect
import math
import platform
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any, Literal, cast

from robot.api import logger
from robot.api.deco import keyword, library

from hp34401a_dmm import (
    DriverConfig,
    FakeTransport,
    Hp34401A,
    MeasurementNotStableError,
    MeasurementReading,
    OverloadError,
    SerialRs232Config,
    StabilityProfile,
    VisaGpibConfig,
)
from hp34401a_dmm import (
    __version__ as CORE_VERSION,
)
from hp34401a_dmm import evidence as _evidence

from .capabilities import CapabilityRegistry
from .configuration import ConfigurationManager
from .converters import (
    as_ac_filter,
    as_aperture,
    as_autozero,
    as_bool,
    as_float,
    as_int,
    as_nplc,
    as_optional_float,
    as_range,
    as_seconds,
    as_terminal,
    as_trigger_source,
)
from .exceptions import (
    DriverCleanupError,
    DriverConnectionError,
    DriverDeviceError,
    DriverProtocolError,
    DriverStateError,
    DriverTimeoutError,
    DriverValidationError,
    Hp34401ARobotError,
    RFDSDriverError,
)
from .sessions import DmmSession, SessionManager
from .version import __version__

try:
    ROBOT_FRAMEWORK_VERSION = package_version("robotframework")
except PackageNotFoundError:  # import-safe metadata inspection in source checkouts
    ROBOT_FRAMEWORK_VERSION = "NOT_INSTALLED"

# Keywords that close DMM session(s). After any of these runs, if zero
# sessions remain open, the evidence run is finalized (see _evidenced below) —
# covers both single-alias teardown (Disconnect/Close DMM on the last open
# alias) and whole-library teardown (Disconnect All/Close All DMMs).
_DISCONNECT_CAPABILITIES = {"Disconnect", "Close DMM", "Disconnect DMM", "Disconnect All", "Close All DMMs"}


def _evidenced(func: Callable) -> Callable:
    """Wrap a keyword method with an RFDS-008 evidence operation record.

    Reads ``self._evidence``/``self._sessions`` on the bound instance, binds
    ``*args``/``**kwargs`` to parameter names for a readable argument record,
    and records success/failure/duration around the call. Finalizes the run
    (writes ``run_summary.json`` + ``evidence_manifest.json``) once a
    disconnect-family keyword leaves zero sessions open — see
    ``_DISCONNECT_CAPABILITIES``.

    Must sit *below* ``@keyword(...)`` in the decorator stack (closest to
    ``def``) — it reads ``wrapper.robot_name`` at call time via closure, which
    ``@keyword`` sets on the object this function returns once the class body
    finishes executing, well before any instance method call happens.
    """
    signature = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(self: Hp34401ALibrary, *args: Any, **kwargs: Any) -> Any:
        capability = getattr(wrapper, "robot_name", None) or func.__name__.replace("_", " ").title()
        run = self._ensure_evidence()
        bound = signature.bind_partial(self, *args, **kwargs)
        bound.apply_defaults()
        arguments = {key: value for key, value in bound.arguments.items() if key != "self"}
        status = "PASS"
        try:
            with run.record_operation(capability, arguments=arguments) as op:
                result = func(self, *args, **kwargs)
                op.set_result(result)
            return result
        except Exception:
            status = "FAIL"
            raise
        finally:
            if capability in _DISCONNECT_CAPABILITIES:
                # Defensive: evidence bookkeeping must never mask the real
                # exception from a disconnect-family keyword (or the AttributeError
                # from a test double standing in for self._sessions) by raising
                # its own error out of this finally block.
                try:
                    sessions_remaining = bool(self._sessions.aliases())
                except Exception:
                    sessions_remaining = True
                if not sessions_remaining:
                    run.finalize(status=status)
                    self._evidence = None

    return wrapper


@library(scope="SUITE", auto_keywords=False, version=__version__)
class Hp34401ALibrary:
    """Production-safe Robot Framework adapter for the HP/Agilent/Keysight 34401A.

    The library delegates all SCPI operations to ``hp34401a_dmm.Hp34401A``.
    Measurement keywords reject overload, invalid, missing, or unstable readings
    rather than returning a fabricated scalar.

    Every public keyword call is recorded as RFDS-008 evidence (arguments,
    duration, the underlying SCPI traffic, failures) under
    ``results/session/rf_hp34401a/`` for troubleshooting — one evidence run
    per library instance (this class is ``SUITE``-scoped), tagged per DMM
    alias. See ``hp34401a_dmm/evidence.py`` and ``docs/logging_and_evidence.md``.
    """

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_AUTO_KEYWORDS = False
    ROBOT_LIBRARY_VERSION = __version__

    def __init__(
        self,
        default_timeout_s: object = 10.0,
        allow_raw_io: object = False,
        evidence_enabled: object = True,
    ) -> None:
        self._sessions = SessionManager()
        self._default_timeout_s = as_seconds(default_timeout_s, name="default_timeout_s")
        self._allow_raw_io = as_bool(allow_raw_io, name="allow_raw_io")
        self._configuration = ConfigurationManager()
        self._capabilities = CapabilityRegistry()
        self._evidence_enabled = as_bool(evidence_enabled, name="evidence_enabled")
        self._evidence: Any = None
        self.ROBOT_LIBRARY_LISTENER = self

    def _ensure_evidence(self) -> Any:
        """Lazily create (or return) this library instance's :class:`evidence.EvidenceRun`.

        Created on first keyword call rather than in ``__init__`` so
        constructing the library alone never touches disk.
        """
        if self._evidence is None:
            if self._evidence_enabled:
                self._evidence = _evidence.EvidenceRun(driver_id="rf_hp34401a", activity="session")
            else:
                self._evidence = _evidence.NullEvidenceRun()
        return self._evidence

    # ------------------------------- internal helpers
    def _execute(self, operation: str, call: Callable[[], Any], alias: object | None = None) -> Any:
        try:
            return call()
        except RFDSDriverError:
            raise
        except Exception as exc:
            active = (
                str(alias).strip()
                if alias is not None and str(alias).strip()
                else self._sessions.active_alias
            )
            name = type(exc).__name__.lower()
            common = {"operation": operation, "alias": active, "details": {"cause_type": type(exc).__name__}}
            if isinstance(exc, ValueError):
                error = DriverValidationError(str(exc), **common)
            elif isinstance(exc, TimeoutError) or "timeout" in name:
                error = DriverTimeoutError(str(exc), **common)
            elif isinstance(exc, (ConnectionError, OSError)) or "connection" in name:
                error = DriverConnectionError(str(exc), **common)
            elif "protocol" in name or "parse" in name:
                error = DriverProtocolError(str(exc), **common)
            elif "device" in name or "overload" in name:
                error = DriverDeviceError(str(exc), **common)
            else:
                error = Hp34401ARobotError(str(exc), operation=operation, alias=active, details=common["details"])
            raise error from exc

    def _session(self, alias: object | None = None) -> DmmSession:
        try:
            return self._sessions.get(alias)
        except ValueError as exc:
            active = str(alias).strip() if alias is not None else self._sessions.active_alias
            raise DriverStateError(str(exc), operation="Get DMM session", alias=active) from exc

    @staticmethod
    def _driver_config(
        *,
        timeout: object = 10.0,
        reset_on_connect: object = False,
        verify_identity: object = True,
        drain_error_queue: object = True,
        clear_status: object = True,
        retry_queries: object = True,
        max_query_retries: object = 1,
        allow_calibration_commands: object = False,
        raw_traffic_log: object = False,
    ) -> DriverConfig:
        return DriverConfig(
            reset_on_connect=as_bool(reset_on_connect, name="reset_on_connect"),
            clear_status_on_connect=as_bool(clear_status, name="clear_status"),
            verify_identity_on_connect=as_bool(verify_identity, name="verify_identity"),
            drain_error_queue_on_connect=as_bool(drain_error_queue, name="drain_error_queue"),
            default_timeout_s=as_seconds(timeout, name="timeout"),
            retry_queries=as_bool(retry_queries, name="retry_queries"),
            max_query_retries=as_int(max_query_retries, name="max_query_retries"),
            allow_calibration_commands=as_bool(
                allow_calibration_commands, name="allow_calibration_commands"
            ),
            raw_traffic_log=as_bool(raw_traffic_log, name="raw_traffic_log"),
        )

    def _register_connected(
        self,
        alias: object,
        driver: Hp34401A,
        *,
        replace: object = False,
        resource: str = "UNKNOWN",
        transport_kind: str = "UNKNOWN",
        timeout_s: float | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        normalized_alias = SessionManager.normalize_alias(alias)
        evidence_run = self._ensure_evidence()
        # Wired before driver.connect() so connection-time SCPI traffic
        # (*IDN?, error-queue drain, etc.) is captured too, not just
        # traffic from keywords called after this session is registered.
        driver.trace_callback = lambda direction, text, _run=evidence_run, _alias=normalized_alias, _kind=transport_kind: _run.log_protocol(
            direction, _kind, text, session_alias=_alias
        )
        try:
            driver.connect()
            identity = driver.identity_cached
            identity_text = getattr(identity, "raw", None) if identity else None
            self._sessions.add(
                alias,
                driver,
                replace=as_bool(replace, name="replace"),
                resource=resource,
                transport_kind=transport_kind,
                timeout_s=timeout_s or self._default_timeout_s,
                options=options,
                identity_text=identity_text,
            )
        except Exception:
            try:
                driver.close()
            except Exception:
                pass
            raise
        identity = driver.identity_cached
        if identity:
            logger.info(
                f"Opened HP34401A session {alias!r}: {identity.manufacturer} "
                f"{identity.model}, serial={identity.serial or 'unknown'}"
            )
            evidence_run.record_device_identity(
                normalized_alias,
                manufacturer=identity.manufacturer,
                model=identity.model,
                serial_number=identity.serial,
                firmware_version=identity.firmware,
                transport=transport_kind,
                resource=resource,
            )
        return str(alias)

    @staticmethod
    def _reading_to_dict(reading: MeasurementReading, session: DmmSession) -> dict[str, Any]:
        result = {
            "timestamp_utc": reading.timestamp_utc.isoformat(),
            "function": reading.function.value,
            "value": reading.value,
            "unit": reading.unit,
            "raw": reading.raw,
            "range_value": reading.range_value,
            "nplc": reading.nplc,
            "aperture_s": reading.aperture_s,
            "is_overload": reading.is_overload,
            "is_valid": reading.is_valid,
            "was_retried": reading.was_retried,
            "retry_count": reading.retry_count,
            "reconnect_count": reading.reconnect_count,
            "recovery_actions": list(reading.recovery_actions),
            "terminal": reading.terminal.value if reading.terminal else None,
            "transport": reading.transport.value if reading.transport else None,
            "alias": session.alias,
            "library_version": __version__,
            "driver_version": CORE_VERSION,
        }
        return result

    @staticmethod
    def _model_to_dict(value: Any) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            raw = asdict(value)
            return Hp34401ALibrary._model_to_dict(raw)
        if isinstance(value, dict):
            return {str(k): Hp34401ALibrary._model_to_dict(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [Hp34401ALibrary._model_to_dict(v) for v in value]
        if hasattr(value, "value") and not isinstance(value, (str, int, float, bool)):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def _accept_reading(self, session: DmmSession, reading: MeasurementReading) -> float:
        session.last_reading = reading
        if reading.is_overload:
            raise OverloadError(
                f"DMM overload in {reading.function.value}; raw response={reading.raw!r}"
            )
        if not reading.is_valid or reading.value is None:
            raise Hp34401ARobotError(
                f"DMM returned an invalid {reading.function.value} reading; raw={reading.raw!r}"
            )
        logger.info(f"{session.alias}: {reading.value:.12g} {reading.unit}")
        return float(reading.value)

    def _measure(
        self,
        operation: str,
        producer: Callable[[Hp34401A], MeasurementReading],
        alias: object | None,
    ) -> float:
        session = self._session(alias)
        return self._execute(
            operation,
            lambda: self._accept_reading(session, producer(session.driver)),
            session.alias,
        )

    # ------------------------------- RFDS-002 canonical lifecycle API
    @keyword("Connect", tags=["rfds:connection", "rfds:low_risk"])
    @_evidenced
    def connect(
        self,
        resource: str | None = None,
        alias: str = "default",
        timeout_s: object | None = None,
        **options: Any,
    ) -> dict[str, Any]:
        """Establish a session and return the RFDS ``connection_state`` schema.

        ``resource`` accepts a VISA resource, serial port, or explicit
        ``SIM::`` resource.  Hardware never falls back to simulation.
        """
        configured = self._configuration.effective()["settings"]
        transport_cfg = configured["transport"]
        selected_resource = str(resource or transport_cfg.get("resource") or "").strip()
        if not selected_resource:
            raise DriverValidationError(
                "Connect requires resource, or a validated configuration containing settings.transport.resource",
                operation="Connect",
                alias=alias,
            )
        existing = self._sessions.find(alias)
        if existing is not None and existing.connected:
            if existing.resource == selected_resource:
                return existing.to_connection_state(
                    active=existing.alias == self._sessions.active_alias,
                    communication_ok=True,
                )
            raise DriverStateError(
                f"Alias {alias!r} is already connected to {existing.resource!r}; disconnect it explicitly before changing resource",
                operation="Connect",
                alias=alias,
            )

        accepted = {
            "transport", "visa_library", "baud_rate", "parity", "data_bits", "stop_bits",
            "dtr_dsr", "remote_on_connect", "local_on_close", "reset_on_connect",
            "verify_identity", "drain_error_queue", "retry_queries", "max_query_retries",
            "allow_calibration_commands", "replace", "raw_traffic_log",
        }
        unknown = sorted(set(options) - accepted)
        if unknown:
            raise DriverValidationError(
                f"Unknown Connect options: {unknown}", operation="Connect", alias=alias
            )
        effective_timeout = (
            self._default_timeout_s
            if timeout_s is None
            else as_seconds(timeout_s, name="timeout_s")
        )
        if selected_resource.upper().startswith("SIM::"):
            self.open_simulated_dmm(
                alias=alias,
                reading=configured["simulation"].get("reading", 12.0),
                identity=configured["simulation"].get(
                    "identity", "HEWLETT-PACKARD,34401A,SIM0001,11-05-01"
                ),
                replace=options.get("replace", False),
            )
            simulated_session = self._sessions.get(alias)
            simulated_session.resource = selected_resource
            simulated_session.timeout_s = effective_timeout
        else:
            self.connect_dmm(
                selected_resource,
                transport=str(options.pop("transport", transport_cfg.get("kind", "AUTO"))),
                alias=alias,
                timeout=effective_timeout,
                **options,
            )
        return self.get_connection_state(alias=alias, refresh=True)

    @keyword("Is Connected", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def is_connected(self, alias: object | None = None) -> bool:
        """Return cached connection state without raising for an unknown alias."""
        session = self._sessions.find(alias)
        return bool(session and session.connected)

    @keyword("Get Connection State", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_connection_state(
        self,
        alias: object | None = None,
        refresh: object = False,
    ) -> dict[str, Any]:
        """Return the stable RFDS connection-state dictionary."""
        session = self._sessions.find(alias)
        requested = (
            str(alias).strip() if alias is not None and str(alias).strip() else self._sessions.active_alias
        ) or "default"
        if session is None:
            return {
                "alias": requested,
                "resource": "UNKNOWN",
                "connected": False,
                "communication_ok": False,
                "transport": "UNKNOWN",
                "identity": None,
                "timeout_s": float(self._default_timeout_s),
                "state": "disconnected",
                "simulated": False,
            }
        communication_ok = session.connected
        if as_bool(refresh, name="refresh") and session.connected:
            communication_ok = self.check_communication(session.alias)
        return session.to_connection_state(
            active=session.alias == self._sessions.active_alias,
            communication_ok=communication_ok,
        )

    @keyword("Check Communication", tags=["rfds:diagnostic", "rfds:low_risk"])
    @_evidenced
    def check_communication(self, alias: object | None = None) -> bool:
        """Perform a bounded, non-destructive identity query and return ``True``."""
        session = self._session(alias)
        response = self._execute(
            "Check Communication",
            lambda: session.driver.query("*IDN?"),
            session.alias,
        )
        if not str(response).strip():
            raise DriverProtocolError(
                "empty identity response",
                operation="Check Communication",
                alias=session.alias,
            )
        session.identity_text = str(response).strip()
        return True

    @keyword("Get Identity", tags=["rfds:identity", "rfds:low_risk"])
    @_evidenced
    def get_identity(
        self,
        alias: object | None = None,
        refresh: object = False,
    ) -> str:
        """Return cached device identity, querying only when requested or unavailable."""
        session = self._session(alias)
        if as_bool(refresh, name="refresh") or not session.identity_text:
            identity = self.identify_dmm(session.alias)
            session.identity_text = str(identity.get("raw") or "").strip()
        if not session.identity_text:
            raise DriverProtocolError(
                "device identity is unavailable",
                operation="Get Identity",
                alias=session.alias,
            )
        return session.identity_text

    @keyword("Get Driver Information", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_driver_information(self) -> dict[str, Any]:
        """Return connection-independent driver identity and compatibility metadata."""
        return {
            "name": "rf_hp34401a",
            "package_version": __version__,
            "api_version": "1.1.0",
            "api_spec": "RFDS-002",
            "api_spec_version": "1.1",
            "robot_framework_min_version": "7.0",
            "python_min_version": "3.10",
            "library_scope": "SUITE",
            "transport_types": ["visa_gpib", "serial_rs232", "simulation"],
            "capability_ids": self.get_driver_capabilities(),
            "simulation_supported": True,
            "identity_source": "device_query",
            "core_driver_version": CORE_VERSION,
            "rfds_core_range": ">=1.0,<2.0",
            "rfds_core_runtime_version": "NOT_INSTALLED",
            "release_class": "D0",
            "vendor": "HP / Agilent / Keysight",
            "model_family": "34401A",
            "supported_os": ["Windows", "Linux"],
        }

    @keyword("Export Diagnostic Bundle", tags=["rfds:diagnostic", "rfds:low_risk"])
    @_evidenced
    def export_diagnostic_bundle(self, destination: object = None) -> str | None:
        """Zip this library instance's RFDS-008 evidence run for troubleshooting.

        Works whether or not any DMM session is currently connected, and does
        not finalize the run — a disconnect-family keyword that leaves zero
        open sessions remains the point at which ``run_summary.json``/
        ``evidence_manifest.json`` are written for the last time. Returns the
        archive path, or ``None`` if ``evidence_enabled=False`` was passed to
        this library instance. ``destination`` defaults to
        ``<result_root>_diagnostic_bundle.zip`` next to the run's own result
        directory.
        """
        run = self._ensure_evidence()
        return run.export_diagnostic_bundle(None if destination in (None, "") else str(destination))

    @keyword("Set Communication Timeout", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def set_communication_timeout(
        self,
        timeout_s: object,
        alias: object | None = None,
    ) -> float:
        """Set a positive finite session or default communication timeout."""
        value = as_seconds(timeout_s, name="timeout_s")
        session = self._sessions.find(alias)
        if session is None:
            if alias is not None and str(alias).strip():
                raise DriverStateError(
                    f"DMM alias {alias!r} is not open",
                    operation="Set Communication Timeout",
                    alias=str(alias),
                )
            self._default_timeout_s = value
            return value
        self._execute(
            "Set Communication Timeout",
            lambda: session.driver._t.set_timeout(value),
            session.alias,
        )
        session.timeout_s = value
        return value

    @keyword("Get Communication Timeout", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_communication_timeout(self, alias: object | None = None) -> float:
        """Return the effective timeout for the selected session or driver default."""
        session = self._sessions.find(alias)
        if session is not None:
            return float(session.timeout_s)
        if alias is not None and str(alias).strip():
            raise DriverStateError(
                f"DMM alias {alias!r} is not open",
                operation="Get Communication Timeout",
                alias=str(alias),
            )
        return float(self._default_timeout_s)

    # ------------------------------- RFDS-002 conditional connection group
    @keyword("List Connections", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def list_connections(self) -> list[dict[str, Any]]:
        """Return one connection-state dictionary per open alias."""
        return self._sessions.states()

    @keyword("Select Connection", tags=["rfds:connection", "rfds:low_risk"])
    @_evidenced
    def select_connection(self, alias: str) -> dict[str, Any]:
        """Select an existing connection and return its state."""
        session = self._execute(
            "Select Connection", lambda: self._sessions.select(alias), alias
        )
        return session.to_connection_state(active=True)

    @keyword("Disconnect All", tags=["rfds:connection", "rfds:low_risk"])
    @_evidenced
    def disconnect_all(self) -> None:
        """Close all sessions while continuing cleanup after individual failures."""
        errors = self._sessions.close_all()
        if errors:
            raise DriverCleanupError(
                "; ".join(errors),
                operation="Disconnect All",
                details={"cleanup_errors": errors},
            )

    @keyword("Get Active Connection", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_active_connection(self) -> str | None:
        """Return the active alias or ``None`` when no session exists."""
        return self._sessions.active_alias

    # ------------------------------- RFDS-002 error-queue aliases
    @keyword("Get Device Error", tags=["rfds:diagnostic", "rfds:low_risk"])
    @_evidenced
    def get_device_error(self, alias: object | None = None) -> dict[str, Any]:
        """Read one device error record."""
        return self.read_dmm_error(alias)

    @keyword("Get All Device Errors", tags=["rfds:diagnostic", "rfds:low_risk"])
    @_evidenced
    def get_all_device_errors(
        self,
        max_count: object = 25,
        alias: object | None = None,
    ) -> list[dict[str, Any]]:
        """Drain the device error queue up to ``max_count`` records."""
        return self.get_dmm_error_queue(max_errors=max_count, alias=alias)

    @keyword("Clear Device Errors", tags=["rfds:diagnostic", "rfds:low_risk"])
    @_evidenced
    def clear_device_errors(self, alias: object | None = None) -> None:
        """Clear status and drain any remaining device error records."""
        self.clear_dmm_status(alias)
        self.get_dmm_error_queue(alias=alias)

    @keyword("Device Error Queue Should Be Empty", tags=["rfds:assertion", "rfds:low_risk"])
    @_evidenced
    def device_error_queue_should_be_empty(self, alias: object | None = None) -> None:
        """Fail unless the device error queue reports no error."""
        self.dmm_error_queue_should_be_empty(alias)

    @keyword("Reset Device", tags=["rfds:configuration", "rfds:high_risk"])
    @_evidenced
    def reset_device(
        self,
        alias: object | None = None,
        wait_until_ready: object = True,
        timeout_s: object | None = None,
    ) -> dict[str, Any]:
        """Perform the 34401A SCPI reset only after this explicit high-risk call."""
        import time

        session = self._session(alias)
        started = time.monotonic()
        if timeout_s is not None:
            self.set_communication_timeout(timeout_s, session.alias)
        self._execute(
            "Reset Device", lambda: session.driver.reset(confirm=True), session.alias
        )
        ready = True
        if as_bool(wait_until_ready, name="wait_until_ready"):
            ready = self.check_communication(session.alias)
        return {
            "reset_type": "SCPI_*RST",
            "ready": bool(ready),
            "elapsed_s": time.monotonic() - started,
            "settings_cleared": True,
        }

    # ------------------------------- RFDS-013 capability discovery
    def _capability_identity(self, mode: str) -> tuple[bool, dict[str, Any] | None]:
        connected = self.is_connected()
        identity: dict[str, Any] | None = None
        if str(mode).strip().lower() in {"live", "effective"} and connected:
            identity = self.identify_dmm()
        return connected, identity

    @keyword("Get Driver Capability Model", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_driver_capability_model(self, mode: str = "effective") -> dict[str, Any]:
        """Return the full RFDS-013 capability model.

        RFDS-002 owns ``Get Driver Capabilities`` and requires a list of IDs;
        this extension provides the detailed RFDS-013 model without changing
        that canonical return type.
        """
        connected, identity = self._capability_identity(mode)
        return self._capabilities.model(connected=connected, identity=identity, mode=mode)

    @keyword("Get Driver Capability", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_driver_capability(
        self,
        capability_id: str,
        mode: str = "effective",
    ) -> dict[str, Any]:
        """Return one capability by exact stable capability identifier."""
        connected, identity = self._capability_identity(mode)
        return self._capabilities.get(
            str(capability_id), connected=connected, identity=identity
        )

    @keyword("Find Driver Capabilities", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def find_driver_capabilities(
        self,
        capability_id: str | None = None,
        keyword_name: str | None = None,
        maximum_risk: str | None = None,
        available_only: object = False,
        mode: str = "effective",
    ) -> list[dict[str, Any]]:
        """Find capabilities using structured filters."""
        connected, identity = self._capability_identity(mode)
        return self._capabilities.find(
            capability_id=capability_id,
            keyword=keyword_name,
            maximum_risk=maximum_risk,
            available_only=as_bool(available_only, name="available_only"),
            connected=connected,
            identity=identity,
        )

    @keyword("Get Driver Features", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_driver_features(self, mode: str = "effective") -> dict[str, Any]:
        """Return normalized feature information from the capability model."""
        return self.get_driver_capability_model(mode)["features"]

    @keyword("Refresh Driver Capabilities", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def refresh_driver_capabilities(self, mode: str = "effective") -> dict[str, Any]:
        """Re-evaluate capability availability and connected identity."""
        return self.get_driver_capability_model(mode)

    @keyword("Validate Driver Capabilities", tags=["rfds:diagnostic", "rfds:low_risk"])
    @_evidenced
    def validate_driver_capabilities(self) -> dict[str, Any]:
        """Validate static capability bindings against the intended public keywords."""
        bound = [
            item["binding"]["robot_keyword"]
            for item in self.get_driver_capability_model("static")["capabilities"]
        ]
        return self._capabilities.validate_bindings(bound)

    # ------------------------------- RFDS-014 configuration API
    @keyword("Get Driver Configuration Schema", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def get_driver_configuration_schema(self) -> dict[str, Any]:
        """Return the canonical RFDS-014 JSON Schema without device I/O."""
        return self._configuration.schema()

    @keyword("Get Driver Default Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def get_driver_default_configuration(self) -> dict[str, Any]:
        """Return a copy of the safe package default configuration."""
        return self._configuration.default()

    @keyword("Get Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def get_driver_configuration(
        self,
        scope: str = "EFFECTIVE",
        alias: object | None = None,
        redact_sensitive: object = True,
        include_sources: object = False,
    ) -> dict[str, Any]:
        """Return current host-side configuration; no device state is changed."""
        del alias, redact_sensitive
        selected = str(scope).strip().upper()
        if selected == "DEFAULT":
            return self._configuration.default()
        if selected != "EFFECTIVE":
            raise DriverValidationError("scope must be DEFAULT or EFFECTIVE")
        result = self._configuration.effective(
            include_sources=as_bool(include_sources, name="include_sources")
        )
        result.setdefault("metadata", {})["configuration_fingerprint"] = self._configuration.fingerprint()
        return result

    @keyword("Validate Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def validate_driver_configuration(
        self,
        configuration: Any,
        strict: object = True,
    ) -> dict[str, Any]:
        """Validate configuration without applying or persisting it."""
        validated = self._configuration.import_json(
            configuration,
            validate_only=True,
            strict=as_bool(strict, name="strict"),
        )
        return {"valid": True, "configuration": validated, "errors": [], "warnings": []}

    @keyword("Import Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def import_driver_configuration(
        self,
        source: Any,
        validate_only: object = False,
        strict: object = True,
    ) -> dict[str, Any]:
        """Import JSON from a mapping, JSON string, or file path transactionally."""
        return self._configuration.import_json(
            source,
            validate_only=as_bool(validate_only, name="validate_only"),
            strict=as_bool(strict, name="strict"),
        )

    @keyword("Export Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def export_driver_configuration(
        self,
        destination: str | None = None,
        indent: object = 2,
    ) -> str:
        """Export canonical JSON and optionally write it atomically to a path."""
        return self._configuration.export_json(
            destination,
            indent=as_int(indent, name="indent"),
        )

    @keyword("Save Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def save_driver_configuration(
        self,
        profile_name: str,
        overwrite: object = False,
    ) -> str:
        """Persist the current host profile only after explicit authorization."""
        return self._configuration.save_profile(
            profile_name,
            overwrite=as_bool(overwrite, name="overwrite"),
        )

    @keyword("Load Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def load_driver_configuration(
        self,
        profile_name: str,
        validate_only: object = False,
    ) -> dict[str, Any]:
        """Load a named user profile and optionally validate without applying."""
        return self._configuration.load_profile(
            profile_name,
            validate_only=as_bool(validate_only, name="validate_only"),
        )

    @keyword("List Driver Configuration Profiles", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def list_driver_configuration_profiles(self) -> list[str]:
        """List explicitly persisted user profile names."""
        return self._configuration.list_profiles()

    @keyword("Delete Driver Configuration Profile", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def delete_driver_configuration_profile(self, profile_name: str) -> None:
        """Delete one named host profile; packaged defaults cannot be deleted."""
        self._configuration.delete_profile(profile_name)

    @keyword("Reset Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def reset_driver_configuration(self) -> dict[str, Any]:
        """Reset runtime host configuration to the safe package default."""
        return self._configuration.reset()

    # ------------------------------- explicit raw I/O authorization
    @keyword("Set Raw I/O Enabled", tags=["rfds:configuration", "rfds:high_risk"])
    @_evidenced
    def set_raw_io_enabled(self, enabled: object) -> bool:
        """Explicitly enable or disable guarded raw SCPI access for this instance."""
        self._allow_raw_io = as_bool(enabled, name="enabled")
        return self._allow_raw_io

    @keyword("Write Raw Command", tags=["rfds:raw_io", "rfds:high_risk"])
    @_evidenced
    def write_raw_command(self, command: str, alias: object | None = None) -> None:
        """Write a guarded raw SCPI command after explicit raw-I/O opt-in."""
        self.write_dmm_command(command, alias)

    @keyword("Query Raw Command", tags=["rfds:raw_io", "rfds:high_risk"])
    @_evidenced
    def query_raw_command(
        self,
        command: str,
        alias: object | None = None,
        timeout_s: object | None = None,
    ) -> str:
        """Query guarded raw SCPI after explicit opt-in."""
        if timeout_s is not None:
            self.set_communication_timeout(timeout_s, alias)
        return self.query_dmm_command(command, alias)

    @keyword("Read Raw Response", tags=["rfds:raw_io", "rfds:high_risk"])
    @_evidenced
    def read_raw_response(
        self,
        alias: object | None = None,
        timeout_s: object | None = None,
    ) -> str:
        """Read one already-pending raw response after explicit opt-in."""
        self._require_raw_io("Read Raw Response")
        session = self._session(alias)
        if timeout_s is not None:
            self.set_communication_timeout(timeout_s, session.alias)
        return self._execute(
            "Read Raw Response", session.driver._t.read_raw, session.alias
        )

    def _require_raw_io(self, operation: str) -> None:
        if not self._allow_raw_io:
            raise DriverStateError(
                "raw I/O is disabled; enable it explicitly using Set Raw I/O Enabled",
                operation=operation,
            )

    # ------------------------------- connection/session
    @keyword("Connect DMM", tags=['rfds:connection', 'rfds:low_risk'])
    @_evidenced
    def connect_dmm(
        self,
        resource: str,
        transport: str = "AUTO",
        alias: str = "default",
        timeout: object = "10 s",
        visa_library: str | None = None,
        baud_rate: object = 9600,
        parity: str = "none",
        data_bits: object = 8,
        stop_bits: object = 2,
        dtr_dsr: object = True,
        remote_on_connect: object = True,
        local_on_close: object = False,
        reset_on_connect: object = False,
        verify_identity: object = True,
        drain_error_queue: object = True,
        retry_queries: object = True,
        max_query_retries: object = 1,
        allow_calibration_commands: object = False,
        replace: object = False,
        raw_traffic_log: object = False,
    ) -> str:
        """Open a DMM session using AUTO, VISA, or SERIAL transport selection.

        ``AUTO`` selects SERIAL for COM and ``/dev/tty*`` resources and VISA
        otherwise. The keyword exists as the transport-neutral project API; the
        explicit VISA and serial keywords remain stable for existing suites.
        """
        resource_text = str(resource).strip()
        if not resource_text:
            raise Hp34401ARobotError("Connect DMM requires a non-empty resource")
        selected = str(transport).strip().upper() or "AUTO"
        if selected == "AUTO":
            upper = resource_text.upper()
            selected = (
                "SERIAL"
                if upper.startswith("COM") or resource_text.startswith("/dev/tty")
                else "VISA"
            )
        if selected in {"VISA", "GPIB", "USB", "LAN"}:
            return self.open_dmm_via_visa(
                resource_text,
                alias=alias,
                timeout=timeout,
                visa_library=visa_library,
                reset_on_connect=reset_on_connect,
                verify_identity=verify_identity,
                drain_error_queue=drain_error_queue,
                retry_queries=retry_queries,
                max_query_retries=max_query_retries,
                allow_calibration_commands=allow_calibration_commands,
                replace=replace,
                raw_traffic_log=raw_traffic_log,
            )
        if selected in {"SERIAL", "RS232", "RS-232"}:
            return self.open_dmm_via_serial(
                resource_text,
                alias=alias,
                baud_rate=baud_rate,
                parity=parity,
                data_bits=data_bits,
                stop_bits=stop_bits,
                timeout=timeout,
                dtr_dsr=dtr_dsr,
                remote_on_connect=remote_on_connect,
                local_on_close=local_on_close,
                verify_identity=verify_identity,
                retry_queries=retry_queries,
                max_query_retries=max_query_retries,
                allow_calibration_commands=allow_calibration_commands,
                replace=replace,
                raw_traffic_log=raw_traffic_log,
            )
        raise Hp34401ARobotError(
            f"Unsupported DMM transport {transport!r}; use AUTO, VISA, or SERIAL"
        )

    # Python compatibility for orchestration libraries written before v26.03.
    # These methods are intentionally not Robot keywords.
    def connect_to_dmm(self, resource: str, *args: Any, **kwargs: Any) -> str:
        if args and "timeout" not in kwargs:
            kwargs["timeout"] = args[0]
        return self.connect_dmm(resource, **kwargs)

    @keyword("Open DMM Via VISA", tags=['rfds:connection', 'rfds:low_risk'])
    @_evidenced
    def open_dmm_via_visa(
        self,
        resource: str,
        alias: str = "default",
        timeout: object = "10 s",
        visa_library: str | None = None,
        reset_on_connect: object = False,
        verify_identity: object = True,
        drain_error_queue: object = True,
        retry_queries: object = True,
        max_query_retries: object = 1,
        allow_calibration_commands: object = False,
        replace: object = False,
        raw_traffic_log: object = False,
    ) -> str:
        """Open a VISA/GPIB session and make ``alias`` active."""

        def action() -> str:
            dc = self._driver_config(
                timeout=timeout,
                reset_on_connect=reset_on_connect,
                verify_identity=verify_identity,
                drain_error_queue=drain_error_queue,
                retry_queries=retry_queries,
                max_query_retries=max_query_retries,
                allow_calibration_commands=allow_calibration_commands,
                raw_traffic_log=raw_traffic_log,
            )
            cfg = VisaGpibConfig(
                resource=str(resource).strip(),
                timeout_s=as_seconds(timeout, name="timeout"),
                visa_library=(str(visa_library).strip() if visa_library else None),
            )
            return self._register_connected(
                alias,
                Hp34401A.from_visa_gpib(cfg, dc),
                replace=replace,
                resource=cfg.resource,
                transport_kind="visa_gpib",
                timeout_s=cfg.timeout_s,
                options={"visa_library": cfg.visa_library},
            )

        return self._execute("Open DMM via VISA", action, alias)

    @keyword("Open DMM Via Serial", tags=['rfds:connection', 'rfds:low_risk'])
    @_evidenced
    def open_dmm_via_serial(
        self,
        port: str,
        alias: str = "default",
        baud_rate: object = 9600,
        parity: str = "none",
        data_bits: object = 8,
        stop_bits: object = 2,
        timeout: object = "10 s",
        dtr_dsr: object = True,
        remote_on_connect: object = True,
        local_on_close: object = False,
        verify_identity: object = True,
        retry_queries: object = True,
        max_query_retries: object = 1,
        allow_calibration_commands: object = False,
        replace: object = False,
        raw_traffic_log: object = False,
    ) -> str:
        """Open an RS-232 session using the instrument's supported serial settings."""

        def action() -> str:
            dc = self._driver_config(
                timeout=timeout,
                verify_identity=verify_identity,
                retry_queries=retry_queries,
                max_query_retries=max_query_retries,
                allow_calibration_commands=allow_calibration_commands,
                raw_traffic_log=raw_traffic_log,
            )
            cfg = SerialRs232Config(
                port=str(port).strip(),
                baudrate=as_int(baud_rate, name="baud_rate"),
                parity=cast(Literal["none", "even", "odd"], str(parity).strip().lower()),
                data_bits=as_int(data_bits, name="data_bits"),
                stop_bits=as_int(stop_bits, name="stop_bits"),
                timeout_s=as_seconds(timeout, name="timeout"),
                use_dtr_dsr=as_bool(dtr_dsr, name="dtr_dsr"),
                require_remote_on_connect=as_bool(remote_on_connect, name="remote_on_connect"),
                send_local_on_close=as_bool(local_on_close, name="local_on_close"),
            )
            return self._register_connected(
                alias,
                Hp34401A.from_serial(cfg, dc),
                replace=replace,
                resource=cfg.port,
                transport_kind="serial_rs232",
                timeout_s=cfg.timeout_s,
                options={"baud_rate": cfg.baudrate, "parity": cfg.parity},
            )

        return self._execute("Open DMM via serial", action, alias)

    @keyword("Open Simulated DMM", tags=['rfds:simulation', 'rfds:low_risk'])
    @_evidenced
    def open_simulated_dmm(
        self,
        alias: str = "default",
        reading: object = 12.0,
        identity: str = "HEWLETT-PACKARD,34401A,SIM0001,11-05-01",
        terminal: str = "FRONT",
        replace: object = False,
    ) -> str:
        """Open deterministic simulation. This keyword never runs automatically as fallback."""

        def action() -> str:
            value = as_float(reading, name="reading")
            responses = {
                "READ?": repr(value),
                "FETCh?": repr(value),
                "ROUTe:TERMinals?": str(terminal).strip().upper(),
                "*TST?": "0",
                "SYSTem:VERSion?": "1991.0",
            }
            transport = FakeTransport(responses=responses, idn=str(identity))
            driver = Hp34401A(transport, DriverConfig())
            return self._register_connected(
                alias,
                driver,
                replace=replace,
                resource="SIM::HP34401A",
                transport_kind="simulation",
                timeout_s=self._default_timeout_s,
                options={"simulated": True},
            )

        return self._execute("Open simulated DMM", action, alias)

    @keyword("List VISA Resources", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def list_visa_resources(self, visa_library: str | None = None) -> list[str]:
        def action() -> list[str]:
            try:
                import pyvisa
            except ImportError as exc:
                raise RuntimeError("PyVISA is not installed; install rf-hp34401a[visa]") from exc
            manager = pyvisa.ResourceManager(visa_library or "")
            try:
                return list(manager.list_resources())
            finally:
                manager.close()

        return self._execute("List VISA resources", action)

    @keyword("Select DMM", tags=['rfds:connection', 'rfds:low_risk'])
    @_evidenced
    def select_dmm(self, alias: str) -> str:
        return self._execute("Select DMM", lambda: self._sessions.select(alias).alias, alias)

    @keyword("Get Active DMM Alias", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_active_dmm_alias(self) -> str | None:
        return self._sessions.active_alias

    @keyword("Get Open DMM Aliases", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_open_dmm_aliases(self) -> list[str]:
        return self._sessions.aliases()

    @keyword("DMM Should Be Connected", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_should_be_connected(self, alias: object | None = None) -> None:
        session = self._session(alias)
        if not session.driver.is_connected():
            raise Hp34401ARobotError(f"DMM is not connected [alias={session.alias}]")

    @keyword("Close DMM", tags=['rfds:connection', 'rfds:low_risk'])
    @_evidenced
    def close_dmm(self, alias: object | None = None) -> None:
        self._execute("Close DMM", lambda: self._sessions.close(alias), alias)

    @keyword("Disconnect DMM", tags=['rfds:connection', 'rfds:low_risk'])
    @_evidenced
    def disconnect_dmm(self, alias: object | None = None) -> None:
        """Transport-neutral alias for ``Close DMM``."""
        self.close_dmm(alias)

    @keyword("Disconnect", tags=["rfds:connection", "rfds:low_risk"])
    @_evidenced
    def disconnect(self, alias: object | None = None) -> None:
        """Close one session idempotently and release its transport resources."""
        self._execute(
            "Disconnect",
            lambda: self._sessions.close(alias, idempotent=True),
            alias,
        )

    def close_connection(self, alias: object | None = None) -> None:
        """Python compatibility alias; not exposed as a Robot keyword."""
        self.close_dmm(alias)

    @keyword("Close All DMMs", tags=['rfds:connection', 'rfds:low_risk'])
    @_evidenced
    def close_all_dmms(self) -> None:
        errors = self._sessions.close_all()
        if errors:
            raise Hp34401ARobotError(
                "One or more DMM sessions failed to close: " + "; ".join(errors)
            )

    # Robot Framework listener callback; auto-keywords are disabled, so it is not exposed.
    def close(self) -> None:
        self._sessions.close_all()

    # ------------------------------- identity/health
    @keyword("Identify DMM", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def identify_dmm(self, alias: object | None = None) -> dict[str, Any]:
        session = self._session(alias)
        return self._execute(
            "Identify DMM", lambda: self._model_to_dict(session.driver.identify()), session.alias
        )

    @keyword("DMM Model Should Be 34401A", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_model_should_be_34401a(self, alias: object | None = None) -> None:
        identity = self.identify_dmm(alias)
        if "34401A" not in str(identity["model"]).upper():
            raise AssertionError(f"Expected model 34401A but received {identity['model']!r}")

    @keyword("Run DMM Self Test", tags=['rfds:diagnostic', 'rfds:medium_risk'])
    @_evidenced
    def run_dmm_self_test(self, alias: object | None = None) -> dict[str, Any]:
        session = self._session(alias)
        return self._execute(
            "Run DMM self-test",
            lambda: self._model_to_dict(session.driver.self_test()),
            session.alias,
        )

    @keyword("DMM Self Test Should Pass", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_self_test_should_pass(self, alias: object | None = None) -> None:
        result = self.run_dmm_self_test(alias)
        if not result["passed"]:
            raise AssertionError(
                f"DMM self-test failed: code={result['code']}, raw={result['raw']!r}"
            )

    @keyword("Get DMM Health", tags=['rfds:diagnostic', 'rfds:low_risk'])
    @_evidenced
    def get_dmm_health(self, alias: object | None = None) -> dict[str, Any]:
        session = self._session(alias)
        return self._execute(
            "Get DMM health", lambda: self._model_to_dict(session.driver.heartbeat()), session.alias
        )

    @keyword("Recover DMM", tags=['rfds:diagnostic', 'rfds:medium_risk'])
    @_evidenced
    def recover_dmm(self, alias: object | None = None) -> dict[str, Any]:
        session = self._session(alias)
        return self._execute(
            "Recover DMM", lambda: self._model_to_dict(session.driver.recover()), session.alias
        )

    @keyword("Clear DMM Status", tags=['rfds:diagnostic', 'rfds:low_risk'])
    @_evidenced
    def clear_dmm_status(self, alias: object | None = None) -> None:
        session = self._session(alias)
        self._execute("Clear DMM status", session.driver.clear_status, session.alias)

    @keyword("Read DMM Error", tags=['rfds:diagnostic', 'rfds:low_risk'])
    @_evidenced
    def read_dmm_error(self, alias: object | None = None) -> dict[str, Any]:
        session = self._session(alias)
        return self._execute(
            "Read DMM error",
            lambda: self._model_to_dict(session.driver.read_error()),
            session.alias,
        )

    @keyword("Get DMM Error Queue", tags=['rfds:diagnostic', 'rfds:low_risk'])
    @_evidenced
    def get_dmm_error_queue(
        self, max_errors: object = 25, alias: object | None = None
    ) -> list[dict[str, Any]]:
        session = self._session(alias)
        return self._execute(
            "Get DMM error queue",
            lambda: self._model_to_dict(
                session.driver.drain_error_queue(as_int(max_errors, name="max_errors"))
            ),
            session.alias,
        )

    @keyword("DMM Error Queue Should Be Empty", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_error_queue_should_be_empty(self, alias: object | None = None) -> None:
        errors = [item for item in self.get_dmm_error_queue(alias=alias) if item["code"] != 0]
        if errors:
            raise AssertionError(f"DMM error queue is not empty: {errors}")

    @keyword("Get DMM Input Terminal", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_dmm_input_terminal(self, alias: object | None = None) -> str:
        session = self._session(alias)
        return self._execute(
            "Get DMM input terminal", lambda: session.driver.query_terminal().value, session.alias
        )

    @keyword("Require DMM Input Terminal", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def require_dmm_input_terminal(self, expected: object, alias: object | None = None) -> None:
        session = self._session(alias)
        terminal = as_terminal(expected)
        self._execute(
            "Require DMM input terminal",
            lambda: session.driver.require_terminal(terminal),
            session.alias,
        )

    @keyword("Get DMM State", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_dmm_state(self, alias: object | None = None) -> str:
        return self._session(alias).driver.state.value

    @keyword("Get DMM Driver Version", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_dmm_driver_version(self) -> str:
        return CORE_VERSION

    @keyword("Get Robot DMM Library Version", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_robot_dmm_library_version(self) -> str:
        return __version__

    @keyword("Get Driver Capabilities", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_driver_capabilities(self) -> list[str]:
        """Return the sorted RFDS-002 capability identifiers without device I/O."""
        return self._capabilities.ids()

    @keyword("Get Driver Metadata", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_driver_metadata(self, alias: object | None = None) -> dict[str, Any]:
        """Return driver, runtime, transport, and connected-instrument metadata."""
        metadata: dict[str, Any] = {
            "driver_name": "rf_hp34401a.Hp34401ALibrary",
            "driver_version": __version__,
            "core_driver_version": CORE_VERSION,
            "driver_status": "D0_DEVELOPMENT_CANDIDATE",
            "supported_models": ["34401A"],
            "supported_transports": ["VISA_GPIB", "SERIAL_RS232", "FAKE"],
            "manufacturer": ["HP", "HEWLETT-PACKARD", "AGILENT", "KEYSIGHT"],
            "python_version": platform.python_version(),
            "robot_framework_version": ROBOT_FRAMEWORK_VERSION,
            "library_build_date": "2026-07-30",
            "git_commit": "UNKNOWN",
            "alias": None,
            "instrument_id": "UNKNOWN",
            "model": "UNKNOWN",
            "serial_number": "UNKNOWN",
            "firmware_version": "UNKNOWN",
            "transport": "UNKNOWN",
            "state": "DISCONNECTED",
        }
        if alias is not None or self._sessions.active_alias is not None:
            session = self._session(alias)
            identity = self.identify_dmm(session.alias)
            metadata.update(
                {
                    "alias": session.alias,
                    "instrument_id": identity.get("raw", "UNKNOWN"),
                    "model": identity.get("model", "UNKNOWN"),
                    "serial_number": identity.get("serial", "UNKNOWN") or "UNKNOWN",
                    "firmware_version": identity.get("firmware", "UNKNOWN") or "UNKNOWN",
                    "transport": session.driver._t.transport_type.value,
                    "state": self.get_dmm_state(session.alias),
                }
            )
        return metadata

    # ------------------------------- configuration
    @keyword("Configure DC Voltage", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_dc_voltage(
        self,
        range_value: object = "DEF",
        nplc: object = 10,
        autozero: object = "ON",
        alias: object | None = None,
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure DC voltage",
            lambda: s.driver.configure_dc_voltage(
                as_range(range_value), as_nplc(nplc), as_autozero(autozero)
            ),
            s.alias,
        )

    @keyword("Configure AC Voltage", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_ac_voltage(
        self, range_value: object = "DEF", ac_filter_hz: object = 20, alias: object | None = None
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure AC voltage",
            lambda: s.driver.configure_ac_voltage(
                as_range(range_value), as_ac_filter(ac_filter_hz)
            ),
            s.alias,
        )

    @keyword("Configure DC Current", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_dc_current(
        self,
        range_value: object = "DEF",
        nplc: object = 10,
        autozero: object = "ON",
        alias: object | None = None,
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure DC current",
            lambda: s.driver.configure_dc_current(
                as_range(range_value), as_nplc(nplc), as_autozero(autozero)
            ),
            s.alias,
        )

    @keyword("Configure AC Current", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_ac_current(
        self, range_value: object = "DEF", ac_filter_hz: object = 20, alias: object | None = None
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure AC current",
            lambda: s.driver.configure_ac_current(
                as_range(range_value), as_ac_filter(ac_filter_hz)
            ),
            s.alias,
        )

    @keyword("Configure 2 Wire Resistance", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_2wire_resistance(
        self,
        range_value: object = "DEF",
        nplc: object = 10,
        autozero: object = "ON",
        alias: object | None = None,
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure 2-wire resistance",
            lambda: s.driver.configure_2wire_resistance(
                as_range(range_value), as_nplc(nplc), as_autozero(autozero)
            ),
            s.alias,
        )

    @keyword("Configure 4 Wire Resistance", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_4wire_resistance(
        self,
        range_value: object = "DEF",
        nplc: object = 10,
        autozero: object = "ON",
        alias: object | None = None,
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure 4-wire resistance",
            lambda: s.driver.configure_4wire_resistance(
                as_range(range_value), as_nplc(nplc), as_autozero(autozero)
            ),
            s.alias,
        )

    @keyword("Configure Frequency", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_frequency(
        self, voltage_range: object = "DEF", aperture: object = 0.1, alias: object | None = None
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure frequency",
            lambda: s.driver.configure_frequency(as_range(voltage_range), as_aperture(aperture)),
            s.alias,
        )

    @keyword("Configure Period", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_period(
        self, voltage_range: object = "DEF", aperture: object = 0.1, alias: object | None = None
    ) -> None:
        s = self._session(alias)
        self._execute(
            "Configure period",
            lambda: s.driver.configure_period(as_range(voltage_range), as_aperture(aperture)),
            s.alias,
        )

    @keyword("Configure Continuity", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_continuity(self, alias: object | None = None) -> None:
        s = self._session(alias)
        self._execute("Configure continuity", s.driver.configure_continuity, s.alias)

    @keyword("Configure Diode", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def configure_diode(self, alias: object | None = None) -> None:
        s = self._session(alias)
        self._execute("Configure diode", s.driver.configure_diode, s.alias)

    # ------------------------------- measurement
    @keyword("Read DMM", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def read_dmm(self, alias: object | None = None) -> float:
        return self._measure("Read DMM", lambda d: d.read_once(), alias)

    @keyword("Measure DC Voltage", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_dc_voltage(
        self, range_value: object = "DEF", nplc: object = 10, alias: object | None = None
    ) -> float:
        return self._measure(
            "Measure DC voltage",
            lambda d: d.measure_dc_voltage(as_range(range_value), as_nplc(nplc)),
            alias,
        )

    @keyword("Measure AC Voltage", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_ac_voltage(
        self, range_value: object = "DEF", ac_filter_hz: object = 20, alias: object | None = None
    ) -> float:
        return self._measure(
            "Measure AC voltage",
            lambda d: d.measure_ac_voltage(as_range(range_value), as_ac_filter(ac_filter_hz)),
            alias,
        )

    @keyword("Measure DC Current", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_dc_current(
        self, range_value: object = "DEF", nplc: object = 10, alias: object | None = None
    ) -> float:
        return self._measure(
            "Measure DC current",
            lambda d: d.measure_dc_current(as_range(range_value), as_nplc(nplc)),
            alias,
        )

    @keyword("Measure AC Current", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_ac_current(
        self, range_value: object = "DEF", ac_filter_hz: object = 20, alias: object | None = None
    ) -> float:
        def producer(d: Hp34401A) -> MeasurementReading:
            d.configure_ac_current(as_range(range_value), as_ac_filter(ac_filter_hz))
            return d.read_once()

        return self._measure("Measure AC current", producer, alias)

    @keyword("Measure 2 Wire Resistance", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_2wire_resistance(
        self, range_value: object = "DEF", nplc: object = 10, alias: object | None = None
    ) -> float:
        return self._measure(
            "Measure 2-wire resistance",
            lambda d: d.measure_2wire_resistance(as_range(range_value), as_nplc(nplc)),
            alias,
        )

    @keyword("Measure 4 Wire Resistance", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_4wire_resistance(
        self, range_value: object = "DEF", nplc: object = 10, alias: object | None = None
    ) -> float:
        return self._measure(
            "Measure 4-wire resistance",
            lambda d: d.measure_4wire_resistance(as_range(range_value), as_nplc(nplc)),
            alias,
        )

    @keyword("Measure Frequency", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_frequency(
        self, voltage_range: object = "DEF", aperture: object = 0.1, alias: object | None = None
    ) -> float:
        def producer(d: Hp34401A) -> MeasurementReading:
            d.configure_frequency(as_range(voltage_range), as_aperture(aperture))
            return d.read_once()

        return self._measure("Measure frequency", producer, alias)

    @keyword("Measure Period", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_period(
        self, voltage_range: object = "DEF", aperture: object = 0.1, alias: object | None = None
    ) -> float:
        def producer(d: Hp34401A) -> MeasurementReading:
            d.configure_period(as_range(voltage_range), as_aperture(aperture))
            return d.read_once()

        return self._measure("Measure period", producer, alias)

    @keyword("Measure Continuity", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_continuity(self, alias: object | None = None) -> float:
        def producer(d: Hp34401A) -> MeasurementReading:
            d.configure_continuity()
            return d.read_once()

        return self._measure("Measure continuity", producer, alias)

    @keyword("Measure Diode", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def measure_diode(self, alias: object | None = None) -> float:
        def producer(d: Hp34401A) -> MeasurementReading:
            d.configure_diode()
            return d.read_once()

        return self._measure("Measure diode", producer, alias)

    def _stable_profile(
        self,
        expected_ohm: object | None,
        range_value: object,
        nplc: object,
        final_nplc: object | None,
        min_settle: object,
        max_wait: object,
        sample_interval: object,
        window_size: object,
        max_stdev_ohm: object | None,
        max_relative_stdev: object | None,
        max_slope_relative_per_s: object | None,
        four_wire: object,
    ) -> StabilityProfile:
        final = (
            None
            if final_nplc is None or str(final_nplc).strip().lower() in {"", "none", "${none}"}
            else as_nplc(final_nplc)
        )
        return StabilityProfile(
            expected_ohm=as_optional_float(expected_ohm, name="expected_ohm"),
            range_ohm=as_range(range_value),
            nplc=as_nplc(nplc),
            final_nplc=final,
            min_settle_s=as_seconds(min_settle, name="min_settle"),
            max_wait_s=as_seconds(max_wait, name="max_wait"),
            sample_interval_s=as_seconds(sample_interval, name="sample_interval"),
            window_size=as_int(window_size, name="window_size"),
            max_stdev_ohm=as_optional_float(max_stdev_ohm, name="max_stdev_ohm"),
            max_relative_stdev=as_optional_float(max_relative_stdev, name="max_relative_stdev"),
            max_slope_relative_per_s=as_optional_float(
                max_slope_relative_per_s, name="max_slope_relative_per_s"
            ),
            four_wire=as_bool(four_wire, name="four_wire"),
        )

    @keyword("Try Read Stable Resistance", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def try_read_stable_resistance(
        self,
        expected_ohm: object | None = None,
        range_value: object = "AUTO",
        nplc: object = 10,
        final_nplc: object | None = 100,
        min_settle: object = "500 ms",
        max_wait: object = "20 s",
        sample_interval: object = "200 ms",
        window_size: object = 5,
        max_stdev_ohm: object | None = None,
        max_relative_stdev: object | None = 0.0005,
        max_slope_relative_per_s: object | None = 0.0005,
        four_wire: object = False,
        alias: object | None = None,
    ) -> dict[str, Any]:
        session = self._session(alias)
        profile = self._stable_profile(
            expected_ohm,
            range_value,
            nplc,
            final_nplc,
            min_settle,
            max_wait,
            sample_interval,
            window_size,
            max_stdev_ohm,
            max_relative_stdev,
            max_slope_relative_per_s,
            four_wire,
        )
        result = self._execute(
            "Try read stable resistance",
            lambda: session.driver.read_stable_resistance(profile),
            session.alias,
        )
        if result.reading is not None:
            session.last_reading = result.reading
        data = self._model_to_dict(result)
        data["alias"] = session.alias
        data["library_version"] = __version__
        data["driver_version"] = CORE_VERSION
        return data

    @keyword("Read Stable Resistance", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def read_stable_resistance(
        self,
        expected_ohm: object | None = None,
        range_value: object = "AUTO",
        nplc: object = 10,
        final_nplc: object | None = 100,
        min_settle: object = "500 ms",
        max_wait: object = "20 s",
        sample_interval: object = "200 ms",
        window_size: object = 5,
        max_stdev_ohm: object | None = None,
        max_relative_stdev: object | None = 0.0005,
        max_slope_relative_per_s: object | None = 0.0005,
        four_wire: object = False,
        alias: object | None = None,
    ) -> float:
        """Return a stable resistance or fail without fabricating a reading."""
        result = self.try_read_stable_resistance(
            expected_ohm=expected_ohm,
            range_value=range_value,
            nplc=nplc,
            final_nplc=final_nplc,
            min_settle=min_settle,
            max_wait=max_wait,
            sample_interval=sample_interval,
            window_size=window_size,
            max_stdev_ohm=max_stdev_ohm,
            max_relative_stdev=max_relative_stdev,
            max_slope_relative_per_s=max_slope_relative_per_s,
            four_wire=four_wire,
            alias=alias,
        )
        if not result["stable"] or result["value"] is None:
            raise MeasurementNotStableError(result["reason"])
        return float(result["value"])

    @keyword("Get Last DMM Reading", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_last_dmm_reading(self, alias: object | None = None) -> dict[str, Any]:
        session = self._session(alias)
        if session.last_reading is None:
            raise Hp34401ARobotError(f"No DMM reading is available [alias={session.alias}]")
        return self._reading_to_dict(session.last_reading, session)

    @keyword("Get Last DMM Reading Value", tags=['rfds:query', 'rfds:low_risk'])
    @_evidenced
    def get_last_dmm_reading_value(self, alias: object | None = None) -> float:
        data = self.get_last_dmm_reading(alias)
        if not data["is_valid"] or data["is_overload"] or data["value"] is None:
            raise Hp34401ARobotError("Last DMM reading is not a valid scalar")
        return float(data["value"])

    # ------------------------------- triggers
    @keyword("Set DMM Trigger Source", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def set_dmm_trigger_source(self, source: object, alias: object | None = None) -> None:
        s = self._session(alias)
        self._execute(
            "Set DMM trigger source",
            lambda: s.driver.set_trigger_source(as_trigger_source(source)),
            s.alias,
        )

    @keyword("Initiate DMM Measurement", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def initiate_dmm_measurement(self, alias: object | None = None) -> None:
        s = self._session(alias)
        self._execute("Initiate DMM measurement", s.driver.initiate, s.alias)

    @keyword("Send DMM Bus Trigger", tags=['rfds:configuration', 'rfds:low_risk'])
    @_evidenced
    def send_dmm_bus_trigger(self, alias: object | None = None) -> None:
        s = self._session(alias)
        self._execute("Send DMM bus trigger", s.driver.trigger_bus, s.alias)

    @keyword("Fetch DMM Readings", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def fetch_dmm_readings(self, alias: object | None = None) -> list[dict[str, Any]]:
        s = self._session(alias)
        readings = self._execute("Fetch DMM readings", s.driver.fetch, s.alias)
        if readings:
            s.last_reading = readings[-1]
        return [self._reading_to_dict(r, s) for r in readings]

    @keyword("Read DMM Once With Bus Trigger", tags=['rfds:measurement', 'rfds:low_risk'])
    @_evidenced
    def read_dmm_once_with_bus_trigger(self, alias: object | None = None) -> float:
        return self._measure("Read DMM once with bus trigger", lambda d: d.read_once_bus(), alias)

    # ------------------------------- assertions
    @keyword("DMM Reading Should Be Valid", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_reading_should_be_valid(self, alias: object | None = None) -> None:
        data = self.get_last_dmm_reading(alias)
        if not data["is_valid"] or data["value"] is None:
            raise AssertionError(f"Invalid DMM reading: {data}")

    @keyword("DMM Reading Should Not Be Overload", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_reading_should_not_be_overload(self, alias: object | None = None) -> None:
        data = self.get_last_dmm_reading(alias)
        if data["is_overload"]:
            raise AssertionError(f"DMM reading is overload: {data}")

    def _value_for_assertion(self, alias: object | None) -> tuple[float, dict[str, Any]]:
        data = self.get_last_dmm_reading(alias)
        if not data["is_valid"] or data["is_overload"] or data["value"] is None:
            raise AssertionError(f"Cannot assert limits for invalid reading: {data}")
        return float(data["value"]), data

    @keyword("DMM Reading Should Be Between", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_reading_should_be_between(
        self, minimum: object, maximum: object, alias: object | None = None
    ) -> None:
        value, data = self._value_for_assertion(alias)
        low, high = as_float(minimum, name="minimum"), as_float(maximum, name="maximum")
        if low > high:
            raise ValueError("minimum must be <= maximum")
        if not low <= value <= high:
            raise AssertionError(
                f"{data['alias']} {data['function']} reading {value} {data['unit']} is outside [{low}, {high}]"
            )

    @keyword("DMM Reading Should Be Close To", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_reading_should_be_close_to(
        self,
        expected: object,
        absolute_tolerance: object = 0.0,
        relative_tolerance: object = 0.0,
        alias: object | None = None,
    ) -> None:
        value, data = self._value_for_assertion(alias)
        exp = as_float(expected, name="expected")
        abs_tol = as_float(absolute_tolerance, name="absolute_tolerance")
        rel_tol = as_float(relative_tolerance, name="relative_tolerance")
        if abs_tol < 0 or rel_tol < 0:
            raise ValueError("tolerances must be >= 0")
        if not math.isclose(value, exp, rel_tol=rel_tol, abs_tol=abs_tol):
            raise AssertionError(
                f"{data['alias']} {data['function']} reading {value} {data['unit']} is not close to {exp}; abs_tol={abs_tol}, rel_tol={rel_tol}"
            )

    @keyword("DMM Reading Should Be Greater Than", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_reading_should_be_greater_than(
        self, minimum: object, alias: object | None = None
    ) -> None:
        value, data = self._value_for_assertion(alias)
        limit = as_float(minimum, name="minimum")
        if not value > limit:
            raise AssertionError(
                f"{data['alias']} reading {value} {data['unit']} is not greater than {limit}"
            )

    @keyword("DMM Reading Should Be Less Than", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_reading_should_be_less_than(self, maximum: object, alias: object | None = None) -> None:
        value, data = self._value_for_assertion(alias)
        limit = as_float(maximum, name="maximum")
        if not value < limit:
            raise AssertionError(
                f"{data['alias']} reading {value} {data['unit']} is not less than {limit}"
            )

    @keyword("Stable Resistance Should Be Between", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def stable_resistance_should_be_between(
        self, result: dict[str, Any], minimum: object, maximum: object
    ) -> None:
        if not result.get("stable") or result.get("value") is None:
            raise AssertionError(f"Resistance was not stable: {result.get('reason')}")
        value = float(result["value"])
        low, high = as_float(minimum, name="minimum"), as_float(maximum, name="maximum")
        if not low <= value <= high:
            raise AssertionError(f"Stable resistance {value} Ohm is outside [{low}, {high}]")

    @keyword("DMM Should Have No Errors", tags=['rfds:assertion', 'rfds:low_risk'])
    @_evidenced
    def dmm_should_have_no_errors(self, context: str = "", alias: object | None = None) -> None:
        s = self._session(alias)
        self._execute(
            "Assert DMM has no errors", lambda: s.driver.assert_no_error(str(context)), s.alias
        )

    # ------------------------------- controlled raw SCPI
    @keyword("Write DMM Command", tags=['rfds:raw_io', 'rfds:high_risk'])
    @_evidenced
    def write_dmm_command(self, command: str, alias: object | None = None) -> None:
        self._require_raw_io("Write DMM Command")
        s = self._session(alias)
        logger.debug(f"{s.alias}: raw SCPI write {command!r}")
        self._execute("Write DMM command", lambda: s.driver.write(str(command)), s.alias)

    @keyword("Query DMM Command", tags=['rfds:raw_io', 'rfds:high_risk'])
    @_evidenced
    def query_dmm_command(self, command: str, alias: object | None = None) -> str:
        self._require_raw_io("Query DMM Command")
        s = self._session(alias)
        logger.debug(f"{s.alias}: raw SCPI query {command!r}")
        return self._execute("Query DMM command", lambda: s.driver.query(str(command)), s.alias)
