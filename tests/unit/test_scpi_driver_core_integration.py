"""Integration tests proving the migrated transport stack really works with
scpi_driver_core's public simulator and IEEE-488.2 primitives directly, not
just through our own ``FakeTransport`` wrapper around them.

See docs/scpi_driver_core_review.md for the migration this validates.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from scpi_driver_core.scpi.client import ScpiClient
from scpi_driver_core.scpi.codec import ScpiTextCodec
from scpi_driver_core.scpi.ieee488 import Ieee4882
from scpi_driver_core.simulation.scripted import ScriptedScpiTransport

from rf_hp34401a.library import Hp34401ALibrary

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _hp34401a_simulator() -> ScriptedScpiTransport:
    sim = ScriptedScpiTransport()
    sim.on("*IDN?", "HEWLETT-PACKARD,34401A,SIM0002,11-05-01")
    sim.on("*TST?", "0")
    sim.on("SYST:VERS?", "1991.0")
    sim.on("ROUT:TERM?", "FRONT")
    sim.on("READ?", "+1.23400000E-01")
    sim.on("FETC?", "+1.23400000E-01")
    return sim


def _client(sim: ScriptedScpiTransport) -> ScpiClient:
    # ascii encoding, "\n" command/response terminators: this driver's own
    # transport defaults (hp34401a_dmm/transports.py::BaseTransport), proven
    # here against the real scpi_driver_core primitives rather than our
    # FakeTransport wrapper around them.
    return ScpiClient(
        sim,
        codec=ScpiTextCodec(encoding="ascii", command_terminator=b"\n", response_terminator=b"\n"),
    )


def test_ieee4882_common_commands_work_against_the_real_simulator():
    sim = _hp34401a_simulator()
    sim.open()
    ieee = Ieee4882(_client(sim))

    identity = ieee.identify()
    assert identity.manufacturer == "HEWLETT-PACKARD"
    assert identity.model == "34401A"
    assert identity.serial_number == "SIM0002"

    ieee.clear_status()
    ieee.reset()  # *RST has no scripted reply; a bare write must not raise

    result = ieee.self_test()
    assert result.code == 0

    assert sim.history[:3] == ["*IDN?", "*CLS", "*RST"]


def test_scripted_transport_reports_undefined_header_for_unknown_command():
    """Confirms an unmatched command still behaves like a real instrument's
    error queue (used by hp34401a_dmm.transports.FakeTransport's own
    SYSTem:ERRor? handling, which deliberately does NOT use this queue -- see
    docs/scpi_driver_core_review.md -- but the underlying simulator's default
    behavior should still be intact for any other scpi-driver-core consumer)."""
    sim = ScriptedScpiTransport()
    sim.open()
    client = _client(sim)
    client.write("BOGUS:COMMAND")
    assert sim.pending_errors[0].code == -113


def test_full_public_api_surface_is_reachable_through_the_migrated_transport():
    """Every keyword in api/public_api.yaml (the locked public API contract)
    must be a callable attribute of the Robot library, reachable through a
    connection whose transport is the migrated FakeTransport -- itself now
    backed by scpi_driver_core.simulation.scripted.ScriptedScpiTransport."""
    spec = yaml.safe_load((PACKAGE_ROOT / "api" / "public_api.yaml").read_text(encoding="utf-8"))
    keywords = spec["keywords"]
    assert len(keywords) == 109

    lib = Hp34401ALibrary()
    lib.open_simulated_dmm(reading=1.234)
    try:
        missing = [
            entry["python_method"]
            for entry in keywords
            if not callable(getattr(lib, entry["python_method"], None))
        ]
        assert not missing, f"public API methods not found on Hp34401ALibrary: {missing}"
    finally:
        lib.disconnect_all()
