# Unreleased change — RFDS-003 shared core packaging

**Date:** 2026-08-15  
**Branch:** `dev`  
**Driver:** `rf_hp34401a`  
**Release status:** Unreleased / D0

## Scope

This change starts the RFDS-003 v2.0 correction identified during the repository-wide driver review.

## Changes made

1. Moved `rfds-core>=1.0,<2.0` from an optional `rfds` extra into the main runtime dependency list in `pyproject.toml`.
2. Updated the RFDS-015 plugin environment validator so absence of the `rfds_core` import is a required `FAIL`, not an unreported condition.
3. Added regression tests that enforce the mandatory runtime dependency and plugin validation behavior.
4. Updated the README to report the current RFDS-003 deviation count and to avoid claiming that the base-class migration is already complete.

## Open RFDS-003 deviations

The following findings remain open and block RFDS-003 completion:

- `Hp34401ALibrary` does not yet inherit from the authoritative `rfds_core.BaseInstrumentLibrary` and still owns its pre-RFDS-003 session/orchestration implementation.
- `Get Driver Information` still reports a fixed `rfds_core_runtime_version="NOT_INSTALLED"` value instead of resolving the effective installed core version at runtime.

The authoritative `rfds_core` implementation is not contained in this repository and was not available in the connected execution environment used for this edit. A local replacement or copied base class was intentionally **not** introduced because RFDS-003 requires one shared, separately versioned core dependency.

## Verification status

Static repository changes were applied on `dev`. No claim is made that the RFDS-003 contract suite, package installation, or HIL qualification passed in this environment because the authoritative `rfds_core` package was unavailable for execution.
