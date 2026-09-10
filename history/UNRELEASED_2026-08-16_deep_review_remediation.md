# Unreleased history — 2026-08-16 deep-review remediation

**Branch:** `dev`  
**Release status:** Unreleased remediation candidate  
**Public API baseline:** 26.07 / 109 keywords

## Purpose

This change set corrects findings from the file-by-file RFDS review without creating a new production release or changing the intended 26.07 public Robot keyword names/signatures.

## Corrected

### CI, Pages and HIL workflow placement

- moved driver automation to repository-root `.github/workflows/` so GitHub actually discovers it;
- added the correct `rf_hp34401a` working directory;
- separated software-quality jobs from the external RFDS-003 shared-core release gate;
- retained explicit manual HIL on self-hosted hardware;
- removed inactive nested workflow copies;
- stopped tracking generated MkDocs `site/` output.

### RFDS-008 evidence integrity

- accumulated run failure state so a prior failed keyword cannot be hidden by successful cleanup;
- corrected simulation/real-hardware execution-mode reporting;
- finalized evidence during listener cleanup when explicit disconnect is omitted;
- corrected diagnostic export ordering and final snapshot regeneration;
- added structured public error codes to evidence records;
- synchronized error/run-summary schemas and added emitted-evidence schema validation.

### RFDS-014 configuration

- added mandatory Draft 2020-12 JSON-Schema validation;
- replaced one-line schema locks with structured RFDS locks and verified SHA-256 at initialization;
- synchronized repository/package schema/default/lock authorities;
- added per-leaf source reporting;
- applied imported timeout/retry/logging/safety/simulation/device-terminal policy to active/new sessions;
- clarified exact schema `1.0.0` behavior and no implicit migration engine;
- synchronized example/simulator profiles to 26.07.

### Public API/runtime behavior

- communication timeout conversion now rejects zero, negative, NaN and infinity;
- public argument validation uses `DriverValidationError` while retaining Python `ValueError` compatibility;
- invalid assertion *configuration* now uses structured validation errors while DUT limit failures remain `AssertionError`;
- `List Connections` preserves last-known `communication_ok` instead of equating an open transport with healthy communication;
- active Robot code no longer uses the core transport `_t` directly for public timeout/raw-response operations.

### RFDS-013 / RFDS-017 / RFDS-019 synchronization

- synchronized the 26.07 static capability model with runtime capability bindings;
- capability validation now compares against the real decorated effective Robot surface;
- retry safety/timing is explicit per modeled operation;
- AI/API/conformance validators inspect inherited facade keywords;
- API/conformance generators are facade-aware and preserve reviewed semantic/governance data;
- added read-only generator-surface regression checks.

### Plugin/package/release

- made `rfds-core>=1.0,<2.0` and `jsonschema>=4.20,<5` mandatory runtime dependencies;
- plugin checks actual installed `rfds-core` compatibility and reports its version;
- driver information/metadata/evidence report runtime shared-core version when installed;
- plugin artifact paths resolve in source and installed-wheel layouts;
- added isolated wheel entry-point/resource validation;
- replaced the frozen 26.06 release builder with version-derived packaging;
- invalidated stale checksums/provenance instead of presenting them as current evidence;
- synchronized current candidate manifest, SBOM, compatibility report, public API diff and release traceability;
- added the missing retrospective v26.07 code review.

### GUI safety

- preserved the existing GUI implementation as `hp34401a_gui/legacy_app.py`;
- active `hp34401a_gui/app.py` requires a fresh operator confirmation before every raw SCPI Query/Write service action;
- normal GUI measurement/identity/health/logging controls are unchanged;
- core calibration protection remains independent.

## Preserved implementation layers

To minimize regression risk, mature implementations were retained byte-for-byte beneath small reviewed facades:

- `rf_hp34401a/legacy_library.py` — original complete 26.07 keyword implementation;
- `rf_hp34401a/runtime_library.py` — cross-cutting runtime corrections;
- `rf_hp34401a/library.py` — final public facade;
- `hp34401a_dmm/legacy_driver.py` — reviewed 1.2.8 core;
- `hp34401a_dmm/driver.py` — explicit runtime-policy/public transport-boundary facade;
- `hp34401a_gui/legacy_app.py` — preserved GUI;
- `hp34401a_gui/app.py` — raw-service authorization launcher.

## Explicitly still open

- `HP34401A-DEV-004`: authoritative RFDS-003 `BaseInstrumentLibrary` integration. The connected repository/environment does not contain the authoritative implementation; no local copy/shim is created.
- `HP34401A-DEV-002`: migration to RFDS-004 v2 canonical byte transport remains a separately reviewed architecture change.
- `HP34401A-DEV-003`: representative real-hardware HIL must be rerun from the final frozen remediation commit.

## Release effect

No D2, P1, full RFDS-003, or fresh release-integrity claim is made by this history entry. Release evidence must be regenerated only after software quality is green, the authoritative shared-core integration is completed, and exact-commit HIL has been executed.
