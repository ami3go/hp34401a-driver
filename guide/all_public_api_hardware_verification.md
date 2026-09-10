# Verify every public HP34401A API on real hardware

1. Install the driver and hardware dependencies in the same uv environment used by Robot Framework.
2. Install and verify the vendor VISA runtime.
3. Confirm the 34401A resource with `python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"`.
4. Copy `tests/hil/profiles/real_hardware_all_api.template.yaml` into the bench repository, resolve every `UNKNOWN`, and obtain the required fixture approval.
5. Connect only that safe, reviewed fixture.
6. Run the default read-only profile with `scripts/run_all_api_hil.ps1`.
7. Review EXCLUDED rows and prepare each required fixture before enabling its profile.
8. Enable only the necessary `RUN_*_PROFILE` variables.
9. Use `-FailOnExclusions` for the final claimed-scope qualification.
10. Preserve the entire timestamped result directory and record instrument model, serial, firmware, transport, fixture, and calibration information.
11. Do not describe simulator or EXCLUDED results as physical validation.

See `docs/real_hardware_api_verification.md` for commands and evidence files.

The v26.06 launcher is part of the evidence mechanism: it registers the file-backed Robot listener. Direct execution of the `.robot` file without the listener is not the approved RFDS-019 run path.
