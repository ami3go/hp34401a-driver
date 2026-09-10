"""Tests for the production-hardening requirements R1-R10 (spec section 4A)."""

import pytest

from hp34401a_dmm import (
    AutoRange,
    AutozeroMode,
    DriverConfig,
    FakeTransport,
    Hp34401A,
    InstrumentConnectionError,
    InstrumentTimeoutError,
    Nplc,
    ProtocolError,
    SafetyError,
    TriggerSource,
    VisaGpibConfig,
)
from hp34401a_dmm.driver import estimate_measurement_timeout_s
from hp34401a_dmm.enums import MeasurementFunction
from hp34401a_dmm.visa_transport import validate_gpib_resource


def _connected(**fake_kw):
    t = FakeTransport(**fake_kw)
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False))
    d.connect()
    return d, t


# --- R1: measurement-read timeout re-measures, never re-fetches -------------
def test_r1_measurement_timeout_remeasures_not_refetches():
    t = FakeTransport(responses={"READ?": "+1.0E+00"})
    # First READ? times out; after recovery, the next READ? succeeds.
    t.timeout_on.add("READ?")

    class OneShotFake(FakeTransport):
        def query(self, command):
            if command == "READ?" and command in self.timeout_on:
                self.timeout_on.discard(command)  # only the first READ? times out
                self.history.append(command)
                self.query_history.append(command)
                self._has_unread_output = True
                raise InstrumentTimeoutError("fake")
            return super().query(command)

    t = OneShotFake(responses={"READ?": "+1.0E+00"})
    t.timeout_on.add("READ?")
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False,
                                 retry_queries=True))
    d.connect()
    t.history.clear()
    reading = d.measure_dc_voltage(10.0, Nplc.PLC10)
    assert reading.value == pytest.approx(1.0)
    assert reading.was_retried is True
    assert reading.retry_count == 1
    # Recovery happened (transport cleared) and the configure was re-applied,
    # i.e. a fresh READ? was issued, not a bare FETCh?.
    assert t.clear_count >= 1
    assert "FETCh?" not in t.history
    assert t.history.count("READ?") == 2  # the timed-out one + the re-measure
    assert "transport_clear" in reading.recovery_actions


def test_r1_status_query_retry_only_for_idempotent():
    # A measurement read with retry disabled must NOT auto-retry.
    t = FakeTransport()
    t.timeout_on.add("READ?")
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False,
                                 retry_queries=False))
    d.connect()
    with pytest.raises(InstrumentTimeoutError):
        d.measure_dc_voltage(10.0, Nplc.PLC10)


# --- R2: RS-232 garbled IDN -> specific diagnostic --------------------------
def test_r2_garbled_idn_raises_settings_diagnostic():
    # Simulate a serial transport by forcing the driver's serial path with a fake
    # whose IDN does not look like a 34401A.
    # scpi-driver-core's ScpiTextCodec encodes with the transport's declared
    # encoding (ascii by default), so the garbled IDN must itself be
    # ascii-encodable; \x00\x01 are non-printable control bytes that still
    # fail parser.looks_like_34401a() same as the previous \xff-containing
    # string did.
    t = FakeTransport(idn="\x00\x01 garbage")
    t._transport_type = __import__("hp34401a_dmm").TransportType.SERIAL_RS232
    d = Hp34401A(t, DriverConfig())
    with pytest.raises(InstrumentConnectionError) as exc:
        d.connect()
    assert "parity" in str(exc.value).lower()


# --- R3: autozero in timeout estimate ---------------------------------------
def test_r3_autozero_doubles_estimated_time():
    on = estimate_measurement_timeout_s(
        MeasurementFunction.VOLT_DC, nplc=100, aperture_s=None, sample_count=1,
        trigger_count=1, trigger_delay_s=0.0, ac_filter_hz=None,
        line_frequency_hz=50, autozero=AutozeroMode.ON,
    )
    off = estimate_measurement_timeout_s(
        MeasurementFunction.VOLT_DC, nplc=100, aperture_s=None, sample_count=1,
        trigger_count=1, trigger_delay_s=0.0, ac_filter_hz=None,
        line_frequency_hz=50, autozero=AutozeroMode.OFF,
    )
    # NPLC=100 @ 50 Hz = 2 s/reading; ON should add ~2 s over OFF.
    assert on > off
    assert (on - off) == pytest.approx(2.0, abs=0.01)


