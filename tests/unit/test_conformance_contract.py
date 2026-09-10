from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from hp34401a_dmm import FakeTransport

ROOT = Path(__file__).resolve().parents[2]


def _module(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rfds019_static_inventory_and_vectors_are_complete():
    validator = _module("validate_call_protocol_conformance")
    errors = validator.validate()
    assert errors == []
    assert len(validator.live_surface()) == 109


def test_every_keyword_has_exactly_one_primary_vector():
    inventory = yaml.safe_load(
        (ROOT / "tests/conformance/data/keyword_inventory.yaml").read_text(encoding="utf-8")
    )["keywords"]
    vectors = yaml.safe_load(
        (ROOT / "tests/conformance/data/protocol_vectors.yaml").read_text(encoding="utf-8")
    )["vectors"]
    assert len(inventory) == len(vectors) == 109
    assert {row["keyword"] for row in inventory} == {row["keyword"] for row in vectors}
    assert len({row["id"] for row in vectors}) == 109
    assert all(row.get("expected_return") is not None for row in vectors)
    assert all(
        (not row["device_facing"]) or row.get("expected_outbound") is not None
        for row in vectors
    )


def test_fake_transport_records_raw_query_responses_at_protocol_boundary():
    transport = FakeTransport(responses={"READ?": "12.345"})
    transport.open()
    assert transport.query("READ?") == "12.345"
    assert transport.query_history == ["READ?"]
    assert transport.response_history == [("READ?", "12.345")]
