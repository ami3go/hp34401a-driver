from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_api_generator_uses_complete_effective_robot_surface():
    generator = _load("rf_hp34401a_generate_api", SCRIPTS / "generate_api_artifacts.py")
    surface = generator.effective_surface()
    assert len(surface) == 109
    names = {item["name"] for item in surface}
    public_api = json.loads((ROOT / "api" / "public_api.yaml").read_text(encoding="utf-8"))
    assert names == {item["name"] for item in public_api["keywords"]}


def test_conformance_generator_check_is_read_only_and_complete():
    generator = _load(
        "rf_hp34401a_generate_conformance", SCRIPTS / "generate_conformance_data.py"
    )
    assert generator.check() == []
    surface = generator.effective_surface()
    assert len(surface) == 109
    inventory = yaml.safe_load(
        (ROOT / "tests" / "conformance" / "data" / "keyword_inventory.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert {item["keyword"] for item in surface} == {
        item["keyword"] for item in inventory["keywords"]
    }
