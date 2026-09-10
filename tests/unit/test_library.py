import pytest
from robot.libdocpkg import LibraryDocumentation

from rf_hp34401a import Hp34401ALibrary
from rf_hp34401a.exceptions import Hp34401ARobotError
from hp34401a_dmm import MeasurementNotStableError


def lib_with_reading(value=12.5):
    lib = Hp34401ALibrary()
    lib.open_simulated_dmm(reading=value)
    return lib


def test_library_import_and_explicit_keywords():
    doc = LibraryDocumentation("rf_hp34401a.Hp34401ALibrary")
    names = {kw.name for kw in doc.keywords}
    assert "Measure DC Voltage" in names
    assert "_execute" not in names
    assert "Open Simulated DMM" in names


def test_identity_and_versions():
    lib = lib_with_reading()
    ident = lib.identify_dmm()
    assert ident["model"] == "34401A"
    assert lib.get_robot_dmm_library_version() == "26.07"
    assert lib.get_dmm_driver_version() == "1.2.8"
    lib.close_all_dmms()


def test_measurement_and_metadata():
    lib = lib_with_reading(12.34)
    assert lib.measure_dc_voltage() == pytest.approx(12.34)
    data = lib.get_last_dmm_reading()
    assert data["function"] == "VOLT:DC"
    assert data["alias"] == "default"
    assert data["library_version"] == "26.07"
    lib.dmm_reading_should_be_between(12, 13)
    lib.dmm_reading_should_be_close_to(12.3, absolute_tolerance=0.1)
    lib.close_all_dmms()


def test_all_measurement_modes_delegate_to_core():
    lib = lib_with_reading(1.25)
    assert lib.measure_ac_voltage() == 1.25
    assert lib.measure_dc_current() == 1.25
    assert lib.measure_ac_current() == 1.25
    assert lib.measure_2wire_resistance() == 1.25
    assert lib.measure_4wire_resistance() == 1.25
    assert lib.measure_frequency() == 1.25
    assert lib.measure_period() == 1.25
    assert lib.measure_continuity() == 1.25
    assert lib.measure_diode() == 1.25
    lib.close_all_dmms()


def test_bus_trigger_path():
    lib = lib_with_reading(3.3)
    lib.configure_dc_voltage()
    assert lib.read_dmm_once_with_bus_trigger() == 3.3
    data = lib.get_last_dmm_reading()
    assert data["value"] == 3.3
    lib.close_all_dmms()


def test_multiple_aliases_are_independent():
    lib = Hp34401ALibrary()
    lib.open_simulated_dmm(alias="a", reading=1)
    lib.open_simulated_dmm(alias="b", reading=2)
    assert lib.measure_dc_voltage(alias="a") == 1
    assert lib.measure_dc_voltage(alias="b") == 2
    assert lib.get_open_dmm_aliases() == ["a", "b"]
    lib.select_dmm("a")
    assert lib.get_active_dmm_alias() == "a"
    lib.close_all_dmms()


def test_overload_is_rejected():
    lib = lib_with_reading(9.9e37)
    with pytest.raises(Hp34401ARobotError, match="overload"):
        lib.measure_dc_voltage()
    data = lib.get_last_dmm_reading()
    assert data["is_overload"] is True
    with pytest.raises(AssertionError):
        lib.dmm_reading_should_not_be_overload()
    lib.close_all_dmms()


def test_stable_resistance_success():
    lib = lib_with_reading(1000.0)
    result = lib.try_read_stable_resistance(
        min_settle=0,
        sample_interval="1 ms",
        max_wait="100 ms",
        window_size=3,
        final_nplc=None,
    )
    assert result["stable"] is True
    assert result["value"] == 1000.0
    assert (
        lib.read_stable_resistance(
            min_settle=0,
            sample_interval="1 ms",
            max_wait="100 ms",
            window_size=3,
            final_nplc=None,
        )
        == 1000.0
    )
    lib.close_all_dmms()


def test_connection_and_assertion_failures_have_context():
    lib = Hp34401ALibrary()
    with pytest.raises(Hp34401ARobotError, match="No DMM session"):
        lib.measure_dc_voltage()
    lib.open_simulated_dmm(reading=5)
    lib.measure_dc_voltage()
    with pytest.raises(AssertionError, match="outside"):
        lib.dmm_reading_should_be_between(10, 20)
    lib.close_all_dmms()


def test_raw_scpi_respects_core_safety():
    lib = lib_with_reading()
    with pytest.raises(Hp34401ARobotError):
        lib.query_dmm_command("*IDN?")
    lib.set_raw_io_enabled(True)
    assert "34401A" in lib.query_dmm_command("*IDN?")
    with pytest.raises(Hp34401ARobotError):
        lib.write_dmm_command("CALibration:SECure:STATe OFF")
    lib.close_all_dmms()


