# Migration

## Python driver to Robot Framework

Use Robot keywords instead of calling the core driver/transport objects directly. Range, NPLC, aperture, filter, trigger, terminal, Boolean, and duration values may be supplied in Robot-friendly form. Scalar measurement keywords reject invalid/overload readings; use `Get Last DMM Reading` when full metadata is needed.

Do not reach through the Robot library to `session.driver._t`. Runtime communication timeout and raw-response access are exposed through the public facade/core methods so tracing, evidence, and transport policy stay centralized.

## Legacy Robot keyword names

The RFDS canonical lifecycle coexists with legacy DMM-specific names for compatibility. Prefer the canonical RFDS-002 keywords for new suites:

- `Connect` instead of `Connect DMM`/transport-specific open keywords;
- `Disconnect` / `Disconnect All` instead of close aliases;
- `Get Identity` instead of `Identify DMM`;
- canonical device-error and raw-I/O groups instead of their legacy aliases.

Compatibility aliases remain documented in `api/compatibility.yaml` and are not removed before the declared API compatibility window.

## Configuration migration

The current RFDS-014 schema version is exactly `1.0.0`. No automatic cross-version configuration migration is implemented. Profiles with a different `schema_version` are rejected.

`config/migrations/` is a reserved review location for a future explicit migration when the schema changes. A migration must be deterministic, version-to-version, tested, recorded in history/review, and must never guess hardware resources or safety authorization.

## RFDS-003 migration

`rfds-core>=1.0,<2.0` is now mandatory and runtime version metadata is reported. The remaining RFDS-003 architecture migration is inheritance/integration with the authoritative shared `BaseInstrumentLibrary`.

That integration is intentionally blocked until the authoritative implementation is available to this repository/environment. Do not create a local class named `BaseInstrumentLibrary`, copy the RFDS base into this driver, or mark the deviation closed based only on a superficial inheritance declaration.
