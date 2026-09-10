"""RFDS-aligned Robot-layer exceptions and diagnostics."""

from __future__ import annotations

from typing import Any, Mapping


class RFDSDriverError(RuntimeError):
    """Base error exposed at the public driver boundary.

    The string form contains a stable error code while ``to_dict`` provides a
    Robot/JSON-compatible diagnostic record. Original exceptions are retained
    using Python exception chaining by the caller.
    """

    default_code = "RFDS-DRV-001"
    default_retryable = False
    default_recovery = "inspect diagnostics and correct the cause"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retryable: bool | None = None,
        severity: str = "ERROR",
        recovery_action: str | None = None,
        operation: str | None = None,
        keyword: str | None = None,
        alias: str | None = None,
        details: Mapping[str, Any] | None = None,
        post_failure_state: str = "UNKNOWN",
    ) -> None:
        self.code = code or self.default_code
        self.message = str(message)
        self.retryable = self.default_retryable if retryable is None else bool(retryable)
        self.severity = severity
        self.recovery_action = recovery_action or self.default_recovery
        self.operation = operation
        self.keyword = keyword
        self.alias = alias
        self.details = dict(details or {})
        self.post_failure_state = post_failure_state
        super().__init__(self.message)

    def __str__(self) -> str:
        subject = self.keyword or self.operation or "Driver operation"
        alias = f" [alias={self.alias}]" if self.alias else ""
        return (
            f"[{self.code}] {subject} failed{alias}: {self.message}. "
            f"Retryable={'yes' if self.retryable else 'no'}. "
            f"Recovery={self.recovery_action}."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "exception_type": type(self).__name__,
            "message": self.message,
            "retryable": self.retryable,
            "severity": self.severity,
            "recovery_action": self.recovery_action,
            "operation": self.operation,
            "keyword": self.keyword,
            "alias": self.alias,
            "post_failure_state": self.post_failure_state,
            "details": dict(self.details),
        }


class Hp34401ARobotError(RFDSDriverError):
    """Backward-compatible adapter exception base name."""

    default_code = "HP34401A-DRV-001"


class DriverValidationError(Hp34401ARobotError, ValueError):
    """Structured RFDS argument/configuration value validation error.

    ``ValueError`` compatibility preserves existing Python callers while the
    RFDS driver hierarchy and stable error code remain authoritative at the
    Robot/public boundary.
    """

    default_code = "RFDS-VAL-001"
    default_recovery = "correct the supplied argument or configuration"


class DriverConfigurationError(Hp34401ARobotError):
    default_code = "RFDS-CFG-001"
    default_recovery = "validate the configuration before applying it"


class DriverStateError(Hp34401ARobotError):
    default_code = "RFDS-STATE-001"
    default_recovery = "establish the required connection and state"


class DriverConnectionError(Hp34401ARobotError):
    default_code = "RFDS-CONN-001"
    default_retryable = True
    default_recovery = "verify the resource, backend and cabling, then reconnect"


class DriverTransportError(Hp34401ARobotError):
    default_code = "RFDS-TR-001"
    default_recovery = "recover or reconnect the transport before continuing"


class DriverProtocolError(Hp34401ARobotError):
    default_code = "RFDS-PROTO-001"
    default_recovery = "inspect the protocol response and instrument error queue"


class DriverDeviceError(Hp34401ARobotError):
    default_code = "RFDS-DEV-001"
    default_recovery = "read and clear the device error queue after correcting the cause"


class DriverTimeoutError(Hp34401ARobotError):
    default_code = "RFDS-TMO-001"
    default_retryable = True
    default_recovery = "verify communication and retry only when the operation is retry-safe"


class DriverSafetyError(Hp34401ARobotError):
    default_code = "RFDS-SAFE-001"
    default_recovery = "place the bench in a verified safe state and review limits"


class DriverUnsupportedOperationError(Hp34401ARobotError):
    default_code = "RFDS-UNSUP-001"
    default_recovery = "use a supported capability or transport profile"


class DriverCleanupError(Hp34401ARobotError):
    default_code = "RFDS-CLEAN-001"
    default_recovery = "verify resource release and perform manual cleanup if necessary"
