# Hardware test setup

HIL tests are disabled by default. Before running them:

1. Connect a known safe voltage or resistance standard.
2. Verify front/rear terminals and current-terminal wiring.
3. Set `VISA_RESOURCE` or `SERIAL_PORT` explicitly.
4. Set safe lower and upper limits.
5. Run the appropriate tagged suite through `scripts/run_hil_tests`.
6. Preserve `output.xml`, `log.html`, `report.html`, Python/Robot versions, library/core versions, identity, and transport information as release evidence.

Reset and self-test are not run unless the HIL suite explicitly enables them.
