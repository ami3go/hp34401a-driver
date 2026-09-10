from __future__ import annotations

import pytest

from rf_hp34401a import Hp34401ALibrary


def test_list_connections_preserves_last_failed_communication_result(monkeypatch):
    lib = Hp34401ALibrary(evidence_enabled=False)
    lib.connect("SIM::DMM", alias="dut")
    assert lib.list_connections()[0]["communication_ok"] is True

    session = lib._sessions.get("dut")

    def fail_query(_command: str) -> str:
        raise TimeoutError("simulated communication failure")

    monkeypatch.setattr(session.driver, "query", fail_query)
    with pytest.raises(Exception):
        lib.check_communication("dut")

    state = lib.get_connection_state("dut", refresh=False)
    listed = lib.list_connections()[0]
    assert state["connected"] is True
    assert state["communication_ok"] is False
    assert listed["connected"] is True
    assert listed["communication_ok"] is False
    lib.disconnect_all()
