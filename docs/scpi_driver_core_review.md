# scpi-driver-core conformance review

## Summary

This driver's `pyproject.toml` previously declared a hard runtime dependency on
`rfds-core>=1.0,<2.0` — a package that does not exist anywhere: no PyPI
release, no GitHub repository under this account or any other. Its own
changelog (`history/UNRELEASED_2026-08-15_rfds_core_packaging.md`) documents
that the intended base-class migration ("RFDS-003") never happened because
"the authoritative rfds-core implementation is not contained in this
repository." In practice this meant:

- `pip install -e .` could never resolve; every install path in CI used
  `pip install -e . --no-deps` to route around it.
- `Hp34401APluginProvider.validate_environment()` unconditionally reported
  `FAIL` for the `rfds-core` check on every real installation.
- `Get Driver Information`/`Get Driver Metadata` always reported
  `rfds_core_runtime_version: "NOT_INSTALLED"`.
- A dedicated CI job (`rfds-core-release-gate`) existed solely to assert a
  package that could never be installed, blocking release qualification
  by construction.

This driver is built on `ami3go/scpi-driver-core` instead — a real, private,
pre-release (`0.1.0.dev0`) package providing framework-independent SCPI/
IEEE-488.2 transport infrastructure. This document records what was migrated
onto it, what deliberately was not, and what remains open.

## What migrated

Per scpi-driver-core's own `CONTRIBUTING.md` design rules ("keep
manufacturer/model-specific semantics in concrete driver packages; core
provides primitives, not instrument semantics"), the migration is scoped to
the transport/protocol boundary:

| Before | After |
|---|---|
| `hp34401a_dmm/serial_transport.py`: hand-rolled `pyserial.Serial` open/read/write | Backed by `scpi_driver_core.transport.serial.SerialTransport` |
| `hp34401a_dmm/visa_transport.py`: hand-rolled `pyvisa` open/read/write | Backed by `scpi_driver_core.transport.visa.VisaTransport` (GPIB, USBTMC, TCPIP INSTR/SOCKET, ASRL — resource-class agnostic) |
| `hp34401a_dmm/transports.py::BaseTransport`: hand-rolled locking, terminator framing | `scpi_driver_core.scpi.client.ScpiClient` + `ScpiTextCodec` own locking, operation-ID correlation, and terminator framing; `BaseTransport` now only owns the one-outstanding-query rule and per-transport device-clear dispatch |
| `hp34401a_dmm/transports.py::FakeTransport`: hand-rolled command→reply dict lookup | Backed by `scpi_driver_core.simulation.scripted.ScriptedScpiTransport`, with its exact prior public surface (`responses`, `error_queue`, `history`, `timeout_on`, ...) preserved so none of the ~20 dependent test files needed to change |
| `pyproject.toml` / `requirements.txt`: `rfds-core>=1.0,<2.0` | `scpi-driver-core @ git+https://github.com/ami3go/scpi-driver-core.git@main` (see "Known limitation" below) |
| `rf_hp34401a/plugin.py::_rfds_core_check` | `_scpi_driver_core_check`, resolving the real `scpi_driver_core` import/distribution |
| `hp34401a_dmm/evidence.py`, `rf_hp34401a/runtime_library.py` | Resolve `scpi-driver-core`'s installed version instead of the fictional `rfds-core`. Field/key names (`rfds_core_version`, `rfds_core_runtime_version`) are kept as-is for schema/public-API compatibility — only what they resolve changed. A rename is a reasonable follow-up for a future major version. |

## What deliberately did not migrate, and why

- **`rf_hp34401a/sessions.py`** (`SessionManager`/`DmmSession`, alias
  validation, active-session tracking). This is Robot-Framework-facing
  bookkeeping with its own alias contract
  (`^[A-Za-z][A-Za-z0-9_.-]{0,63}$`, reserved words) that is exercised by the
  public API/conformance suites. scpi-driver-core's own `SessionRegistry` has
  different, looser alias rules (bare strip+casefold); swapping it would risk
  silently changing the documented public API contract, which was not asked
  for.
- **`hp34401a_dmm/legacy_driver.py`'s measurement/config/parsing logic**,
  `rf_hp34401a/capabilities.py`, `converters.py`, `evidence.py`, the Robot
  keyword library itself — all instrument-specific business logic, which is
  exactly what scpi-driver-core's design rules say must not live in the core.
- **`PrologixUsbGpibTransport`** — already an intentional `NotImplementedError`
  stub in both the old and new code; scpi-driver-core has no Prologix backend
  either.

## Known limitations / deviations

1. **No PyPI release for scpi-driver-core.** It is `0.1.0.dev0`, private, with
   no tags. The dependency is pinned to `@main` via a git URL. Installing this
   driver requires git access (and, for a private-repo clone over HTTPS,
   credentials) to `ami3go/scpi-driver-core`. CI needs a token with access to
   that repo to install it; this was not wired up as part of this migration
   and should be added as a repo secret before CI is expected to pass.
2. **`SerialTransport` does not expose pyserial's `dsrdtr` hardware
   flow-control flag.** The 34401A's RS-232 config
   (`SerialRs232Config.use_dtr_dsr`) is accepted but not applied, because
   `scpi_driver_core.transport.serial.SerialTransport` has no constructor
   parameter or public accessor for it (only `dtr`/`rts` output-line control,
   a different concept). This is called out here rather than worked around by
   reaching into scpi-driver-core's private `_resource` attribute. Worth
   raising upstream if 34401A serial hardware testing shows it's load-bearing.
