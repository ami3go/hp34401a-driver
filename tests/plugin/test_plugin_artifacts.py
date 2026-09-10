from __future__ import annotations

from pathlib import Path

from rf_hp34401a.plugin import Hp34401APluginProvider


def test_plugin_descriptor_resolves_all_declared_artifacts_in_source_checkout():
    descriptor = Hp34401APluginProvider.get_descriptor()
    resolved = descriptor["resolved_artifacts"]
    assert set(resolved) == {
        "capability_model",
        "configuration_schema",
        "ai_contract",
        "protocol_vectors",
    }
    for name, path in resolved.items():
        assert Path(path).is_file(), f"{name} did not resolve: {path}"
