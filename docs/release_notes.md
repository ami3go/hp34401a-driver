# Release notes — 26.07 baseline / Unreleased remediation

The last public API baseline is **26.07** (`26.7.0`) with 109 Robot keywords. The current `dev` tree is an **unreleased remediation candidate**, not a new approved release.

## 26.07 baseline

26.07 added the RFDS-008 structured evidence engine and `Export Diagnostic Bundle`. A retrospective review on 2026-08-16 found integrity defects in the original evidence lifecycle, so the historical 26.07 source is not retroactively promoted to production-ready status.

## Unreleased corrections

The remediation corrects:

- repository-root CI, manual HIL, and Pages workflows;
- evidence run status accumulation so earlier failures cannot be hidden by successful cleanup;
- diagnostic export/manifest ordering;
- evidence finalization during listener cleanup;
- simulation-vs-real-hardware execution-mode reporting;
- RFDS-014 Draft 2020-12 schema enforcement and structured schema-lock verification;
- effective runtime application of imported timeout/retry/logging/safety/simulation/device policy;
- finite-positive public communication timeouts and structured validation errors;
- capability binding validation against the actual inherited Robot export surface;
- current 26.07 static capability metadata;
- mandatory `rfds-core>=1.0,<2.0` dependency and runtime version reporting;
- installed-wheel plugin artifact resolution;
- current release builder version derivation and provenance/checksum regeneration policy;
- stale 26.06 release metadata and generated MkDocs source-control output;
- the missing v26.07 code-review record.

## Compatibility

The correction preserves the 109-keyword 26.07 Robot surface. The mature implementation remains in `legacy_library.py` under a corrected facade, and the reviewed 1.2.8 core remains in `legacy_driver.py` under an explicit runtime-policy facade. The RFDS contract validators now inspect the effective inherited Robot surface, not just methods physically declared in one source file.

## Open release blockers

The current candidate remains D0. It must not claim D2/P1 or full RFDS-003 conformance until:

1. the authoritative shared `rfds-core` implementation is available and `Hp34401ALibrary` is correctly integrated with `BaseInstrumentLibrary`;
2. active CI passes its Python, Robot, examples, documentation, package and installed-wheel gates on the final commit;
3. RFDS-019/HIL is executed on representative real HP34401A hardware from that exact frozen commit;
4. release manifest, SBOM, provenance, checksums and traceability are regenerated from that commit.

The `release/` directory is deliberately marked remediation/pending where fresh evidence has not yet been generated. Do not interpret pending candidate files as an approved release attestation.
