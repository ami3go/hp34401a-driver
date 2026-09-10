#!/usr/bin/env python3
"""Validate one rf_hp34401a RFDS-008 evidence run directory.

Checks (RFDS-008 §37 integrity/ordering/schema tests, scoped to what this
driver actually produces):

1. ``run_summary.json`` and ``evidence_manifest.json`` exist and parse as JSON.
2. Every artifact listed in the manifest exists, and its SHA-256 hash matches
   the file on disk.
3. No file under the run directory is missing from the manifest (except the
   manifest itself and files under ``integrity/``).
4. Every ``.jsonl`` file under ``events/`` and ``protocol/`` contains one JSON
   object per line, and each stream's ``sequence`` field is a gap-free,
   duplicate-free run starting at 1.

Exit code is 0 if every check passes, 1 otherwise. Findings are printed to
stderr; a one-line OK/FAIL summary is printed to stdout.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_manifest(root: Path, findings: list) -> None:
    manifest_path = root / "evidence_manifest.json"
    if not manifest_path.exists():
        findings.append(f"MISSING: {manifest_path}")
        return
    manifest = _load_json(manifest_path)
    listed_paths = set()
    for entry in manifest.get("artifacts", []):
        rel = entry["path"]
        listed_paths.add(rel)
        artifact_path = root / rel
        if not artifact_path.exists():
            findings.append(f"MANIFEST ENTRY MISSING FROM DISK: {rel}")
            continue
        actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if actual_hash != entry["sha256"]:
            findings.append(f"HASH MISMATCH: {rel} (manifest={entry['sha256']}, actual={actual_hash})")
        actual_size = artifact_path.stat().st_size
        if actual_size != entry["size_bytes"]:
            findings.append(f"SIZE MISMATCH: {rel} (manifest={entry['size_bytes']}, actual={actual_size})")

    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel == "evidence_manifest.json" or rel.startswith("integrity/"):
            continue
        if rel not in listed_paths:
            findings.append(f"FILE NOT IN MANIFEST: {rel}")


def _check_run_summary(root: Path, findings: list) -> None:
    path = root / "run_summary.json"
    if not path.exists():
        findings.append(f"MISSING: {path}")
        return
    summary = _load_json(path)
    for required in ("schema", "run_id", "final_status", "error_count", "evidence_completeness"):
        if required not in summary:
            findings.append(f"run_summary.json missing required field: {required}")


def _check_jsonl_streams(root: Path, findings: list) -> None:
    for jsonl_path in sorted(root.rglob("*.jsonl")):
        rel = jsonl_path.relative_to(root)
        sequences = []
        for line_number, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                findings.append(f"{rel}:{line_number}: invalid JSON ({exc})")
                continue
            sequence = record.get("sequence")
            if sequence is None:
                findings.append(f"{rel}:{line_number}: missing 'sequence' field")
                continue
            sequences.append(sequence)
        expected = list(range(1, len(sequences) + 1))
        if sequences != expected:
            findings.append(f"{rel}: sequence numbers {sequences} are not a gap-free run starting at 1")


def validate(root: Path) -> list:
    findings: list = []
    if not root.exists():
        return [f"run directory does not exist: {root}"]
    _check_run_summary(root, findings)
    _check_manifest(root, findings)
    _check_jsonl_streams(root, findings)
    return findings


def main(argv: list) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <evidence_run_directory>", file=sys.stderr)
        return 2
    root = Path(argv[1])
    findings = validate(root)
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        print(f"FAIL: {len(findings)} finding(s) in {root}")
        return 1
    print(f"OK: {root} is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
