from __future__ import annotations

import json
from pathlib import Path

import pytest

from rf_hp34401a import Hp34401ALibrary
from rf_hp34401a.capabilities import CapabilityRegistry
from rf_hp34401a.configuration import ConfigurationManager
from rf_hp34401a.exceptions import (
    DriverConfigurationError,
    DriverStateError,
    DriverValidationError,
    RFDSDriverError,
)
from rf_hp34401a.plugin import Hp34401APluginProvider


def test_structured_exception_and_canonical_connection_api(tmp_path, monkeypatch):
    monkeypatch.setenv("RF_HP34401A_PROFILE_DIR", str(tmp_path / "profiles"))
    lib = Hp34401ALibrary(default_timeout_s="2 s")
    disconnected = lib.get_connection_state("missing")
    assert disconnected["connected"] is False
    assert lib.is_connected("missing") is False
    assert lib.get_active_connection() is None
    assert lib.get_communication_timeout() == 2.0
    assert lib.set_communication_timeout("3 s") == 3.0
    with pytest.raises(DriverStateError):
        lib.get_communication_timeout("missing")
    with pytest.raises(DriverStateError):
        lib.set_communication_timeout(1, "missing")
    with pytest.raises(DriverValidationError):
        lib.connect()
    with pytest.raises(DriverValidationError):
        lib.connect("SIM::DMM", unknown=True)

    state = lib.connect("SIM::DMM", alias="dmm", timeout_s="500 ms")
    assert state["connected"] and state["simulated"]
    assert state["communication_ok"]
    assert lib.connect("SIM::DMM", alias="dmm")["session_id"] == state["session_id"]
    with pytest.raises(DriverStateError):
        lib.connect("SIM::OTHER", alias="dmm")
    assert lib.check_communication("dmm") is True
    assert "34401A" in lib.get_identity("dmm")
    assert "34401A" in lib.get_identity("dmm", refresh=True)
    assert lib.select_connection("dmm")["active"] is True
    assert lib.list_connections()[0]["alias"] == "dmm"
    assert lib.get_active_connection() == "dmm"
    assert lib.set_communication_timeout("1.5 s", "dmm") == 1.5
    assert lib.get_communication_timeout("dmm") == 1.5
    lib.disconnect("dmm")
    lib.disconnect("dmm")
    assert not lib.is_connected("dmm")

    err = DriverValidationError("bad input", operation="Connect", alias="x")
    assert isinstance(err, RFDSDriverError)
    data = err.to_dict()
    assert data["code"] == "RFDS-VAL-001"
    assert data["alias"] == "x"
    assert "Retryable=no" in str(err)


def test_driver_information_metadata_capability_discovery_and_filters():
    registry = CapabilityRegistry()
    ids = registry.ids()
    assert ids == sorted(ids)
    assert "connection" in ids
    assert registry.model_ids()[0].count(".") >= 1
    static = registry.model(mode="static")
    assert static["source"]["connected"] is False
    assert static["identity"]["model"] == "UNKNOWN"
    with pytest.raises(DriverValidationError):
        registry.model(mode="invalid")
    cap = registry.get("measure.voltage.dc", connected=True)
    assert cap["availability"]["available"] is True
    assert cap["timing"]["retry_safe"] is False
    with pytest.raises(DriverValidationError):
        registry.get("missing")
    with pytest.raises(DriverValidationError):
        registry.find(maximum_risk="invalid")
    assert registry.find(capability_id="measure.", maximum_risk="low")
    assert registry.find(keyword="Voltage", available_only=True, connected=True)
    assert registry.find(available_only=True, connected=False)
    invalid = registry.validate_bindings([])
    assert invalid["valid"] is False
    valid = registry.validate_bindings(
        item["binding"]["robot_keyword"] for item in static["capabilities"]
    )
    assert valid["valid"] is True
    assert valid["actual_robot_keyword_count"] >= valid["capability_count"]

    lib = Hp34401ALibrary()
    info = lib.get_driver_information()
    assert info["package_version"] == "26.07"
    assert info["release_class"] == "D0"
    assert info["capability_ids"] == ids
    metadata = lib.get_driver_metadata()
    assert metadata["driver_status"] == "D0_DEVELOPMENT_CANDIDATE"
    assert metadata["state"] == "DISCONNECTED"
    assert lib.get_driver_capability_model("static")["source"]["connected"] is False
    assert lib.get_driver_capability("measure.voltage.dc", "static")["risk"] == "low"
    assert lib.find_driver_capabilities(capability_id="measure.", maximum_risk="low", mode="static")
    assert lib.get_driver_features("static")["simulation"] is True
    assert lib.refresh_driver_capabilities("static")["validation"]["valid"] is True
    assert lib.validate_driver_capabilities()["valid"] is True

    lib.connect("SIM::DMM")
    live = lib.get_driver_capability_model("live")
    assert live["identity"]["model"] == "34401A"
    assert lib.find_driver_capabilities(available_only=True, mode="effective")
    assert lib.get_driver_metadata()["model"] == "34401A"
    lib.disconnect_all()