# --- R4: line frequency explicit; no 'auto' ---------------------------------
def test_r4_no_auto_line_frequency():
    cfg = DriverConfig()
    assert cfg.line_frequency_hz in (50, 60)
    # Unknown value collapses to conservative 50 inside the estimator.
    t = estimate_measurement_timeout_s(
        MeasurementFunction.VOLT_DC, nplc=10, aperture_s=None, sample_count=1,
        trigger_count=1, trigger_delay_s=0.0, ac_filter_hz=None,
        line_frequency_hz=999, autozero=AutozeroMode.OFF,
    )
    assert t > 0


# --- R6: CONFigure resets state; no stale BUS trigger across steps -----------
def test_r6_configure_clears_prior_bus_trigger_source():
    d, t = _connected(responses={"READ?": "+1.0E+00"})
    d.set_trigger_source(TriggerSource.BUS)
    assert d._trigger_source is TriggerSource.BUS
    # A new configure must reset trigger source to IMMediate so a later READ? is safe.
    d.configure_dc_voltage(10.0, Nplc.PLC10)
    assert d._trigger_source is TriggerSource.IMMEDIATE
    # read_query is now allowed (no deadlock risk).
    assert d.read_query() == "+1.0E+00"


# --- R8: self-test uses a dedicated long timeout ----------------------------
def test_r8_self_test_uses_long_timeout(monkeypatch):
    d, t = _connected(responses={"*TST?": "+0"})
    seen = []
    orig = t.set_timeout
    t.set_timeout = lambda s: seen.append(s)  # type: ignore
    result = d.self_test()
    assert result.passed
    assert 30.0 in seen  # self_test_timeout_s applied


# --- R10: GPIB address validation -------------------------------------------
def test_r10_talk_only_address_rejected():
    with pytest.raises(InstrumentConnectionError):
        validate_gpib_resource("GPIB0::31::INSTR")


def test_r10_out_of_range_address_rejected():
    with pytest.raises(InstrumentConnectionError):
        validate_gpib_resource("GPIB0::40::INSTR")


def test_r10_valid_address_ok():
    validate_gpib_resource("GPIB0::22::INSTR")  # no raise


def test_r10_visa_config_validates_on_construction():
    from hp34401a_dmm.visa_transport import VisaGpibTransport
    with pytest.raises(InstrumentConnectionError):
        VisaGpibTransport(VisaGpibConfig(resource="GPIB0::31::INSTR"))


# --- Safety gating (spec section 24) ----------------------------------------
def test_calibration_blocked_by_default():
    d, t = _connected()
    with pytest.raises(SafetyError):
        d.write("CALibration:VALue 1.0")


def test_reset_requires_confirm():
    d, t = _connected()
    with pytest.raises(SafetyError):
        d.reset()
    d.reset(confirm=True)  # ok
    assert "*RST" in t.history


def test_rwlock_blocked():
    d, t = _connected()
    with pytest.raises(SafetyError):
        d.write("SYSTem:RWLock")


