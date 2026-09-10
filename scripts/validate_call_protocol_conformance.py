#!/usr/bin/env python3
"""Validate RFDS-019 inventory/vector completeness without opening hardware."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "conformance" / "data"


def live_surface() -> dict[str, str]:
    """Return effective Robot keyword -> Python method mapping, including inheritance."""
    from rf_hp34401a import Hp34401ALibrary

    result: dict[str, str] = {}
    for python_name, method in inspect.getmembers(Hp34401ALibrary, predicate=callable):
        robot_name = getattr(method, "robot_name", None)
        if not robot_name:
            continue
        name = str(robot_name)
        if name in result and result[name] != python_name:
            raise RuntimeError(
                f"Duplicate Robot keyword {name!r}: {result[name]!r} and {python_name!r}"
            )
        result[name] = python_name
    return result


def load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def validate() -> list[str]:
    errors: list[str] = []
    actual = live_surface()
    inventory = load(DATA / "keyword_inventory.yaml")
    vectors = load(DATA / "protocol_vectors.yaml")
    exclusions = load(DATA / "exclusions.yaml")
    items = list(inventory.get("keywords", []))
    vector_items = list(vectors.get("vectors", []))
    inventory_names = [str(item.get("keyword")) for item in items]
    vector_names = [str(item.get("keyword")) for item in vector_items]
    if set(inventory_names) != set(actual):
        errors.append(
            f"Inventory mismatch: missing={sorted(set(actual)-set(inventory_names))}, "
            f"extra={sorted(set(inventory_names)-set(actual))}"
        )
    if set(vector_names) != set(actual):
        errors.append(
            f"Vector mismatch: missing={sorted(set(actual)-set(vector_names))}, "
            f"extra={sorted(set(vector_names)-set(actual))}"
        )
    if len(inventory_names) != len(set(inventory_names)):
        errors.append("Duplicate keyword in inventory")
    if len(vector_names) != len(set(vector_names)):
        errors.append("Duplicate keyword in protocol vectors")
    by_name = {str(item.get("keyword")): item for item in items}
    vector_by_name = {str(item.get("keyword")): item for item in vector_items}
    for name, method in actual.items():
        if by_name.get(name, {}).get("driver_method") != method:
            errors.append(f"{name}: driver_method does not match effective adapter")
        vector_id = by_name.get(name, {}).get("protocol_vector")
        if vector_by_name.get(name, {}).get("id") != vector_id:
            errors.append(f"{name}: protocol_vector reference is stale")
        if by_name.get(name, {}).get("device_facing") and not vector_by_name.get(name, {}).get("expected_outbound"):
            errors.append(f"{name}: device-facing vector has no outbound oracle")
    if str(inventory.get("driver_version")) != "26.07":
        errors.append("keyword_inventory driver_version must be 26.07")
    if str(inventory.get("rfds019_version")) != "1.1":
        errors.append("keyword_inventory rfds019_version must be 1.1")
    if str(vectors.get("rfds019_version")) != "1.1":
        errors.append("protocol_vectors rfds019_version must be 1.1")
    if not exclusions.get("exclusions"):
        errors.append("exclusions.yaml must document real-device HIL status")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("RFDS-019 static validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"RFDS-019 static validation PASSED: {len(live_surface())} keywords/vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
