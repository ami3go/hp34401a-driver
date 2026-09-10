"""RFDS-corrected public Robot Framework facade for the HP 34401A.

The complete reviewed 26.07 keyword implementation is preserved in
``legacy_library``.  This facade keeps the same 109-keyword surface while
correcting cross-cutting RFDS behavior: effective configuration application,
communication-health caching, runtime shared-core metadata, evidence teardown,
and the private-transport boundary.
"""

from __future__ import annotations

import math
import platform
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Any

from robot.api.deco import keyword, library
from robot.utils import timestr_to_secs

from hp34401a_dmm import StabilityProfile
from hp34401a_dmm import __version__ as CORE_VERSION

from .converters import (
    as_bool,
    as_float,
    as_int,
    as_nplc,
    as_optional_float,
    as_range,
    as_seconds,
)
from .exceptions import DriverCleanupError, DriverStateError, DriverValidationError
from .legacy_library import Hp34401ALibrary as _LegacyHp34401ALibrary
from .legacy_library import ROBOT_FRAMEWORK_VERSION, _evidenced
from .version import __version__


def _as_nonnegative_seconds(value: Any, *, name: str) -> float:
    """Convert a duration that explicitly permits zero (not a timeout)."""
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        try:
            seconds = float(timestr_to_secs(str(value).strip()))
        except Exception as exc:
            raise DriverValidationError(f"{name} must be a valid duration") from exc
    if not math.isfinite(seconds) or seconds < 0:
        raise DriverValidationError(f"{name} must be finite and >= 0 seconds")
    return seconds


def _rfds_core_runtime_version() -> str:
    """Resolve the installed shared-core version.

    The field name is retained for RFDS-facing API compatibility, but it now
    resolves the real ``scpi-driver-core`` dependency rather than the
    fictional ``rfds-core`` package this driver used to depend on. See
    ``docs/scpi_driver_core_review.md``.
    """
    try:
        return package_version("scpi-driver-core")
    except PackageNotFoundError:
        return "NOT_INSTALLED"


