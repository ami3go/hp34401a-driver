#!/usr/bin/env python3
"""Verify that the real-hardware Robot suite accounts for every public keyword."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api" / "public_api.yaml"
SUITE = ROOT / "tests" / "hil" / "verify_all_public_api_real_hardware.robot"
HELPER = ROOT / "tests" / "hil" / "support" / "RealHardwareApiCoverage.py"
LISTENER = ROOT / "tests" / "hil" / "support" / "RealHardwareApiListener.py"
POWERSHELL_RUNNER = ROOT / "scripts" / "run_all_api_hil.ps1"
SHELL_RUNNER = ROOT / "scripts" / "run_all_api_hil.sh"


def validate() -> list[str]:
    errors: list[str] = []
    api = json.loads(API.read_text(encoding="utf-8"))
    names = [str(item["name"]) for item in api["keywords"]]
    text = SUITE.read_text(encoding="utf-8")
    missing = [name for name in names if name not in text]
    if missing:
        errors.append(f"Public keywords missing from real-HIL suite: {missing}")
    required_controls = [
        "${HIL_ENABLED}", "${FAIL_ON_EXCLUSIONS}", "${VISA_RESOURCE}",
        "Exclude Real Hardware API Keywords", "Finalize Real Hardware API Coverage",
        "Suite Teardown", "RUN_DC_VOLTAGE_PROFILE", "RUN_RAW_IO_PROFILE",
        "RUN_RESET_PROFILE", "RUN_SERIAL_PROFILE",
    ]
    for control in required_controls:
        if control not in text:
            errors.append(f"Missing required HIL control {control!r}")
    if "Open Simulated DMM" not in text:
        errors.append("The simulator-only public API must remain explicitly accounted for")
    try:
        exclusion_block = text.split("Register Disabled Profile Exclusions\n", 1)[1].split(
            "\nNormalize HIL Boolean Variables\n", 1
        )[0]
    except IndexError:
        exclusion_block = ""
    excluded = {
        line.strip()[7:].strip()
        for line in exclusion_block.splitlines()
        if line.strip().startswith("...    ") and line.strip()[7:].strip() in names
    }
    invoked: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("    "):
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("[", "...", "#", "IF ", "END", "ELSE")):
            continue
        stripped = re.sub(r"^\$\{[^}]+\}=\s{2,}", "", stripped)
        token = re.split(r"\s{2,}", stripped, maxsplit=1)[0]
        if token in names:
            invoked.add(token)
    uncovered = sorted(set(names) - excluded - invoked)
    if uncovered:
        errors.append(f"Default HIL profile leaves APIs neither invoked nor excluded: {uncovered}")
    if "Register Disabled Profile Exclusions" not in text:
        errors.append("Disabled profiles must be registered during suite setup")
    if "Pass Execution" not in text:
        errors.append("Disabled profiles must terminate cleanly after recording EXCLUDED APIs")
    helper = HELPER.read_text(encoding="utf-8")
    if "load_results" not in helper or "merge_record" not in helper:
        errors.append("HIL coverage helper must use file-backed state")
    if not LISTENER.exists():
        errors.append("Explicit real-hardware API listener is missing")
    else:
        listener = LISTENER.read_text(encoding="utf-8")
        if "def end_keyword" not in listener or "merge_record" not in listener:
            errors.append("Explicit listener does not persist public keyword results")
    for runner in (POWERSHELL_RUNNER, SHELL_RUNNER):
        runner_text = runner.read_text(encoding="utf-8")
        if "--listener" not in runner_text or "RF_HP34401A_HIL_COVERAGE_STATE" not in runner_text:
            errors.append(f"{runner.name} must register the file-backed Robot listener")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Real-hardware all-API suite validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    count = len(json.loads(API.read_text(encoding="utf-8"))["keywords"])
    print(f"Real-hardware all-API suite validation PASSED: {count}/{count} keyword names accounted for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
