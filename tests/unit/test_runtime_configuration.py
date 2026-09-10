from __future__ import annotations

import json
from pathlib import Path

import pytest

from rf_hp34401a import Hp34401ALibrary
from rf_hp34401a.exceptions import DriverValidationError


def _profile(lib: Hp34401ALibrary) -> dict:
    return json.loads(json.dumps(lib.get_driver_default_configuration()))


def test_imported_simulation_profile_is_explicit_connect_selector(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    lib = Hp34401ALibrary(default_timeout_s="2 s")
    profile = _profile(lib)
    profile["profile"] = {
        "name": "runtime",
        "description": "runtime policy test",
        "scope": "SESSION",
    }
    profile["settings"]["simulation"]["enabled"] = True
    profile["settings"]["simulation"]["reading"] = 7.5
    profile["settings"]["timeouts"]["communication_s"] = 3.0
    profile["settings"]["timeouts"]["self_test_s"] = 4.0
    profile["settings"]["timeouts"]["long_measurement_s"] = 5.0
    profile["settings"]["retry"]["query_enabled"] = False
    profile["settings"]["retry"]["max_query_retries"] = 0
    profile["settings"]["safety"]["allow_raw_scpi"] = True
    profile["settings"]["safety"]["allow_calibration_commands"] = True
    profile["settings"]["logging"]["raw_traffic"] = True

    imported = lib.import_driver_configuration(profile)
    sources = imported["metadata"]["resolved_sources"]
    assert sources["settings.timeouts.communication_s"] == "RUNTIME_IMPORT"
    assert lib.get_communication_timeout() == 3.0

    state = lib.connect(alias="configured")
    assert state["simulated"] is True
    assert state["resource"].startswith("SIM::")
    assert lib.measure_dc_voltage(alias="configured") == 7.5
    assert lib.get_communication_timeout("configured") == 3.0

    session = lib._sessions.get("configured")
    assert session.driver._cfg.default_timeout_s == 3.0
    assert session.driver._cfg.self_test_timeout_s == 4.0
    assert session.driver._cfg.long_measurement_timeout_s == 5.0
    assert session.driver._cfg.retry_queries is False
    assert session.driver._cfg.max_query_retries == 0
    assert session.driver._cfg.allow_calibration_commands is True
    assert session.driver._cfg.raw_traffic_log is True
    assert lib.query_raw_command("*IDN?", alias="configured")
    lib.disconnect_all()


def test_package_default_simulation_never_silently_replaces_missing_resource(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    lib = Hp34401ALibrary()
    with pytest.raises(DriverValidationError):
        lib.connect()


def test_reset_configuration_restores_package_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    lib = Hp34401ALibrary(default_timeout_s="2 s")
    profile = _profile(lib)
    profile["profile"]["name"] = "runtime"
    profile["profile"]["scope"] = "SESSION"
    profile["settings"]["timeouts"]["communication_s"] = 3.0
    profile["settings"]["safety"]["allow_raw_scpi"] = True
    lib.import_driver_configuration(profile)
    assert lib.get_communication_timeout() == 3.0
    reset = lib.reset_driver_configuration()
    assert reset["profile"]["scope"] == "PACKAGE"
    assert lib.get_communication_timeout() == 10.0
    assert lib._allow_raw_io is False


def test_zero_timeout_is_structured_public_validation_error():
    lib = Hp34401ALibrary()
    with pytest.raises(DriverValidationError):
        lib.set_communication_timeout(0)
    with pytest.raises(DriverValidationError):
        lib.connect("SIM::DMM", timeout_s=0)
