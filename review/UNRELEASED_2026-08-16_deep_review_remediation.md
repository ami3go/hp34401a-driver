# Remediation review — 2026-08-16

**Driver:** `rf_hp34401a`  
**Branch:** `dev`  
**Public API baseline:** 26.07 / 109 keywords  
**Verdict:** SOFTWARE REMEDIATION IN VALIDATION — NOT RELEASE READY

## Review basis

This review closes or reclassifies the findings from the deep file-by-file RFDS audit. The changes intentionally preserve the reviewed 26.07 public Robot surface while correcting implementation, validation, evidence, packaging, workflow, documentation and traceability defects.

## Findings disposition

### Corrected in source

- inactive nested GitHub workflows;
- frozen v26.06 release builder;
- stale v26.04/v26.05/v26.06 current-runtime tests;
- false-PASS evidence finalization;
- diagnostic export/live-manifest integrity drift;
- listener-cleanup evidence finalization;
- incorrect simulator evidence mode;
- partial handwritten RFDS-014 validation;
- non-structured/unverified schema lock;
- effective configuration not driving runtime behavior;
- capability model self-validation;
- stale 26.06 static capability model;
- zero/NaN/infinite communication timeouts;
- raw public validation errors;
- stale release manifest/SBOM/provenance/checksums/auxiliary reports;
- plugin runtime core compatibility checking;
- runtime shared-core version reporting;
- requirements/pyproject dependency drift;
- missing v26.07 code-review record;
- adapter-only coverage gate;
- adapter access to private core transport for timeout/raw-response operations;
- cached communication health being overwritten by open-transport state;
- source generators that ignored inherited facade keywords;
- GUI raw-SCPI service operation without explicit operator authorization;
- committed generated MkDocs `site/` output;
- stale thin configuration/capability/architecture/migration/install documentation.

### Closed deviations

- `HP34401A-DEV-001` — mandatory compatible shared-core dependency declaration.
- `HP34401A-DEV-005` — runtime shared-core version reporting.

### Open external/architecture/physical items

- `HP34401A-DEV-004` — **HIGH / release blocker**: correct integration with the authoritative RFDS-003 `BaseInstrumentLibrary`. The authoritative implementation is not present in the connected repository/environment. A local imitation/fork is prohibited.
- `HP34401A-DEV-002` — RFDS-004 v2 canonical byte-transport migration remains a separately reviewed architecture change; the mature line-oriented implementation is preserved until equivalent behavior is proven.
- `HP34401A-DEV-003` — exact-commit representative real-device HIL remains pending.

## Validation strategy

Repository-root CI now separates:

1. four software-quality matrix jobs: Windows/Linux × Python 3.10/3.13;
2. a distinct RFDS-003 shared-core release-gate job after software quality.

Software quality includes:

- effective-surface RFDS-002/RFDS-017 validation;
- effective-surface RFDS-019 inventory/vector validation;
- facade-aware conformance generator check;
- HIL source-accounting checks;
- Python unit/core/evidence/plugin tests;
- >=80% combined `rf_hp34401a` + `hp34401a_dmm` line coverage;
- Robot tests;
- all non-hardware examples;
- Libdoc;
- strict MkDocs build;
- wheel/sdist build;
- isolated installed-wheel plugin entry-point/resource validation.

During remediation, CI artifacts were intentionally retained for failing pytest runs so each remaining failure could be diagnosed rather than bypassed. One such run reached 175 tests with only seven stale/version/export-regression failures; those sources were then corrected. A later artifact reduced the set to one real diagnostic-export integrity ordering failure, which was subsequently corrected at the public export boundary.

## Release gate

This review does **not** authorize a new RFDS release ZIP yet.

Release requires all of the following:

- software-quality matrix green on the final frozen commit;
- authoritative `BaseInstrumentLibrary` integration and compatible shared-core gate green;
- real HP34401A HIL from that exact commit;
- regenerated manifest/SBOM/provenance/checksums/traceability from that commit;
- final review update recording those immutable evidence identifiers.

## Conclusion

The deep-review source findings have been corrected except for explicitly documented items that depend on the external authoritative shared core, a separately reviewed RFDS-004 architecture migration, or physical hardware qualification. Those remaining items are not hidden by compatibility shims or simulator evidence.
