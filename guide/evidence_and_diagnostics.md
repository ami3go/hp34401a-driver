# Guide: diagnosing a failed DMM session

A task-oriented companion to `docs/logging_and_evidence.md` (which describes the RFDS-008
evidence system itself, and how it relates to the driver's other evidence — `logging_utils.py`
production logs, the `tests/hil/` real-hardware conformance suite, and the
`tests/conformance/` protocol-vector suite).

## "A suite failed and I wasn't watching it run — what happened?"

1. Ask whoever ran it for the evidence run directory (`results/session/rf_hp34401a/<run>/`), or
   for the zip from `Export Diagnostic Bundle` if it was called (add it to suite teardown — see
   below — so it always is).
2. Open `run_summary.md` first — the one-paragraph version.
3. Open `events/errors.jsonl`. Each line is one exception; find the one whose `capability`
   matches the keyword Robot reported as failing.
4. Note its `operation_id`. Search `events/operations.jsonl` for that ID for the exact arguments
   passed (per-alias, since a suite may use several DMM aliases at once).
5. Search `protocol/exchanges.jsonl` for the same `operation_id` for the exact SCPI
   commands/responses that operation exchanged, and which transport (`visa_gpib`, `serial_rs232`,
   `simulation`) carried them — before assuming a SCPI bug, check whether the same command works
   over a different transport to the same instrument.

## "Make every future failure on this bench leave a diagnostic bundle automatically"

```robotframework
*** Settings ***
Library         rf_hp34401a.Hp34401ALibrary
Suite Setup     Connect    ${VISA_RESOURCE}    alias=dut
Suite Teardown  Teardown With Diagnostics

*** Keywords ***
Teardown With Diagnostics
    ${bundle}=    Export Diagnostic Bundle
    Log    Diagnostic bundle: ${bundle}    console=True
    Disconnect All
```

## "Which transport actually carried a given SCPI command?"

Every line in `protocol/exchanges.jsonl` has a `"transport"` field
(`visa_gpib`/`serial_rs232`/`simulation`) and a `"session_alias"` field. This driver can reach
the same instrument three different physical ways, so this is often the fastest way to tell
"the SCPI command was wrong" apart from "this transport dropped/mangled it."

## "I just want to turn this off"

```robotframework
Library    rf_hp34401a.Hp34401ALibrary    evidence_enabled=${FALSE}
```

Nothing gets written to `results/`. Exceptions still reach Robot's own log and the standard
Python logger.

## Validating that a run directory wasn't tampered with or truncated

```console
python scripts/validate_evidence.py results/session/rf_hp34401a/<run>/
```

Reports any hash mismatch, missing file, or JSONL stream with a gap or duplicate in its
`sequence` numbers. Exit code is non-zero on any finding.
