#!/usr/bin/env python3
"""Validate RFDS-017 and RFDS-002 artifacts against the actual Robot surface."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANDATORY_TOP_LEVEL = {
    "rfds017_version", "identity", "mental_model", "state_machine", "resources",
    "dependencies", "capabilities", "errors", "safety", "verification_objectives",
    "setup_teardown", "limitations", "planning_hints", "unknown_handling",
    "conformance", "open_questions",
}


def _format(value: Any) -> str:
    if value is None:
        return "${NONE}"
    if value is True:
        return "${TRUE}"
    if value is False:
        return "${FALSE}"
    return str(value)


def _canonical_text_bytes(path: Path) -> bytes:
    """Hash reviewed text independently of checkout LF/CRLF conversion."""
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8")


def public_keyword_surface() -> list[str]:
    """Return the effective Robot keyword surface, including inherited methods."""
    from rf_hp34401a import Hp34401ALibrary

    lines: list[str] = []
    seen: set[str] = set()
    for _python_name, method in inspect.getmembers(Hp34401ALibrary, predicate=callable):
        name = getattr(method, "robot_name", None)
        if not name:
            continue
        robot_name = str(name)
        if robot_name in seen:
            raise RuntimeError(f"Duplicate Robot keyword export {robot_name!r}")
        seen.add(robot_name)
        signature = inspect.signature(method)
        parts: list[str] = []
        for parameter in signature.parameters.values():
            if parameter.name == "self":
                continue
            if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                parts.append(f"*{parameter.name}")
                continue
            if parameter.kind is inspect.Parameter.VAR_KEYWORD:
                parts.append(f"**{parameter.name}")
                continue
            if parameter.default is inspect.Parameter.empty:
                parts.append(parameter.name)
            else:
                parts.append(f"{parameter.name}={_format(parameter.default)}")
        lines.append(f"{robot_name}({', '.join(parts)})")
    return sorted(lines, key=lambda line: line.split("(", 1)[0])


def surface_hash(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def validate(contract_path: Path | None = None, lock_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    contract_file = contract_path or (ROOT / "ai" / "hp34401a_ai_contract.yaml")
    lock_file = lock_path or (ROOT / "ai" / "hp34401a_ai_contract.lock")
    public_api_path = ROOT / "api" / "public_api.yaml"
    contract = load_yaml(contract_file)
    lock = load_yaml(lock_file)
    public_api = json.loads(public_api_path.read_text(encoding="utf-8"))
    live = public_keyword_surface()
    live_names = {line.split("(", 1)[0] for line in live}
    contract_lines = sorted(
        [str(item.get("signature")) for item in contract.get("capabilities", [])],
        key=lambda line: line.split("(", 1)[0],
    )
    api_lines = sorted(
        [str(item.get("signature")) for item in public_api.get("keywords", [])],
        key=lambda line: line.split("(", 1)[0],
    )
    missing = sorted(MANDATORY_TOP_LEVEL - set(contract))
    if missing:
        errors.append(f"Missing AI-contract sections: {missing}")
    if live != contract_lines:
        errors.append("RFDS-017 keyword signatures differ from the effective Robot library")
    if live != api_lines:
        errors.append("RFDS-002 public_api keyword signatures differ from the effective Robot library")
    inventory = load_yaml(ROOT / "tests" / "conformance" / "data" / "keyword_inventory.yaml")
    inventory_names = {str(item.get("keyword")) for item in inventory.get("keywords", [])}
    if inventory_names != live_names:
        errors.append(
            f"RFDS-019 inventory mismatch: missing={sorted(live_names-inventory_names)}, "
            f"extra={sorted(inventory_names-live_names)}"
        )
    expected_hash = surface_hash(live)
    if lock.get("algorithm") != "SHA-256" or lock.get("sha256") != expected_hash:
        errors.append("hp34401a_ai_contract.lock effective-surface hash mismatch")
    if lock.get("keyword_count") != len(live) or lock.get("surface") != live:
        errors.append("hp34401a_ai_contract.lock keyword surface/count mismatch")
    expected_api_hash = hashlib.sha256(_canonical_text_bytes(public_api_path)).hexdigest()
    if lock.get("public_api_sha256") != expected_api_hash:
        errors.append("hp34401a_ai_contract.lock public_api hash mismatch")
    if str(contract.get("identity", {}).get("driver_version")) != "26.7.0":
        errors.append("AI contract driver version must be 26.7.0")
    if public_api.get("library", {}).get("package_version") != "26.07":
        errors.append("public_api package version must be 26.07")
    if sorted(public_api.get("capabilities", [])) != public_api.get("capabilities", []):
        errors.append("public_api capabilities must be sorted")
    if public_api.get("library", {}).get("auto_keywords") is not False:
        errors.append("public_api must declare auto_keywords=false")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("RFDS-002/RFDS-017 validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    live = public_keyword_surface()
    print(
        f"RFDS-002/RFDS-017 validation PASSED: {len(live)} keywords, "
        f"SHA-256 {surface_hash(live)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
