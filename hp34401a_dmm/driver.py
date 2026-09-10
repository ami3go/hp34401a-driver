"""Corrected public HP34401A core facade.

The reviewed v1.2.8 implementation is preserved in ``legacy_driver``. This
module adds the small runtime-policy API required by the Robot/RFDS adapter so
the adapter never reaches into the private transport object directly.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from .legacy_driver import Hp34401A as _LegacyHp34401A
from .legacy_driver import estimate_measurement_timeout_s


class Hp34401A(_LegacyHp34401A):
    """v1.2.8 driver plus explicit runtime transport/policy operations."""

    @staticmethod
    def _positive_finite(value: Any, name: str) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be numeric") from exc
        if not math.isfinite(result) or result <= 0:
            raise ValueError(f"{name} must be finite and > 0")
        return result

    @property
    def transport_type(self):
        """Return the active transport enum without exposing transport internals."""
        return self._t.transport_type

    @property
    def transport_name(self) -> str:
        """Return the active transport display/resource name."""
        return self._t.name

    def set_communication_timeout(self, timeout_s: float) -> float:
        """Set the live transport timeout and persist it in driver policy."""
        value = self._positive_finite(timeout_s, "timeout_s")
        with self._locked():
            self._t.set_timeout(value)
            self._cfg = replace(self._cfg, default_timeout_s=value)
        return value

    def read_raw_response(self) -> str:
        """Read one pending raw response through the core transport boundary."""
        with self._locked():
            response = self._t.read_raw()
            if self.trace_callback is not None:
                self.trace_callback("inbound", response)
            return response

    def apply_runtime_policy(
        self,
        *,
        communication_timeout_s: float | None = None,
        self_test_timeout_s: float | None = None,
        long_measurement_timeout_s: float | None = None,
        retry_queries: bool | None = None,
        max_query_retries: int | None = None,
        allow_calibration_commands: bool | None = None,
        raw_traffic_log: bool | None = None,
    ) -> None:
        """Apply host-side policy that is safe to change on an open session.

        Transport addressing and serial/VISA framing remain connect-time
        properties. Timeouts, query retry policy, calibration authorization,
        and raw-traffic logging are effective immediately.
        """
        changes: dict[str, Any] = {}
        if communication_timeout_s is not None:
            changes["default_timeout_s"] = self._positive_finite(
                communication_timeout_s, "communication_timeout_s"
            )
        if self_test_timeout_s is not None:
            changes["self_test_timeout_s"] = self._positive_finite(
                self_test_timeout_s, "self_test_timeout_s"
            )
        if long_measurement_timeout_s is not None:
            changes["long_measurement_timeout_s"] = self._positive_finite(
                long_measurement_timeout_s, "long_measurement_timeout_s"
            )
        if retry_queries is not None:
            changes["retry_queries"] = bool(retry_queries)
        if max_query_retries is not None:
            value = int(max_query_retries)
            if value < 0:
                raise ValueError("max_query_retries must be >= 0")
            changes["max_query_retries"] = value
        if allow_calibration_commands is not None:
            changes["allow_calibration_commands"] = bool(allow_calibration_commands)
        if raw_traffic_log is not None:
            changes["raw_traffic_log"] = bool(raw_traffic_log)

        with self._locked():
            if communication_timeout_s is not None:
                self._t.set_timeout(changes["default_timeout_s"])
            if raw_traffic_log is not None and hasattr(self._t, "_raw_traffic_log"):
                # The core owns its transport object, so transport-specific
                # implementation detail stays below the Robot adapter boundary.
                self._t._raw_traffic_log = bool(raw_traffic_log)
            if changes:
                self._cfg = replace(self._cfg, **changes)


__all__ = ["Hp34401A", "estimate_measurement_timeout_s"]
