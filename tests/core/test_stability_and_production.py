"""Stability, production runner, error-mapping and CLI-import-safety tests."""

import datetime as dt

import pytest

from hp34401a_dmm import (
    AutoRange,
    DriverConfig,
    FakeTransport,
    Hp34401A,
    InputTerminal,
    MeasurementFunction,
    Nplc,
    StabilityProfile,
    TestStep,
    TestSequence,
    TransportType,
    check_limits,
    read_stable_resistance,
    run_measurement_step,
    run_sequence,
)
from hp34401a_dmm.errors import (
    CommandError,
    ExecutionError,
    QueryError,
    scpi_error_for,
)
from hp34401a_dmm.measurement import MeasurementReading


def _reading(value, *, overload=False):
    return MeasurementReading(
        timestamp_utc=dt.datetime.now(dt.timezone.utc),
        monotonic_s=0.0,
        function=MeasurementFunction.RES_2W,
        value=None if overload else value,
        unit="Ohm",
        raw=str(value),
        is_overload=overload,
        is_valid=not overload,
        transport=TransportType.FAKE,
    )


def test_stability_accepts_stable_data():
    clock = {"t": 0.0}

    def now():
        return clock["t"]

    def sleep(s):
        clock["t"] += s

    samples = iter([1_000_000.0, 1_000_001.0, 999_999.0, 1_000_000.5, 999_999.5,
                    1_000_000.0, 1_000_000.2])

    def sampler():
        v = next(samples)
        r = _reading(v)
        return MeasurementReading(**{**r.__dict__, "monotonic_s": now()}) if False else \
            MeasurementReading(
                timestamp_utc=r.timestamp_utc, monotonic_s=now(),
                function=r.function, value=r.value, unit=r.unit, raw=r.raw,
                is_overload=False, is_valid=True, transport=TransportType.FAKE)

    profile = StabilityProfile(expected_ohm=1e6, range_ohm=1e6, window_size=5,
                               min_settle_s=0.0, sample_interval_s=0.1, max_wait_s=10.0,
                               final_nplc=None, max_relative_stdev=0.01,
                               max_slope_relative_per_s=0.05)
    result = read_stable_resistance(sampler, profile, now=now, sleep=sleep)
    assert result.stable is True
    assert result.value is not None


def test_stability_rejects_drifting_data():
    clock = {"t": 0.0}

    def now():
        return clock["t"]

    def sleep(s):
        clock["t"] += s

    # Monotonic strong drift -> never satisfies slope threshold.
    counter = {"n": 0}

    def sampler():
        counter["n"] += 1
        v = 1_000_000.0 + counter["n"] * 50_000.0  # 5% per sample drift
        return MeasurementReading(
            timestamp_utc=dt.datetime.now(dt.timezone.utc), monotonic_s=now(),
            function=MeasurementFunction.RES_2W, value=v, unit="Ohm", raw=str(v),
            is_overload=False, is_valid=True, transport=TransportType.FAKE)

    profile = StabilityProfile(expected_ohm=1e6, range_ohm=1e6, window_size=5,
                               min_settle_s=0.0, sample_interval_s=0.1, max_wait_s=2.0,
                               final_nplc=None, max_relative_stdev=0.0005,
                               max_slope_relative_per_s=0.0005)
    result = read_stable_resistance(sampler, profile, now=now, sleep=sleep)
    assert result.stable is False
    assert result.value is None
    assert "did not stabilize" in result.reason


def test_check_limits():
    assert check_limits(5.0, 1.0, 10.0) == "PASS"
    assert check_limits(0.5, 1.0, 10.0) == "FAIL"
    assert check_limits(11.0, 1.0, 10.0) == "FAIL"
    assert check_limits(None, 1.0, 10.0) == "FAIL"
    assert check_limits(5.0, None, None) == "PASS"


def _connected(responses=None):
    t = FakeTransport(responses=responses or {})
    d = Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                 drain_error_queue_on_connect=False,
                                 clear_status_on_connect=False))
    d.connect()
    return d, t


