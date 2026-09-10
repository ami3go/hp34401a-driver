# Changelog

## Unreleased — 2026-09-10

- Extracted this driver from the `RobotFrameworks_hw_drivers` monorepo into its own repository, per the `Lab-equipment-pyDrivers` hub convention.
- Migrated the transport/protocol layer onto the real shared library, [`scpi-driver-core`](https://github.com/ami3go/scpi-driver-core), replacing the `rfds-core>=1.0,<2.0` runtime dependency that was never published anywhere (no PyPI release, no repository). `SerialRs232Transport` and `VisaGpibTransport` are now backed by `scpi_driver_core.transport.serial.SerialTransport`/`.transport.visa.VisaTransport`; `BaseTransport`'s locking/framing is now `scpi_driver_core.scpi.client.ScpiClient` + `ScpiTextCodec`; `FakeTransport` is now backed by `scpi_driver_core.simulation.scripted.ScriptedScpiTransport`. See `docs/scpi_driver_core_review.md` for the full before/after, known limitations, and pre-existing bugs this surfaced.
- Fixed a pre-existing bug in `tests/conformance/support/ConformanceHarness.py` that made all 113 RFDS-019 protocol-conformance vectors fail immediately with `KeyError: 'from_visa_gpib'`, independent of this migration.
- Fixed two pre-existing Robot syntax bugs that made `tests/api` fail unconditionally (`Should Be True    Is Connected    ...` evaluated as a Python expression instead of calling the keyword; missing `Library Collections` import), and one stale hardcoded version assertion in `examples/13_canonical_lifecycle_capability_configuration.robot`.
- Added `tests/unit/test_scpi_driver_core_integration.py`, exercising `scpi_driver_core`'s `Ieee4882`/`ScriptedScpiTransport` directly (not just through this driver's `FakeTransport` wrapper) and asserting every keyword in `api/public_api.yaml` is reachable on `Hp34401ALibrary`.

## Unreleased — 2026-08-16

- Activated repository-root GitHub Actions for cross-platform quality gates, manual HIL, and GitHub Pages; removed the inactive driver-local workflow copies.
- Corrected RFDS-008 evidence integrity so any prior keyword failure keeps the final run status at `FAIL`, diagnostic export remains manifest-valid, simulation evidence is labeled `SIMULATION`, and listener cleanup finalizes unfinished evidence runs.
- Enforced RFDS-014 Draft 2020-12 JSON Schema validation and structured SHA-256 schema-lock verification; synchronized root/package configuration authorities and added leaf-level configuration source reporting.
- Applied imported RFDS-014 timeout, retry, logging, raw-I/O, calibration, simulation, and expected-terminal policy to the active runtime path.
- Added finite-positive RFDS timeout validation and structured `DriverValidationError` conversion at the public argument boundary.
- Added explicit core methods for communication timeout, raw-response access, transport metadata, and runtime policy so the active Robot facade no longer accesses the core transport privately.
- Synchronized RFDS-013 capability data with v26.07 and validate capability bindings against the actual decorated Robot keyword surface.
- Made `rfds-core>=1.0,<2.0` and `jsonschema>=4.20,<5` mandatory runtime dependencies, added runtime rfds-core version checks/reporting, and added installed-wheel plugin resource validation.
- Replaced the frozen v26.06 release builder with version-derived release packaging and invalidated stale release checksums/provenance until a frozen commit is rebuilt.
- Removed committed generated MkDocs `site/` output; GitHub Pages now builds from `docs/` and `mkdocs.yml`.
- Added the missing retrospective v26.07 code-review record and new regression coverage for evidence, configuration integrity, runtime configuration, plugin artifacts, and timeout semantics.
- RFDS-003 `BaseInstrumentLibrary` inheritance remains blocked until the authoritative shared `rfds-core` implementation is available; this dev branch does not claim full RFDS-003, D2, or P1 conformance.

## 26.07 — 2026-08-08

- Added an RFDS-008 structured evidence engine (`hp34401a_dmm/evidence.py`): every public keyword call is now recorded with correlated arguments, duration, result/failure, and the literal SCPI commands/responses it caused on whichever of the three transports (VISA, RS-232, Prologix) or the simulator carried it, tagged per DMM alias, finalized into a SHA-256-hashed manifest under `results/session/rf_hp34401a/`.
- Added the `Export Diagnostic Bundle` keyword (109th public keyword) to zip the current evidence run for troubleshooting; regenerated the RFDS-002/RFDS-017 AI contract, RFDS-019 keyword inventory/protocol vectors, and HIL coverage state to include it.
- Added `docs/logging_and_evidence.md` and `guide/evidence_and_diagnostics.md` explaining how this relates to the existing `logging_utils.py` production logs and the `tests/hil/`/`tests/conformance/` conformance suites.
- Added `schemas/evidence/*.schema.json` and `scripts/validate_evidence.{py,sh,bat,ps1}` (recomputes evidence-manifest hashes and JSONL sequence integrity).
- Added `tests/evidence/test_evidence.py`.
- Does not change SCPI behavior, measurement logic, or any existing public keyword's signature or return value.