def test_real_transport_timeout_keeps_unread_output_until_clear():
    from scpi_driver_core.exceptions import TransportTimeoutError as CoreTimeoutError
    from scpi_driver_core.transport.models import TransportDescriptor, TransportState, WriteResult

    from hp34401a_dmm.transports import BaseTransport
    from hp34401a_dmm.enums import TransportType
    from hp34401a_dmm.errors import InstrumentTimeoutError, ProtocolError

    class AlwaysTimesOutCoreTransport:
        """A minimal scpi_driver_core.transport.base.Transport whose reads
        always time out, to exercise BaseTransport's one-outstanding-query
        recovery bookkeeping independent of any real backend."""

        def __init__(self):
            self.state = TransportState.CREATED
            self.is_open = False
            self.descriptor = TransportDescriptor(kind="fake", address="timeout-test")

        def open(self):
            self.state = TransportState.OPEN
            self.is_open = True
            return self.descriptor

        def close(self):
            self.state = TransportState.CLOSED
            self.is_open = False

        def write(self, data, *, timeout_s=None, operation_id=None):
            return WriteResult(bytes_written=len(data))

        def read(self, request, *, timeout_s=None, operation_id=None):
            raise CoreTimeoutError("timeout")

        def transact(self, outbound, response, *, timeout_s=None, replay_policy=None, operation_id=None):
            self.write(outbound, timeout_s=timeout_s, operation_id=operation_id)
            return self.read(response, timeout_s=timeout_s, operation_id=operation_id)

        def flush(self, direction):
            pass

    class TimeoutTransport(BaseTransport):
        _transport_type = TransportType.FAKE

        @property
        def name(self):
            return "timeout-test"

        def _build_core_transport(self):
            return AlwaysTimesOutCoreTransport()

    t = TimeoutTransport()
    t.open()
    with pytest.raises(InstrumentTimeoutError):
        t.query("READ?")
    with pytest.raises(ProtocolError):
        t.query("SYSTem:ERRor?")
    t.clear()
    # After clear the unread-output guard is released, even though this query still times out.
    with pytest.raises(InstrumentTimeoutError):
        t.query("SYSTem:ERRor?")


def test_failed_connect_closes_opened_transport():
    t = FakeTransport(idn="garbled")
    t._transport_type = __import__("hp34401a_dmm").TransportType.SERIAL_RS232
    d = Hp34401A(t, DriverConfig())
    with pytest.raises(InstrumentConnectionError):
        d.connect()
    assert not t.is_open()

# --- R11: safe low-level query timeout retry --------------------------------
def test_r11_idempotent_query_retries_after_clear_without_error_drain():
    class OneShotStatusTimeout(FakeTransport):
        def query(self, command):
            if command == "*IDN?" and command in self.timeout_on:
                self.timeout_on.discard(command)
                self.history.append(command)
                self.query_history.append(command)
                self._has_unread_output = True
                raise InstrumentTimeoutError("first *IDN? timed out")
            return super().query(command)

    t = OneShotStatusTimeout()
    t.timeout_on.add("*IDN?")
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False,
                                 retry_queries=True,
                                 max_query_retries=1,
                                 query_retry_delay_s=0.0))
    d.connect()
    t.history.clear()
    raw = d.query("*IDN?")
    assert "34401A" in raw
    assert t.clear_count == 1
    assert t.query_history.count("*IDN?") == 2
    # Error queue must not be drained before retrying SYSTem:ERRor? / status
    # queries, otherwise the retry could consume/alter the data being requested.
    assert "SYSTem:ERRor?" not in t.history


def test_r11_query_timeout_no_retry_when_disabled():
    t = FakeTransport()
    t.timeout_on.add("*IDN?")
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False,
                                 retry_queries=False))
    d.connect()
    with pytest.raises(InstrumentTimeoutError):
        d.query("*IDN?")
    assert t.clear_count == 0


def test_r11_read_query_not_retried_by_raw_query_policy():
    t = FakeTransport()
    t.timeout_on.add("READ?")
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False,
                                 retry_queries=True,
                                 max_query_retries=2,
                                 retry_all_queries_on_timeout=True,
                                 query_retry_delay_s=0.0))
    d.connect()
    with pytest.raises(InstrumentTimeoutError):
        d.query("READ?")
    # READ? is handled by read_once() as a fresh re-measure, not by raw query retry.
    assert t.query_history.count("READ?") == 1
    assert t.clear_count == 0


