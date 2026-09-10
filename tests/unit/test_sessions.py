import pytest

from hp34401a_dmm import DriverConfig, FakeTransport, Hp34401A
from rf_hp34401a.sessions import SessionManager


def driver():
    d = Hp34401A(
        FakeTransport(),
        DriverConfig(verify_identity_on_connect=False, drain_error_queue_on_connect=False),
    )
    d.connect()
    return d


def test_named_sessions_and_selection():
    sm = SessionManager()
    sm.add("one", driver())
    sm.add("two", driver())
    assert sm.active_alias == "two"
    assert sm.select("one").alias == "one"
    assert sm.aliases() == ["one", "two"]
    sm.close_all()


def test_duplicate_alias_rejected():
    sm = SessionManager()
    sm.add("one", driver())
    d2 = driver()
    with pytest.raises(ValueError):
        sm.add("one", d2)
    d2.close()
    sm.close_all()


def test_close_is_idempotent_through_registry_cleanup():
    sm = SessionManager()
    sm.add("one", driver())
    sm.close("one")
    assert sm.aliases() == []


def test_session_error_and_replace_paths():
    sm = SessionManager()
    with pytest.raises(ValueError):
        sm.add(" ", driver())
    with pytest.raises(ValueError):
        sm.select("missing")
    first = driver()
    sm.add("one", first)
    second = driver()
    sm.add("one", second, replace=True)
    assert not first.is_connected()
    assert sm.get("one").driver is second
    sm.close_all()


def test_close_all_collects_errors():
    class BadDriver:
        def close(self):
            raise RuntimeError("close failed")

    sm = SessionManager()
    bad = type("S", (), {"alias": "bad", "driver": BadDriver()})()
    sm._sessions["bad"] = bad
    sm._active_key = "bad"
    errors = sm.close_all()
    assert errors == ["bad: close failed"]
    assert sm.active_alias is None