def test_run_measurement_step_pass():
    d, t = _connected({"READ?": "+5.00000000E+00"})
    step = TestStep(name="vout", function=MeasurementFunction.VOLT_DC,
                    range_value=10.0, nplc=Nplc.PLC10, lower_limit=4.5, upper_limit=5.5)
    result = run_measurement_step(d, step, dut_id="DUT001", station_id="LINE1")
    assert result.pass_fail == "PASS"
    assert result.reading.value == pytest.approx(5.0)


def test_run_measurement_step_fail_on_overload():
    d, t = _connected({"READ?": "9.90000000E+37"})
    step = TestStep(name="vout", function=MeasurementFunction.VOLT_DC,
                    range_value=10.0, lower_limit=4.5, upper_limit=5.5)
    result = run_measurement_step(d, step, dut_id="DUT001", station_id="LINE1")
    assert result.pass_fail == "FAIL"  # overload -> FAIL, not fabricated


def test_terminal_mismatch_fails_safely():
    d, t = _connected({"READ?": "+5.0E+00", "ROUTe:TERMinals?": "FRON"})
    step = TestStep(name="vout", function=MeasurementFunction.VOLT_DC,
                    range_value=10.0, required_terminal=InputTerminal.REAR)
    result = run_measurement_step(d, step, dut_id="DUT001", station_id="LINE1")
    assert result.pass_fail == "ERROR"
    assert "terminal" in (result.error or "").lower()


def test_sequence_aggregates_worst_result():
    d, t = _connected({"READ?": "+5.00000000E+00"})
    seq = TestSequence(name="seq", steps=(
        TestStep("a", MeasurementFunction.VOLT_DC, 10.0, lower_limit=4.0, upper_limit=6.0),
        TestStep("b", MeasurementFunction.VOLT_DC, 10.0, lower_limit=9.0, upper_limit=10.0),
    ))
    result = run_sequence(d, seq, "DUT1", "LINE1")
    assert result.pass_fail == "FAIL"  # second step out of limits


def test_error_code_mapping_ranges():
    assert isinstance(scpi_error_for(-113), CommandError)
    assert isinstance(scpi_error_for(-222), ExecutionError)
    assert isinstance(scpi_error_for(-410), QueryError)


def test_cli_help_needs_no_hardware():
    from hp34401a_dmm import cli
    parser = cli._build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])
    assert exc.value.code == 0


def test_cli_measure_dc_voltage_runs_with_fake(monkeypatch):
    from hp34401a_dmm import cli

    def fake_make_driver(args):
        t = FakeTransport(responses={"READ?": "+3.30000000E+00"})
        return Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                        drain_error_queue_on_connect=False,
                                        clear_status_on_connect=False))

    monkeypatch.setattr(cli, "_make_driver", fake_make_driver)
    rc = cli.main(["measure", "dc-voltage", "--visa", "GPIB0::22::INSTR", "--range", "10"])
    assert rc == 0


def test_stability_profile_rejects_invalid_window_size():
    with pytest.raises(ValueError):
        StabilityProfile(window_size=0)


def test_stability_profile_rejects_negative_sleep_time():
    with pytest.raises(ValueError):
        StabilityProfile(sample_interval_s=-0.1)


def test_cli_invalid_range_returns_clean_error(monkeypatch, capsys):
    from hp34401a_dmm import cli

    def fake_make_driver(args):
        t = FakeTransport(responses={"READ?": "+3.30000000E+00"})
        return Hp34401A(t, DriverConfig(verify_identity_on_connect=False,
                                        drain_error_queue_on_connect=False,
                                        clear_status_on_connect=False))

    monkeypatch.setattr(cli, "_make_driver", fake_make_driver)
    rc = cli.main(["measure", "dc-voltage", "--visa", "GPIB0::22::INSTR", "--range", "7"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "Unsupported VOLT_DC range" in captured.err
    assert "Traceback" not in captured.err
