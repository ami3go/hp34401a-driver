# Installation

## Runtime requirements

`rf_hp34401a` requires:

- Python 3.10–3.13;
- Robot Framework `>=7,<8`;
- authoritative shared `rfds-core>=1.0,<2.0`;
- `jsonschema>=4.20,<5` for RFDS-014 Draft 2020-12 configuration validation.

A normal installation must be able to resolve the authoritative `rfds-core` distribution. Do not create a local `rfds_core` compatibility package inside this driver.

## Base installation

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

If the package installer reports that `rfds-core` cannot be resolved, the shared-core release prerequisite is unavailable in the configured package source. Source-only CI can still exercise this driver with `--no-deps` after explicitly installing the remaining test dependencies, but that is not a production installation and does not close RFDS-003.

## Hardware extras

```bash
python -m pip install -e ".[visa]"    # VISA/GPIB
python -m pip install -e ".[serial]"  # RS-232
python -m pip install -e ".[hardware]" # both
```

PyVISA is an API layer. Install the approved compatible vendor VISA runtime separately for physical GPIB/USB/VXI-11 access.

For RS-232, verify the instrument front-panel baud/parity/data-bit settings and the physical cable/handshake configuration before treating a software timeout as a driver defect.

## Development installation

```bash
python -m pip install -e ".[dev,hardware]"
```

Then run the software gates from the driver root:

```bash
python scripts/validate_ai_contract.py
python scripts/validate_call_protocol_conformance.py
python scripts/generate_conformance_data.py --check
python -m pytest
python -m robot --exclude hardware --outputdir results/examples examples
python -m mkdocs build --strict
```

The repository-root CI runs these gates on Windows/Linux and Python 3.10/3.13. The authoritative shared-core release check is a separate RFDS-003 job after software-quality validation.
