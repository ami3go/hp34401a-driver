"""RFDS-008 structured evidence engine for rf_hp34401a.

One evidence run is created per ``Hp34401ALibrary`` instance and correlates
public keyword calls with literal SCPI traffic.  Run status is fail-closed:
once any recorded operation fails, later cleanup success cannot turn the run
back into PASS.  Integrity manifests are generated only after all events that
belong to the exported snapshot have been recorded.
"""

from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import logging
import os
import platform
import socket
import sys
import threading
import time
import traceback
import uuid
import zipfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logging_utils import _json_default as _logging_utils_json_default

SCHEMA_VERSION = "1.0.0"

logger = logging.getLogger("hp34401a_dmm.evidence")

_SENSITIVE_KEY_MARKERS = ("password", "secret", "token", "api_key", "apikey", "credential", "auth")

_current_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hp34401a_correlation_id", default=None
)
_current_operation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hp34401a_operation_id", default=None
)
_current_suite_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hp34401a_suite_id", default=None
)
_current_test_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hp34401a_test_id", default=None
)
_current_keyword: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hp34401a_keyword", default=None
)


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _new_run_id() -> str:
    now = datetime.now(timezone.utc)
    return (
        f"run-{now.strftime('%Y%m%dT%H%M%S')}.{now.microsecond // 1000:03d}Z-{uuid.uuid4().hex[:8]}"
    )


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    try:
        return _logging_utils_json_default(obj)
    except Exception:  # noqa: BLE001 - last-resort JSON fallback for arbitrary types
        return repr(obj)


def _looks_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return _json_default(value)


def redact_mapping(data: Mapping[str, Any]) -> dict:
    """Redact credential-shaped keys recursively."""
    result: dict = {}
    for key, value in data.items():
        if _looks_sensitive(str(key)):
            result[key] = {"value": "<REDACTED>", "redacted": True, "reason": "credential"}
        else:
            result[key] = _json_safe(value)
    return result


def _classify_exception(exc: BaseException) -> str:
    """Map the public/core exception hierarchy to a stable RFDS category."""
    name = type(exc).__name__
    if "Validation" in name:
        return "VALIDATION"
    if "Configuration" in name:
        return "CONFIGURATION"
    if "State" in name:
        return "STATE"
    if "Timeout" in name:
        return "TIMEOUT"
    if "Connection" in name:
        return "CONNECTION"
    if "Protocol" in name or "SCPI" in name or "Recovery" in name:
        return "PROTOCOL"
    if "Cleanup" in name:
        return "CLEANUP"
    if "Unsupported" in name:
        return "UNSUPPORTED"
    if "Safety" in name:
        return "SAFETY"
    if "Device" in name or "Overload" in name or "Stable" in name:
        return "DEVICE"
    return "UNKNOWN"


def _safe_distribution_version(dist_name: str) -> str | None:
    try:
        import importlib.metadata as importlib_metadata

        return importlib_metadata.version(dist_name)
    except Exception:  # noqa: BLE001 - best-effort version probe, must not raise
        return None


def _safe_module_version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
        return getattr(module, "__version__", None)
    except Exception:  # noqa: BLE001 - best-effort version probe, must not raise
        return None


def _sanitized_hostname() -> str:
    try:
        return hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()[:12]
    except Exception:  # noqa: BLE001 - hostname lookup must never raise
        return "UNKNOWN"


class _OperationContext:
    def __init__(self) -> None:
        self.result: Any = None

    def set_result(self, value: Any) -> None:
        self.result = value


class _NullOperationContext:
    def set_result(self, value: Any) -> None:  # pragma: no cover - trivial
        pass


