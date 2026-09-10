from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _validator_module():
    path = ROOT / "scripts" / "validate_ai_contract.py"
    spec = importlib.util.spec_from_file_location("validate_ai_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rfds017_contract_matches_all_public_keywords():
    module = _validator_module()
    errors = module.validate(ROOT / "ai" / "hp34401a_ai_contract.yaml", ROOT / "ai" / "hp34401a_ai_contract.lock")
    assert errors == []
    contract = yaml.safe_load((ROOT / "ai" / "hp34401a_ai_contract.yaml").read_text(encoding="utf-8"))
    assert contract["rfds017_version"] == "3.0"
    assert contract["identity"]["driver_version"] == "26.7.0"
    assert len(contract["capabilities"]) == 109
    assert len({item["keyword"] for item in contract["capabilities"]}) == 109


def test_lock_detects_stale_interface(tmp_path):
    module = _validator_module()
    lock = yaml.safe_load((ROOT / "ai" / "hp34401a_ai_contract.lock").read_text(encoding="utf-8"))
    lock["sha256"] = "0" * 64
    stale_lock = tmp_path / "hp34401a_ai_contract.lock"
    stale_lock.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
    errors = module.validate(ROOT / "ai" / "hp34401a_ai_contract.yaml", stale_lock)
    assert any("hash mismatch" in error for error in errors)


def test_rfds018_bench_template_contains_mandatory_sections():
    template = yaml.safe_load(
        (ROOT / "examples" / "bench" / "system_ai_contract.template.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert template["rfds018_version"] == "1.0"
    required = {
        "available_drivers",
        "physical_topology",
        "shared_resources",
        "signal_graph",
        "preferred_measurement_sources",
        "requirement_coverage",
        "test_templates",
        "bench_constraints",
        "scheduling_rules",
        "global_safety",
    }
    assert required <= set(template)
    assert template["contract_status"] == "TEMPLATE"