def test_configuration_read_status_and_trigger_wrappers():
    lib = lib_with_reading(4.2)
    lib.dmm_should_be_connected()
    lib.configure_dc_voltage(10, 1, "ON")
    assert lib.read_dmm() == 4.2
    lib.configure_ac_voltage(10, 200)
    lib.configure_dc_current(1, 0.2, "ONCE")
    lib.configure_ac_current(1, 3)
    lib.configure_2wire_resistance(1000, 10, "OFF")
    lib.configure_4wire_resistance(1000, 100, "ON")
    lib.configure_frequency(10, 1)
    lib.configure_period(10, 0.01)
    lib.configure_continuity()
    lib.configure_diode()
    lib.clear_dmm_status()
    assert lib.get_dmm_state() in {"CONNECTED_REMOTE", "CONFIGURED"}
    assert lib.get_dmm_input_terminal() == "FRONT"
    lib.require_dmm_input_terminal("FRONT")
    lib.set_dmm_trigger_source("BUS")
    lib.initiate_dmm_measurement()
    lib.send_dmm_bus_trigger()
    readings = lib.fetch_dmm_readings()
    assert readings[0]["value"] == 4.2
    lib.close_dmm()
    assert lib.get_open_dmm_aliases() == []


def test_error_queue_health_recovery_and_failure_assertions():
    lib = lib_with_reading(5)
    session = lib._sessions.get()
    session.driver._t.error_queue.extend(['-100,"Command error"'])
    error = lib.read_dmm_error()
    assert error["code"] == -100
    session.driver._t.error_queue.extend(['-200,"Execution error"'])
    errors = lib.get_dmm_error_queue()
    assert errors[0]["code"] == -200
    session.driver._t.error_queue.extend(['-300,"Device error"'])
    with pytest.raises(AssertionError):
        lib.dmm_error_queue_should_be_empty()
    session.driver._t.error_queue.extend(['-400,"Query error"'])
    with pytest.raises(Hp34401ARobotError):
        lib.dmm_should_have_no_errors("test")
    health = lib.get_dmm_health()
    assert "connected" in health
    recovery = lib.recover_dmm()
    assert recovery["succeeded"] is True
    lib.close_all_dmms()


def test_assertion_variants_and_last_reading_errors():
    lib = Hp34401ALibrary()
    lib.open_simulated_dmm(reading=10)
    with pytest.raises(Hp34401ARobotError):
        lib.get_last_dmm_reading()
    lib.measure_dc_voltage()
    assert lib.get_last_dmm_reading_value() == 10
    lib.dmm_reading_should_be_greater_than(9)
    lib.dmm_reading_should_be_less_than(11)
    with pytest.raises(AssertionError):
        lib.dmm_reading_should_be_greater_than(11)
    with pytest.raises(AssertionError):
        lib.dmm_reading_should_be_less_than(9)
    with pytest.raises(AssertionError):
        lib.dmm_reading_should_be_close_to(20)
    with pytest.raises(ValueError):
        lib.dmm_reading_should_be_close_to(10, -1)
    with pytest.raises(ValueError):
        lib.dmm_reading_should_be_between(20, 10)
    with pytest.raises(AssertionError):
        lib.stable_resistance_should_be_between({"stable": False, "reason": "timeout"}, 1, 2)
    with pytest.raises(AssertionError):
        lib.stable_resistance_should_be_between({"stable": True, "value": 10}, 1, 2)
    lib.close_all_dmms()


def test_stable_resistance_failure_is_not_fabricated():
    lib = lib_with_reading(1000)
    result = lib.try_read_stable_resistance(
        min_settle="20 ms", max_wait="1 ms", sample_interval="1 ms", window_size=3
    )
    assert result["stable"] is False
    assert result["value"] is None
    with pytest.raises(MeasurementNotStableError):
        lib.read_stable_resistance(
            min_settle="20 ms", max_wait="1 ms", sample_interval="1 ms", window_size=3
        )
    lib.close_all_dmms()


def test_open_via_visa_and_serial_factory_paths(monkeypatch):
    from hp34401a_dmm import DriverConfig, FakeTransport, Hp34401A

    def make_driver(*args, **kwargs):
        return Hp34401A(FakeTransport(responses={"SYSTem:VERSion?": "1991.0"}), DriverConfig())

    monkeypatch.setattr(Hp34401A, "from_visa_gpib", staticmethod(make_driver))
    monkeypatch.setattr(Hp34401A, "from_serial", staticmethod(make_driver))
    lib = Hp34401ALibrary()
    assert lib.open_dmm_via_visa("GPIB0::22::INSTR", alias="visa") == "visa"
    assert lib.open_dmm_via_serial("COM1", alias="serial") == "serial"
    lib.close_all_dmms()