3. **The RFDS-019 driver-call-protocol conformance harness
   (`tests/conformance/support/ConformanceHarness.py`) had a pre-existing bug**
   unrelated to this migration: it read/restored
   `Hp34401A.__dict__["from_visa_gpib"]`/`["from_serial"]` directly, but those
   classmethods are defined on `legacy_driver.Hp34401A` and inherited by the
   exported `hp34401a_dmm.Hp34401A` (`driver.Hp34401A`), so they are not in
   the subclass's own `__dict__`. This made **all 113** conformance vectors
   fail immediately with `KeyError: 'from_visa_gpib'`, both before and after
   this migration (verified against the unmodified `dev` branch). Fixed here
   with a sentinel-based save/restore that works regardless of which class in
   the MRO owns the attribute.
4. **With that harness bug fixed, 4 conformance vectors still fail** — and
   fail identically on the unmigrated `dev` branch, confirming they are
   pre-existing driver bugs, not regressions from this migration:
   - `HP34401A-KW-057 Get Driver Metadata`: fails with "DMM alias 'dut' is not
     open" in a vector sequence where it's expected to succeed.
   - `HP34401A-KW-091 Recover DMM`: return dictionary is missing a `state`
     key the vector expects.
   - `HP34401A-ERR-001 Query DMM Command`: after a timeout on `*IDN?`, the
     recovery step (`Identify DMM`) fails with "Query while previous response
     unread" — the one-outstanding-query flag is not cleared between the
     failed raw query and the recovery attempt in this code path.
   - `HP34401A-ERR-002 Measure DC Voltage`: a malformed `READ?` reply is
     reported as `DriverProtocolError` ("Partial/garbled reading response"),
     not the `*parse*`-matching error the vector expects.

   These are real, pre-existing product bugs surfaced by fixing the harness,
   not something this transport migration should silently fix — they're
   business-logic issues in `legacy_library.py`/`runtime_library.py`, outside
   this migration's scope. Recommend a follow-up issue.
5. **CI's `scripts/validate_call_protocol_conformance.py` is static-only**
   (keyword name/count/shape validation) and does not catch the above; the
   dynamic check is `scripts/run_call_protocol_conformance.py` /
   `tests/conformance/driver_call_protocol_conformance.robot`, which was not
   part of the CI gate. Worth adding.

## Real-hardware check

A genuine HP 34401A was available on the development machine, bridged over
USBTMC through a XyphroLabs GPIB-USB adapter (USB VID:PID `03eb:2065`,
enumerating as an "Atmel LUFA Test and Measurement Demo" — the adapter's
firmware, not the instrument). A direct, byte-level `*IDN?` probe against the
kernel's `/dev/usbtmc0` character device returned:

```
HEWLETT-PACKARD,34401A,0,11-5-2
```

confirming a real, responsive 34401A. Routing this through the migrated
`VisaGpibTransport` (i.e., through `pyvisa`/`pyvisa-py`) was attempted but not
completed: `pyvisa-py`'s USB backend uses `libusb`/`pyusb`, which requires the
kernel's `usbtmc` driver to release the interface first. Unbinding it
(`/sys/bus/usb/drivers/usbtmc/unbind`) failed with `Permission denied (os
error 13)` even under `sudo` in this sandboxed environment — a container-level
restriction (no `CAP_SYS_ADMIN` for USB driver rebinding), not a credentials
problem. This is an environment limitation, not a defect in the migration:
`scpi_driver_core.transport.visa.VisaTransport` itself places no additional
constraint beyond what `pyvisa` requires. Re-running the real-hardware HIL
suite (`tests/hil/verify_all_public_api_real_hardware.robot`) against this
instrument from a machine (or container) with USB driver-rebind capability is
a reasonable follow-up — see `guide/real_hardware_host_setup.md` (repo root)
for exactly how to do that, including the udev-rule workaround for this
specific kernel-driver-vs-libusb conflict.

## What was also fixed along the way (pre-existing, unrelated to scpi-driver-core)

- `tests/api/mandatory_api.robot` and `tests/api/return_type.robot`: two Robot
  syntax bugs (`Should Be True    Is Connected    alias=dut` evaluates the
  literal text `Is Connected` as a Python expression instead of calling the
  keyword and checking its result; a missing `Library Collections` import).
  These made the entire `tests/api` suite fail unconditionally regardless of
  transport.
- `examples/13_canonical_lifecycle_capability_configuration.robot`: asserted
  a stale `package_version` (`26.06` vs. the actual `26.07`).

## Verification performed

- `pytest`: 169 passed, 2 skipped (pre-existing, unrelated skips).
- `robot tests/robot`: 33/33 passed.
- `robot tests/api`: 5/5 passed (after the two pre-existing bug fixes above).
- `robot tests/capability`, `tests/plugin`, `tests/configuration`: all passed.
- `robot --exclude hardware examples`: 12/12 passed (after the version fix).
- `scripts/validate_ai_contract.py`, `scripts/validate_call_protocol_conformance.py`:
  both PASSED (static checks, unaffected by the runtime transport swap).
- `scripts/run_call_protocol_conformance.py` (dynamic RFDS-019 suite): 4
  pre-existing failures remain, documented above; confirmed identical on the
  unmodified `dev` branch once the harness bug is fixed there too.
