"""RFDS-008 evidence engine tests (§37: schema/correlation/ordering/redaction/integrity).

Scoped to what rf_hp34401a's hp34401a_dmm/evidence.py actually produces — not an attempt
to cover every optional item in the RFDS-008 checklist. See
docs/logging_and_evidence.md's "what this system deliberately does not do".

Uses `Open Simulated DMM` throughout so no real instrument or VISA runtime is required.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from rf_hp34401a import Hp34401ALibrary
from hp34401a_dmm import evidence as evidence_module

_SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_evidence", _SCRIPTS_DIR / "validate_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_root(tmp_path: Path) -> Path:
    session_root = tmp_path / "results" / "session" / "rf_hp34401a"
    run_dirs = sorted(session_root.iterdir())
    assert run_dirs, "no evidence run directory was created"
    return run_dirs[-1]


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    library = Hp34401ALibrary()
    library.open_simulated_dmm(alias="default", reading=12.5)
    yield library, tmp_path


# ---------------------------------------------------------------------------
# Structure and manifest integrity
# ---------------------------------------------------------------------------

def test_disconnect_all_finalizes_a_complete_evidence_run(lib):
    library, tmp_path = lib
    library.measure_dc_voltage()
    library.disconnect_all()
    root = _run_root(tmp_path)

    for expected in (
        "run_summary.json",
        "run_summary.md",
        "environment.json",
        "device_identity.json",
        "evidence_manifest.json",
        "events/events.jsonl",
        "events/operations.jsonl",
        "protocol/exchanges.jsonl",
        "protocol/outbound_trace.log",
        "integrity/checksums.sha256",
    ):
        assert (root / expected).exists(), f"missing {expected}"

    summary = json.loads((root / "run_summary.json").read_text())
    assert summary["schema"] == "rfds.run_summary"
    assert summary["final_status"] == "PASS"
    assert summary["driver_id"] == "rf_hp34401a"

    identity = json.loads((root / "device_identity.json").read_text())
    assert "default" in identity["sessions"]
    assert identity["sessions"]["default"]["transport"] == "simulation"


def test_single_alias_disconnect_finalizes_when_it_is_the_last_session(lib):
    """Disconnect (not Disconnect All) on the only open alias must also finalize."""
    library, tmp_path = lib
    library.disconnect(alias="default")
    root = _run_root(tmp_path)
    assert (root / "run_summary.json").exists()


def test_multi_alias_session_does_not_finalize_until_all_close(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    library = Hp34401ALibrary()
    library.open_simulated_dmm(alias="a", reading=1.0)
    library.open_simulated_dmm(alias="b", reading=2.0)
    library.disconnect(alias="a")
    session_root = tmp_path / "results" / "session" / "rf_hp34401a"
    if session_root.exists():
        for run_dir in session_root.iterdir():
            assert not (run_dir / "run_summary.json").exists()
    library.disconnect(alias="b")
    root = _run_root(tmp_path)
    assert (root / "run_summary.json").exists()
    identity = json.loads((root / "device_identity.json").read_text())
    assert set(identity["sessions"]) == {"a", "b"}


def test_manifest_hashes_match_files_on_disk(lib):
    library, tmp_path = lib
    library.measure_dc_voltage()
    library.disconnect_all()
    root = _run_root(tmp_path)

    manifest = json.loads((root / "evidence_manifest.json").read_text())
    assert manifest["artifact_count"] == len(manifest["artifacts"])
    assert manifest["artifact_count"] > 0
    for entry in manifest["artifacts"]:
        data = (root / entry["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert len(data) == entry["size_bytes"]

    listed_paths = {entry["path"] for entry in manifest["artifacts"]}
    assert "evidence_manifest.json" not in listed_paths
    assert "integrity/checksums.sha256" not in listed_paths


def test_manifest_lists_every_file_under_the_run_root(lib):
    library, tmp_path = lib
    library.disconnect_all()
    root = _run_root(tmp_path)
    manifest = json.loads((root / "evidence_manifest.json").read_text())
    listed = {entry["path"] for entry in manifest["artifacts"]}
    on_disk = {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and p.name not in ("evidence_manifest.json", "checksums.sha256")
    }
    assert listed == on_disk


# ---------------------------------------------------------------------------
# JSONL correctness: valid JSON, gap-free monotonic sequence per stream
# ---------------------------------------------------------------------------

def test_jsonl_streams_are_valid_and_gap_free(lib):
    library, tmp_path = lib
    library.measure_dc_voltage()
    library.measure_ac_voltage()
    try:
        library.measure_dc_voltage(alias="does-not-exist")
    except Exception:
        pass
    library.disconnect_all()
    root = _run_root(tmp_path)

    for jsonl_path in root.rglob("*.jsonl"):
        sequences = []
        for line in jsonl_path.read_text().splitlines():
            record = json.loads(line)
            sequences.append(record["sequence"])
        assert sequences == list(range(1, len(sequences) + 1)), jsonl_path


def test_protocol_exchanges_are_tagged_with_transport(lib):
    library, tmp_path = lib
    library.measure_dc_voltage()
    library.disconnect_all()
    root = _run_root(tmp_path)
    exchanges = [json.loads(line) for line in (root / "protocol" / "exchanges.jsonl").read_text().splitlines()]
    assert exchanges
    assert all(entry["transport"] == "simulation" for entry in exchanges)
    assert all(entry["session_alias"] == "default" for entry in exchanges)


def test_nested_operations_share_one_correlation_id(lib):
    """Connect-family keywords call _register_connected internally; the resulting
    protocol exchanges should correlate with the outer keyword's operation."""
    library, tmp_path = lib
    library.disconnect_all()
    root = _run_root(tmp_path)
    operations = [json.loads(line) for line in (root / "events" / "operations.jsonl").read_text().splitlines()]
    connect_op = next(op for op in operations if op["capability"] == "Open Simulated DMM")
    exchanges = [json.loads(line) for line in (root / "protocol" / "exchanges.jsonl").read_text().splitlines()]
    assert any(exchange["correlation_id"] == connect_op["correlation_id"] for exchange in exchanges)


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

