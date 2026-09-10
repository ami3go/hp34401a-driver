#!/usr/bin/env python3
"""Facade-aware RFDS-019 conformance-data generator.

The reviewed vector-construction rules remain preserved in
``legacy_generate_conformance_data.py``. This wrapper replaces only the source
surface discovery with runtime introspection of the effective inherited Robot
library, so facade layering cannot silently drop keywords. ``--check`` is
read-only and is safe for CI.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEGACY = Path(__file__).with_name("legacy_generate_conformance_data.py")
INVENTORY = ROOT / "tests" / "conformance" / "data" / "keyword_inventory.yaml"


def _robot_default(value: Any) -> Any:
    if value is inspect.Parameter.empty:
        return None
    if value is None:
        return None
    if value is True:
        return True
    if value is False:
        return False
    return value


def effective_surface() -> list[dict[str, Any]]:
    """Return the complete effective Robot surface, including inherited methods."""
    from rf_hp34401a import Hp34401ALibrary

    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for python_name, method in inspect.getmembers(Hp34401ALibrary, predicate=callable):
        robot_name = getattr(method, "robot_name", None)
        if not robot_name:
            continue
        name = str(robot_name)
        if name in seen:
            raise RuntimeError(f"Duplicate Robot keyword export {name!r}")
        seen.add(name)
        arguments: list[dict[str, Any]] = []
        for parameter in inspect.signature(method).parameters.values():
            if parameter.name == "self":
                continue
            if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                arguments.append({"name": parameter.name, "required": False, "default": "*args"})
                continue
            if parameter.kind is inspect.Parameter.VAR_KEYWORD:
                arguments.append({"name": parameter.name, "required": False, "default": "**kwargs"})
                continue
            required = parameter.default is inspect.Parameter.empty
            arguments.append(
                {
                    "name": parameter.name,
                    "required": required,
                    "default": None if required else _robot_default(parameter.default),
                }
            )
        output.append(
            {
                "keyword": name,
                "driver_method": python_name,
                "arguments": arguments,
            }
        )
    return sorted(output, key=lambda item: item["keyword"])


def _load_legacy():
    spec = importlib.util.spec_from_file_location("rf_hp34401a_legacy_conformance_generator", LEGACY)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load reviewed generator {LEGACY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.source_surface = effective_surface
    return module


def check() -> list[str]:
    errors: list[str] = []
    live = effective_surface()
    inventory = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    existing = {
        str(item["keyword"]): str(item["driver_method"])
        for item in inventory.get("keywords", [])
    }
    current = {item["keyword"]: item["driver_method"] for item in live}
    if set(existing) != set(current):
        errors.append(
            f"inventory surface mismatch: missing={sorted(set(current)-set(existing))}, "
            f"extra={sorted(set(existing)-set(current))}"
        )
    mismatched = sorted(
        name for name in set(existing) & set(current) if existing[name] != current[name]
    )
    if mismatched:
        errors.append(f"inventory Python bindings are stale: {mismatched}")
    if len(live) != 109:
        errors.append(f"expected reviewed 109-keyword surface, found {len(live)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate current inventory against the effective Robot surface without writing files.",
    )
    args = parser.parse_args()
    if args.check:
        errors = check()
        if errors:
            print("RFDS-019 generator surface check FAILED:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("RFDS-019 generator surface check PASSED: 109 effective Robot keywords")
        return 0

    module = _load_legacy()
    module.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