def test_configuration_manager_all_paths(tmp_path, monkeypatch):
    profile_dir = tmp_path / "profiles"
    monkeypatch.setenv("RF_HP34401A_PROFILE_DIR", str(profile_dir))
    manager = ConfigurationManager()
    schema = manager.schema()
    default = manager.default()
    assert schema["$id"]
    sources = manager.effective(include_sources=True)["metadata"]["resolved_sources"]
    assert sources["settings.timeouts.communication_s"] == "PACKAGE_DEFAULT"
    assert manager.fingerprint().startswith("sha256:")
    assert len(manager.fingerprint().split(":", 1)[1]) == 64
    assert manager.validate(default) == default

    bad_cases = [
        None,
        {},
        {**default, "rfds014_version": "9"},
        {**default, "schema_id": "bad"},
        {**default, "schema_version": "9"},
        {**default, "driver": {"driver_name": "bad"}},
        {**default, "profile": "bad"},
        {**default, "settings": "bad"},
    ]
    for bad in bad_cases:
        with pytest.raises(DriverValidationError):
            manager.validate(bad)  # type: ignore[arg-type]

    for profile_name in ["", ".hidden", "bad/name", "x" * 65]:
        bad = json.loads(json.dumps(default))
        bad["profile"]["name"] = profile_name
        with pytest.raises(DriverValidationError):
            manager.validate(bad)

    bad = json.loads(json.dumps(default))
    bad["settings"]["unknown"] = {}
    with pytest.raises(DriverValidationError):
        manager.validate(bad, strict=True)
    # RFDS-014 non-strict compatibility does not permit unknown core keys.
    with pytest.raises(DriverValidationError):
        manager.validate(bad, strict=False)

    for section in ("timeouts", "simulation", "transport"):
        bad = json.loads(json.dumps(default))
        bad["settings"][section] = "bad"
        with pytest.raises(DriverValidationError):
            manager.validate(bad)
    bad = json.loads(json.dumps(default))
    bad["settings"]["timeouts"]["communication_s"] = 0
    with pytest.raises(DriverValidationError):
        manager.validate(bad)
    bad = json.loads(json.dumps(default))
    bad["settings"]["simulation"]["enabled"] = "yes"
    with pytest.raises(DriverValidationError):
        manager.validate(bad)
    bad = json.loads(json.dumps(default))
    bad["settings"]["transport"]["resource"] = 1
    with pytest.raises(DriverValidationError):
        manager.validate(bad)
    bad = json.loads(json.dumps(default))
    del bad["settings"]["retry"]
    with pytest.raises(DriverValidationError):
        manager.validate(bad)

    applied = manager.apply(default)
    assert (
        applied["metadata"]["resolved_sources"]["settings.retry.max_query_retries"]
        == "RUNTIME_IMPORT"
    )
    text = json.dumps(default)
    assert manager.import_json(text, validate_only=True)["schema_id"]
    path = tmp_path / "profile.json"
    path.write_text(text, encoding="utf-8")
    assert manager.import_json(path, validate_only=True)["schema_id"]
    with pytest.raises(DriverConfigurationError):
        manager.import_json("{broken")
    exported_path = tmp_path / "export" / "profile.json"
    exported = manager.export_json(exported_path, indent=4)
    assert exported_path.read_text(encoding="utf-8") == exported

    saved = Path(manager.save_profile("profile_one"))
    assert saved.exists()
    with pytest.raises(DriverConfigurationError):
        manager.save_profile("profile_one")
    manager.save_profile("profile_one", overwrite=True)
    assert manager.list_profiles() == ["profile_one"]
    assert (
        manager.load_profile("profile_one", validate_only=True)["profile"]["name"] == "profile_one"
    )
    manager.delete_profile("profile_one")
    manager.delete_profile("profile_one")
    assert manager.list_profiles() == []
    with pytest.raises(DriverConfigurationError):
        manager.load_profile("missing")
    reset = manager.reset()
    assert reset["metadata"]["resolved_sources"]["settings.transport.kind"] == "PACKAGE_DEFAULT"