@library(scope="SUITE", auto_keywords=False, version=__version__)
class Hp34401ALibrary(_LegacyHp34401ALibrary):
    """Production-safe RFDS facade preserving the complete 26.07 API."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_AUTO_KEYWORDS = False
    ROBOT_LIBRARY_VERSION = __version__

    def __init__(
        self,
        default_timeout_s: object = 10.0,
        allow_raw_io: object = False,
        evidence_enabled: object = True,
    ) -> None:
        super().__init__(default_timeout_s, allow_raw_io, evidence_enabled)
        self._communication_health: dict[str, bool] = {}

    @staticmethod
    def _alias_key(alias: object) -> str:
        return str(alias).strip().casefold()

    def _effective_settings(self) -> tuple[dict[str, Any], dict[str, str]]:
        document = self._configuration.effective(include_sources=True)
        sources = dict(document.get("metadata", {}).get("resolved_sources", {}))
        return document["settings"], sources

    def _apply_effective_policy(self) -> None:
        """Apply effective RFDS-014 host policy to defaults and open sessions."""
        settings, _sources = self._effective_settings()
        timeouts = settings["timeouts"]
        retry = settings["retry"]
        safety = settings["safety"]
        logging = settings["logging"]

        communication_s = as_seconds(timeouts["communication_s"], name="communication_s")
        self_test_s = as_seconds(timeouts["self_test_s"], name="self_test_s")
        long_s = as_seconds(timeouts["long_measurement_s"], name="long_measurement_s")
        self._default_timeout_s = communication_s
        self._allow_raw_io = as_bool(safety["allow_raw_scpi"], name="allow_raw_scpi")

        for alias in list(self._sessions.aliases()):
            session = self._sessions.get(alias)
            self._execute(
                "Apply Driver Configuration",
                lambda s=session: s.driver.apply_runtime_policy(
                    communication_timeout_s=communication_s,
                    self_test_timeout_s=self_test_s,
                    long_measurement_timeout_s=long_s,
                    retry_queries=as_bool(retry["query_enabled"], name="query_enabled"),
                    max_query_retries=as_int(retry["max_query_retries"], name="max_query_retries"),
                    allow_calibration_commands=as_bool(
                        safety["allow_calibration_commands"],
                        name="allow_calibration_commands",
                    ),
                    raw_traffic_log=as_bool(logging["raw_traffic"], name="raw_traffic"),
                ),
                session.alias,
            )
            session.timeout_s = communication_s

    @keyword("Import Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def import_driver_configuration(
        self,
        source: Any,
        validate_only: object = False,
        strict: object = True,
    ) -> dict[str, Any]:
        validate = as_bool(validate_only, name="validate_only")
        result = self._configuration.import_json(
            source,
            validate_only=validate,
            strict=as_bool(strict, name="strict"),
        )
        if not validate:
            self._apply_effective_policy()
        return result

    @keyword("Load Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def load_driver_configuration(
        self,
        profile_name: str,
        validate_only: object = False,
    ) -> dict[str, Any]:
        validate = as_bool(validate_only, name="validate_only")
        result = self._configuration.load_profile(profile_name, validate_only=validate)
        if not validate:
            self._apply_effective_policy()
        return result

    @keyword("Reset Driver Configuration", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def reset_driver_configuration(self) -> dict[str, Any]:
        result = self._configuration.reset()
        self._apply_effective_policy()
        return result

    @keyword("Connect", tags=["rfds:connection", "rfds:low_risk"])
    @_evidenced
    def connect(
        self,
        resource: str | None = None,
        alias: str = "default",
        timeout_s: object | None = None,
        **options: Any,
    ) -> dict[str, Any]:
        """Connect using explicit arguments plus the effective RFDS-014 profile.

        Simulation remains explicit: an omitted resource resolves to SIM only
        when a validated imported profile explicitly has ``simulation.enabled``
        set true. Hardware resources never fall back to simulation.
        """
        settings, sources = self._effective_settings()
        transport = settings["transport"]
        retry = settings["retry"]
        safety = settings["safety"]
        logging = settings["logging"]
        simulation = settings["simulation"]

        selected_resource = str(resource or transport.get("resource") or "").strip()
        if not selected_resource and as_bool(simulation["enabled"], name="simulation.enabled"):
            selected_resource = "SIM::HP34401A"

        merged = dict(options)
        config_defaults = {
            "transport": transport.get("kind", "AUTO"),
            "visa_library": transport.get("visa_library"),
            "baud_rate": transport.get("baud_rate", 9600),
            "parity": transport.get("parity", "none"),
            "data_bits": transport.get("data_bits", 8),
            "stop_bits": transport.get("stop_bits", 2),
            "retry_queries": retry.get("query_enabled", True),
            "max_query_retries": retry.get("max_query_retries", 1),
            "allow_calibration_commands": safety.get("allow_calibration_commands", False),
            "raw_traffic_log": logging.get("raw_traffic", False),
        }
        for name, value in config_defaults.items():
            if value is not None:
                merged.setdefault(name, value)

        # Preserve an explicit constructor timeout until a runtime profile has
        # actually overridden the timeout source.
        effective_timeout = timeout_s
        if effective_timeout is None:
            source = sources.get("settings.timeouts.communication_s", "PACKAGE_DEFAULT")
            effective_timeout = (
                settings["timeouts"]["communication_s"]
                if source != "PACKAGE_DEFAULT"
                else self._default_timeout_s
            )

        if sources.get("settings.safety.allow_raw_scpi") != "PACKAGE_DEFAULT":
            self._allow_raw_io = as_bool(
                safety["allow_raw_scpi"], name="allow_raw_scpi"
            )

        legacy_connect = _LegacyHp34401ALibrary.connect.__wrapped__
        state = legacy_connect(
            self,
            selected_resource or None,
            alias=alias,
            timeout_s=effective_timeout,
            **merged,
        )

        try:
            session = self._sessions.get(alias)
            session.driver.apply_runtime_policy(
                communication_timeout_s=as_seconds(
                    effective_timeout, name="communication_timeout_s"
                ),
                self_test_timeout_s=as_seconds(
                    settings["timeouts"]["self_test_s"], name="self_test_s"
                ),
                long_measurement_timeout_s=as_seconds(
                    settings["timeouts"]["long_measurement_s"],
                    name="long_measurement_s",
                ),
                retry_queries=as_bool(retry["query_enabled"], name="query_enabled"),
                max_query_retries=as_int(
                    retry["max_query_retries"], name="max_query_retries"
                ),
                allow_calibration_commands=as_bool(
                    safety["allow_calibration_commands"],
                    name="allow_calibration_commands",
                ),
                raw_traffic_log=as_bool(logging["raw_traffic"], name="raw_traffic"),
            )
            session.timeout_s = as_seconds(
                effective_timeout, name="communication_timeout_s"
            )
            expected_terminal = str(settings["device"]["expected_terminal"]).upper()
            if expected_terminal in {"FRONT", "REAR"}:
                self.require_dmm_input_terminal(expected_terminal, alias)
        except Exception:
            self._sessions.close(alias, idempotent=True)
            self._communication_health.pop(self._alias_key(alias), None)
            raise

        self._communication_health[self._alias_key(alias)] = bool(
            state.get("communication_ok", False)
        )
        return self.get_connection_state(alias=alias, refresh=False)

    @keyword("Check Communication", tags=["rfds:diagnostic", "rfds:low_risk"])
    @_evidenced
    def check_communication(self, alias: object | None = None) -> bool:
        session = self._session(alias)
        key = self._alias_key(session.alias)
        legacy = _LegacyHp34401ALibrary.check_communication.__wrapped__
        try:
            result = bool(legacy(self, session.alias))
        except Exception:
            self._communication_health[key] = False
            raise
        self._communication_health[key] = result
        return result

    @keyword("Get Connection State", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_connection_state(
        self,
        alias: object | None = None,
        refresh: object = False,
    ) -> dict[str, Any]:
        legacy = _LegacyHp34401ALibrary.get_connection_state.__wrapped__
        do_refresh = as_bool(refresh, name="refresh")
        result = legacy(self, alias=alias, refresh=do_refresh)
        session = self._sessions.find(alias)
        if session is not None:
            key = self._alias_key(session.alias)
            if do_refresh:
                self._communication_health[key] = bool(result["communication_ok"])
            elif key in self._communication_health:
                result["communication_ok"] = self._communication_health[key]
        return result

    @keyword("Disconnect", tags=["rfds:connection", "rfds:low_risk"])
    def disconnect(self, alias: object | None = None) -> None:
        session = self._sessions.find(alias)
        key = self._alias_key(session.alias) if session is not None else None
        super().disconnect(alias)
        if key is not None:
            self._communication_health.pop(key, None)

    @keyword("Disconnect All", tags=["rfds:connection", "rfds:low_risk"])
    def disconnect_all(self) -> None:
        super().disconnect_all()
        self._communication_health.clear()

    @keyword("Set Communication Timeout", tags=["rfds:configuration", "rfds:low_risk"])
    @_evidenced
    def set_communication_timeout(
        self,
        timeout_s: object,
        alias: object | None = None,
    ) -> float:
        value = as_seconds(timeout_s, name="timeout_s")
        session = self._sessions.find(alias)
        if session is None:
            if alias is not None and str(alias).strip():
                raise DriverStateError(
                    f"DMM alias {alias!r} is not open",
                    operation="Set Communication Timeout",
                    alias=str(alias),
                )
            self._default_timeout_s = value
            return value
        result = self._execute(
            "Set Communication Timeout",
            lambda: session.driver.set_communication_timeout(value),
            session.alias,
        )
        session.timeout_s = result
        return float(result)

    @keyword("Read Raw Response", tags=["rfds:raw_io", "rfds:high_risk"])
    @_evidenced
    def read_raw_response(
        self,
        alias: object | None = None,
        timeout_s: object | None = None,
    ) -> str:
        self._require_raw_io("Read Raw Response")
        session = self._session(alias)
        if timeout_s is not None:
            self.set_communication_timeout(timeout_s, session.alias)
        return self._execute(
            "Read Raw Response", session.driver.read_raw_response, session.alias
        )

    @keyword("Get Driver Information", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_driver_information(self) -> dict[str, Any]:
        legacy = _LegacyHp34401ALibrary.get_driver_information.__wrapped__
        result = legacy(self)
        result["rfds_core_runtime_version"] = _rfds_core_runtime_version()
        return result

    @keyword("Get Driver Metadata", tags=["rfds:query", "rfds:low_risk"])
    @_evidenced
    def get_driver_metadata(self, alias: object | None = None) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "driver_name": "rf_hp34401a.Hp34401ALibrary",
            "driver_version": __version__,
            "core_driver_version": CORE_VERSION,
            "driver_status": "D0_DEVELOPMENT_CANDIDATE",
            "supported_models": ["34401A"],
            "supported_transports": ["VISA_GPIB", "SERIAL_RS232", "FAKE"],
            "manufacturer": ["HP", "HEWLETT-PACKARD", "AGILENT", "KEYSIGHT"],
            "python_version": platform.python_version(),
            "robot_framework_version": ROBOT_FRAMEWORK_VERSION,
            "rfds_core_runtime_version": _rfds_core_runtime_version(),
            "library_build_date": "2026-08-16",
            "git_commit": "UNKNOWN",
            "alias": None,
            "instrument_id": "UNKNOWN",
            "model": "UNKNOWN",
            "serial_number": "UNKNOWN",
            "firmware_version": "UNKNOWN",
            "transport": "UNKNOWN",
            "state": "DISCONNECTED",
        }
        if alias is not None or self._sessions.active_alias is not None:
            session = self._session(alias)
            identity = self.identify_dmm(session.alias)
            metadata.update(
                {
                    "alias": session.alias,
                    "instrument_id": identity.get("raw", "UNKNOWN"),
                    "model": identity.get("model", "UNKNOWN"),
                    "serial_number": identity.get("serial", "UNKNOWN") or "UNKNOWN",
                    "firmware_version": identity.get("firmware", "UNKNOWN") or "UNKNOWN",
                    "transport": session.driver.transport_type.value,
                    "state": self.get_dmm_state(session.alias),
                }
            )
        return metadata

    def _stable_profile(
        self,
        expected_ohm: object | None,
        range_value: object,
        nplc: object,
        final_nplc: object | None,
        min_settle: object,
        max_wait: object,
        sample_interval: object,
        window_size: object,
        max_stdev_ohm: object | None,
        max_relative_stdev: object | None,
        max_slope_relative_per_s: object | None,
        four_wire: object,
    ) -> StabilityProfile:
        final = (
            None
            if final_nplc is None or str(final_nplc).strip().lower() in {"", "none", "${none}"}
            else as_nplc(final_nplc)
        )
        return StabilityProfile(
            expected_ohm=as_optional_float(expected_ohm, name="expected_ohm"),
            range_ohm=as_range(range_value),
            nplc=as_nplc(nplc),
            final_nplc=final,
            min_settle_s=_as_nonnegative_seconds(min_settle, name="min_settle"),
            max_wait_s=as_seconds(max_wait, name="max_wait"),
            sample_interval_s=as_seconds(sample_interval, name="sample_interval"),
            window_size=as_int(window_size, name="window_size"),
            max_stdev_ohm=as_optional_float(max_stdev_ohm, name="max_stdev_ohm"),
            max_relative_stdev=as_optional_float(
                max_relative_stdev, name="max_relative_stdev"
            ),
            max_slope_relative_per_s=as_optional_float(
                max_slope_relative_per_s, name="max_slope_relative_per_s"
            ),
            four_wire=as_bool(four_wire, name="four_wire"),
        )

    # Robot listener callback. Cleanup must be best-effort and evidence must be
    # finalized exactly once even when users omit an explicit Disconnect keyword.
    def close(self) -> None:
        errors = self._sessions.close_all()
        self._communication_health.clear()
        run = self._evidence
        if run is None:
            return
        try:
            if errors:
                run.record_error(
                    DriverCleanupError(
                        "; ".join(errors),
                        operation="Library Close",
                        details={"cleanup_errors": errors},
                    ),
                    capability="Library Close",
                )
            run.finalize(status="FAIL" if errors else "PASS")
        except Exception:
            # Listener cleanup must never mask the original Robot failure.
            pass
        finally:
            self._evidence = None


__all__ = ["Hp34401ALibrary"]
