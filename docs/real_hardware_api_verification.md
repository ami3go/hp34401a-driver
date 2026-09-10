# Real-hardware all-API verification

`tests/hil/verify_all_public_api_real_hardware.robot` is the authoritative opt-in Robot suite for physical API coverage.

## Safety model

The suite is fail-closed:

- `HIL_ENABLED:True` is mandatory;
- a real `VISA_RESOURCE` is mandatory;
- no simulation fallback is permitted;
- physical measurement families are separately enabled;
- self-test, reset, raw SCPI, and serial verification require explicit opt-in;
- every public keyword receives PASS, FAIL, EXCLUDED, or NOT RUN status;
- a zero-exclusion run is required for full claimed scope.

## Run

```powershell
.\scripts\run_all_api_hil.ps1 -VisaResource "GPIB0::22::INSTR"
```

For an approved DC voltage fixture:

```powershell
.\scripts\run_all_api_hil.ps1 `
    -VisaResource "GPIB0::22::INSTR" `
    -ExtraRobotArgs @("--variable", "RUN_DC_VOLTAGE_PROFILE:True")
```

Add `-FailOnExclusions` only when all required profiles and fixtures are prepared.

## Evidence

The timestamped result directory contains Robot reports plus:

- `real_hardware_api_coverage.json`;
- `real_hardware_api_coverage.csv`;
- `real_hardware_api_summary.md`;
- `environment.json`;
- `device_identity.json`.

The reviewed profile template is `tests/hil/profiles/real_hardware_all_api.template.yaml`. Copy it into the bench repository, resolve every `UNKNOWN`, and map its approvals to the Robot variables before execution.

An EXCLUDED keyword is visible but is not hardware proof.

## Coverage listener

Use the packaged launcher rather than calling the Robot file alone. The launcher registers `tests/hil/support/RealHardwareApiListener.py` and points it to a run-local state file. The listener records each nested public driver keyword at the Robot execution boundary. Disabled fixture groups are registered as `EXCLUDED` during suite setup. This prevents successful calls or approved exclusions from being lost before teardown.
