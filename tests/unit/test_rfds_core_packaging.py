"""Regression tests for the shared-core packaging requirement.

Historically this asserted the presence of ``rfds-core``, a package that was
never published anywhere (no PyPI release, no repository) — see
``docs/scpi_driver_core_review.md``. These tests now assert the real
dependency, ``scpi-driver-core``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from rf_hp34401a.plugin import Hp34401APluginProvider

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def test_scpi_driver_core_is_a_runtime_dependency() -> None:
    """scpi-driver-core must be in the main project dependency set."""
    text = (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_section = text.split("[project.optional-dependencies]", 1)[0]
    assert "scpi-driver-core @ git+" in project_section


def test_plugin_environment_treats_missing_scpi_driver_core_as_required(monkeypatch) -> None:
    """Plugin discovery must not report a conformant environment without scpi-driver-core."""
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: None if name == "scpi_driver_core" else object(),
    )

    result = Hp34401APluginProvider.validate_environment()
    check = next(item for item in result["checks"] if item["id"] == "scpi-driver-core")

    assert check["required"] is True
    assert check["status"] == "FAIL"
    assert result["status"] == "FAIL"
