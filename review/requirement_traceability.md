# Requirement traceability — 26.07 baseline / Unreleased remediation

Status meanings: **PASS** = implementation plus current automated/static evidence where applicable; **PENDING** = required execution/evidence not yet produced; **OPEN DEVIATION** = known requirement gap documented in `api/deviations.yaml`.

| Requirement | Implementation | Verification | Current status |
|---|---|---|---|
| RFDS-001 stable identity/class | `version.py`, `pyproject.toml`, current release manifest | version-derived release builder; current metadata checks | PASS for D0 identity; release integrity pending freeze |
| RFDS-001 canonical lifecycle | active `library.py` facade + inherited 26.07 keywords | Python canonical API tests; Robot/HIL | Software verification in active CI; real HIL PENDING |
| RFDS-001 representative physical validation | `tests/hil/verify_all_public_api_real_hardware.robot` | exact-commit HIL | **OPEN HP34401A-DEV-003 / PENDING** |
| RFDS-002 explicit public API | decorators; `api/public_api.yaml` | runtime effective-surface AI/API validator | PASS static, 109-keyword authority |
| RFDS-002 universal lifecycle/identity/timeout keywords | corrected facade + inherited API | current unit/Robot tests | PASS subject to current CI completion |
| RFDS-002 finite positive public communication timeouts | `converters.as_seconds`; core facade timeout setter | zero/negative/NaN/inf regression tests | PASS software |
| RFDS-002 no silent simulation fallback | canonical `Connect`; package defaults | runtime configuration tests | PASS software |
| RFDS-002 compatibility aliases | inherited DMM-specific keywords; `api/compatibility.yaml` | effective Robot surface + compatibility tests | PASS static/software |
| RFDS-003 mandatory shared-core dependency | `pyproject.toml`, `requirements.txt`, plugin environment check | packaging regression | **CLOSED HP34401A-DEV-001** |
| RFDS-003 runtime core-version reporting | driver info/metadata, plugin, evidence environment | source/runtime metadata tests | **CLOSED HP34401A-DEV-005** |
| RFDS-003 `BaseInstrumentLibrary` inheritance/orchestration | not yet integrated | authoritative shared-core contract suite required | **OPEN HP34401A-DEV-004 / release blocker** |
| RFDS-003 concrete-driver coverage >=80% | active adapter + embedded core | CI `pytest --cov=rf_hp34401a --cov=hp34401a_dmm --cov-fail-under=80` | PENDING final green CI |
| RFDS-004 transport behavior | reviewed VISA/serial/fake core; active public core facade | core tests, RFDS-019 vectors, HIL | legacy behavior covered; **OPEN HP34401A-DEV-002** for v2 canonical transport migration |
| RFDS-005 package layout | flat package, history/review/examples/scripts/guide/docs/release | release-builder structural checks | PASS structure; final release package PENDING |
| RFDS-005 >=10 examples | 13 numbered examples + index/runners | offline Robot examples | PASS structure; current CI rerun pending |
| RFDS-005 README/Pages/guide | README, `docs/`, `guide/`, root Pages workflow | strict MkDocs; CI/Pages | Source synchronized; final build PENDING current CI |
| RFDS-006 coding/public-boundary style | active facades + preserved reviewed implementation | unit/static review | PASS with remaining GUI service-gate risk tracked separately |
| RFDS-007 structured public errors | `exceptions.py`, converters, `_execute`, evidence `error_code` | exception/failure-path tests | PASS software; public assertion parameter overrides still require final regression check |
| RFDS-008 fail-closed evidence | `hp34401a_dmm/evidence.py` | evidence unit/regression + validator | PASS implementation; current CI rerun pending |
| RFDS-008 simulation honesty | execution mode updated from actual transport | regression test | PASS software |
| RFDS-009 layered testing | unit/core/evidence/plugin/Robot/conformance/HIL trees | root CI + manual HIL workflow | Automated layers active; physical HIL PENDING |
| RFDS-010 review | deep review, v26.07 retrospective review, Unreleased review/history | review checklist/manual review | PASS record for remediation planning; production approval not claimed |
| RFDS-012 GUI integration metadata | public API/capability/configuration/plugin models | static model/plugin validation | Implemented; GUI raw-service authorization still to close before P1 |
| RFDS-013 capability model | `capabilities.py`, `capability/capability_model.yaml` | actual Robot export binding validation | PASS static/software |
| RFDS-014 schema validation | Draft 2020-12 `jsonschema` validator | negative/enum/required-field tests | PASS software |
| RFDS-014 schema lock | structured JSON lock + SHA-256 verification | tamper/parity tests | PASS software |
| RFDS-014 effective runtime policy | active facade applies timeout/retry/safety/logging/simulation/terminal policy | runtime configuration tests | PASS software |
| RFDS-014 migration honesty | exact schema 1.0.0 only; no implicit migration engine | invalid-version validation + docs | PASS current-version behavior |
| RFDS-015 plugin entry point | one `rfds.drivers` entry point, side-effect-free provider | source plugin tests + installed-wheel validator | Source PASS; installed-wheel CI PENDING |
| RFDS-017 AI contract | `ai/hp34401a_ai_contract.yaml` + lock | effective inherited Robot-surface validator | PASS static on Linux CI after facade migration |
| RFDS-018 integration | bench template | template review | TEMPLATE only; deployed bench facts PENDING/site-owned |
| RFDS-019 inventory/vector coverage | inventory/vectors/exclusions + runtime validator | effective inherited surface comparison | PASS static on Linux CI, 109/109 |
| RFDS-019 official Robot protocol execution | conformance runner | active CI | PENDING later CI stage/current final run |
| RFDS-019 real hardware execution | manual HIL workflow/runner | physical bench | PENDING; not claimed |
| Generated docs are reproducible | `site/` ignored; root Pages workflow | `mkdocs build --strict` | Source policy PASS; current CI PENDING |
| Release manifest/SBOM/provenance/checksums current | `release/` candidate records + release builder | frozen-commit build | Metadata marked remediation/pending; final integrity PENDING |
| Provenance exact source revision | `scripts/build_release.py` resolves `git rev-parse HEAD` | release build | PENDING frozen candidate build |
| D2/P1 production qualification | real HIL + complete RFDS-003 + release evidence | physical/release gates | **NOT CLAIMED / BLOCKED** |