def test_redact_mapping_masks_sensitive_keys():
    redacted = evidence_module.redact_mapping({"alias": "default", "password": "hunter2", "auth_token": "abc"})
    assert redacted["alias"] == "default"
    assert redacted["password"] == {"value": "<REDACTED>", "redacted": True, "reason": "credential"}
    assert redacted["auth_token"]["redacted"] is True


def test_redaction_applies_to_operation_arguments(tmp_path, monkeypatch):
    """No current keyword takes a credential-shaped argument; this proves the
    plumbing redacts one anyway if a future keyword or caller passes one, by
    exercising EvidenceRun.record_operation() directly."""
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    run = evidence_module.EvidenceRun(driver_id="rf_hp34401a", activity="session")
    with run.record_operation("Test Capability", arguments={"alias": "dut", "api_token": "s3cr3t"}) as op:
        op.set_result("ok")
    run.finalize(status="PASS")
    operations = [json.loads(line) for line in (run.root / "events" / "operations.jsonl").read_text().splitlines()]
    record = operations[0]
    assert record["arguments"]["alias"] == "dut"
    assert record["arguments"]["api_token"] == {"value": "<REDACTED>", "redacted": True, "reason": "credential"}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def test_error_is_recorded_with_traceback_and_category(lib):
    library, tmp_path = lib
    with pytest.raises(Exception):
        library.select_dmm("does-not-exist")
    library.disconnect_all()
    root = _run_root(tmp_path)
    errors = [json.loads(line) for line in (root / "events" / "errors.jsonl").read_text().splitlines()]
    assert len(errors) >= 1
    assert errors[0]["category"] in {
        "VALIDATION", "STATE", "TIMEOUT", "CONNECTION", "PROTOCOL", "DEVICE", "CLEANUP", "UNSUPPORTED", "UNKNOWN",
    }
    assert "Traceback" in errors[0]["traceback"]


# ---------------------------------------------------------------------------
# NullEvidenceRun / evidence_enabled=False
# ---------------------------------------------------------------------------

def test_evidence_disabled_writes_nothing_to_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    library = Hp34401ALibrary(evidence_enabled=False)
    library.open_simulated_dmm(alias="default", reading=1.0)
    library.measure_dc_voltage()
    library.disconnect_all()
    assert not (tmp_path / "results").exists()


def test_evidence_disabled_export_diagnostic_bundle_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("RFDS_EVIDENCE_ROOT", str(tmp_path / "results"))
    library = Hp34401ALibrary(evidence_enabled=False)
    library.open_simulated_dmm(alias="default", reading=1.0)
    assert library.export_diagnostic_bundle() is None
    library.disconnect_all()


# ---------------------------------------------------------------------------
# Export Diagnostic Bundle
# ---------------------------------------------------------------------------

def test_export_diagnostic_bundle_produces_a_readable_zip(lib):
    library, tmp_path = lib
    library.measure_dc_voltage()
    bundle_path = library.export_diagnostic_bundle()
    assert bundle_path is not None
    archive_path = Path(bundle_path)
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert any(name.endswith("environment.json") for name in names)
        assert any(name.endswith("events/operations.jsonl") for name in names)
    library.disconnect_all()


def test_export_diagnostic_bundle_honors_explicit_destination(lib):
    library, tmp_path = lib
    destination = tmp_path / "custom" / "bundle.zip"
    result = library.export_diagnostic_bundle(str(destination))
    assert Path(result) == destination
    assert destination.exists()
    library.disconnect_all()


# ---------------------------------------------------------------------------
# validate_evidence.py
# ---------------------------------------------------------------------------

def test_validate_evidence_script_accepts_a_clean_run(lib):
    library, tmp_path = lib
    library.measure_dc_voltage()
    library.disconnect_all()
    root = _run_root(tmp_path)
    validator = _load_validator()
    findings = validator.validate(root)
    assert findings == []


def test_validate_evidence_script_detects_tampering(lib):
    library, tmp_path = lib
    library.disconnect_all()
    root = _run_root(tmp_path)
    events_path = root / "events" / "events.jsonl"
    with events_path.open("a") as handle:
        handle.write("this is not json\n")
    validator = _load_validator()
    findings = validator.validate(root)
    assert any("HASH MISMATCH" in finding and "events.jsonl" in finding for finding in findings)
    assert any("invalid JSON" in finding for finding in findings)


def test_validate_evidence_script_detects_missing_manifest_entry(lib):
    library, tmp_path = lib
    library.disconnect_all()
    root = _run_root(tmp_path)
    (root / "attachments" / "extra_note.txt").write_text("not tracked")
    validator = _load_validator()
    findings = validator.validate(root)
    assert any("FILE NOT IN MANIFEST" in finding for finding in findings)
