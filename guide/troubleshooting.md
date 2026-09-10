# Troubleshooting

- **Identity mismatch:** confirm that the resource points to a 34401A and not another instrument.
- **Timeout:** verify termination, serial flow control, GPIB address, and vendor connection utility operation.
- **Overload:** select a suitable range and inspect DUT wiring; the library intentionally does not return a scalar.
- **Unstable resistance:** increase settling time, NPLC, window size, or stability thresholds based on fixture behavior.
- **Calibration command blocked:** use reviewed calibration tooling and explicitly enable calibration commands only for authorized procedures.
- **BUS trigger failure:** configure a measurement before triggering and use the complete safe sequence.

## `Evaluating expression 'true' failed`

This occurred in v26.04 when Robot command-line variables were supplied as lowercase strings, for example `--variable HIL_ENABLED:true`. Release 26.05 normalizes all HIL Boolean variables before expression evaluation. Reinstall the package and rerun the packaged suite. Both `true` and `True` are accepted in v26.05.

## Real-hardware suite reports executed APIs as NOT RUN

Release 26.05 could complete real VISA calls successfully but lose nested keyword evidence before suite teardown. Release 26.06 registers an explicit file-backed Robot listener in `run_all_api_hil.ps1` and `run_all_api_hil.sh`. Reinstall the package and run the packaged launcher; do not copy only the `.robot` file without its `support/` directory and launcher. Disabled fixture profiles are recorded as `EXCLUDED`, while executed APIs are recorded as `PASS` or `FAIL`.
