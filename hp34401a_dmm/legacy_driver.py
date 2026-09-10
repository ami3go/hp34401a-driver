"""High-level, production-safe HP 34401A driver (spec sections 8, 11-16, 20-24).

This module owns the safety-critical command sequencing:
  * one-outstanding-query enforcement (also enforced in the transport),
  * READ?-with-BUS rejection and the INITiate -> wait -> *TRG -> FETCh? flow,
  * overload classification, never returning a fabricated value,
  * R1: measurement-read failures re-measure, never re-fetch stale data,
  * R6: settings are re-applied after every CONFigure,
  * calibration/reset safety gating.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import logging
import re
import threading
import time
from collections.abc import Callable

from . import parser
from .config import DriverConfig, SerialRs232Config, StabilityProfile, VisaGpibConfig
from .enums import (
    MAX_COUNT,
    MAX_INTERNAL_READINGS,
    NPLC_FUNCTIONS,
    RANGE_TABLES,
    AcFilterHz,
    Aperture,
    AutoRange,
    AutozeroMode,
    CommandState,
    InputTerminal,
    MeasurementFunction,
    Nplc,
    TriggerSource,
)
from .errors import (
    Hp34401AError,
    InstrumentConnectionError,
    InstrumentTimeoutError,
    ProtocolError,
    SafetyError,
    scpi_error_for,
)
from .measurement import (
    ErrorRecord,
    HealthReport,
    Identity,
    MeasurementReading,
    RecoveryReport,
    SelfTestResult,
)
from .transports import Transport

_log = logging.getLogger("hp34401a_dmm")

# Queries that are safe to retry after a timeout only after transport clear.
# READ? is intentionally NOT listed: a timed-out READ? may have triggered a
# measurement; high-level read_once() performs a fresh re-measure instead.
_RETRYABLE_QUERY_PREFIXES = (
    "*IDN?",
    "SYSTEM:ERROR?",
    "SYST:ERR?",
    "SYSTEM:VERSION?",
    "SYST:VERS?",
    "*STB?",
    "*ESR?",
    "ROUTE:TERMINALS?",
    "ROUT:TERM?",
    "FETCH?",
    "FETC?",
    "DATA:POINTS?",
    "DATA:POIN?",
)
_NON_RETRYABLE_QUERY_PREFIXES = ("READ?", "*TST?")

# Calibration command guard (spec section 24).
_CAL_COMMAND_RE = re.compile(r"^\s*CAL(ibration)?\b", re.IGNORECASE)
_RWLOCK_RE = re.compile(r"RWL(ock)?", re.IGNORECASE)

_CONFIGURE_MNEMONIC = {
    MeasurementFunction.VOLT_DC: "CONFigure:VOLTage:DC",
    MeasurementFunction.VOLT_AC: "CONFigure:VOLTage:AC",
    MeasurementFunction.CURR_DC: "CONFigure:CURRent:DC",
    MeasurementFunction.CURR_AC: "CONFigure:CURRent:AC",
    MeasurementFunction.RES_2W: "CONFigure:RESistance",
    MeasurementFunction.RES_4W: "CONFigure:FRESistance",
    MeasurementFunction.FREQ: "CONFigure:FREQuency",
    MeasurementFunction.PERIOD: "CONFigure:PERiod",
    MeasurementFunction.CONTINUITY: "CONFigure:CONTinuity",
    MeasurementFunction.DIODE: "CONFigure:DIODe",
}

_SENSE_MNEMONIC = {
    MeasurementFunction.VOLT_DC: "VOLTage:DC",
    MeasurementFunction.CURR_DC: "CURRent:DC",
    MeasurementFunction.RES_2W: "RESistance",
    MeasurementFunction.RES_4W: "FRESistance",
    MeasurementFunction.VOLT_AC: "VOLTage:AC",
    MeasurementFunction.CURR_AC: "CURRent:AC",
    MeasurementFunction.FREQ: "FREQuency",
    MeasurementFunction.PERIOD: "PERiod",
}


def estimate_measurement_timeout_s(
    function: MeasurementFunction,
    nplc: float | None,
    aperture_s: float | None,
    sample_count: int,
    trigger_count: int,
    trigger_delay_s: float,
    ac_filter_hz: float | None,
    line_frequency_hz: int,
    autozero: AutozeroMode = AutozeroMode.ON,
    margin_s: float = 2.0,
) -> float:
    """Estimate a finite measurement timeout from configuration (spec section 15, R3/R4)."""
    if line_frequency_hz not in (50, 60):
        line_frequency_hz = 50  # R4 conservative default

    # Per-reading integration time.
    if nplc is not None:
        per_reading = nplc / line_frequency_hz
    elif aperture_s is not None:
        per_reading = aperture_s
    elif ac_filter_hz is not None:
        # AC settling dominated by the filter; ~ a few cycles of the filter.
        per_reading = max(0.6, 7.0 / ac_filter_hz)
    else:
        per_reading = 0.1

    # R3: autozero ON/ONCE roughly doubles per-reading time.
    autozero_factor = 2.0 if autozero in (AutozeroMode.ON, AutozeroMode.ONCE) else 1.0

    settling_margin_s = 0.5
    if function in (MeasurementFunction.VOLT_AC, MeasurementFunction.CURR_AC):
        settling_margin_s = 1.0

    total = (
        margin_s
        + sample_count * trigger_count * per_reading * autozero_factor
        + trigger_delay_s * trigger_count
        + settling_margin_s
    )
    return float(total)


class Hp34401A:
    """High-level production-safe HP 34401A DMM driver."""

    def __init__(self, transport: Transport, driver_config: DriverConfig | None = None) -> None:
        self._t = transport
        self._cfg = driver_config or DriverConfig()
        self._state = CommandState.CLOSED
        self._identity: Identity | None = None
        self._scpi_version: str | None = None
        self._reconnect_count = 0
        self._trigger_source = TriggerSource.IMMEDIATE
        self._terminal: InputTerminal | None = None
        # R1/R6: remember how to re-apply the active configuration for re-measure.
        self._last_configure: Callable[[], None] | None = None
        self._active_function: MeasurementFunction | None = None
        self._active_nplc: float | None = None
        self._active_aperture: float | None = None
        self._active_autozero: AutozeroMode = AutozeroMode.ON
        self._active_ac_filter: float | None = None
        self._is_serial = transport.transport_type.name == "SERIAL_RS232"
        # Prevent recursive timeout-retry while the recovery routine itself is
        # using status/error queries.
        self._in_recovery = False
        # Driver-level sequence lock: the transport lock protects bytes on the
        # wire, but production measurements are multi-command SCPI sequences.
        # This RLock prevents configure/read/trigger flows from interleaving
        # across application threads when DriverConfig.thread_safe=True.
        self._op_lock = threading.RLock()
        # Optional RFDS-008 protocol-trace hook, set by the RF adapter layer
        # (rf_hp34401a/library.py) once a session's EvidenceRun exists. Called as
        # trace_callback(direction, text) with direction "outbound"/"inbound" for
        # every SCPI command/query this driver sends, regardless of which of the
        # three transports (VISA/serial/Prologix) carried it. None by default so
        # this core driver has no dependency on the evidence layer.
        self.trace_callback: Callable[[str, str], None] | None = None

    def _locked(self) -> contextlib.AbstractContextManager[object]:
        return self._op_lock if self._cfg.thread_safe else contextlib.nullcontext()

    # ------------------------------------------------------------------ factories
    @classmethod
    def from_serial(
        cls, config: SerialRs232Config, driver_config: DriverConfig | None = None
    ) -> Hp34401A:
        from .serial_transport import SerialRs232Transport

        dc = driver_config or DriverConfig()
        transport = SerialRs232Transport(config, raw_traffic_log=dc.raw_traffic_log)
        return cls(transport, dc)

    @classmethod
    def from_visa_gpib(
        cls, config: VisaGpibConfig, driver_config: DriverConfig | None = None
    ) -> Hp34401A:
        from .visa_transport import VisaGpibTransport

        dc = driver_config or DriverConfig()
        transport = VisaGpibTransport(config, raw_traffic_log=dc.raw_traffic_log)
        return cls(transport, dc)

    # ------------------------------------------------------------------ context
    def __enter__(self) -> Hp34401A:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ connection
    def connect(self) -> None:
        with self._locked():
            try:
                self._t.open()
                self._t.set_timeout(self._cfg.default_timeout_s)

                if self._is_serial:
                    self._connect_serial()
                else:
                    self._connect_visa()

                if self._cfg.verify_identity_on_connect:
                    self._identity = self.identify()
                    self._validate_identity(self._identity)
                    try:
                        self._scpi_version = self.query("SYSTem:VERSion?")
                    except Hp34401AError:
                        self._scpi_version = None

                if self._cfg.drain_error_queue_on_connect:
                    pre_existing = self.drain_error_queue()
                    for rec in pre_existing:
                        if not rec.is_no_error:
                            _log.warning("Pre-existing instrument error on connect: %s", rec)

                if self._cfg.clear_status_on_connect:
                    self.clear_status()

                if self._cfg.reset_on_connect:
                    self.reset(confirm=True)

                self._state = CommandState.CONNECTED_REMOTE
            except Exception:
                try:
                    self._t.close()
                finally:
                    self._state = CommandState.CLOSED
                raise

    def _validate_identity(self, identity: Identity) -> None:
        if not parser.looks_like_34401a(identity.raw):
            raise InstrumentConnectionError(
                "Connected instrument does not look like an HP/Agilent/Keysight "
                f"34401A DMM: {identity.raw!r}. Check the VISA/GPIB resource, "
                "RS-232 port, cable, and rack addressing before production use."
            )

    def _connect_serial(self) -> None:
        scfg = getattr(self._t, "config", None)
        if scfg is not None and getattr(scfg, "recover_on_connect", False):
            self._t.write_raw("\x03")
            self._t.clear()
        # RS-232 requires remote mode (spec section 13.1).
        self._t.write("SYSTem:REMote")
        self._state = CommandState.CONNECTED_REMOTE
        # R2: verify identity looks right; a garbled IDN means a settings mismatch.
        raw = self.query("*IDN?")
        if not parser.looks_like_34401a(raw):
            raise InstrumentConnectionError(
                "RS-232 *IDN? did not return a recognisable 34401A identity "
                f"(got {raw!r}). This usually means the front-panel parity/data-bits/"
                "baud do not match the driver config. The instrument factory default "
                "is EVEN parity / 7 data bits; the driver default is none/8 (R2)."
            )
        self._identity = Identity(*parser.parse_identity(raw), raw=raw)

    def _connect_visa(self) -> None:
        if getattr(getattr(self._t, "config", None), "clear_on_connect", False):
            self._t.clear()
        self._state = CommandState.CONNECTED_REMOTE

    def close(self) -> None:
        with self._locked():
            try:
                if self._is_serial:
                    scfg = getattr(self._t, "config", None)
                    if scfg is not None and getattr(scfg, "send_local_on_close", False):
                        try:
                            self._t.write("SYSTem:LOCal")
                        except Hp34401AError:
                            pass
            finally:
                self._t.close()
                self._state = CommandState.CLOSED

    def is_connected(self) -> bool:
        return self._t.is_open() and self._state != CommandState.CLOSED

    # ------------------------------------------------------------------ raw SCPI
    def write(self, command: str) -> None:
        with self._locked():
            self._guard_safety(command)
            if self.trace_callback is not None:
                self.trace_callback("outbound", command)
            try:
                self._t.write(command)
            except InstrumentTimeoutError:
                self._state = CommandState.ERROR_RECOVERY
                raise
            except Hp34401AError:
                self._state = CommandState.ERROR_RECOVERY
                raise

    def query(self, command: str) -> str:
        """Send one SCPI query with safe timeout retry.

        A timeout can leave a late response in the instrument/adapter output
        buffer. Retrying blindly is unsafe because the next query may read stale
        data. Therefore every retry is preceded by transport clear and a short
        stale-output flush. ``READ?`` is not retried here; high-level
        ``read_once()`` recovers and performs a fresh measurement instead.
        """
        with self._locked():
            self._guard_safety(command)
            if self.trace_callback is not None:
                self.trace_callback("outbound", command)
            attempts_left = (
                self._cfg.max_query_retries
                if self._should_retry_timeout_query(command)
                else 0
            )
            last_timeout: InstrumentTimeoutError | None = None

            for attempt in range(attempts_left + 1):
                try:
                    self._state = CommandState.HAS_UNREAD_OUTPUT
                    resp = self._t.query(command)
                    self._state = CommandState.CONNECTED_REMOTE
                    if self.trace_callback is not None:
                        self.trace_callback("inbound", resp)
                    if attempt > 0:
                        _log.warning(
                            "Query %r succeeded after %d timeout retry attempt(s)",
                            command,
                            attempt,
                        )
                    return resp
                except InstrumentTimeoutError as exc:
                    last_timeout = exc
                    self._state = CommandState.ERROR_RECOVERY
                    if attempt >= attempts_left:
                        raise
                    _log.warning(
                        "Timeout during query %r; clearing transport before retry %d/%d",
                        command,
                        attempt + 1,
                        attempts_left,
                    )
                    self._recover_before_query_retry()
                    if self._cfg.query_retry_delay_s > 0:
                        time.sleep(self._cfg.query_retry_delay_s)
                except Hp34401AError:
                    self._state = CommandState.ERROR_RECOVERY
                    raise

            # Unreachable, but keeps type checkers happy.
            assert last_timeout is not None
            raise last_timeout

    def _should_retry_timeout_query(self, command: str) -> bool:
        if not self._cfg.retry_queries or self._cfg.max_query_retries <= 0:
            return False
        if self._in_recovery:
            return False
        normalized = _normalize_scpi_query(command)
        if any(normalized.startswith(prefix) for prefix in _NON_RETRYABLE_QUERY_PREFIXES):
            return False
        if self._cfg.retry_all_queries_on_timeout:
            return True
        return any(normalized.startswith(prefix) for prefix in _RETRYABLE_QUERY_PREFIXES)

    def _recover_before_query_retry(self) -> None:
        """Recover stale output without querying the error queue recursively."""
        self._transport_recover(drain_errors=False)

    def query_float(self, command: str) -> float:
        return parser.parse_float(self.query(command))

    def query_int(self, command: str) -> int:
        return int(round(self.query_float(command)))

    def _guard_safety(self, command: str) -> None:
        if _CAL_COMMAND_RE.match(command) and not self._cfg.allow_calibration_commands:
            raise SafetyError(
                "Calibration commands are blocked by default. Set "
                "allow_calibration_commands=True and use an explicit calibration task."
            )
        if _RWLOCK_RE.search(command):
            raise SafetyError("SYSTem:RWLock is not permitted unless explicitly requested.")

    # ------------------------------------------------------------------ identity / health
    def identify(self) -> Identity:
        raw = self.query("*IDN?")
        ident = Identity(*parser.parse_identity(raw), raw=raw)
        self._identity = ident
        return ident

    def self_test(self) -> SelfTestResult:
        # R8: dedicated long timeout for *TST?.
        self._t.set_timeout(self._cfg.self_test_timeout_s)
        try:
            raw = self.query("*TST?")
        finally:
            self._t.set_timeout(self._cfg.default_timeout_s)
        code = parser.parse_float(raw)
        passed = code == 0
        return SelfTestResult(
            passed=passed,
            code=int(code),
            raw=raw,
            message="self-test passed" if passed else "self-test FAILED",
        )

    def clear_status(self) -> None:
        self.write("*CLS")

    def reset(self, confirm: bool = False) -> None:
        # spec section 24: *RST requires explicit confirmation.
        if not confirm:
            raise SafetyError("reset() requires confirm=True (sends *RST).")
        self.write("*RST")
        # *RST does not clear the error queue (spec section 3); state is unconfigured.
        self._state = CommandState.CONNECTED_REMOTE
        self._trigger_source = TriggerSource.IMMEDIATE
        self._active_function = None
        self._last_configure = None

    def heartbeat(self) -> HealthReport:
        now = _dt.datetime.now(_dt.timezone.utc)
        try:
            ident = self._identity or self.identify()
            pending = self.drain_error_queue()
            real = tuple(r for r in pending if not r.is_no_error)
            return HealthReport(
                connected=self.is_connected(),
                identity=ident,
                error_queue_clean=len(real) == 0,
                pending_errors=real,
                state=self._state.value,
                timestamp_utc=now,
            )
        except Hp34401AError as exc:
            return HealthReport(
                connected=False,
                identity=self._identity,
                error_queue_clean=False,
                pending_errors=(),
                state=self._state.value,
                timestamp_utc=now,
                message=str(exc),
            )

    def recover(self) -> RecoveryReport:
        actions: list[str] = []
        try:
            self._transport_recover(actions)
            # reconfigure if we know how
            if self._last_configure is not None:
                self._last_configure()
                actions.append("reconfigure")
            self._state = (
                CommandState.CONFIGURED
                if self._last_configure
                else CommandState.CONNECTED_REMOTE
            )
            return RecoveryReport(True, tuple(actions), self._state.value)
        except Hp34401AError as exc:
            return RecoveryReport(False, tuple(actions), self._state.value, str(exc))

    def _transport_recover(
        self, actions: list[str] | None = None, *, drain_errors: bool = True
    ) -> None:
        """Spec section 16: clear -> short flush -> optional drain.

        During query-timeout retry we deliberately skip error-queue draining so
        recovery does not recursively call query() before the original command
        has been retried.
        """
        acts = actions if actions is not None else []
        self._in_recovery = True
        try:
            self._t.clear()
            acts.append("transport_clear")
            # A post-clear raw read can otherwise block for the full measurement
            # timeout when there is no stale output. Use a short timeout for recovery
            # and then restore the normal default timeout.
            self._t.set_timeout(0.2)
            try:
                try:
                    self._t.read_raw()  # flush any stale output if present
                    acts.append("flush_stale_output")
                except Hp34401AError:
                    pass
            finally:
                self._t.set_timeout(self._cfg.default_timeout_s)
            if self._is_serial:
                # Re-assert remote after a device clear on RS-232 (R-note).
                try:
                    self._t.write("SYSTem:REMote")
                    acts.append("reassert_remote")
                except Hp34401AError:
                    pass
            try:
                if drain_errors:
                    self.drain_error_queue()
                    acts.append("drain_error_queue")
            except Hp34401AError:
                pass
        finally:
            self._in_recovery = False

    # ------------------------------------------------------------------ errors
    def read_error(self) -> ErrorRecord:
        raw = self.query("SYSTem:ERRor?")
        parsed = parser.parse_error(raw)
        return ErrorRecord(parsed.code, parsed.message, parsed.raw)

    def drain_error_queue(self, max_errors: int = 25) -> list[ErrorRecord]:
        out: list[ErrorRecord] = []
        for _ in range(max_errors):
            rec = self.read_error()
            out.append(rec)
            if rec.is_no_error:
                break
        return out

    def assert_no_error(self, context: str = "") -> None:
        rec = self.read_error()
        if not rec.is_no_error:
            # drain the rest so the queue is clean before we raise
            self.drain_error_queue()
            message = f"{context}: {rec.message}" if context else rec.message
            raise scpi_error_for(rec.code, message, rec.raw)

    # ------------------------------------------------------------------ terminals
    def query_terminal(self) -> InputTerminal:
        raw = self.query("ROUTe:TERMinals?").strip().upper()
        if raw.startswith("FRON"):
            self._terminal = InputTerminal.FRONT
        elif raw.startswith("REAR"):
            self._terminal = InputTerminal.REAR
        else:
            self._terminal = InputTerminal.UNKNOWN
        return self._terminal

    def require_terminal(self, expected: InputTerminal) -> None:
        actual = self.query_terminal()
        if actual != expected:
            raise Hp34401AError(
                f"Input terminal mismatch: step requires {expected.value} but "
                f"instrument reports {actual.value}. Failing safely (spec section 18)."
            )

    # ------------------------------------------------------------------ validation
    @staticmethod
    def _validate_range(function: MeasurementFunction, range_value: float | AutoRange) -> str:
        if isinstance(range_value, AutoRange):
            # The 34401A CONFigure/MEASure range argument accepts MIN/MAX/DEF.
            # It does not use AUTO as a range token; use DEF for autorange and
            # then explicitly enable SENSe:<func>:RANGe:AUTO ON below.
            return "DEF" if range_value == AutoRange.AUTO else range_value.value
        table = RANGE_TABLES.get(function)
        if table is not None and not any(abs(range_value - r) <= 1e-9 * max(1.0, r) for r in table):
            raise ValueError(
                f"Unsupported {function.name} range {range_value!r}; valid: {list(table)}"
            )
        # Emit a clean numeric token.
        return repr(float(range_value)) if range_value != int(range_value) else str(int(range_value))

    @staticmethod
    def _validate_counts(sample_count: int, trigger_count: int) -> None:
        for n, label in ((sample_count, "sample_count"), (trigger_count, "trigger_count")):
            if n < 1:
                raise ValueError(f"{label} must be >= 1")
            if n > MAX_COUNT:
                raise ValueError(f"{label} exceeds instrument max {MAX_COUNT}")
        if sample_count * trigger_count > MAX_INTERNAL_READINGS:
            raise ValueError(
                f"sample_count*trigger_count ({sample_count * trigger_count}) exceeds the "
                f"{MAX_INTERNAL_READINGS}-reading internal memory. Reduce counts or use "
                "the streaming/INFinite path (R5)."
            )

    # ------------------------------------------------------------------ configure
    def _apply_configure(
        self,
        function: MeasurementFunction,
        range_value: float | AutoRange,
        *,
        nplc: Nplc | None = None,
        autozero: AutozeroMode = AutozeroMode.ON,
        ac_filter_hz: AcFilterHz | None = None,
        aperture_s: Aperture | None = None,
    ) -> None:
        """R6: re-apply ALL settings after CONFigure (which resets state)."""
        with self._locked():
            range_token = self._validate_range(function, range_value)
            conf = _CONFIGURE_MNEMONIC[function]
            if function in (MeasurementFunction.CONTINUITY, MeasurementFunction.DIODE):
                self.write(conf)
            else:
                self.write(f"{conf} {range_token},DEF")

            # Autorange explicit. AUTO is mapped to DEF in CONFigure and then
            # forced ON here. MIN/MAX/DEF are left to the instrument defaults.
            sense = _SENSE_MNEMONIC.get(function)
            if sense is not None:
                if isinstance(range_value, AutoRange) and range_value == AutoRange.AUTO:
                    self.write(f"SENSe:{sense}:RANGe:AUTO ON")
                elif not isinstance(range_value, AutoRange):
                    self.write(f"SENSe:{sense}:RANGe:AUTO OFF")

            # NPLC only for DCV/DCI/2W/4W.
            if nplc is not None and function in NPLC_FUNCTIONS:
                self.write(f"SENSe:{sense}:NPLCycles {_num(nplc.value)}")

            # Autozero where applicable.
            if function in NPLC_FUNCTIONS:
                self.write(f"SENSe:ZERO:AUTO {autozero.value}")

            if ac_filter_hz is not None:
                self.write(f"SENSe:DETector:BANDwidth {ac_filter_hz.value}")

            # R6 bookkeeping for re-measure / recover.
            self._active_function = function
            self._active_nplc = nplc.value if nplc is not None else None
            self._active_aperture = aperture_s.value if aperture_s is not None else None
            self._active_autozero = autozero
            self._active_ac_filter = float(ac_filter_hz.value) if ac_filter_hz else None
            self._trigger_source = TriggerSource.IMMEDIATE  # CONFigure resets to IMM
            self._state = CommandState.CONFIGURED

    def configure_dc_voltage(
        self, range_v: float | AutoRange, nplc: Nplc, autozero: AutozeroMode = AutozeroMode.ON
    ) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.VOLT_DC, range_v, nplc=nplc, autozero=autozero
        )
        self._last_configure()

    def configure_ac_voltage(
        self, range_v: float | AutoRange, ac_filter_hz: AcFilterHz = AcFilterHz.HZ20
    ) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.VOLT_AC, range_v, ac_filter_hz=ac_filter_hz
        )
        self._last_configure()

    def configure_dc_current(
        self, range_a: float | AutoRange, nplc: Nplc, autozero: AutozeroMode = AutozeroMode.ON
    ) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.CURR_DC, range_a, nplc=nplc, autozero=autozero
        )
        self._last_configure()

    def configure_ac_current(
        self, range_a: float | AutoRange, ac_filter_hz: AcFilterHz = AcFilterHz.HZ20
    ) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.CURR_AC, range_a, ac_filter_hz=ac_filter_hz
        )
        self._last_configure()

    def configure_2wire_resistance(
        self, range_ohm: float | AutoRange, nplc: Nplc, autozero: AutozeroMode = AutozeroMode.ON
    ) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.RES_2W, range_ohm, nplc=nplc, autozero=autozero
        )
        self._last_configure()

    def configure_4wire_resistance(
        self, range_ohm: float | AutoRange, nplc: Nplc, autozero: AutozeroMode = AutozeroMode.ON
    ) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.RES_4W, range_ohm, nplc=nplc, autozero=autozero
        )
        self._last_configure()

    def configure_frequency(self, voltage_range_v: float | AutoRange, aperture_s: Aperture) -> None:
        def _do() -> None:
            self._apply_configure(MeasurementFunction.FREQ, voltage_range_v, aperture_s=aperture_s)
            self.write(f"SENSe:FREQuency:APERture {_num(aperture_s.value)}")
        self._last_configure = _do
        _do()

    def configure_period(self, voltage_range_v: float | AutoRange, aperture_s: Aperture) -> None:
        def _do() -> None:
            self._apply_configure(MeasurementFunction.PERIOD, voltage_range_v, aperture_s=aperture_s)
            self.write(f"SENSe:PERiod:APERture {_num(aperture_s.value)}")
        self._last_configure = _do
        _do()

    def configure_continuity(self) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.CONTINUITY, AutoRange.DEF
        )
        self._last_configure()

    def configure_diode(self) -> None:
        self._last_configure = lambda: self._apply_configure(
            MeasurementFunction.DIODE, AutoRange.DEF
        )
        self._last_configure()

    # ------------------------------------------------------------------ measure
    def _build_reading(self, value: float | None, raw: str, **over: object) -> MeasurementReading:
        func = self._active_function or MeasurementFunction.VOLT_DC
        overload = value is not None and parser.is_overload(value)
        return MeasurementReading(
            timestamp_utc=_dt.datetime.now(_dt.timezone.utc),
            monotonic_s=time.monotonic(),
            function=func,
            value=None if overload else value,
            unit=func.unit,
            raw=raw,
            range_value=None,
            nplc=self._active_nplc,
            aperture_s=self._active_aperture,
            is_overload=overload,
            is_valid=(value is not None) and not overload,
            terminal=self._terminal,
            transport=self._t.transport_type,
            **over,  # type: ignore[arg-type]
        )

    def read_once(self) -> MeasurementReading:
        """Single immediate-triggered reading (spec section 14.1).

        R1: on a read timeout, recover and RE-MEASURE; never re-fetch stale data.
        """
        with self._locked():
            if not self.is_connected():
                raise InstrumentConnectionError("DMM is not connected")
            if self._active_function is None:
                raise ProtocolError("No measurement function configured before read_once()")
            if self._state not in (CommandState.CONFIGURED, CommandState.CONNECTED_REMOTE):
                raise ProtocolError(f"Cannot read in driver state {self._state.value}")
            timeout = estimate_measurement_timeout_s(
                self._active_function or MeasurementFunction.VOLT_DC,
                self._active_nplc,
                self._active_aperture,
                1,
                1,
                0.0,
                self._active_ac_filter,
                self._cfg.line_frequency_hz,
                self._active_autozero,
            )
            active_timeout = max(timeout, self._cfg.default_timeout_s)
            self._t.set_timeout(active_timeout)

            def _do_read() -> str:
                self.write("TRIGger:SOURce IMMediate")
                self.write("TRIGger:COUNt 1")
                self.write("SAMPle:COUNt 1")
                return self.query("READ?")

            recovery_actions: list[str] = []
            retry_count = 0
            try:
                raw = _do_read()
            except InstrumentTimeoutError:
                if not self._cfg.retry_queries:
                    self._state = CommandState.ERROR_RECOVERY
                    raise
                # R1: clean recovery, then re-MEASURE (fresh READ?), not re-FETCH.
                self._transport_recover(recovery_actions)
                # _transport_recover intentionally uses a short timeout and then
                # restores the default timeout; re-apply the active measurement
                # timeout before retrying a slow NPLC/autozero/AC-filter reading.
                self._t.set_timeout(active_timeout)
                if self._last_configure is not None:
                    self._last_configure()
                    recovery_actions.append("reconfigure")
                retry_count = 1
                raw = _do_read()
            finally:
                self._t.set_timeout(self._cfg.default_timeout_s)

            values = parser.parse_reading_list(raw)
            reading = self._build_reading(
                values[0],
                raw,
                was_retried=retry_count > 0,
                retry_count=retry_count,
                reconnect_count=self._reconnect_count,
                recovery_actions=tuple(recovery_actions),
            )
            self._state = CommandState.CONNECTED_REMOTE
            return reading

    def measure_dc_voltage(
        self, range_v: float | AutoRange = AutoRange.DEF, nplc: Nplc = Nplc.PLC10
    ) -> MeasurementReading:
        with self._locked():
            self.configure_dc_voltage(range_v, nplc)
            return self.read_once()

    def measure_ac_voltage(
        self, range_v: float | AutoRange = AutoRange.DEF, ac_filter_hz: AcFilterHz = AcFilterHz.HZ20
    ) -> MeasurementReading:
        with self._locked():
            self.configure_ac_voltage(range_v, ac_filter_hz)
            return self.read_once()

    def measure_dc_current(
        self, range_a: float | AutoRange = AutoRange.DEF, nplc: Nplc = Nplc.PLC10
    ) -> MeasurementReading:
        with self._locked():
            self.configure_dc_current(range_a, nplc)
            return self.read_once()

    def measure_2wire_resistance(
        self, range_ohm: float | AutoRange = AutoRange.DEF, nplc: Nplc = Nplc.PLC10
    ) -> MeasurementReading:
        with self._locked():
            self.configure_2wire_resistance(range_ohm, nplc)
            return self.read_once()

    def measure_4wire_resistance(
        self, range_ohm: float | AutoRange = AutoRange.DEF, nplc: Nplc = Nplc.PLC10
    ) -> MeasurementReading:
        with self._locked():
            self.configure_4wire_resistance(range_ohm, nplc)
            return self.read_once()

    def read_stable_resistance(self, profile: StabilityProfile):
        """Driver-level stable resistance helper that honors final_nplc.

        The pure stability algorithm accepts a sampler only. This wrapper owns the
        instrument and can therefore reconfigure to ``profile.final_nplc`` before
        the final precision reading.
        """
        with self._locked():
            from .stability import read_stable_resistance as _read_stable

            measure = self.measure_4wire_resistance if profile.four_wire else self.measure_2wire_resistance

            def sampler() -> MeasurementReading:
                return measure(profile.range_ohm, profile.nplc)

            def final_sampler() -> MeasurementReading:
                return measure(profile.range_ohm, profile.final_nplc or profile.nplc)

            return _read_stable(
                sampler,
                profile,
                final_sampler=final_sampler if profile.final_nplc is not None else None,
            )

    # ------------------------------------------------------------------ bus trigger
    def set_trigger_source(self, source: TriggerSource) -> None:
        self.write(f"TRIGger:SOURce {source.value}")
        self._trigger_source = source

    def initiate(self) -> None:
        # FETCh? returns readings from internal memory. Ensure that memory is
        # enabled because a user/raw command may have disabled it before this API
        # call or during recovery.
        self.write('DATA:FEED RDG_STORE,"CALC"')
        self.write("INITiate")
        self._state = CommandState.WAITING_FOR_TRIGGER

    def trigger_bus(self) -> None:
        if self._trigger_source != TriggerSource.BUS:
            raise ProtocolError("trigger_bus() requires trigger source BUS.")
        self.write("*TRG")

    def fetch(self) -> list[MeasurementReading]:
        raw = self.query("FETCh?")
        values = parser.parse_reading_list(raw)
        return [self._build_reading(v, raw, reconnect_count=self._reconnect_count) for v in values]

    def read_once_bus(self) -> MeasurementReading:
        """BUS-triggered single reading (spec section 14.2, R7).

        Never uses READ? with BUS. Also never places *OPC? between INITiate
        and *TRG because the operation cannot complete until the bus trigger is
        received; doing so can deadlock or leave stale *OPC? output.
        """
        with self._locked():
            if not self.is_connected():
                raise InstrumentConnectionError("DMM is not connected")
            if self._active_function is None:
                raise ProtocolError("No measurement function configured before read_once_bus()")
            if self._state not in (CommandState.CONFIGURED, CommandState.CONNECTED_REMOTE):
                raise ProtocolError(f"Cannot BUS-read in driver state {self._state.value}")
            self.set_trigger_source(TriggerSource.BUS)
            self.write("TRIGger:COUNt 1")
            self.write("SAMPle:COUNt 1")
            self.initiate()
            time.sleep(0.05 if self._is_serial else 0.02)
            self.trigger_bus()
            readings = self.fetch()
            if not readings:
                raise ProtocolError("FETCh? returned no readings")
            self._state = CommandState.CONNECTED_REMOTE
            return readings[0]

    # guard: forbid READ? with BUS (spec section 22)
    def read_query(self) -> str:
        if self._trigger_source == TriggerSource.BUS:
            raise ProtocolError(
                "READ? is forbidden with trigger source BUS (deadlock). Use the "
                "INITiate -> *TRG -> FETCh? flow via read_once_bus()."
            )
        return self.query("READ?")

    @property
    def state(self) -> CommandState:
        return self._state

    @property
    def identity_cached(self) -> Identity | None:
        return self._identity


def _num(value: float) -> str:
    """Format a numeric token without trailing .0 noise for whole numbers."""
    if value == int(value):
        return str(int(value))
    return repr(value)


def _normalize_scpi_query(command: str) -> str:
    """Normalize SCPI query text for retry policy matching."""
    return " ".join(command.strip().upper().split())
