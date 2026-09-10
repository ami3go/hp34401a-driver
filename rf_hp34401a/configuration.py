"""RFDS-014 host-side JSON configuration support.

Configuration is validated against the published Draft 2020-12 JSON Schema
and the schema is authenticated by the packaged RFDS ``schema.lock`` before
any profile is accepted.  Import/export never opens hardware or writes device
non-volatile state.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .exceptions import DriverConfigurationError, DriverValidationError

_SCHEMA_ID = "rf_hp34401a.configuration"
_SCHEMA_VERSION = "1.0.0"
_RFDS014_VERSION = "1.0"


def _resource_dir() -> Path:
    return Path(__file__).resolve().parent / "resources" / "configuration"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _profile_root() -> Path:
    override = os.environ.get("RF_HP34401A_PROFILE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "RFDS" / "rf_hp34401a" / "profiles"
    return Path.home() / ".config" / "rfds" / "rf_hp34401a" / "profiles"


def _safe_profile_name(name: str) -> str:
    text = str(name).strip()
    if not text or len(text) > 64:
        raise DriverValidationError("Profile name must contain 1 to 64 characters")
    if text in {".", ".."} or text.startswith("."):
        raise DriverValidationError("Profile name may not be hidden or relative")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if any(char not in allowed for char in text):
        raise DriverValidationError(
            "Profile name may contain only letters, digits, underscore, hyphen and period"
        )
    return text


def _source_map(value: Mapping[str, Any], source: str, prefix: str = "settings") -> dict[str, str]:
    result: dict[str, str] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}"
        if isinstance(item, Mapping):
            result.update(_source_map(item, source, path))
        else:
            result[path] = source
    return result


class ConfigurationManager:
    """Validate, merge, import, export, and explicitly persist driver profiles."""

    def __init__(self) -> None:
        resource_dir = _resource_dir()
        self._schema_path = resource_dir / "schema.json"
        self._lock_path = resource_dir / "schema.lock"
        self._schema = self._load_json(self._schema_path)
        self._verify_schema_lock()
        self._validator = Draft202012Validator(self._schema)
        self._default = self._load_json(resource_dir / "default.json")
        self._effective = deepcopy(self._default)
        self._sources = _source_map(self._effective.get("settings", {}), "PACKAGE_DEFAULT")
        self.validate(self._default, strict=True)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DriverConfigurationError(f"Cannot load configuration file {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise DriverConfigurationError(f"Configuration file {path} must contain a JSON object")
        return loaded

    def _verify_schema_lock(self) -> None:
        lock = self._load_json(self._lock_path)
        if lock.get("schema_id") != _SCHEMA_ID:
            raise DriverConfigurationError(
                f"schema.lock schema_id must be {_SCHEMA_ID!r}, got {lock.get('schema_id')!r}"
            )
        if lock.get("schema_version") != _SCHEMA_VERSION:
            raise DriverConfigurationError(
                "schema.lock schema_version does not match the supported configuration schema"
            )
        expected = str(lock.get("sha256") or "").strip().lower()
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise DriverConfigurationError("schema.lock sha256 must contain a 64-character hex digest")
        try:
            actual = hashlib.sha256(self._schema_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise DriverConfigurationError(f"Cannot read configuration schema: {exc}") from exc
        if actual != expected:
            raise DriverConfigurationError(
                f"RFDS_CONFIG_INTEGRITY: schema.lock mismatch: expected {expected}, calculated {actual}"
            )

    def schema(self) -> dict[str, Any]:
        return deepcopy(self._schema)

    def default(self) -> dict[str, Any]:
        return deepcopy(self._default)

    def effective(self, *, include_sources: bool = False) -> dict[str, Any]:
        result = deepcopy(self._effective)
        if include_sources:
            result.setdefault("metadata", {})["resolved_sources"] = deepcopy(self._sources)
        return result

    def validate(self, document: Mapping[str, Any], *, strict: bool = True) -> dict[str, Any]:
        if not isinstance(document, Mapping):
            raise DriverValidationError("Driver configuration must be a JSON object")
        data = deepcopy(dict(document))

        # RFDS-014 non-strict mode is only a compatibility allowance for data
        # inside approved extension namespaces.  This schema already permits
        # arbitrary contents under ``extensions``.  Unknown core/top-level keys
        # therefore remain invalid in both modes and are never silently applied.
        del strict
        errors = sorted(self._validator.iter_errors(data), key=lambda err: list(err.absolute_path))
        if errors:
            first = errors[0]
            path = ".".join(str(part) for part in first.absolute_path) or "<root>"
            raise DriverValidationError(f"Configuration schema validation failed at {path}: {first.message}")

        if data.get("rfds014_version") != _RFDS014_VERSION:
            raise DriverValidationError(
                f"Unsupported rfds014_version {data.get('rfds014_version')!r}; expected {_RFDS014_VERSION}"
            )
        if data.get("schema_id") != _SCHEMA_ID:
            raise DriverValidationError(f"Configuration schema_id must be {_SCHEMA_ID!r}")
        if data.get("schema_version") != _SCHEMA_VERSION:
            raise DriverValidationError(
                f"Unsupported schema_version {data.get('schema_version')!r}; expected {_SCHEMA_VERSION}"
            )
        profile = data.get("profile")
        if isinstance(profile, Mapping):
            _safe_profile_name(str(profile.get("name", "")))
        return data

    def apply(self, document: Mapping[str, Any], *, strict: bool = True) -> dict[str, Any]:
        candidate = self.validate(document, strict=strict)
        self._effective = deepcopy(candidate)
        self._sources = _source_map(self._effective.get("settings", {}), "RUNTIME_IMPORT")
        return self.effective(include_sources=True)

    def import_json(
        self,
        source: str | Path | Mapping[str, Any],
        *,
        validate_only: bool = False,
        strict: bool = True,
    ) -> dict[str, Any]:
        if isinstance(source, Mapping):
            data = dict(source)
        else:
            text = str(source).strip()
            try:
                if text.startswith("{") or text.startswith("["):
                    data = json.loads(text)
                else:
                    path = Path(text).expanduser()
                    data = self._load_json(path) if path.exists() else json.loads(text)
            except (json.JSONDecodeError, OSError) as exc:
                raise DriverConfigurationError(f"Invalid configuration JSON or path: {exc}") from exc
        validated = self.validate(data, strict=strict)
        return validated if validate_only else self.apply(validated, strict=strict)

    def export_json(
        self,
        destination: str | Path | None = None,
        *,
        indent: int = 2,
    ) -> str:
        if isinstance(indent, bool) or int(indent) < 0 or int(indent) > 16:
            raise DriverValidationError("JSON indent must be an integer from 0 to 16")
        text = json.dumps(self._effective, indent=int(indent), sort_keys=True, ensure_ascii=False) + "\n"
        if destination is not None:
            path = Path(destination).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(path, text)
        return text

    def fingerprint(self) -> str:
        semantic = {"settings": self._effective.get("settings", {})}
        digest = hashlib.sha256(_canonical_json(semantic).encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def save_profile(self, name: str, *, overwrite: bool = False) -> str:
        profile_name = _safe_profile_name(name)
        root = _profile_root()
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{profile_name}.json"
        if path.exists() and not overwrite:
            raise DriverConfigurationError(
                f"Configuration profile {profile_name!r} already exists; set overwrite=true explicitly"
            )
        document = deepcopy(self._effective)
        document.setdefault("profile", {})["name"] = profile_name
        document["profile"]["scope"] = "USER"
        self.validate(document, strict=True)
        self._atomic_write(
            path,
            json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        )
        return str(path)

    def load_profile(self, name: str, *, validate_only: bool = False) -> dict[str, Any]:
        profile_name = _safe_profile_name(name)
        path = _profile_root() / f"{profile_name}.json"
        if not path.exists():
            raise DriverConfigurationError(f"Configuration profile {profile_name!r} does not exist")
        return self.import_json(path, validate_only=validate_only)

    def list_profiles(self) -> list[str]:
        root = _profile_root()
        if not root.exists():
            return []
        return sorted(path.stem for path in root.glob("*.json") if path.is_file())

    def delete_profile(self, name: str) -> None:
        profile_name = _safe_profile_name(name)
        path = _profile_root() / f"{profile_name}.json"
        if path.exists():
            path.unlink()

    def reset(self) -> dict[str, Any]:
        self._effective = deepcopy(self._default)
        self._sources = _source_map(self._effective.get("settings", {}), "PACKAGE_DEFAULT")
        return self.effective(include_sources=True)

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
