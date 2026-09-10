"""Hardware-gated integration tests (spec section 29.3). Skipped unless env vars set."""
import os
import pytest

from hp34401a_dmm import (
    DriverConfig, Hp34401A, SerialRs232Config, VisaGpibConfig,
)

RUN = os.environ.get("HP34401A_RUN_HARDWARE_TESTS") == "1"
SERIAL_PORT = os.environ.get("HP34401A_SERIAL_PORT")
VISA_RESOURCE = os.environ.get("HP34401A_VISA_RESOURCE")

pytestmark = pytest.mark.skipif(not RUN, reason="set HP34401A_RUN_HARDWARE_TESTS=1 to run")


@pytest.mark.skipif(not VISA_RESOURCE, reason="set HP34401A_VISA_RESOURCE")
def test_visa_identify_and_clean_error_queue():
    d = Hp34401A.from_visa_gpib(VisaGpibConfig(resource=VISA_RESOURCE))
    with d:
        ident = d.identify()
        assert "34401A" in ident.model
        d.query("SYSTem:VERSion?")
        d.clear_status()
        errs = [e for e in d.drain_error_queue() if not e.is_no_error]
        assert errs == []
        r = d.measure_dc_voltage()
        assert r.is_valid or r.is_overload


@pytest.mark.skipif(not SERIAL_PORT, reason="set HP34401A_SERIAL_PORT")
def test_serial_remote_mode_and_identify():
    d = Hp34401A.from_serial(SerialRs232Config(port=SERIAL_PORT))
    with d:
        ident = d.identify()
        assert "34401A" in ident.model
        assert d.is_connected()