class EvidenceRun:
    """Own one RFDS-008 result directory for one library instance."""

    SCHEMA = "rfds.run_summary"

    def __init__(
        self,
        *,
        driver_id: str = "rf_hp34401a",
        activity: str = "session",
        result_root: Path | None = None,
        execution_mode: str = "UNKNOWN",
    ) -> None:
        self.run_id = _new_run_id()
        self.driver_id = driver_id
        self.activity = activity
        self.execution_mode = str(execution_mode).upper()
        base = result_root or Path(os.environ.get("RFDS_EVIDENCE_ROOT", "results"))
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.root = base / activity / driver_id / f"{timestamp}_{self.run_id}"
        self._lock = threading.Lock()
        self._sequence: dict[str, int] = {}
        self._operation_counter = 0
        self._error_counter = 0
        self._start_monotonic = time.monotonic()
        self._start_time = _utc_now_iso()
        self._error_count = 0
        self._warning_count = 0
        self._run_failed = False
        self._finalized = False
        self._device_identities: dict[str, dict] = {}
        self._make_dirs()
        self._write_environment()
        self.emit_event("RUN_STARTED", f"Evidence run started for driver {driver_id}", level="INFO")

    def _make_dirs(self) -> None:
        for sub in ("events", "protocol", "cleanup", "integrity", "attachments"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def _environment_payload(self) -> dict[str, Any]:
        return {
            "schema": "rfds.environment",
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "timestamp_utc": _utc_now_iso(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "host_token": _sanitized_hostname(),
            "robot_framework_version": _safe_distribution_version("robotframework"),
            "driver_distribution_version": _safe_distribution_version("rf-hp34401a")
            or _safe_distribution_version("rf_hp34401a"),
            "driver_source_version": _safe_module_version("rf_hp34401a"),
            "core_driver_version": _safe_module_version("hp34401a_dmm"),
            # Field name retained for schema compatibility; resolves the real
            # scpi-driver-core dependency (see docs/scpi_driver_core_review.md).
            "rfds_core_version": _safe_distribution_version("scpi-driver-core"),
            "execution_mode": self.execution_mode,
            "clock_synchronization": "UNKNOWN",
        }

    def _write_environment(self) -> None:
        self._write_json(self.root / "environment.json", self._environment_payload())

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
                encoding="utf-8",
            )

    def _append_jsonl(self, path: Path, stream_key: str, record: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            seq = self._sequence[stream_key] = self._sequence.get(stream_key, 0) + 1
            record = dict(record)
            record["sequence"] = seq
            with path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(record, ensure_ascii=False, sort_keys=True, default=_json_default)
                    + "\n"
                )

    def emit_event(
        self,
        event_type: str,
        message: str,
        *,
        level: str = "INFO",
        data: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
        operation_id: str | None = None,
        session_alias: str | None = None,
    ) -> None:
        record = {
            "schema": "rfds.event",
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "producer_id": f"rf_hp34401a:{session_alias or self.driver_id}",
            "timestamp_utc": _utc_now_iso(),
            "monotonic_ns": time.monotonic_ns(),
            "level": level,
            "event_type": event_type,
            "correlation_id": correlation_id or _current_correlation_id.get(),
            "operation_id": operation_id or _current_operation_id.get(),
            "source": {
                "component": "driver",
                "driver_id": self.driver_id,
                "session_alias": session_alias,
                "suite_id": _current_suite_id.get(),
                "test_id": _current_test_id.get(),
                "robot_keyword": _current_keyword.get(),
            },
            "message": message,
            "data": redact_mapping(dict(data or {})),
        }
        self._append_jsonl(self.root / "events" / "events.jsonl", "events", record)
        python_level = {
            "TRACE": logging.DEBUG,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARN": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }.get(level, logging.INFO)
        logger.log(python_level, "[%s] %s", event_type, message)
        if level == "WARN":
            self._warning_count += 1

    @contextlib.contextmanager
    def record_operation(
        self,
        capability: str,
        *,
        arguments: Mapping[str, Any] | None = None,
        session_alias: str | None = None,
    ):
        with self._lock:
            self._operation_counter += 1
            operation_id = f"op-{self._operation_counter:06d}"
        correlation_id = _current_correlation_id.get() or f"corr-{uuid.uuid4().hex[:12]}"
        corr_token = _current_correlation_id.set(correlation_id)
        op_token = _current_operation_id.set(operation_id)
        safe_arguments = redact_mapping(dict(arguments or {}))
        start_monotonic = time.monotonic_ns()
        start_time = _utc_now_iso()
        self.emit_event(
            "OPERATION_STARTED",
            f"{capability} started",
            level="DEBUG",
            correlation_id=correlation_id,
            operation_id=operation_id,
            data={"arguments": safe_arguments},
            session_alias=session_alias,
        )
        ctx = _OperationContext()
        status = "PASS"
        error_summary: str | None = None
        try:
            yield ctx
        except Exception as exc:
            status = "FAIL"
            self._run_failed = True
            error_summary = f"{type(exc).__name__}: {exc}"
            self.record_error(
                exc,
                correlation_id=correlation_id,
                operation_id=operation_id,
                capability=capability,
                session_alias=session_alias,
            )
            raise
        finally:
            duration_s = (time.monotonic_ns() - start_monotonic) / 1e9
            record = {
                "schema": "rfds.operation",
                "schema_version": SCHEMA_VERSION,
                "run_id": self.run_id,
                "operation_id": operation_id,
                "correlation_id": correlation_id,
                "capability": capability,
                "session_alias": session_alias,
                "arguments": safe_arguments,
                "start_timestamp_utc": start_time,
                "end_timestamp_utc": _utc_now_iso(),
                "duration_s": round(duration_s, 6),
                "result": _json_safe(ctx.result) if status == "PASS" else None,
                "status": status,
                "error_summary": error_summary,
            }
            self._append_jsonl(self.root / "events" / "operations.jsonl", "operations", record)
            self.emit_event(
                "OPERATION_COMPLETED" if status == "PASS" else "OPERATION_FAILED",
                f"{capability} {'completed' if status == 'PASS' else 'failed'} in {duration_s:.4f}s",
                level="INFO" if status == "PASS" else "ERROR",
                correlation_id=correlation_id,
                operation_id=operation_id,
                session_alias=session_alias,
            )
            _current_correlation_id.reset(corr_token)
            _current_operation_id.reset(op_token)

    def log_protocol(
        self,
        direction: str,
        transport_kind: str,
        text: str,
        *,
        session_alias: str | None = None,
    ) -> None:
        if direction not in ("outbound", "inbound"):
            raise ValueError("direction must be 'outbound' or 'inbound'")
        exchange_id = f"pex-{uuid.uuid4().hex[:10]}"
        record = {
            "schema": "rfds.protocol_exchange",
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "protocol_exchange_id": exchange_id,
            "operation_id": _current_operation_id.get(),
            "correlation_id": _current_correlation_id.get(),
            "timestamp_utc": _utc_now_iso(),
            "transport": transport_kind,
            "direction": direction,
            "session_alias": session_alias,
            "operation": text,
        }
        self._append_jsonl(self.root / "protocol" / "exchanges.jsonl", "protocol_exchanges", record)
        trace_path = self.root / "protocol" / f"{direction}_trace.log"
        with self._lock, trace_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{record['timestamp_utc']} [{exchange_id}] ({transport_kind}) {text}\n")

    def record_error(
        self,
        exc: BaseException,
        *,
        correlation_id: str | None = None,
        operation_id: str | None = None,
        capability: str | None = None,
        session_alias: str | None = None,
        recoverable: bool | None = None,
    ) -> None:
        with self._lock:
            self._error_counter += 1
            error_id = f"err-{self._error_counter:06d}"
        self._run_failed = True
        record = {
            "schema": "rfds.error",
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "error_id": error_id,
            "timestamp_utc": _utc_now_iso(),
            "correlation_id": correlation_id or _current_correlation_id.get(),
            "operation_id": operation_id or _current_operation_id.get(),
            "capability": capability,
            "session_alias": session_alias,
            "category": _classify_exception(exc),
            "error_code": getattr(exc, "code", None),
            "exception_type": type(exc).__qualname__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "recoverable": recoverable,
        }
        self._append_jsonl(self.root / "events" / "errors.jsonl", "errors", record)
        self._error_count += 1
        logger.error("[%s] %s (%s): %s", error_id, capability or "?", type(exc).__name__, exc)

    def record_device_identity(self, session_alias: str, **fields: Any) -> None:
        existing = self._device_identities.get(session_alias, {})
        existing.update({key: value for key, value in fields.items() if value is not None})
        self._device_identities[session_alias] = existing
        transport = str(fields.get("transport") or "").lower()
        if transport == "simulation":
            self.execution_mode = "SIMULATION"
            self._write_environment()
        elif transport and self.execution_mode == "UNKNOWN":
            self.execution_mode = "REAL_HARDWARE"
            self._write_environment()
        payload = {
            "schema": "rfds.device_identity",
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "timestamp_utc": _utc_now_iso(),
            "sessions": self._device_identities,
        }
        self._write_json(self.root / "device_identity.json", payload)

    def _write_manifest(self) -> None:
        skip_names = {"evidence_manifest.json", "checksums.sha256"}
        entries = []
        for path in sorted(self.root.rglob("*")):
            if path.is_dir() or path.name in skip_names:
                continue
            relative = path.relative_to(self.root)
            data = path.read_bytes()
            entries.append(
                {
                    "path": str(relative).replace(os.sep, "/"),
                    "role": _role_for(relative),
                    "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        manifest = {
            "schema": "rfds.evidence_manifest",
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "generated_timestamp_utc": _utc_now_iso(),
            "artifact_count": len(entries),
            "artifacts": entries,
        }
        self._write_json(self.root / "evidence_manifest.json", manifest)
        checksum_path = self.root / "integrity" / "checksums.sha256"
        checksum_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            checksum_path.write_text(
                "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries),
                encoding="utf-8",
            )

    def finalize(self, status: str = "PASS") -> Path:
        if self._finalized:
            return self.root
        requested = str(status).strip().upper() or "PASS"
        effective = (
            "FAIL"
            if self._run_failed or self._error_count > 0 or requested == "FAIL"
            else requested
        )
        self.emit_event(
            "RUN_FINISHING", f"Evidence run finalizing with status {effective}", level="INFO"
        )
        duration_s = time.monotonic() - self._start_monotonic
        summary = {
            "schema": self.SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "activity": self.activity,
            "driver_id": self.driver_id,
            "start_timestamp_utc": self._start_time,
            "end_timestamp_utc": _utc_now_iso(),
            "duration_s": round(duration_s, 3),
            "execution_mode": self.execution_mode,
            "final_status": effective,
            "error_count": self._error_count,
            "warning_count": self._warning_count,
            "dropped_events": 0,
            "evidence_completeness": "COMPLETE",
            "device_identity_reference": (
                "device_identity.json" if self._device_identities else None
            ),
            "result_root": str(self.root),
        }
        self._write_json(self.root / "run_summary.json", summary)
        self._write_markdown_summary(summary)
        self._write_manifest()
        self._finalized = True
        return self.root

    def _write_markdown_summary(self, summary: dict) -> None:
        lines = [
            f"# Evidence run summary — {summary['driver_id']}",
            "",
            f"- Run ID: `{summary['run_id']}`",
            f"- Activity: {summary['activity']}",
            f"- Execution mode: {summary['execution_mode']}",
            f"- Started: {summary['start_timestamp_utc']}",
            f"- Finished: {summary['end_timestamp_utc']}",
            f"- Duration: {summary['duration_s']} s",
            f"- Final status: **{summary['final_status']}**",
            f"- Errors: {summary['error_count']}, Warnings: {summary['warning_count']}",
            f"- Evidence completeness: {summary['evidence_completeness']}",
            "",
            "Generated from `run_summary.json`. See `events/operations.jsonl` for every keyword",
            "call this run made, `events/errors.jsonl` for failures, and `protocol/exchanges.jsonl`",
            "for the underlying SCPI commands/responses, in the order they happened.",
            "",
        ]
        (self.root / "run_summary.md").write_text("\n".join(lines), encoding="utf-8")

    def export_diagnostic_bundle(self, destination: str | None = None) -> str:
        if destination:
            zip_path = Path(destination)
            zip_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            zip_path = self.root.parent / f"{self.root.name}_diagnostic_bundle.zip"

        # The export event belongs to the snapshot, so write it before the
        # manifest and archive.  Nothing under the evidence root is mutated
        # after the manifest is generated.
        self.emit_event(
            "DIAGNOSTIC_BUNDLE_EXPORTED",
            f"Diagnostic bundle snapshot requested at {zip_path}",
            level="INFO",
        )
        self._write_manifest()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.root.rglob("*")):
                if path.is_file():
                    archive.write(
                        path, arcname=str(Path(self.root.name) / path.relative_to(self.root))
                    )
        return str(zip_path)


_ROLE_BY_NAME = {
    "run_summary.json": "AUTHORITATIVE_RESULT",
    "run_summary.md": "DERIVED_REPORT",
    "environment.json": "IDENTITY",
    "device_identity.json": "IDENTITY",
}


def _role_for(relative_path: Path) -> str:
    name = relative_path.name
    if name in _ROLE_BY_NAME:
        return _ROLE_BY_NAME[name]
    parts = relative_path.parts
    if parts and parts[0] == "protocol":
        return "RAW_OBSERVATION"
    if relative_path.suffix == ".jsonl":
        return "STRUCTURED_EVENT"
    if parts and parts[0] == "integrity":
        return "INTEGRITY"
    return "DERIVED_REPORT"


class NullEvidenceRun:
    """Used when ``evidence_enabled=False``: same interface, writes nothing."""

    run_id: str | None = None

    @contextlib.contextmanager
    def record_operation(
        self, capability: str, *, arguments: Mapping[str, Any] | None = None, session_alias=None
    ):
        logger.debug("%s(%s)", capability, dict(arguments or {}))
        yield _NullOperationContext()

    def emit_event(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def log_protocol(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def record_error(self, exc: BaseException, **_kwargs: Any) -> None:
        logger.error("%s: %s", type(exc).__name__, exc)

    def record_device_identity(self, session_alias: str, **_kwargs: Any) -> None:
        pass

    def finalize(self, status: str = "PASS") -> None:
        return None

    def export_diagnostic_bundle(self, destination: str | None = None) -> None:
        logger.warning(
            "Diagnostic bundle requested but evidence_enabled=False; nothing was recorded."
        )


class EvidenceListener:
    """Optional Robot listener for suite/test/keyword correlation."""

    ROBOT_LISTENER_API_VERSION = 3

    def start_suite(self, data: Any, result: Any) -> None:
        _current_suite_id.set(getattr(data, "longname", str(data)))

    def end_suite(self, data: Any, result: Any) -> None:
        _current_suite_id.set(None)

    def start_test(self, data: Any, result: Any) -> None:
        _current_test_id.set(getattr(data, "longname", str(data)))

    def end_test(self, data: Any, result: Any) -> None:
        _current_test_id.set(None)

    def start_keyword(self, data: Any, result: Any) -> None:
        _current_keyword.set(getattr(data, "name", str(data)))

    def end_keyword(self, data: Any, result: Any) -> None:
        _current_keyword.set(None)


__all__ = [
    "SCHEMA_VERSION",
    "EvidenceListener",
    "EvidenceRun",
    "NullEvidenceRun",
    "redact_mapping",
]
