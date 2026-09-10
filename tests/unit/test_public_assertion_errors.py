from __future__ import annotations

import pytest

from rf_hp34401a import Hp34401ALibrary
from rf_hp34401a.exceptions import DriverValidationError


def test_invalid_assertion_limits_use_structured_validation_error():
    lib = Hp34401ALibrary(evidence_enabled=False)
    lib.open_simulated_dmm(reading=5.0)
    lib.measure_dc_voltage()

    with pytest.raises(DriverValidationError) as excinfo:
        lib.dmm_reading_should_be_between(10, 1)
    assert excinfo.value.code == "RFDS-VAL-001"

    with pytest.raises(DriverValidationError):
        lib.dmm_reading_should_be_close_to(5.0, absolute_tolerance=-1)

    with pytest.raises(DriverValidationError):
        lib.stable_resistance_should_be_between(
            {"stable": True, "value": 5.0}, 10, 1
        )
    lib.disconnect_all()


def test_valid_limits_still_use_assertion_error_for_dut_failure():
    lib = Hp34401ALibrary(evidence_enabled=False)
    lib.open_simulated_dmm(reading=5.0)
    lib.measure_dc_voltage()
    with pytest.raises(AssertionError):
        lib.dmm_reading_should_be_between(0, 1)
    lib.disconnect_all()
