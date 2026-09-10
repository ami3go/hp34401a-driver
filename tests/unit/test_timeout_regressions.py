from __future__ import annotations

import math

import pytest

from rf_hp34401a.converters import as_seconds
from rf_hp34401a.exceptions import DriverValidationError


@pytest.mark.parametrize("value", [0, 0.0, "0 s", -1, "-1 ms", math.nan, math.inf, -math.inf])
def test_public_timeout_converter_rejects_non_positive_or_non_finite_values(value):
    with pytest.raises(DriverValidationError):
        as_seconds(value, name="timeout_s")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1 ms", 0.001), ("500 ms", 0.5), ("2 s", 2.0), ("1 min", 60.0)],
)
def test_public_timeout_converter_accepts_finite_positive_values(value, expected):
    assert as_seconds(value, name="timeout_s") == expected
