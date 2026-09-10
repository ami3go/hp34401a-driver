from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import rf_hp34401a.configuration as configuration_module
from rf_hp34401a.configuration import ConfigurationManager
from rf_hp34401a.exceptions import DriverConfigurationError, DriverValidationError


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
RESOURCE_DIR = PACKAGE_ROOT / "rf_hp34401a" / "resources" / "configuration"


def test_root_and_packaged_configuration_authorities_match():
    assert (PACKAGE_ROOT / "config" / "schema.json").read_bytes() == (
        RESOURCE_DIR / "schema.json"
    ).read_bytes()
    assert (PACKAGE_ROOT / "config" / "schema.lock").read_bytes() == (
        RESOURCE_DIR / "schema.lock"
    ).read_bytes()
    assert (PACKAGE_ROOT / "config" / "default.json").read_bytes() == (
        RESOURCE_DIR / "default.json"
    ).read_bytes()


def test_schema_lock_contains_required_rfds_fields():
    lock = json.loads((RESOURCE_DIR / "schema.lock").read_text(encoding="utf-8"))
    assert lock["schema_id"] == "rf_hp34401a.configuration"
    assert lock["schema_version"] == "1.0.0"
    assert len(lock["sha256"]) == 64


def test_schema_tamper_fails_configuration_initialization(tmp_path, monkeypatch):
    tampered = tmp_path / "configuration"
    shutil.copytree(RESOURCE_DIR, tampered)
    schema_path = tampered / "schema.json"
    schema_path.write_text(schema_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    monkeypatch.setattr(configuration_module, "_resource_dir", lambda: tampered)
    with pytest.raises(DriverConfigurationError, match="RFDS_CONFIG_INTEGRITY"):
        ConfigurationManager()


def test_json_schema_rejects_unknown_nested_core_fields_even_non_strict():
    manager = ConfigurationManager()
    document = manager.default()
    document["settings"]["retry"]["unsupported"] = True
    with pytest.raises(DriverValidationError):
        manager.validate(document, strict=False)


def test_json_schema_rejects_invalid_enums_and_missing_required_sections():
    manager = ConfigurationManager()
    invalid_enum = manager.default()
    invalid_enum["settings"]["transport"]["kind"] = "CAN"
    with pytest.raises(DriverValidationError):
        manager.validate(invalid_enum)

    missing = manager.default()
    del missing["settings"]["safety"]
    with pytest.raises(DriverValidationError):
        manager.validate(missing)
