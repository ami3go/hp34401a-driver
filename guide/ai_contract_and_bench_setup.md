# AI contract and test-bench setup

## Validate the driver contract

From the project root:

```powershell
python scripts/validate_ai_contract.py
```

The command compares `ai/hp34401a_ai_contract.yaml` and `ai/hp34401a_ai_contract.lock` against the live Robot keyword names and signatures. Do not edit the lock manually after a keyword change; regenerate the contract and lock together and review the semantic changes.

## Add the driver to a test bench

RFDS-017 describes this DMM only. RFDS-018 describes the complete physical test environment.

1. Copy `examples/bench/system_ai_contract.template.yaml` to the bench repository.
2. Rename it to `system_ai_contract.yaml`.
3. Set the actual DMM VISA resource or serial port.
4. Record the physical front/rear terminal selection.
5. Describe every relay, fixture, DUT node, power source, and shared resource.
6. Replace each `UNKNOWN` with a verified value or retain `UNKNOWN` and prevent autonomous execution.
7. Define preferred measurement instruments and conflict rules.
8. Define the emergency shutdown sequence using the real source and relay keywords.
9. Link DUT requirements to driver verification objectives.
10. Record HIL evidence and approved instrument firmware.

## E-Resistor matrix integration

The HP34401A library includes `connect_to_dmm()` as a Python compatibility method for orchestration libraries that instantiate the DMM internally. A separate monkey-patch library is no longer required in v26.06.

The bench contract must still define:

- the E-Resistor driver alias and IP resource;
- both Phidget relay serial numbers;
- logical channel-to-relay routing;
- DMM terminal and fixture wiring;
- the required settling delay after resistance and relay changes;
- a rule forbidding resistance measurements while an external source energizes the selected path;
- teardown ordering: sources disabled, relays opened, DMM disconnected.

## Conservative UNKNOWN handling

An unresolved safety or topology value is not permission to guess. Treat unknown risk as high, unknown retry as never retry, unknown concurrency as one exclusive operation, and unknown idempotency as non-idempotent.
