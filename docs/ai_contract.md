# AI driver and test-bench contracts

## Single-driver contract

The canonical contract is stored in:

```text
ai/hp34401a_ai_contract.yaml
ai/hp34401a_ai_contract.lock
```

The YAML contract is a machine-first description of the HP34401A Robot library. It lists all public keywords using their exact Robot names and signatures and describes the state machine, resources, physical connection points, errors, recovery, safety, timing, verification oracles, and setup/teardown.

Validate it with:

```powershell
python scripts/validate_ai_contract.py
```

Validation fails when a keyword is missing, duplicated, has a different signature, references an unknown state/error, uses a non-closed classification, lacks a valid oracle, or no longer matches the interface-lock hash.

## Complete test-bench contract

A driver cannot know the physical bench wiring, DUT nodes, relay routes, source limits, shared USB/VISA resources, emergency workflow, or laboratory authorization rules. Those facts belong in the RFDS-018 bench contract.

Use:

```text
examples/bench/system_ai_contract.template.yaml
```

Copy it into the bench/test repository as:

```text
system_ai_contract.yaml
```

Replace every `UNKNOWN` using measured or approved bench facts. Do not auto-fill optimistic assumptions. Until all safety-relevant unknowns are resolved, an AI planner must treat the bench as not approved for autonomous hardware control.

## RFDS-019 linkage

The contract `conformance` section identifies the keyword inventory, protocol vectors, exclusions, Robot suite, runner, profile, and mandatory evidence files. RFDS-019 uses this metadata to verify declared calls; it does not use RFDS-017 as proof of vendor-manual feature completeness.
