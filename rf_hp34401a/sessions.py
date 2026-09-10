"""Named DMM session registry with deterministic RFDS lifecycle semantics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hp34401a_dmm import Hp34401A, MeasurementReading

_ALIAS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_RESERVED = {"NONE", "NULL", "TRUE", "FALSE", "ALL", "DEFAULTS"}


@dataclass(slots=True)
class DmmSession:
    alias: str
    driver: Hp34401A
    resource: str = "UNKNOWN"
    transport_kind: str = "UNKNOWN"
    timeout_s: float = 10.0
    options: dict[str, Any] = field(default_factory=dict)
    connected_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    generation: int = 1
    identity_text: str | None = None
    last_reading: MeasurementReading | None = None
    last_error: dict[str, Any] | None = None

    @property
    def connected(self) -> bool:
        try:
            return bool(self.driver.is_connected())
        except Exception:
            return False

    def to_connection_state(
        self,
        *,
        active: bool = False,
        communication_ok: bool | None = None,
    ) -> dict[str, Any]:
        connected = self.connected
        state = "connected" if connected else "disconnected"
        return {
            "alias": self.alias,
            "resource": self.resource,
            "connected": connected,
            "communication_ok": connected if communication_ok is None else bool(communication_ok),
            "transport": self.transport_kind,
            "identity": self.identity_text,
            "timeout_s": float(self.timeout_s),
            "state": state,
            "simulated": self.transport_kind == "simulation",
            "connected_at": self.connected_at_utc,
            "session_id": f"{self.alias}:{self.generation}",
            "active": active,
        }


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, DmmSession] = {}
        self._active_key: str | None = None
        self._generations: dict[str, int] = {}

    @staticmethod
    def normalize_alias(alias: object) -> str:
        text = str(alias).strip()
        if not text:
            raise ValueError("DMM alias must not be empty")
        if not _ALIAS_RE.fullmatch(text):
            raise ValueError(
                "DMM alias must start with a letter and contain only letters, digits, '.', '_' or '-'"
            )
        if text.upper() in _RESERVED:
            raise ValueError(f"DMM alias {text!r} is reserved")
        return text

    @classmethod
    def key_for(cls, alias: object) -> str:
        return cls.normalize_alias(alias).casefold()

    def add(
        self,
        alias: object,
        driver: Hp34401A,
        *,
        replace: bool = False,
        resource: str = "UNKNOWN",
        transport_kind: str = "UNKNOWN",
        timeout_s: float = 10.0,
        options: dict[str, Any] | None = None,
        identity_text: str | None = None,
    ) -> DmmSession:
        display = self.normalize_alias(alias)
        key = display.casefold()
        if key in self._sessions and not replace:
            raise ValueError(f"DMM alias {display!r} is already open")
        if key in self._sessions:
            self._sessions[key].driver.close()
        generation = self._generations.get(key, 0) + 1
        self._generations[key] = generation
        session = DmmSession(
            alias=display,
            driver=driver,
            resource=resource,
            transport_kind=transport_kind,
            timeout_s=float(timeout_s),
            options=dict(options or {}),
            generation=generation,
            identity_text=identity_text,
        )
        self._sessions[key] = session
        self._active_key = key
        return session

    def select(self, alias: object) -> DmmSession:
        key = self.key_for(alias)
        try:
            session = self._sessions[key]
        except KeyError as exc:
            raise ValueError(f"DMM alias {self.normalize_alias(alias)!r} is not open") from exc
        self._active_key = key
        return session

    def get(self, alias: object | None = None) -> DmmSession:
        if alias is not None and str(alias).strip():
            key = self.key_for(alias)
            try:
                return self._sessions[key]
            except KeyError as exc:
                raise ValueError(f"DMM alias {self.normalize_alias(alias)!r} is not open") from exc
        if self._active_key is None:
            raise ValueError("No DMM session is open")
        return self._sessions[self._active_key]

    def find(self, alias: object | None = None) -> DmmSession | None:
        try:
            return self.get(alias)
        except ValueError:
            return None

    @property
    def active_alias(self) -> str | None:
        if self._active_key is None:
            return None
        return self._sessions[self._active_key].alias

    def aliases(self) -> list[str]:
        return [session.alias for session in self._sessions.values()]

    def states(self) -> list[dict[str, Any]]:
        return [
            session.to_connection_state(active=(key == self._active_key))
            for key, session in self._sessions.items()
        ]

    def close(self, alias: object | None = None, *, idempotent: bool = False) -> bool:
        session = self.find(alias)
        if session is None:
            if idempotent:
                return False
            if alias is None:
                raise ValueError("No DMM session is open")
            raise ValueError(f"DMM alias {self.normalize_alias(alias)!r} is not open")
        key = session.alias.casefold()
        try:
            session.driver.close()
        finally:
            self._sessions.pop(key, None)
            if self._active_key == key:
                self._active_key = next(iter(self._sessions), None)
        return True

    def close_all(self) -> list[str]:
        errors: list[str] = []
        for key, session in list(self._sessions.items()):
            try:
                session.driver.close()
            except Exception as exc:  # cleanup must continue
                errors.append(f"{session.alias}: {exc}")
            finally:
                self._sessions.pop(key, None)
        self._active_key = None
        return errors
