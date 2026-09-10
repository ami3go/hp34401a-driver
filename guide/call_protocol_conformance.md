# Running RFDS-019 conformance

## Prerequisites

Install the development dependencies into the same uv environment used by Robot Framework:

```powershell
uv pip install -e ".[dev,hardware]"
```

Confirm the interpreter:

```powershell
python -c "import sys, robot; print(sys.executable); print(robot.__version__)"
```

## Static preflight

```powershell
python scripts/validate_ai_contract.py
python scripts/validate_call_protocol_conformance.py
```

The second command fails when a public keyword is absent from the inventory, lacks a primary vector, has a stale driver-method mapping, or has no outbound oracle despite being device-facing.

## Full Robot execution

```powershell
.\scripts\run_call_protocol_conformance.ps1
```

An alternate result root can be selected:

```powershell
.\scripts\run_call_protocol_conformance.ps1 -OutputRoot C:\TestEvidence\HP34401A
```

The script preserves Robot Framework's exit code and prints the timestamped evidence directory.

## Reviewing evidence

Open `report.html` for suite status and `log.html` for individual keyword execution. Review these machine-readable files when investigating a failure:

- `keyword_inventory.json` — live exported interface and execution state;
- `keyword_coverage.csv` — one row per public keyword;
- `protocol_vector_results.json` — vector-level result, return type, and observed traffic;
- `outbound_trace.log` — serialized SCPI operations grouped by vector;
- `inbound_trace.log` — raw responses captured before parsing;
- `exclusions.json` — declared real-device prerequisites and approved software alternatives.

## Real hardware

Do not change the unattended simulator profile into a real-device profile by editing addresses in the vector file. Use `tests/hil/` and a completed RFDS-018 `system_ai_contract.yaml` that identifies the resource, fixture, allowed operations, startup/shutdown sequence, and safety limits. VISA traces or serial traces should be retained with the HIL evidence.
