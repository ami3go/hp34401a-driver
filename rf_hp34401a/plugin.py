"""Side-effect-free RFDS-015 plugin provider."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import sysconfig
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .version import __version__

_SCPI_DRIVER_CORE_REQUIREMENT = ">=0.1.0.dev0 (pre-release, installed from source/VCS)"
_ARTIFACT_INSTALL_PATHS = {
    "capability_model": Path("share/rf_hp34401a/capability/capability_model.yaml"),
    "configuration_schema": Path("share/rf_hp34401a/config/schema.json"),
    "ai_contract": Path("share/rf_hp34401a/ai/hp34401a_ai_contract.yaml"),
    "protocol_vectors": Path("share/rf_hp34401a/conformance/protocol_vectors.yaml"),
}


def _scpi_driver_core_check() -> dict[str, Any]:
    """Return a side-effect-free scpi-driver-core compatibility check.

    This driver previously required a package named ``rfds-core`` that was
    never published anywhere (no PyPI release, no repository). The actual
    shared transport/SCPI infrastructure this driver is built on is
    ``scpi-driver-core`` (import name ``scpi_driver_core``); see
    ``docs/scpi_driver_core_review.md``.
    """

    check: dict[str, Any] = {
        "id": "scpi-driver-core",
        "status": "FAIL",
        "required": True,
        "requirement": _SCPI_DRIVER_CORE_REQUIREMENT,
        "installed_version": None,
    }
    if importlib.util.find_spec("scpi_driver_core") is None:
        check["reason"] = "scpi_driver_core module is not importable"
        return check
    try:
        installed = importlib.metadata.version("scpi-driver-core")
    except importlib.metadata.PackageNotFoundError:
        check["reason"] = (
            "scpi_driver_core is importable but scpi-driver-core distribution "
            "metadata is missing"
        )
        return check

    check["installed_version"] = installed
    check["status"] = "PASS"
    return check


def _resolve_artifact(field: str, source_relative: str) -> str:
    """Resolve a manifest artifact from a source checkout or installed wheel."""

    source_candidate = Path(__file__).resolve().parents[1] / source_relative
    if source_candidate.exists():
        return str(source_candidate)

    data_root = Path(sysconfig.get_path("data"))
    return str(data_root / _ARTIFACT_INSTALL_PATHS[field])


class Hp34401APluginProvider:
    """Expose driver metadata without constructing or connecting the driver."""

    @classmethod
    def _manifest(cls) -> dict[str, Any]:
        path = Path(__file__).resolve().parent / "resources" / "plugin_manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def get_descriptor(cls) -> dict[str, Any]:
        descriptor = cls._manifest()
        descriptor["installed_driver_version"] = __version__
        descriptor["resolved_artifacts"] = {
            field: _resolve_artifact(field, str(descriptor[field]))
            for field in _ARTIFACT_INSTALL_PATHS
        }
        return descriptor

    @classmethod
    def validate_environment(cls) -> dict[str, Any]:
        checks: list[dict[str, Any]] = [
            {"id": "python", "status": "PASS", "value": platform.python_version()},
            {
                "id": "robotframework",
                "status": "PASS" if importlib.util.find_spec("robot") else "FAIL",
                "required": True,
            },
            _scpi_driver_core_check(),
            {
                "id": "pyvisa",
                "status": "PASS" if importlib.util.find_spec("pyvisa") else "WARNING",
                "required": False,
                "capability": "VISA_GPIB",
            },
            {
                "id": "pyserial",
                "status": "PASS" if importlib.util.find_spec("serial") else "WARNING",
                "required": False,
                "capability": "SERIAL_RS232",
            },
        ]
        return {
            "status": "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS",
            "checks": checks,
        }

    @classmethod
    def create_library(cls, configuration: Mapping[str, Any] | None = None) -> Any:
        # Delayed import preserves metadata-only discovery and import safety.
        from .library import Hp34401ALibrary

        library = Hp34401ALibrary()
        if configuration is not None:
            library.import_driver_configuration(configuration)
        return library
