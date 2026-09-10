from __future__ import annotations

from hp34401a_gui.app import guarded_raw_service_call, is_raw_service_command


def test_raw_service_callbacks_are_identified_by_exact_callback_name():
    def raw_query():
        return None

    def raw_write():
        return None

    def identify():
        return None

    assert is_raw_service_command(raw_query) is True
    assert is_raw_service_command(raw_write) is True
    assert is_raw_service_command(identify) is False


def test_raw_service_call_is_not_executed_when_operator_declines():
    calls: list[str] = []

    def command():
        calls.append("executed")
        return "result"

    assert guarded_raw_service_call(command, lambda: False) is None
    assert calls == []


def test_raw_service_call_executes_once_after_explicit_authorization():
    calls: list[str] = []

    def command():
        calls.append("executed")
        return "result"

    assert guarded_raw_service_call(command, lambda: True) == "result"
    assert calls == ["executed"]
