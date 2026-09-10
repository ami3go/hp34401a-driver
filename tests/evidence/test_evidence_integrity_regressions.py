from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from rf_hp34401a import Hp34401ALibrary


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_evidence_regression", SCRIPTS / "validate_evidence.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_root(tmp_path: Path) -> Path:
    parent = tmp_path / "results" / "session" / "rf_hp34401a"
    roots = sorted(path for path in parent.iterdir() if path.is_dir())
    assert roots
    return roots[-1]


def test_prior_keyword_failure_cannot_be_hidden_by_successful_disconnect(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    library = Hp34401ALibrary()
    library.open_simulated_dmm(alias="default", reading=1.0)
    with pytest.raises(Exception):
        library.select_dmm("missing")
    library.disconnect_all()

    root = _run_root(tmp_path)
    summary = json.loads((root / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["final_status"] == "FAIL"
    assert summary["error_count"] >= 1


def test_diagnostic_export_keeps_live_manifest_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    library = Hp34401ALibrary()
    library.open_simulated_dmm(alias="default", reading=1.0)
    library.measure_dc_voltage()
    bundle = library.export_diagnostic_bundle()
    assert bundle is not None and Path(bundle).exists()

    root = _run_root(tmp_path)
    # Mid-session export is a valid integrity snapshot even though the final
    # run summary is intentionally not written until disconnect/listener close.
    findings = _load_validator().validate(root)
    assert all("HASH MISMATCH" not in finding for finding in findings)
    assert all("FILE NOT IN MANIFEST" not in finding for finding in findings)
    library.disconnect_all()
    assert _load_validator().validate(root) == []


def test_simulated_session_is_not_labeled_real_hardware(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    library = Hp34401ALibrary()
    library.open_simulated_dmm(alias="default", reading=1.0)
    root = _run_root(tmp_path)
    environment = json.loads((root / "environment.json").read_text(encoding="utf-8"))
    assert environment["execution_mode"] == "SIMULATION"
    library.disconnect_all()
