import pytest

from hp34401a_dmm import AutoRange, InputTerminal, Nplc, TriggerSource
from rf_hp34401a.converters import (
    as_bool,
    as_nplc,
    as_range,
    as_seconds,
    as_terminal,
    as_trigger_source,
)


def test_bool_conversion():
    assert as_bool("yes") is True
    assert as_bool("OFF") is False
    with pytest.raises(ValueError):
        as_bool("perhaps")


def test_range_conversion():
    assert as_range("auto") is AutoRange.AUTO
    assert as_range("default") is AutoRange.DEF
    assert as_range("10") == 10.0
    with pytest.raises(ValueError):
        as_range(0)


def test_nplc_conversion():
    assert as_nplc("10") is Nplc.PLC10
    with pytest.raises(ValueError):
        as_nplc(2)


def test_other_enum_conversions():
    assert as_trigger_source("imm") is TriggerSource.IMMEDIATE
    assert as_terminal("rear") is InputTerminal.REAR


def test_robot_time_conversion():
    assert as_seconds("500 ms") == pytest.approx(0.5)


def test_extended_converter_paths():
    from hp34401a_dmm import AcFilterHz, Aperture, AutozeroMode
    from rf_hp34401a.converters import (
        as_ac_filter,
        as_aperture,
        as_autozero,
        as_float,
        as_int,
        as_optional_float,
    )

    assert as_bool(1) is True
    assert as_bool(0.0) is False
    assert as_float("1.25") == 1.25
    assert as_int("2.0") == 2
    assert as_optional_float("") is None
    assert as_optional_float("3.5") == 3.5
    assert as_aperture("0.1") is Aperture.APER0_1
    assert as_ac_filter("20") is AcFilterHz.HZ20
    assert as_autozero("once") is AutozeroMode.ONCE
    with pytest.raises(ValueError):
        as_float("x")
    with pytest.raises(ValueError):
        as_int("1.2")
    with pytest.raises(ValueError):
        as_seconds(-1)
    with pytest.raises(ValueError):
        as_aperture(0.5)
    with pytest.raises(ValueError):
        as_ac_filter(10)
    with pytest.raises(ValueError):
        as_autozero("sometimes")
    with pytest.raises(ValueError):
        as_trigger_source("timer")
    with pytest.raises(ValueError):
        as_terminal("side")


def test_enum_instance_and_remaining_error_paths():
    from hp34401a_dmm import AutoRange, AutozeroMode, InputTerminal, TriggerSource
    from rf_hp34401a.converters import as_autozero, as_int

    assert as_range(AutoRange.MAX) is AutoRange.MAX
    assert as_autozero(AutozeroMode.ON) is AutozeroMode.ON
    assert as_trigger_source(TriggerSource.BUS) is TriggerSource.BUS
    assert as_terminal(InputTerminal.FRONT) is InputTerminal.FRONT
    with pytest.raises(ValueError):
        as_int("not-an-int")
    with pytest.raises(ValueError):
        as_range("-10")
