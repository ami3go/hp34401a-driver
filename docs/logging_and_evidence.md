# Logging and evidence (RFDS-008)

`rf_hp34401a` records public Robot keyword calls as structured evidence so failures can be diagnosed after the original bench session. The implementation is `hp34401a_dmm/evidence.py`.

## Evidence systems and authority

| System | Question it answers | Scope |
|---|---|---|
| `hp34401a_dmm/logging_utils.py` | What did long-running measurement logging record? | Production/station logging, opt-in |
| `tests/hil/verify_all_public_api_real_hardware.robot` | Was the public API exercised on representative real hardware? | Formal HIL/RFDS qualification |
| `tests/conformance/driver_call_protocol_conformance.robot` | Does each keyword produce its reviewed protocol behavior? | RFDS-019 protocol-vector conformance |
| `hp34401a_dmm/evidence.py` | What happened during this particular Robot/library session? | Per-session diagnostic evidence, on by default |

These systems are complementary. Per-session evidence does not promote simulation to hardware qualification and does not replace RFDS-019/HIL.

## Evidence run layout

One `Hp34401ALibrary` instance produces one evidence run, normally finalized when the last DMM session is disconnected. Listener/library cleanup also finalizes an unfinished run when an explicit disconnect was omitted.

```text
results/session/rf_hp34401a/<UTC timestamp>_<run_id>/
├── run_summary.json
├── run_summary.md
├── environment.json
├── device_identity.json
├── evidence_manifest.json
├── events/
│   ├── events.jsonl
│   ├── operations.jsonl
│   └── errors.jsonl
├── protocol/
│   ├── exchanges.jsonl
│   ├── outbound_trace.log
│   └── inbound_trace.log
└── integrity/
    └── checksums.sha256
```

`environment.json` records Python, Robot Framework, driver/core versions, effective `rfds-core` distribution version when installed, sanitized host token, and execution mode.

`device_identity.json` records identity per alias. Protocol exchanges include transport and alias so multi-session evidence remains attributable.

## Fail-closed run status

Run status is accumulated across the whole evidence run.

- Any recorded operation failure marks the run failed.
- Later successful cleanup cannot change a failed run back to `PASS`.
- Cleanup errors are recorded and force `FAIL`.
- A successful run finalizes `PASS` only when no earlier error was recorded.

This behavior has dedicated regression coverage for “failed keyword followed by successful disconnect”.

## Simulation honesty

The evidence run begins with execution mode `UNKNOWN` because library construction alone does not prove how the driver will be used.

When a session identity is recorded:

- simulated transport sets run execution mode to `SIMULATION`;
- real VISA/serial transport sets it to `REAL_HARDWARE` when the mode was still unknown.

Each device and protocol record still carries its own transport/alias. Simulation evidence is never accepted as D2/P1 physical evidence.

## Error records

`events/errors.jsonl` records:

- category;
- public structured `error_code` when the exception exposes one;
- exception type/message;
- correlation and operation IDs;
- alias/capability;
- traceback;
- recoverability state when known.

Categories map the public/core hierarchy to stable RFDS-oriented classes such as validation, configuration, state, timeout, connection, protocol, cleanup, unsupported, safety, device, or unknown. The public error code remains the more specific machine-readable identifier when available.

## Correlation

Operations, events and protocol traffic carry `operation_id` and `correlation_id`. Nested calls retain their parent correlation so one user-visible keyword can be followed through internal calls and literal SCPI traffic.

## Enabling/disabling evidence

Evidence is enabled by default:

```robotframework
Library    rf_hp34401a.Hp34401ALibrary
```

Disable only explicitly:

```robotframework
Library    rf_hp34401a.Hp34401ALibrary    evidence_enabled=${FALSE}
```

With evidence disabled, normal Robot/Python errors still propagate; only the structured evidence directory is omitted.

## Diagnostic bundle export

```robotframework
${path}=    Export Diagnostic Bundle
Log    ${path}    console=True
```

The export event is written **before** the evidence manifest and ZIP snapshot are generated. No evidence file is then mutated as part of that export operation, so the live evidence root remains consistent with its manifest immediately after export.

The ZIP is a snapshot of the run at export time. A later operation may legitimately evolve the live run and its next manifest; final disconnect/listener cleanup regenerates the authoritative final run manifest.

## Integrity validation

```console
python scripts/validate_evidence.py results/session/rf_hp34401a/<run>/
```

The validator recomputes SHA-256 hashes, verifies JSONL structure/sequence ordering, checks manifest coverage, and requires the expected run summary for a finalized run. Regression tests also validate the live evidence root directly after diagnostic export.

## Data protection

Credential-shaped mapping keys such as passwords, tokens, API keys, secrets and authentication fields are redacted before structured operation arguments are written. Do not use this as a substitute for bench-level data-classification/retention policy; RFDS evidence may still contain instrument identity, resources, commands, readings, and troubleshooting information.

## Deliberate limits

- Cryptographic signing and long-term archival/retention policy belong to the release/bench evidence system, not this single driver module.
- HIL qualification must still be run on real hardware.
- The evidence module is driver-local until the authoritative shared `rfds-core` provides a reviewed common evidence implementation suitable for migration.
