from __future__ import annotations

import json
from pathlib import Path

from rf_hp34401a import Hp34401ALibrary


def _run_root(tmp_path: Path) -> Path:
    roots = sorted((tmp_path / "results" / "session" / "rf_hp34401a").iterdir())
    assert roots
    return roots[-1]


def test_listener_close_finalizes_run_without_explicit_disconnect(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    lib = Hp34401ALibrary()
    lib.open_simulated_dmm(reading=1.0)
    lib.measure_dc_voltage()
    lib.close()

    root = _run_root(tmp_path)
    summary = json.loads((root / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["final_status"] == "PASS"
    assert (root / "evidence_manifest.json").is_file()


def test_listener_close_preserves_prior_failure_status(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    lib = Hp34401ALibrary()
    lib.open_simulated_dmm(reading=1.0)
    try:
        lib.select_dmm("missing")
    except Exception:
        pass
    lib.close()

    root = _run_root(tmp_path)
    summary = json.loads((root / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["final_status"] == "FAIL"
