from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

from rf_hp34401a import Hp34401ALibrary


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas" / "evidence"


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _validate(name: str, instance: dict) -> None:
    Draft7Validator(_schema(name), format_checker=FormatChecker()).validate(instance)


def _run_root(tmp_path: Path) -> Path:
    parent = tmp_path / "results" / "session" / "rf_hp34401a"
    roots = sorted(path for path in parent.iterdir() if path.is_dir())
    assert roots
    return roots[-1]


def test_finalized_evidence_matches_published_json_schemas(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    lib = Hp34401ALibrary()
    lib.open_simulated_dmm(alias="dut", reading=2.5)
    lib.measure_dc_voltage(alias="dut")
    try:
        lib.select_dmm("missing")
    except Exception:
        pass
    lib.disconnect_all()

    root = _run_root(tmp_path)
    _validate("run_summary.schema.json", json.loads((root / "run_summary.json").read_text()))
    _validate("device_identity.schema.json", json.loads((root / "device_identity.json").read_text()))
    _validate("evidence_manifest.schema.json", json.loads((root / "evidence_manifest.json").read_text()))

    streams = [
        ("events/events.jsonl", "event.schema.json"),
        ("events/operations.jsonl", "operation.schema.json"),
        ("events/errors.jsonl", "error.schema.json"),
    ]
    for relative, schema_name in streams:
        path = root / relative
        assert path.is_file()
        for line in path.read_text(encoding="utf-8").splitlines():
            _validate(schema_name, json.loads(line))
