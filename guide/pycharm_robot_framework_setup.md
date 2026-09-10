# PyCharm and Robot Framework setup

## 1. Install Python

Use Python 3.10–3.13. Python 3.13 is the preferred current development target.

Windows:

```powershell
py -3.13 --version
```

Linux:

```bash
python3 --version
```

## 2. Open the driver project

For an extracted release package, open the fixed internal folder:

```text
rf_hp34401a/
```

It is the directory containing `pyproject.toml`, `rf_hp34401a/`, `hp34401a_dmm/`, `examples/`, `tests/`, and `scripts/`.

For the monorepo, either open the repository root and mark `rf_hp34401a` as the working/content root for this driver, or open the `rf_hp34401a` subdirectory directly.

## 3. Provide the authoritative RFDS shared core

The driver requires:

```text
rfds-core>=1.0,<2.0
```

The authoritative package must be available to the selected Python package index/environment before a normal dependency-resolving installation can succeed. Do not create a local `rfds_core` compatibility shim inside this driver.

## 4. Create the virtual environment

In PyCharm use **Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter → Virtualenv** and create `.venv` inside the driver directory.

Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,hardware]"
```

Linux:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e '.[dev,hardware]'
```

A normal install resolves mandatory Robot Framework, `rfds-core`, and `jsonschema`; the `hardware` extra adds PyVISA and pyserial.

For source-only remediation work on a machine where the authoritative shared core is deliberately unavailable, CI uses `pip install -e . --no-deps` **after** installing all other test dependencies explicitly. That mode is not a production installation and leaves the RFDS shared-core release gate intentionally blocked.

## 5. Configure PyCharm

Select the project `.venv` interpreter. Mark the driver directory as a Sources/Content Root if PyCharm has opened the whole monorepo.

Install a maintained Robot Framework language-server/plugin from **Settings → Plugins**. After restart, verify `.robot` files have syntax highlighting, keyword completion, and navigation.

## 6. Create a Robot run configuration

Create a Python run configuration:

- **Module name:** `robot`
- **Working directory:** the `rf_hp34401a` driver root
- **Interpreter:** project `.venv`
- **Parameters:** for example:

```text
--outputdir results examples/02_dc_voltage_limits.robot
```

Real VISA/GPIB example:

```text
--variable VISA_RESOURCE:GPIB0::22::INSTR examples/12_visa_gpib_connection.robot
```

Serial example on Windows:

```text
--variable SERIAL_PORT:COM3 examples/11_rs232_connection.robot
```

## 7. Start with offline validation

Before connecting hardware, run:

```powershell
python scripts/validate_ai_contract.py
python scripts/validate_call_protocol_conformance.py
python -m pytest
python -m robot --exclude hardware --outputdir results/examples examples
```

Then inspect `results/log.html` and `results/report.html` for Robot runs.

## 8. Debug library/core code

The active Robot facade is:

```text
rf_hp34401a/library.py
```

The preserved mature 26.07 keyword implementation is:

```text
rf_hp34401a/legacy_library.py
```

The active core facade is `hp34401a_dmm/driver.py`; the reviewed 1.2.8 implementation is in `hp34401a_dmm/legacy_driver.py`.

For cross-cutting RFDS behavior, place breakpoints in the active facade. For measurement/SCPI sequencing, follow the call into the legacy implementation/core transport rather than adding a second protocol path.

## 9. Hardware setup

For VISA/GPIB, install a vendor VISA runtime (for example the approved site Keysight/NI implementation), verify the instrument in the vendor connection utility, and then use `List VISA Resources` or the hardware examples.

For RS-232, verify the instrument-side baud/parity/data-bit/stop-bit settings and close any other application holding the COM/tty device.

Use the dedicated HIL guide and explicit fixture/safety profiles before running all-public-API hardware qualification.

## Troubleshooting

- **`No matching distribution found for rfds-core`:** the authoritative shared-core package/index is not available. Source-only CI can still run with `--no-deps`, but release qualification remains blocked.
- **Library not found:** verify PyCharm is using the project `.venv` and the working directory is the driver root.
- **`jsonschema` missing:** reinstall the current package/runtime dependencies; RFDS-014 validation requires it.
- **PyVISA backend missing:** install the approved VISA runtime plus `.[visa]` or `.[hardware]`.
- **GPIB resource absent:** verify adapter/instrument addressing in the vendor utility before changing driver code.
- **COM access denied:** close terminals/vendor tools and verify OS device assignment.
- **Keyword not recognized:** re-index/invalidate PyCharm caches after selecting the correct interpreter and confirm Libdoc generation succeeds.
- **Schema lock mismatch:** do not edit `schema.json` alone; update root and packaged authorities together and regenerate the reviewed SHA-256 lock.
