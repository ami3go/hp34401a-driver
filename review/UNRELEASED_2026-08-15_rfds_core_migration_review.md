# RFDS-003 migration review — unreleased 2026-08-15

**Driver:** `rf_hp34401a`  
**Branch:** `dev`  
**Review verdict:** **PARTIAL / BLOCKED**

## Findings reviewed

| ID | Severity | Finding | Status |
|---|---:|---|---|
| HP34401-001 | High | Robot library does not inherit `BaseInstrumentLibrary` | **OPEN / BLOCKED** |
| HP34401-002 | High | `rfds-core` is optional instead of a runtime dependency | **CORRECTED** |
| HP34401-003 | Medium | Runtime `rfds-core` version is hard-coded as `NOT_INSTALLED` | **OPEN** |
| HP34401-004 | Verification | Re-run conformance, package and HIL qualification after migration | **OPEN** |

## Review of corrections

### HP34401-002 — corrected

`pyproject.toml` now declares `rfds-core>=1.0,<2.0` in `[project].dependencies`. The redundant optional `rfds` extra was removed. This matches the RFDS-003 shared-core packaging model.

The RFDS-015 provider now treats the `rfds_core` import as a required environment check. This prevents metadata-only discovery from reporting a healthy environment when the mandatory shared core is absent.

Regression tests were added under `tests/unit/test_rfds_core_packaging.py`.

### HP34401-001 — intentionally not faked

The current `Hp34401ALibrary` still owns `SessionManager`, lifecycle orchestration, timeout behavior and operation execution directly. Converting the class to a syntactic subclass without using the authoritative base orchestration would create false conformance and is rejected by this review.

The correct next implementation step is to use the actual `rfds_core.BaseInstrumentLibrary` distribution, map the HP transport/core into the RFDS-003 hook model, and migrate connection/session ownership without changing the RFDS-002 public keyword contract.

### HP34401-003 — still open

`Get Driver Information` must resolve the installed `rfds-core` distribution version at runtime. That change should be implemented together with the real base integration so the reported value is derived from the same authoritative package that provides `BaseInstrumentLibrary`.

## Release decision

Do **not** promote this correction as RFDS-003 complete. Keep release class D0 until:

1. the authoritative `rfds-core` package is available to the build/test environment;
2. `Hp34401ALibrary` inherits and uses `BaseInstrumentLibrary` orchestration;
3. effective core version reporting is implemented;
4. RFDS-003 contract tests, RFDS-019 conformance, package installation and relevant HIL tests are rerun with recorded evidence.
