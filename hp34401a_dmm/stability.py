"""Adaptive stable-resistance measurement (spec section 17).

Accepts only when the rolling window's standard deviation and slope are below
thresholds; on non-convergence it returns a failed result and never silently
uses the last value.
"""

from __future__ import annotations

import statistics
import time
from typing import Callable

from .config import StabilityProfile
from .enums import AutoRange, MeasurementFunction, Nplc
from .measurement import MeasurementReading, StableMeasurementResult
from . import parser


def _linear_slope(times: list[float], values: list[float]) -> float:
    """Least-squares slope (value units per second)."""
    n = len(times)
    if n < 2:
        return 0.0
    mean_t = sum(times) / n
    mean_v = sum(values) / n
    denom = sum((t - mean_t) ** 2 for t in times)
    if denom == 0:
        return 0.0
    num = sum((t - mean_t) * (v - mean_v) for t, v in zip(times, values))
    return num / denom


def read_stable_resistance(
    sampler: Callable[[], MeasurementReading],
    profile: StabilityProfile,
    *,
    final_sampler: Callable[[], MeasurementReading] | None = None,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> StableMeasurementResult:
    """Run the adaptive settling algorithm.

    ``sampler`` returns one MeasurementReading per call (already configured for
    the right range/NPLC).  ``now``/``sleep`` are injectable for deterministic
    tests.
    """
    unit = "Ohm"
    t_start = now()
    sleep(profile.min_settle_s)

    window_t: list[float] = []
    window_v: list[float] = []
    last_reason = "no samples"

    while True:
        elapsed = now() - t_start
        if elapsed > profile.max_wait_s:
            return StableMeasurementResult(
                stable=False,
                value=None,
                unit=unit,
                samples=tuple(window_v),
                stdev=_safe_stdev(window_v),
                relative_stdev=_safe_rel_stdev(window_v),
                slope_relative_per_s=None,
                elapsed_s=elapsed,
                reason=f"did not stabilize within {profile.max_wait_s}s ({last_reason})",
            )

        reading = sampler()
        if reading.is_overload:
            if profile.reject_overload:
                return StableMeasurementResult(
                    stable=False, value=None, unit=unit, samples=tuple(window_v),
                    stdev=None, relative_stdev=None, slope_relative_per_s=None,
                    elapsed_s=now() - t_start, reason="overload reading rejected",
                )
        elif reading.value is not None:
            window_t.append(reading.monotonic_s)
            window_v.append(reading.value)
            if len(window_v) > profile.window_size:
                window_t.pop(0)
                window_v.pop(0)

        if len(window_v) >= profile.window_size:
            stable, last_reason, metrics = _evaluate(window_t, window_v, profile)
            if stable:
                final_reading = reading
                if profile.final_nplc is not None:
                    # The pure algorithm cannot change instrument NPLC itself.
                    # A driver-level caller may provide final_sampler that
                    # reconfigures to profile.final_nplc before reading.
                    final_reading = (final_sampler or sampler)()
                value = final_reading.value if not final_reading.is_overload else None
                if value is None:
                    return StableMeasurementResult(
                        stable=False, value=None, unit=unit, samples=tuple(window_v),
                        stdev=metrics[0], relative_stdev=metrics[1],
                        slope_relative_per_s=metrics[2], elapsed_s=now() - t_start,
                        reason="final precision reading was overload",
                    )
                return StableMeasurementResult(
                    stable=True, value=value, unit=unit, samples=tuple(window_v),
                    stdev=metrics[0], relative_stdev=metrics[1],
                    slope_relative_per_s=metrics[2], elapsed_s=now() - t_start,
                    reason="stable", reading=final_reading,
                )

        sleep(profile.sample_interval_s)


def _evaluate(
    times: list[float], values: list[float], profile: StabilityProfile
) -> tuple[bool, str, tuple[float | None, float | None, float | None]]:
    mean_v = sum(values) / len(values)
    stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
    rel_stdev = (stdev / abs(mean_v)) if mean_v else float("inf")
    slope = _linear_slope(times, values)
    rel_slope = abs(slope / mean_v) if mean_v else float("inf")
    metrics = (stdev, rel_stdev, rel_slope)

    if profile.max_stdev_ohm is not None and stdev > profile.max_stdev_ohm:
        return False, f"stdev {stdev:.4g} > {profile.max_stdev_ohm:.4g} Ohm", metrics
    if profile.max_relative_stdev is not None and rel_stdev > profile.max_relative_stdev:
        return False, f"rel_stdev {rel_stdev:.4g} > {profile.max_relative_stdev:.4g}", metrics
    if (
        profile.max_slope_relative_per_s is not None
        and rel_slope > profile.max_slope_relative_per_s
    ):
        return False, f"rel_slope {rel_slope:.4g}/s > {profile.max_slope_relative_per_s:.4g}/s", metrics
    return True, "stable", metrics


def _safe_stdev(values: list[float]) -> float | None:
    return statistics.pstdev(values) if len(values) > 1 else None


def _safe_rel_stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean_v = sum(values) / len(values)
    if not mean_v:
        return None
    return statistics.pstdev(values) / abs(mean_v)
