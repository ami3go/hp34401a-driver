"""Command-sequence tests using the FakeTransport (spec sections 14, 22, 29.1)."""

import pytest

from hp34401a_dmm import (
    AutoRange,
    AutozeroMode,
    DriverConfig,
    FakeTransport,
    Hp34401A,
    Nplc,
    ProtocolError,
    TriggerSource,
)
from hp34401a_dmm.driver import estimate_measurement_timeout_s
from hp34401a_dmm.enums import MeasurementFunction


def make_driver(responses=None, **fake_kw):
    t = FakeTransport(responses=responses or {}, **fake_kw)
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False))
    d.connect()
    return d, t


def test_dc_voltage_config_sequence():
    d, t = make_driver({"READ?": "+1.00000000E+01"})
    t.history.clear()
    d.measure_dc_voltage(10.0, Nplc.PLC10)
    # Exact emitted SCPI, in order.
    assert t.history == [
        "CONFigure:VOLTage:DC 10,DEF",
        "SENSe:VOLTage:DC:RANGe:AUTO OFF",
        "SENSe:VOLTage:DC:NPLCycles 10",
        "SENSe:ZERO:AUTO ON",
        "TRIGger:SOURce IMMediate",
        "TRIGger:COUNt 1",
        "SAMPle:COUNt 1",
        "READ?",
    ]


def test_autorange_emits_range_auto_on():
    d, t = make_driver({"READ?": "+1.0E+00"})
    t.history.clear()
    d.measure_2wire_resistance(AutoRange.AUTO, Nplc.PLC10)
    assert "SENSe:RESistance:RANGe:AUTO ON" in t.history
    assert "CONFigure:RESistance DEF,DEF" in t.history
    assert "CONFigure:RESistance AUTO,DEF" not in t.history


def test_read_with_bus_trigger_is_rejected():
    d, t = make_driver()
    d.set_trigger_source(TriggerSource.BUS)
    with pytest.raises(ProtocolError):
        d.read_query()


def test_bus_trigger_uses_init_trg_fetch_not_read():
    d, t = make_driver({"FETCh?": "+5.0E+00", "*OPC?": "1"})
    t.history.clear()
    d.configure_dc_voltage(10.0, Nplc.PLC10)
    t.history.clear()
    reading = d.read_once_bus()
    assert reading.value == pytest.approx(5.0)
    # Must use INITiate ... *TRG ... FETCh?, and never READ?.
    assert "INITiate" in t.history
    assert "*TRG" in t.history
    assert "FETCh?" in t.history
    assert "READ?" not in t.history
    # *TRG must come after INITiate.
    assert t.history.index("*TRG") > t.history.index("INITiate")


def test_overload_classified_not_returned_as_value():
    d, t = make_driver({"READ?": "9.90000000E+37"})
    reading = d.measure_dc_voltage(10.0, Nplc.PLC10)
    assert reading.is_overload is True
    assert reading.value is None
    assert reading.is_valid is False


def test_count_product_above_512_rejected():
    d, t = make_driver()
    with pytest.raises(ValueError):
        d._validate_counts(sample_count=600, trigger_count=1)
    with pytest.raises(ValueError):
        d._validate_counts(sample_count=23, trigger_count=23)  # 529 > 512


def test_invalid_range_rejected():
    d, t = make_driver()
    with pytest.raises(ValueError):
        d.configure_dc_voltage(7.0, Nplc.PLC10)  # 7 V is not a valid DCV range


def test_one_outstanding_query_protection():
    # FakeTransport simulates a timeout that leaves output unread; a second
    # query must raise ProtocolError before sending.
    t = FakeTransport()
    t.timeout_on.add("READ?")
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False,
                                 retry_queries=False))
    d.connect()
    from hp34401a_dmm import InstrumentTimeoutError
    with pytest.raises(InstrumentTimeoutError):
        d.query("READ?")
    with pytest.raises(ProtocolError):
        t.query("SYSTem:ERRor?")  # transport still has unread output flagged


def test_bus_trigger_does_not_use_opc_and_enables_reading_memory():
    d, t = make_driver({"FETCh?": "+5.0E+00", "*OPC?": "1"})
    t.history.clear()
    d.configure_dc_voltage(10.0, Nplc.PLC10)
    t.history.clear()
    d.read_once_bus()
    assert "*OPC?" not in t.history
    assert 'DATA:FEED RDG_STORE,"CALC"' in t.history
    assert t.history.index('DATA:FEED RDG_STORE,"CALC"') < t.history.index("INITiate")
    assert t.history.index("*TRG") > t.history.index("INITiate")
    assert t.history.index("FETCh?") > t.history.index("*TRG")


def test_read_once_requires_configuration():
    d, _ = make_driver()
    with pytest.raises(ProtocolError, match="No measurement function configured"):
        d.read_once()