def test_transport_neutral_connect_and_python_compatibility(monkeypatch):
    lib = Hp34401ALibrary()
    calls = []

    def visa(resource, **kwargs):
        calls.append(("VISA", resource, kwargs))
        return kwargs.get("alias", "default")

    def serial(port, **kwargs):
        calls.append(("SERIAL", port, kwargs))
        return kwargs.get("alias", "default")

    monkeypatch.setattr(lib, "open_dmm_via_visa", visa)
    monkeypatch.setattr(lib, "open_dmm_via_serial", serial)

    assert lib.connect_dmm("USB0::1::INSTR", alias="usb") == "usb"
    assert calls[-1][0] == "VISA"
    assert lib.connect_dmm("COM7", alias="serial") == "serial"
    assert calls[-1][0] == "SERIAL"
    assert lib.connect_to_dmm("GPIB0::22::INSTR", alias="legacy") == "legacy"
    assert calls[-1][0] == "VISA"
    with pytest.raises(Hp34401ARobotError, match="Unsupported DMM transport"):
        lib.connect_dmm("resource", transport="CAN")


def test_disconnect_python_compatibility_and_metadata():
    lib = Hp34401ALibrary()
    disconnected = lib.get_driver_metadata()
    assert disconnected["driver_version"] == "26.07"
    assert disconnected["state"] == "DISCONNECTED"
    capabilities = lib.get_driver_capabilities()
    assert "connection" in capabilities
    assert "dc_voltage_measurement" in capabilities
    information = lib.get_driver_information()
    assert information["release_class"] == "D0"

    lib.open_simulated_dmm(alias="legacy", reading=1.0)
    metadata = lib.get_driver_metadata("legacy")
    assert metadata["model"] == "34401A"
    assert metadata["transport"] == "FAKE"
    lib.disconnect("legacy")
    assert lib.get_open_dmm_aliases() == []


def test_list_visa_resources_with_fake_module(monkeypatch):
    import sys
    import types

    class RM:
        def __init__(self, library):
            self.library = library

        def list_resources(self):
            return ("GPIB0::22::INSTR",)

        def close(self):
            self.closed = True

    monkeypatch.setitem(sys.modules, "pyvisa", types.SimpleNamespace(ResourceManager=RM))
    lib = Hp34401ALibrary()
    assert lib.list_visa_resources() == ["GPIB0::22::INSTR"]


def test_identity_and_terminal_assertion_failures():
    lib = Hp34401ALibrary()
    with pytest.raises(Hp34401ARobotError):
        lib.open_simulated_dmm(identity="ACME,1234,S,1", terminal="REAR", reading=1)
    lib.open_simulated_dmm(terminal="REAR")
    with pytest.raises(Hp34401ARobotError):
        lib.require_dmm_input_terminal("FRONT")
    lib.close()


def test_failure_branches_for_model_selftest_invalid_reading_and_cleanup(monkeypatch):
    from hp34401a_dmm import MeasurementFunction, MeasurementReading
    from datetime import datetime, timezone

    lib = lib_with_reading(1)
    monkeypatch.setattr(lib, "identify_dmm", lambda alias=None: {"model": "NOT-A-DMM"})
    with pytest.raises(AssertionError):
        lib.dmm_model_should_be_34401a()
    monkeypatch.setattr(
        lib, "run_dmm_self_test", lambda alias=None: {"passed": False, "code": 1, "raw": "1"}
    )
    with pytest.raises(AssertionError):
        lib.dmm_self_test_should_pass()

    session = lib._sessions.get()
    invalid = MeasurementReading(
        timestamp_utc=datetime.now(timezone.utc),
        monotonic_s=0.0,
        function=MeasurementFunction.VOLT_DC,
        value=None,
        unit="V",
        raw="",
        is_valid=False,
    )
    session.last_reading = invalid
    with pytest.raises(Hp34401ARobotError):
        lib.get_last_dmm_reading_value()
    with pytest.raises(AssertionError):
        lib.dmm_reading_should_be_valid()
    with pytest.raises(AssertionError):
        lib.dmm_reading_should_be_between(0, 1)
    lib.close_all_dmms()


def test_list_visa_missing_dependency_and_close_all_error(monkeypatch):
    import builtins

    lib = Hp34401ALibrary()
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyvisa":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(Hp34401ARobotError, match="PyVISA"):
        lib.list_visa_resources()

    class BadSessions:
        active_alias = None

        def close_all(self):
            return ["bad: failed"]

    lib._sessions = BadSessions()
    with pytest.raises(Hp34401ARobotError, match="failed to close"):
        lib.close_all_dmms()
