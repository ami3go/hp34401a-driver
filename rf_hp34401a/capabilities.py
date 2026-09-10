"""RFDS-013 capability discovery for the HP 34401A driver."""

from __future__ import annotations

import inspect
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable

from .exceptions import DriverValidationError
from .version import __version__


_RFDS002_CAPABILITY_IDS = [
    "ac_current_measurement", "ac_voltage_measurement", "capability_discovery",
    "configuration", "connection", "continuity_measurement", "dc_current_measurement",
    "dc_voltage_measurement", "device_reset", "diagnostics", "diode_measurement",
    "error_queue", "four_wire_resistance_measurement", "frequency_measurement",
    "identity", "measurement_assertions", "multi_connection", "period_measurement",
    "raw_io", "self_test", "simulation", "stable_resistance_measurement",
    "terminal_verification", "triggered_acquisition", "two_wire_resistance_measurement",
]

# Retry safety is an operation property, not a risk-level inference.  Timeout
# values below describe the default operation envelope exposed to planners;
# the effective session timeout can still be configured at runtime.
_CAPABILITIES: list[dict[str, Any]] = [
    {"capability_id": "connection.session.open", "keyword": "Connect", "risk": "low", "requires_connection": False, "timeout_s": 10.0, "retry_safe": False},
    {"capability_id": "connection.session.close", "keyword": "Disconnect", "risk": "low", "requires_connection": False, "timeout_s": 10.0, "retry_safe": True},
    {"capability_id": "connection.session.inspect", "keyword": "Get Connection State", "risk": "none", "requires_connection": False, "timeout_s": 10.0, "retry_safe": True},
    {"capability_id": "identity.device.read", "keyword": "Get Identity", "risk": "none", "requires_connection": True, "timeout_s": 10.0, "retry_safe": True},
    {"capability_id": "system.communication.check", "keyword": "Check Communication", "risk": "none", "requires_connection": True, "timeout_s": 10.0, "retry_safe": True},
    {"capability_id": "system.error.read", "keyword": "Get Device Error", "risk": "none", "requires_connection": True, "timeout_s": 10.0, "retry_safe": True},
    {"capability_id": "system.error.clear", "keyword": "Clear Device Errors", "risk": "low", "requires_connection": True, "timeout_s": 10.0, "retry_safe": False},
    {"capability_id": "system.self_test.execute", "keyword": "Run DMM Self Test", "risk": "medium", "requires_connection": True, "timeout_s": 30.0, "retry_safe": False},
    {"capability_id": "measure.voltage.dc", "keyword": "Measure DC Voltage", "risk": "low", "requires_connection": True, "unit": "V", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.voltage.ac", "keyword": "Measure AC Voltage", "risk": "low", "requires_connection": True, "unit": "V", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.current.dc", "keyword": "Measure DC Current", "risk": "low", "requires_connection": True, "unit": "A", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.current.ac", "keyword": "Measure AC Current", "risk": "low", "requires_connection": True, "unit": "A", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.resistance.two_wire", "keyword": "Measure 2 Wire Resistance", "risk": "low", "requires_connection": True, "unit": "ohm", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.resistance.four_wire", "keyword": "Measure 4 Wire Resistance", "risk": "low", "requires_connection": True, "unit": "ohm", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.frequency", "keyword": "Measure Frequency", "risk": "low", "requires_connection": True, "unit": "Hz", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.period", "keyword": "Measure Period", "risk": "low", "requires_connection": True, "unit": "s", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.continuity", "keyword": "Measure Continuity", "risk": "low", "requires_connection": True, "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.diode", "keyword": "Measure Diode", "risk": "low", "requires_connection": True, "unit": "V", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "measure.resistance.stable", "keyword": "Read Stable Resistance", "risk": "low", "requires_connection": True, "unit": "ohm", "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "acquisition.trigger.configure", "keyword": "Set DMM Trigger Source", "risk": "low", "requires_connection": True, "timeout_s": 10.0, "retry_safe": False},
    {"capability_id": "acquisition.trigger.initiate", "keyword": "Initiate DMM Measurement", "risk": "low", "requires_connection": True, "timeout_s": 60.0, "retry_safe": False},
    {"capability_id": "acquisition.trigger.bus", "keyword": "Send DMM Bus Trigger", "risk": "low", "requires_connection": True, "timeout_s": 10.0, "retry_safe": False},
    {"capability_id": "protocol.scpi.raw_write", "keyword": "Write DMM Command", "risk": "high", "requires_connection": True, "explicit_opt_in": True, "timeout_s": 10.0, "retry_safe": False},
    {"capability_id": "protocol.scpi.raw_query", "keyword": "Query DMM Command", "risk": "medium", "requires_connection": True, "explicit_opt_in": True, "timeout_s": 10.0, "retry_safe": False},
    {"capability_id": "simulation.instrument.open", "keyword": "Open Simulated DMM", "risk": "none", "requires_connection": False, "timeout_s": 10.0, "retry_safe": False},
]


class CapabilityRegistry:
    """Return deterministic static/effective capability information."""

    def ids(self) -> list[str]:
        """Return RFDS-002 capability identifiers in sorted order."""
        return list(_RFDS002_CAPABILITY_IDS)

    def model_ids(self) -> list[str]:
        """Return RFDS-013 dot-separated functional capability identifiers."""
        return sorted(item["capability_id"] for item in _CAPABILITIES)

    def model(self, *, connected: bool = False, identity: dict[str, Any] | None = None, mode: str = "effective") -> dict[str, Any]:
        source_mode = str(mode).strip().lower()
        if source_mode not in {"static", "configured", "live", "effective"}:
            raise DriverValidationError(
                "Capability discovery mode must be STATIC, CONFIGURED, LIVE or EFFECTIVE"
            )
        capabilities = []
        for raw in _CAPABILITIES:
            item = deepcopy(raw)
            requires = bool(item.pop("requires_connection", False))
            timeout_s = float(item.pop("timeout_s"))
            retry_safe = bool(item.pop("retry_safe"))
            item["support_state"] = "supported"
            item["availability"] = {
                "available": (connected or not requires),
                "state": "ready" if (connected or not requires) else "disconnected",
                "reason": None if (connected or not requires) else "connection required",
            }
            item["binding"] = {"robot_keyword": item.pop("keyword")}
            item["timing"] = {
                "timeout_s": timeout_s,
                "cancellable": False,
                "retry_safe": retry_safe,
            }
            capabilities.append(item)
        known_identity = identity or {}
        return {
            "schema": {"name": "rfds-capability-model", "version": "1.0"},
            "driver": {
                "id": "rf_hp34401a",
                "name": "HP/Agilent/Keysight 34401A Robot Framework Driver",
                "version": __version__,
                "api_version": "1.1",
                "capability_model_version": "1.0",
            },
            "source": {
                "discovery_mode": source_mode,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "connected": connected,
                "stale": False,
            },
            "identity": {
                "manufacturer": known_identity.get("manufacturer", "UNKNOWN"),
                "model": known_identity.get("model", "UNKNOWN"),
                "serial_number": known_identity.get("serial", "UNKNOWN") or "UNKNOWN",
                "firmware_version": known_identity.get("firmware", "UNKNOWN") or "UNKNOWN",
            },
            "features": {
                "measurement_functions": [
                    "VOLT_DC", "VOLT_AC", "CURR_DC", "CURR_AC", "RES_2W", "RES_4W",
                    "FREQ", "PERIOD", "CONTINUITY", "DIODE"
                ],
                "multi_session": True,
                "simulation": True,
                "raw_scpi_guarded": True,
            },
            "resources": [{"resource_id": "dmm.acquisition", "access": "exclusive_operation"}],
            "capabilities": capabilities,
            "validation": {"valid": True, "errors": [], "warnings": []},
            "extensions": {"rf_hp34401a": {"supported_models": ["34401A"]}},
        }

    def get(self, capability_id: str, *, connected: bool = False, identity: dict[str, Any] | None = None) -> dict[str, Any]:
        model = self.model(connected=connected, identity=identity)
        for capability in model["capabilities"]:
            if capability["capability_id"] == capability_id:
                return capability
        raise DriverValidationError(f"Unknown capability_id {capability_id!r}")

    def find(
        self,
        *,
        capability_id: str | None = None,
        keyword: str | None = None,
        maximum_risk: str | None = None,
        available_only: bool = False,
        connected: bool = False,
        identity: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        if maximum_risk is not None and str(maximum_risk).lower() not in rank:
            raise DriverValidationError(
                "maximum_risk must be one of none, low, medium, high, critical"
            )
        maximum = rank[str(maximum_risk).lower()] if maximum_risk else 4
        matches: list[dict[str, Any]] = []
        for item in self.model(connected=connected, identity=identity)["capabilities"]:
            if capability_id and capability_id.lower() not in item["capability_id"].lower():
                continue
            if keyword and keyword.lower() not in item["binding"]["robot_keyword"].lower():
                continue
            if rank.get(item["risk"], 4) > maximum:
                continue
            if available_only and not item["availability"]["available"]:
                continue
            matches.append(item)
        return matches

    @staticmethod
    def _actual_robot_keywords() -> set[str]:
        # Delayed import avoids the capabilities<->library import cycle during
        # module initialization.  Robot's @keyword decorator stores robot_name
        # on the callable; inherited/private helper methods have no such marker.
        from .library import Hp34401ALibrary

        exported: set[str] = set()
        for _name, member in inspect.getmembers(Hp34401ALibrary, predicate=callable):
            robot_name = getattr(member, "robot_name", None)
            if robot_name:
                exported.add(str(robot_name))
        return exported

    def validate_bindings(self, exported_keywords: Iterable[str] | None = None) -> dict[str, Any]:
        """Validate capability bindings against the actual Robot export surface.

        ``exported_keywords`` is retained for compatibility with earlier
        callers, but it is only an additional cross-check; the authoritative
        comparison is made against the decorated library methods themselves.
        """

        actual = self._actual_robot_keywords()
        declared = {item["keyword"] for item in _CAPABILITIES}
        missing = sorted(declared - actual)
        provided_missing: list[str] = []
        if exported_keywords is not None:
            provided = {str(item) for item in exported_keywords}
            provided_missing = sorted(declared - provided)
        return {
            "valid": not missing and not provided_missing,
            "capability_count": len(_CAPABILITIES),
            "missing_keyword_bindings": missing,
            "missing_from_supplied_inventory": provided_missing,
            "actual_robot_keyword_count": len(actual),
            "warnings": [],
        }
