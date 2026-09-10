#!/usr/bin/env python3
"""Synchronize RFDS-002/RFDS-017 artifacts from the effective Robot surface.

This generator deliberately preserves reviewed semantic metadata already held
in ``api/public_api.yaml`` and ``ai/hp34401a_ai_contract.yaml``.  It updates
only fields that can be derived mechanically from the effective inherited
Robot library (name, Python binding, signature, tags, documentation and
surface locks).  Governance records such as deviations and architectural
decisions are never overwritten by code generation.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "api" / "public_api.yaml"
AI_PATH = ROOT / "ai" / "hp34401a_ai_contract.yaml"
LOCK_PATH = ROOT / "ai" / "hp34401a_ai_contract.lock"
DEVICE_OPS_PATH = ROOT / "api" / "device_operations.md"


def _robot_default(value: Any) -> str:
    if value is None:
        return "${NONE}"
    if value is True:
        return "${TRUE}"
    if value is False:
        return "${FALSE}"
    return str(value)


def _annotation(value: Any) -> str:
    if value is inspect.Signature.empty:
        return "Any"
    if isinstance(value, str):
        return value
    return inspect.formatannotation(value)


def effective_surface() -> list[dict[str, Any]]:
    """Return mechanically derivable metadata for every effective Robot keyword."""
    from rf_hp34401a import Hp34401ALibrary

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for python_name, method in inspect.getmembers(Hp34401ALibrary, predicate=callable):
        robot_name = getattr(method, "robot_name", None)
        if not robot_name:
            continue
        name = str(robot_name)
        if name in seen:
            raise RuntimeError(f"Duplicate Robot keyword export {name!r}")
        seen.add(name)
        signature = inspect.signature(method)
        sig_parts: list[str] = []
        arguments: list[dict[str, Any]] = []
        for parameter in signature.parameters.values():
            if parameter.name == "self":
                continue
            if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                sig_parts.append(f"*{parameter.name}")
                arguments.append(
                    {"name": parameter.name, "type": "list", "required": False, "default": []}
                )
                continue
            if parameter.kind is inspect.Parameter.VAR_KEYWORD:
                sig_parts.append(f"**{parameter.name}")
                arguments.append(
                    {"name": parameter.name, "type": "dict", "required": False, "default": {}}
                )
                continue
            required = parameter.default is inspect.Parameter.empty
            default = None if required else parameter.default
            sig_parts.append(
                parameter.name if required else f"{parameter.name}={_robot_default(default)}"
            )
            arguments.append(
                {
                    "name": parameter.name,
                    "type": _annotation(parameter.annotation),
                    "required": required,
                    "default": default,
                }
            )
        doc = inspect.getdoc(method) or f"Execute {name}."
        tags = [str(tag) for tag in (getattr(method, "robot_tags", None) or [])]
        items.append(
            {
                "name": name,
                "python_method": python_name,
                "signature": f"{name}({', '.join(sig_parts)})",
                "arguments": arguments,
                "return_type": _annotation(signature.return_annotation),
                "tags": tags,
                "documentation": doc.splitlines()[0].strip(),
            }
        )
    return sorted(items, key=lambda item: item["name"])


def _load_json_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a mapping")
    return data


def _merge_public_api(surface: list[dict[str, Any]]) -> dict[str, Any]:
    document = _load_json_yaml(API_PATH)
    existing = {str(item["name"]): item for item in document.get("keywords", [])}
    merged: list[dict[str, Any]] = []
    for derived in surface:
        name = derived["name"]
        if name not in existing:
            raise SystemExit(
                f"New Robot keyword {name!r} has no reviewed RFDS-002 semantic metadata. "
                "Add/review it explicitly before regenerating."
            )
        item = copy.deepcopy(existing[name])
        item["name"] = name
        item["python_method"] = derived["python_method"]
        item["signature"] = derived["signature"]
        # Preserve reviewed units/accepted constraints while synchronizing the
        # mechanical name/type/required/default fields.
        old_args = {str(arg.get("name")): arg for arg in item.get("arguments", [])}
        new_args: list[dict[str, Any]] = []
        for arg in derived["arguments"]:
            combined = copy.deepcopy(old_args.get(arg["name"], {}))
            combined.update(arg)
            new_args.append(combined)
        item["arguments"] = new_args
        if derived["tags"]:
            item["tags"] = derived["tags"]
        item["documentation"] = derived["documentation"]
        merged.append(item)

    extra = sorted(set(existing) - {item["name"] for item in surface})
    if extra:
        raise SystemExit(
            f"RFDS-002 contains keywords no longer exported by Robot library: {extra}. "
            "Review compatibility/removal before regenerating."
        )

    document.setdefault("library", {})["package_version"] = "26.07"
    document["library"]["api_version"] = "1.1.0"
    document["keywords"] = merged
    return document


def _merge_ai_contract(
    public_api: dict[str, Any], surface: list[dict[str, Any]]
) -> dict[str, Any]:
    contract = _load_json_yaml(AI_PATH)
    existing = {str(item["keyword"]): item for item in contract.get("capabilities", [])}
    api_by_name = {str(item["name"]): item for item in public_api["keywords"]}
    capabilities: list[dict[str, Any]] = []
    for derived in surface:
        name = derived["name"]
        if name not in existing:
            raise SystemExit(
                f"New Robot keyword {name!r} has no reviewed RFDS-017 capability metadata"
            )
        item = copy.deepcopy(existing[name])
        item["keyword"] = name
        item["signature"] = derived["signature"]
        item["purpose"] = api_by_name[name].get("documentation", derived["documentation"])
        item["protocol_vector"] = api_by_name[name].get("protocol_vector")
        if derived["tags"]:
            item["tags"] = derived["tags"]
        capabilities.append(item)

    extra = sorted(set(existing) - {item["name"] for item in surface})
    if extra:
        raise SystemExit(f"RFDS-017 contains non-exported keywords: {extra}")

    contract.setdefault("identity", {})["driver_version"] = "26.7.0"
    contract["identity"]["api_version"] = "1.1.0"
    contract["capabilities"] = capabilities
    contract.setdefault("conformance", {})["exported_keyword_count"] = len(surface)
    contract["conformance"]["rfds002"] = {
        "version": "1.1",
        "public_api": "api/public_api.yaml",
        "keyword_count": len(surface),
    }
    return contract


def _write_lock(public_api: dict[str, Any], surface: list[dict[str, Any]]) -> None:
    surface_lines = [item["signature"] for item in surface]
    surface_hash = hashlib.sha256("\n".join(surface_lines).encode("utf-8")).hexdigest()
    api_bytes = (json.dumps(public_api, indent=2, sort_keys=False) + "\n").encode("utf-8")
    lock = {
        "algorithm": "SHA-256",
        "sha256": surface_hash,
        "public_api_sha256": hashlib.sha256(api_bytes).hexdigest(),
        "keyword_count": len(surface_lines),
        "surface": surface_lines,
    }
    LOCK_PATH.write_text(yaml.safe_dump(lock, sort_keys=False, width=160), encoding="utf-8")


def _write_device_operations(public_api: dict[str, Any]) -> None:
    lines = ["# Device operations", ""]
    for item in public_api["keywords"]:
        if item.get("device_facing"):
            lines.append(f"- `{item['name']}` — {item.get('documentation', '')}")
    DEVICE_OPS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    surface = effective_surface()
    public_api = _merge_public_api(surface)
    public_text = json.dumps(public_api, indent=2, sort_keys=False) + "\n"
    API_PATH.write_text(public_text, encoding="utf-8")

    contract = _merge_ai_contract(public_api, surface)
    AI_PATH.write_text(
        yaml.safe_dump(contract, sort_keys=False, width=120), encoding="utf-8"
    )
    _write_lock(public_api, surface)
    _write_device_operations(public_api)
    print(
        f"Synchronized reviewed RFDS-002/RFDS-017 artifacts for {len(surface)} "
        "effective Robot keywords; governance files were not modified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