def test_library_configuration_keywords_and_raw_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("RF_HP34401A_PROFILE_DIR", str(tmp_path / "profiles"))
    lib = Hp34401ALibrary()
    schema = lib.get_driver_configuration_schema()
    default = lib.get_driver_default_configuration()
    assert schema["$id"]
    assert lib.get_driver_configuration("DEFAULT") == default
    effective = lib.get_driver_configuration(include_sources=True)
    assert effective["metadata"]["configuration_fingerprint"].startswith("sha256:")
    with pytest.raises(DriverValidationError):
        lib.get_driver_configuration("INVALID")
    assert lib.validate_driver_configuration(default)["valid"] is True
    assert lib.import_driver_configuration(default, validate_only=True)["schema_id"]
    assert lib.import_driver_configuration(default)["schema_id"]
    export_path = tmp_path / "export.json"
    assert json.loads(lib.export_driver_configuration(str(export_path)))["schema_id"]
    assert Path(lib.save_driver_configuration("unit", overwrite=True)).exists()
    assert "unit" in lib.list_driver_configuration_profiles()
    assert lib.load_driver_configuration("unit", validate_only=True)["profile"]["name"] == "unit"
    lib.delete_driver_configuration_profile("unit")
    assert lib.reset_driver_configuration()["profile"]["scope"] == "PACKAGE"

    lib.connect("SIM::DMM")
    with pytest.raises(DriverStateError):
        lib.query_raw_command("*IDN?")
    assert lib.set_raw_io_enabled(True) is True
    assert "34401A" in lib.query_raw_command("*IDN?", timeout_s="1 s")
    lib.write_raw_command("*CLS")
    assert isinstance(lib.read_raw_response(timeout_s="1 s"), str)
    assert lib.set_raw_io_enabled(False) is False
    lib.disconnect_all()


def test_plugin_provider_is_metadata_only():
    descriptor = Hp34401APluginProvider.get_descriptor()
    assert descriptor["plugin_id"] == "rf_hp34401a"
    assert descriptor["installed_driver_version"] == "26.07"
    status = Hp34401APluginProvider.validate_environment()
    assert status["status"] in {"PASS", "FAIL"}
    assert {item["id"] for item in status["checks"]} == {
        "python",
        "robotframework",
        "scpi-driver-core",
        "pyvisa",
        "pyserial",
    }
    core = next(item for item in status["checks"] if item["id"] == "scpi-driver-core")
    assert core["required"] is True
    library = Hp34401APluginProvider.create_library()
    assert isinstance(library, Hp34401ALibrary)
    configured = Hp34401APluginProvider.create_library(library.get_driver_default_configuration())
    assert configured.get_driver_configuration()["schema_id"] == "rf_hp34401a.configuration"


def test_real_hardware_all_api_suite_static_inventory():
    import importlib.util

    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "validate_real_hardware_api_suite.py"
    spec = importlib.util.spec_from_file_location("validate_real_hardware_api_suite", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.validate() == []


def test_real_hardware_boolean_normalization():
    from tests.hil.support.RealHardwareApiCoverage import RealHardwareApiCoverage

    helper = RealHardwareApiCoverage()
    for value in (True, 1, "true", "TRUE", " yes ", "On", "enabled"):
        assert helper.normalize_boolean_value(value, "flag") is True
    for value in (False, 0, "false", "FALSE", " no ", "Off", "disabled", ""):
        assert helper.normalize_boolean_value(value, "flag") is False
    with pytest.raises(AssertionError, match="flag must be a Boolean value"):
        helper.normalize_boolean_value("maybe", "flag")