## 26.06 — 2026-07-31

- Fixed RFDS real-hardware all-API bookkeeping so executed public keywords are captured by an explicit file-backed Robot listener.
- Registered disabled fixture profiles as EXCLUDED during suite setup, before test execution.
- Changed disabled profile test cases to terminate as successful profile declarations after exclusions are recorded.
- Split coverage report generation from acceptance assertion so the summary is always logged before a teardown failure.
- Added regression validation for the listener, shared state file, launchers, and 108-keyword inventory.

## 26.05 — 2026-07-31

- Fixed lowercase command-line Boolean handling in the all-public-API real-hardware Robot suite.
- Added fail-closed normalization for `true/false`, `yes/no`, `on/off`, and `1/0`.
- Normalized every HIL profile flag before Robot `IF` expressions and Boolean assertions.
- Updated PowerShell and Linux HIL runners to emit canonical `True`/`False`.
- Prevented suite teardown from reporting all 108 APIs as `NOT RUN` when preflight fails before coverage starts.
- Preserved the complete 108-keyword public API without signature changes.

## 26.04 — 2026-07-30

- Added RFDS-002 v1.1 canonical lifecycle and conditional keyword groups.
- Added RFDS-013 capability discovery, RFDS-014 JSON configuration, and RFDS-015 plugin metadata.
- Added structured RFDS-007 errors and explicit raw-I/O authorization.
- Expanded synchronized API/AI/conformance artifacts to 108 public keywords.
- Added all-public-API real-hardware Robot verification with explicit safety profiles and evidence.
- Preserved all v26.03 compatibility keywords and matrix-orchestration methods.

## 26.03 — 2026-07-24

- Added RFDS-019 v1.1 public-call and protocol-conformance structure.
- Added complete 69-keyword inventory and one primary vector per exported keyword.
- Added exact SCPI/transport oracles for 50 device-facing keywords and raw inbound-response capture.
- Added timeout, malformed-response, SCPI-error, calibration-blocking, and recovery vectors.
- Added timestamped Robot runners and machine-readable conformance evidence generation.
- Added conformance documentation, lifecycle gate reviews, tests, traceability, and release-candidate status.
- Preserved the 69-keyword public Robot interface and RFDS-017 interface hash.

## 26.02 — 2026-07-21

- Added the transport-neutral `Connect DMM` and `Disconnect DMM` project-standard keywords while preserving every v26.01 public keyword.
- Added `Get Driver Metadata` and `Get Driver Capabilities` for runtime discovery and multi-driver planning.
- Integrated non-keyword Python compatibility methods used by legacy orchestration libraries, including `connect_to_dmm`, `disconnect`, and `close_connection`.
- Replaced the variadic strict stable-resistance signature with an explicit Robot signature.
- Added the canonical RFDS-017 v3.0 `ai/ai_contract.yaml` covering all public keywords exactly once.
- Added `ai/ai_contract.lock`, a SHA-256 lock over the normalized public keyword surface.
- Added contract validation and CI enforcement for signatures, states, error references, enums, verification oracles, and lock staleness.
- Added an RFDS-018 `system_ai_contract.yaml` bench template with conservative `UNKNOWN` values for site-specific topology and limits.
- Added AI-contract and bench-integration documentation, tests, release records, and traceability.
- Updated versioning, Libdoc, MkDocs, packaging, and release scripts for v26.02.

## 26.01 — 2026-07-18

- Added explicit SUITE-scoped Robot Framework library.
- Added named VISA, serial, and deterministic simulated sessions.
- Added all principal 34401A measurement modes and BUS-trigger support.
- Added strict overload and invalid-reading rejection.
- Added stable-resistance strict and non-strict keywords.
- Added metadata dictionaries, assertions, health, recovery, terminal, and error keywords.
- Added 12 examples, scripts, guides, tests, Libdoc generation, CI, and GitHub Pages sources.
- Incorporated reviewed core driver version 1.2.8 without duplicating SCPI logic.