def test_r11_fetch_query_retries_after_clear():
    class OneShotFetchTimeout(FakeTransport):
        def query(self, command):
            if command == "FETCh?" and command in self.timeout_on:
                self.timeout_on.discard(command)
                self.history.append(command)
                self.query_history.append(command)
                self._has_unread_output = True
                raise InstrumentTimeoutError("first FETCh? timed out")
            return super().query(command)

    t = OneShotFetchTimeout(responses={"FETCh?": "+2.0E+00"})
    t.timeout_on.add("FETCh?")
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False,
                                 retry_queries=True,
                                 max_query_retries=1,
                                 query_retry_delay_s=0.0))
    d.connect()
    t.history.clear()
    d.configure_dc_voltage(10.0, Nplc.PLC10)
    d.initiate()
    readings = d.fetch()
    assert readings[0].value == pytest.approx(2.0)
    assert t.clear_count == 1
    assert t.query_history.count("FETCh?") == 2


def test_r11_driver_config_validates_retry_parameters():
    with pytest.raises(ValueError):
        DriverConfig(max_query_retries=-1)
    with pytest.raises(ValueError):
        DriverConfig(query_retry_delay_s=-0.1)

# --- v1.2.3 hardening ------------------------------------------------------
def test_auto_range_auto_uses_configure_def_not_auto():
    d, t = _connected(responses={"READ?": "+1.0E+00"})
    d.measure_dc_voltage(AutoRange.AUTO, Nplc.PLC10)
    assert "CONFigure:VOLTage:DC DEF,DEF" in t.history
    assert "CONFigure:VOLTage:DC AUTO,DEF" not in t.history
    assert "SENSe:VOLTage:DC:RANGe:AUTO ON" in t.history


def test_production_value_error_becomes_error_result():
    from hp34401a_dmm import TestStep, run_measurement_step

    d, _t = _connected(responses={"READ?": "+1.0E+00"})
    step = TestStep(name="bad", function=MeasurementFunction.VOLT_DC, range_value=7.0)
    result = run_measurement_step(d, step, dut_id="DUT", station_id="ST")
    assert result.pass_fail == "ERROR"
    assert "Unsupported" in (result.error or "")


def test_read_once_bus_requires_prior_configuration():
    d, _t = _connected(responses={"FETCh?": "+1.0E+00"})
    with pytest.raises(ProtocolError):
        d.read_once_bus()


def test_visa_wrong_identity_rejected_on_connect():
    t = FakeTransport(idn="TEKTRONIX,DPO4054,123,FV1")
    t._transport_type = __import__("hp34401a_dmm").TransportType.VISA_GPIB
    d = Hp34401A(t, DriverConfig(drain_error_queue_on_connect=False, clear_status_on_connect=False))
    with pytest.raises(InstrumentConnectionError):
        d.connect()


def test_serial_partial_response_is_timeout(monkeypatch):
    """A read_until() that returns bytes without the terminator (pyserial's
    partial-read-on-timeout behaviour) must surface as InstrumentTimeoutError.

    This behaviour now lives in scpi_driver_core.transport.serial.SerialTransport
    (exercised here through our SerialRs232Transport adapter); a fake ``serial``
    module is injected so the test needs neither pyserial nor real hardware.
    """
    import sys
    import types

    from hp34401a_dmm.serial_transport import SerialRs232Transport
    from hp34401a_dmm.config import SerialRs232Config

    class PartialSerial:
        def __init__(self, **kwargs):
            self.timeout = kwargs.get("timeout")
            self.write_timeout = kwargs.get("write_timeout")

        def write(self, data):
            return len(data)

        def read_until(self, terminator, size=None):
            return b"+1.234"  # no newline terminator -> pyserial timeout partial

        def reset_input_buffer(self):
            pass

        def reset_output_buffer(self):
            pass

        def close(self):
            pass

    fake_serial_module = types.SimpleNamespace(Serial=lambda **kwargs: PartialSerial(**kwargs))
    monkeypatch.setitem(sys.modules, "serial", fake_serial_module)

    tr = SerialRs232Transport(SerialRs232Config(port="COM1"))
    tr.open()
    with pytest.raises(InstrumentTimeoutError):
        tr.query("READ?")


def test_query_non_timeout_error_sets_error_recovery():
    d, t = _connected()
    t._has_unread_output = True
    with pytest.raises(ProtocolError):
        d.query("*IDN?")
    assert d.state.value == "ERROR_RECOVERY"


def test_gui_module_import_safe():
    import hp34401a_dmm.gui as gui
    assert callable(gui.main)
