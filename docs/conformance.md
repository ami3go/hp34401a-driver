# RFDS-019 call and protocol conformance

Release 26.06 adds the project-standard RFDS-019 v1.1 conformance suite. The suite verifies the complete path from a Robot Framework keyword call to the serialized 34401A SCPI operation and back to the Robot-compatible result.

## Artifacts

```text
tests/conformance/
├── driver_call_protocol_conformance.robot
├── resources/
│   ├── conformance_keywords.resource
│   └── conformance_variables.resource
├── data/
│   ├── keyword_inventory.yaml
│   ├── protocol_vectors.yaml
│   └── exclusions.yaml
├── expected/response_schemas/
└── support/ConformanceHarness.py
```

The inventory contains all 109 exported Robot keywords. Each keyword has one primary callability vector. Fifty device-facing keywords have outbound SCPI or transport-boundary oracles. Four additional vectors verify timeout handling, malformed measurement responses, SCPI error reporting, calibration-command blocking, and post-failure recovery.

## Observation point

The unattended profile uses `hp34401a_dmm.FakeTransport`. It records writes, queries, raw responses, and transport clears at the same line-oriented SCPI boundary used by the production driver. Internal adapter-method mocking is not used as the protocol oracle.

## Run

```powershell
python scripts/validate_call_protocol_conformance.py
python scripts/run_call_protocol_conformance.py
```

PowerShell, CMD, and Linux wrappers are also provided:

```powershell
.\scripts\run_call_protocol_conformance.ps1
```

```cmd
scripts\run_call_protocol_conformance.bat
```

```bash
./scripts/run_call_protocol_conformance.sh
```

Each execution creates a UTC timestamped directory under:

```text
results/call_protocol_conformance/hp34401a/<timestamp>/
```

It contains Robot `output.xml`, `log.html`, and `report.html`, plus inventory, coverage, protocol result, outbound trace, inbound trace, environment, identity, exclusions, and Markdown summary files.

## Acceptance boundary

The simulator profile verifies public callability, exact protocol construction, deterministic raw responses, parser behavior, documented failures, and recovery. It does not prove physical measurement accuracy or vendor VISA/RS-232 behavior. Representative real-device confirmation remains an opt-in HIL gate and must use verified RFDS-018 bench data.
