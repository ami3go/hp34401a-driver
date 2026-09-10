# Public keyword reference — 26.07

The authoritative public surface contains **109** explicitly exported Robot Framework keywords.

This Markdown index is generated from `api/public_api.yaml`. Generate the full official HTML/XML Libdoc with the packaged `generate_libdoc` scripts in an environment containing Robot Framework.

## Check Communication

- Python method: `check_communication`
- Signature: `Check Communication(alias=${NONE})`
- Return: `bool`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-001`

Perform a bounded, non-destructive identity query and return ``True``.

## Clear DMM Status

- Python method: `clear_dmm_status`
- Signature: `Clear DMM Status(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-002`

Execute Clear DMM Status.

## Clear Device Errors

- Python method: `clear_device_errors`
- Signature: `Clear Device Errors(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-003`

Clear status and drain any remaining device error records.

## Close All DMMs

- Python method: `close_all_dmms`
- Signature: `Close All DMMs()`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-004`

Execute Close All DMMs.

## Close DMM

- Python method: `close_dmm`
- Signature: `Close DMM(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-005`

Execute Close DMM.

## Configure 2 Wire Resistance

- Python method: `configure_2wire_resistance`
- Signature: `Configure 2 Wire Resistance(range_value=DEF, nplc=10, autozero=ON, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-006`

Execute Configure 2 Wire Resistance.

## Configure 4 Wire Resistance

- Python method: `configure_4wire_resistance`
- Signature: `Configure 4 Wire Resistance(range_value=DEF, nplc=10, autozero=ON, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-007`

Execute Configure 4 Wire Resistance.

## Configure AC Current

- Python method: `configure_ac_current`
- Signature: `Configure AC Current(range_value=DEF, ac_filter_hz=20, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-008`

Execute Configure AC Current.

## Configure AC Voltage

- Python method: `configure_ac_voltage`
- Signature: `Configure AC Voltage(range_value=DEF, ac_filter_hz=20, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-009`

Execute Configure AC Voltage.

## Configure Continuity

- Python method: `configure_continuity`
- Signature: `Configure Continuity(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-010`

Execute Configure Continuity.

## Configure DC Current

- Python method: `configure_dc_current`
- Signature: `Configure DC Current(range_value=DEF, nplc=10, autozero=ON, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-011`

Execute Configure DC Current.

## Configure DC Voltage

- Python method: `configure_dc_voltage`
- Signature: `Configure DC Voltage(range_value=DEF, nplc=10, autozero=ON, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-012`

Execute Configure DC Voltage.

## Configure Diode

- Python method: `configure_diode`
- Signature: `Configure Diode(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-013`

Execute Configure Diode.

## Configure Frequency

- Python method: `configure_frequency`
- Signature: `Configure Frequency(voltage_range=DEF, aperture=0.1, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-014`

Execute Configure Frequency.

## Configure Period

- Python method: `configure_period`
- Signature: `Configure Period(voltage_range=DEF, aperture=0.1, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-015`

Execute Configure Period.

## Connect

- Python method: `connect`
- Signature: `Connect(resource=${NONE}, alias=default, timeout_s=${NONE}, **options)`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-016`

Establish a session and return the RFDS ``connection_state`` schema.

## Connect DMM

- Python method: `connect_dmm`
- Signature: `Connect DMM(resource, transport=AUTO, alias=default, timeout=10 s, visa_library=${NONE}, baud_rate=9600, parity=none, data_bits=8, stop_bits=2, dtr_dsr=${TRUE}, remote_on_connect=${TRUE}, local_on_close=${FALSE}, reset_on_connect=${FALSE}, verify_identity=${TRUE}, drain_error_queue=${TRUE}, retry_queries=${TRUE}, max_query_retries=1, allow_calibration_commands=${FALSE}, replace=${FALSE}, raw_traffic_log=${FALSE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-017`

Open a DMM session using AUTO, VISA, or SERIAL transport selection.

## DMM Error Queue Should Be Empty

- Python method: `dmm_error_queue_should_be_empty`
- Signature: `DMM Error Queue Should Be Empty(alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-018`

Execute DMM Error Queue Should Be Empty.

## DMM Model Should Be 34401A

- Python method: `dmm_model_should_be_34401a`
- Signature: `DMM Model Should Be 34401A(alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-019`

Execute DMM Model Should Be 34401A.

## DMM Reading Should Be Between

- Python method: `dmm_reading_should_be_between`
- Signature: `DMM Reading Should Be Between(minimum, maximum, alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-020`

Execute DMM Reading Should Be Between.

## DMM Reading Should Be Close To

- Python method: `dmm_reading_should_be_close_to`
- Signature: `DMM Reading Should Be Close To(expected, absolute_tolerance=0.0, relative_tolerance=0.0, alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-021`

Execute DMM Reading Should Be Close To.

## DMM Reading Should Be Greater Than

- Python method: `dmm_reading_should_be_greater_than`
- Signature: `DMM Reading Should Be Greater Than(minimum, alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-022`

Execute DMM Reading Should Be Greater Than.

## DMM Reading Should Be Less Than

- Python method: `dmm_reading_should_be_less_than`
- Signature: `DMM Reading Should Be Less Than(maximum, alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-023`

Execute DMM Reading Should Be Less Than.

## DMM Reading Should Be Valid

- Python method: `dmm_reading_should_be_valid`
- Signature: `DMM Reading Should Be Valid(alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-024`

Execute DMM Reading Should Be Valid.

## DMM Reading Should Not Be Overload

- Python method: `dmm_reading_should_not_be_overload`
- Signature: `DMM Reading Should Not Be Overload(alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-025`

Execute DMM Reading Should Not Be Overload.

## DMM Self Test Should Pass

- Python method: `dmm_self_test_should_pass`
- Signature: `DMM Self Test Should Pass(alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-026`

Execute DMM Self Test Should Pass.

## DMM Should Be Connected

- Python method: `dmm_should_be_connected`
- Signature: `DMM Should Be Connected(alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-027`

Execute DMM Should Be Connected.

## DMM Should Have No Errors

- Python method: `dmm_should_have_no_errors`
- Signature: `DMM Should Have No Errors(context=, alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-028`

Execute DMM Should Have No Errors.

## Delete Driver Configuration Profile

- Python method: `delete_driver_configuration_profile`
- Signature: `Delete Driver Configuration Profile(profile_name)`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-029`

Delete one named host profile; packaged defaults cannot be deleted.

## Device Error Queue Should Be Empty

- Python method: `device_error_queue_should_be_empty`
- Signature: `Device Error Queue Should Be Empty(alias=${NONE})`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-030`

Fail unless the device error queue reports no error.

## Disconnect

- Python method: `disconnect`
- Signature: `Disconnect(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-031`

Close one session idempotently and release its transport resources.

## Disconnect All

- Python method: `disconnect_all`
- Signature: `Disconnect All()`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-032`

Close all sessions while continuing cleanup after individual failures.

## Disconnect DMM

- Python method: `disconnect_dmm`
- Signature: `Disconnect DMM(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-033`

Transport-neutral alias for ``Close DMM``.

## Export Diagnostic Bundle

- Python method: `export_diagnostic_bundle`
- Signature: `Export Diagnostic Bundle(destination=${NONE})`
- Return: `str | None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-109`

Zip this library instance's RFDS-008 evidence run for troubleshooting. See
`logging_and_evidence.md`.

## Export Driver Configuration

- Python method: `export_driver_configuration`
- Signature: `Export Driver Configuration(destination=${NONE}, indent=2)`
- Return: `str`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-034`

Export canonical JSON and optionally write it atomically to a path.

## Fetch DMM Readings

- Python method: `fetch_dmm_readings`
- Signature: `Fetch DMM Readings(alias=${NONE})`
- Return: `list[dict[str, Any]]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-035`

Execute Fetch DMM Readings.

## Find Driver Capabilities

- Python method: `find_driver_capabilities`
- Signature: `Find Driver Capabilities(capability_id=${NONE}, keyword_name=${NONE}, maximum_risk=${NONE}, available_only=${FALSE}, mode=effective)`
- Return: `list[dict[str, Any]]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-036`

Find capabilities using structured filters.

## Get Active Connection

- Python method: `get_active_connection`
- Signature: `Get Active Connection()`
- Return: `str | None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-037`

Return the active alias or ``None`` when no session exists.

## Get Active DMM Alias

- Python method: `get_active_dmm_alias`
- Signature: `Get Active DMM Alias()`
- Return: `str | None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-038`

Execute Get Active DMM Alias.

## Get All Device Errors

- Python method: `get_all_device_errors`
- Signature: `Get All Device Errors(max_count=25, alias=${NONE})`
- Return: `list[dict[str, Any]]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-039`

Drain the device error queue up to ``max_count`` records.

## Get Communication Timeout

- Python method: `get_communication_timeout`
- Signature: `Get Communication Timeout(alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-040`

Return the effective timeout for the selected session or driver default.

## Get Connection State

- Python method: `get_connection_state`
- Signature: `Get Connection State(alias=${NONE}, refresh=${FALSE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-041`

Return the stable RFDS connection-state dictionary.

## Get DMM Driver Version

- Python method: `get_dmm_driver_version`
- Signature: `Get DMM Driver Version()`
- Return: `str`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-042`

Execute Get DMM Driver Version.

## Get DMM Error Queue

- Python method: `get_dmm_error_queue`
- Signature: `Get DMM Error Queue(max_errors=25, alias=${NONE})`
- Return: `list[dict[str, Any]]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-043`

Execute Get DMM Error Queue.

## Get DMM Health

- Python method: `get_dmm_health`
- Signature: `Get DMM Health(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-044`

Execute Get DMM Health.

## Get DMM Input Terminal

- Python method: `get_dmm_input_terminal`
- Signature: `Get DMM Input Terminal(alias=${NONE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-045`

Execute Get DMM Input Terminal.

## Get DMM State

- Python method: `get_dmm_state`
- Signature: `Get DMM State(alias=${NONE})`
- Return: `str`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-046`

Execute Get DMM State.

## Get Device Error

- Python method: `get_device_error`
- Signature: `Get Device Error(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-047`

Read one device error record.

## Get Driver Capabilities

- Python method: `get_driver_capabilities`
- Signature: `Get Driver Capabilities()`
- Return: `list[str]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-048`

Return the sorted RFDS-002 capability identifiers without device I/O.

## Get Driver Capability

- Python method: `get_driver_capability`
- Signature: `Get Driver Capability(capability_id, mode=effective)`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-049`

Return one capability by exact stable capability identifier.

## Get Driver Capability Model

- Python method: `get_driver_capability_model`
- Signature: `Get Driver Capability Model(mode=effective)`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-050`

Return the full RFDS-013 capability model.

## Get Driver Configuration

- Python method: `get_driver_configuration`
- Signature: `Get Driver Configuration(scope=EFFECTIVE, alias=${NONE}, redact_sensitive=${TRUE}, include_sources=${FALSE})`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-051`

Return current host-side configuration; no device state is changed.

## Get Driver Configuration Schema

- Python method: `get_driver_configuration_schema`
- Signature: `Get Driver Configuration Schema()`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-052`

Return the canonical RFDS-014 JSON Schema without device I/O.

## Get Driver Default Configuration

- Python method: `get_driver_default_configuration`
- Signature: `Get Driver Default Configuration()`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-053`

Return a copy of the safe package default configuration.

## Get Driver Features

- Python method: `get_driver_features`
- Signature: `Get Driver Features(mode=effective)`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-054`

Return normalized feature information from the capability model.

## Get Driver Information

- Python method: `get_driver_information`
- Signature: `Get Driver Information()`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-055`

Return connection-independent driver identity and compatibility metadata.

## Get Driver Metadata

- Python method: `get_driver_metadata`
- Signature: `Get Driver Metadata(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-056`

Return driver, runtime, transport, and connected-instrument metadata.

## Get Identity

- Python method: `get_identity`
- Signature: `Get Identity(alias=${NONE}, refresh=${FALSE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-057`

Return cached device identity, querying only when requested or unavailable.

## Get Last DMM Reading

- Python method: `get_last_dmm_reading`
- Signature: `Get Last DMM Reading(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-058`

Execute Get Last DMM Reading.

## Get Last DMM Reading Value

- Python method: `get_last_dmm_reading_value`
- Signature: `Get Last DMM Reading Value(alias=${NONE})`
- Return: `float`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-059`

Execute Get Last DMM Reading Value.

## Get Open DMM Aliases

- Python method: `get_open_dmm_aliases`
- Signature: `Get Open DMM Aliases()`
- Return: `list[str]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-060`

Execute Get Open DMM Aliases.

## Get Robot DMM Library Version

- Python method: `get_robot_dmm_library_version`
- Signature: `Get Robot DMM Library Version()`
- Return: `str`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-061`

Execute Get Robot DMM Library Version.

## Identify DMM

- Python method: `identify_dmm`
- Signature: `Identify DMM(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-062`

Execute Identify DMM.

## Import Driver Configuration

- Python method: `import_driver_configuration`
- Signature: `Import Driver Configuration(source, validate_only=${FALSE}, strict=${TRUE})`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-063`

Import JSON from a mapping, JSON string, or file path transactionally.

## Initiate DMM Measurement

- Python method: `initiate_dmm_measurement`
- Signature: `Initiate DMM Measurement(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-064`

Execute Initiate DMM Measurement.

## Is Connected

- Python method: `is_connected`
- Signature: `Is Connected(alias=${NONE})`
- Return: `bool`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-065`

Return cached connection state without raising for an unknown alias.

## List Connections

- Python method: `list_connections`
- Signature: `List Connections()`
- Return: `list[dict[str, Any]]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-066`

Return one connection-state dictionary per open alias.

## List Driver Configuration Profiles

- Python method: `list_driver_configuration_profiles`
- Signature: `List Driver Configuration Profiles()`
- Return: `list[str]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-067`

List explicitly persisted user profile names.

## List VISA Resources

- Python method: `list_visa_resources`
- Signature: `List VISA Resources(visa_library=${NONE})`
- Return: `list[str]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-068`

Execute List VISA Resources.

## Load Driver Configuration

- Python method: `load_driver_configuration`
- Signature: `Load Driver Configuration(profile_name, validate_only=${FALSE})`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-069`

Load a named user profile and optionally validate without applying.

## Measure 2 Wire Resistance

- Python method: `measure_2wire_resistance`
- Signature: `Measure 2 Wire Resistance(range_value=DEF, nplc=10, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-070`

Execute Measure 2 Wire Resistance.

## Measure 4 Wire Resistance

- Python method: `measure_4wire_resistance`
- Signature: `Measure 4 Wire Resistance(range_value=DEF, nplc=10, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-071`

Execute Measure 4 Wire Resistance.

## Measure AC Current

- Python method: `measure_ac_current`
- Signature: `Measure AC Current(range_value=DEF, ac_filter_hz=20, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-072`

Execute Measure AC Current.

## Measure AC Voltage

- Python method: `measure_ac_voltage`
- Signature: `Measure AC Voltage(range_value=DEF, ac_filter_hz=20, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-073`

Execute Measure AC Voltage.

## Measure Continuity

- Python method: `measure_continuity`
- Signature: `Measure Continuity(alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-074`

Execute Measure Continuity.

## Measure DC Current

- Python method: `measure_dc_current`
- Signature: `Measure DC Current(range_value=DEF, nplc=10, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-075`

Execute Measure DC Current.

## Measure DC Voltage

- Python method: `measure_dc_voltage`
- Signature: `Measure DC Voltage(range_value=DEF, nplc=10, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-076`

Execute Measure DC Voltage.

## Measure Diode

- Python method: `measure_diode`
- Signature: `Measure Diode(alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-077`

Execute Measure Diode.

## Measure Frequency

- Python method: `measure_frequency`
- Signature: `Measure Frequency(voltage_range=DEF, aperture=0.1, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-078`

Execute Measure Frequency.

## Measure Period

- Python method: `measure_period`
- Signature: `Measure Period(voltage_range=DEF, aperture=0.1, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-079`

Execute Measure Period.

## Open DMM Via Serial

- Python method: `open_dmm_via_serial`
- Signature: `Open DMM Via Serial(port, alias=default, baud_rate=9600, parity=none, data_bits=8, stop_bits=2, timeout=10 s, dtr_dsr=${TRUE}, remote_on_connect=${TRUE}, local_on_close=${FALSE}, verify_identity=${TRUE}, retry_queries=${TRUE}, max_query_retries=1, allow_calibration_commands=${FALSE}, replace=${FALSE}, raw_traffic_log=${FALSE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-080`

Open an RS-232 session using the instrument's supported serial settings.

## Open DMM Via VISA

- Python method: `open_dmm_via_visa`
- Signature: `Open DMM Via VISA(resource, alias=default, timeout=10 s, visa_library=${NONE}, reset_on_connect=${FALSE}, verify_identity=${TRUE}, drain_error_queue=${TRUE}, retry_queries=${TRUE}, max_query_retries=1, allow_calibration_commands=${FALSE}, replace=${FALSE}, raw_traffic_log=${FALSE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-081`

Open a VISA/GPIB session and make ``alias`` active.

## Open Simulated DMM

- Python method: `open_simulated_dmm`
- Signature: `Open Simulated DMM(alias=default, reading=12.0, identity=HEWLETT-PACKARD,34401A,SIM0001,11-05-01, terminal=FRONT, replace=${FALSE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-082`

Open deterministic simulation. This keyword never runs automatically as fallback.

## Query DMM Command

- Python method: `query_dmm_command`
- Signature: `Query DMM Command(command, alias=${NONE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-083`

Execute Query DMM Command.

## Query Raw Command

- Python method: `query_raw_command`
- Signature: `Query Raw Command(command, alias=${NONE}, timeout_s=${NONE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-084`

Query guarded raw SCPI after explicit opt-in.

## Read DMM

- Python method: `read_dmm`
- Signature: `Read DMM(alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-085`

Execute Read DMM.

## Read DMM Error

- Python method: `read_dmm_error`
- Signature: `Read DMM Error(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-086`

Execute Read DMM Error.

## Read DMM Once With Bus Trigger

- Python method: `read_dmm_once_with_bus_trigger`
- Signature: `Read DMM Once With Bus Trigger(alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-087`

Execute Read DMM Once With Bus Trigger.

## Read Raw Response

- Python method: `read_raw_response`
- Signature: `Read Raw Response(alias=${NONE}, timeout_s=${NONE})`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-088`

Read one already-pending raw response after explicit opt-in.

## Read Stable Resistance

- Python method: `read_stable_resistance`
- Signature: `Read Stable Resistance(expected_ohm=${NONE}, range_value=AUTO, nplc=10, final_nplc=100, min_settle=500 ms, max_wait=20 s, sample_interval=200 ms, window_size=5, max_stdev_ohm=${NONE}, max_relative_stdev=0.0005, max_slope_relative_per_s=0.0005, four_wire=${FALSE}, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-089`

Return a stable resistance or fail without fabricating a reading.

## Recover DMM

- Python method: `recover_dmm`
- Signature: `Recover DMM(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-090`

Execute Recover DMM.

## Refresh Driver Capabilities

- Python method: `refresh_driver_capabilities`
- Signature: `Refresh Driver Capabilities(mode=effective)`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-091`

Re-evaluate capability availability and connected identity.

## Require DMM Input Terminal

- Python method: `require_dmm_input_terminal`
- Signature: `Require DMM Input Terminal(expected, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-092`

Execute Require DMM Input Terminal.

## Reset Device

- Python method: `reset_device`
- Signature: `Reset Device(alias=${NONE}, wait_until_ready=${TRUE}, timeout_s=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-093`

Perform the 34401A SCPI reset only after this explicit high-risk call.

## Reset Driver Configuration

- Python method: `reset_driver_configuration`
- Signature: `Reset Driver Configuration()`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-094`

Reset runtime host configuration to the safe package default.

## Run DMM Self Test

- Python method: `run_dmm_self_test`
- Signature: `Run DMM Self Test(alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-095`

Execute Run DMM Self Test.

## Save Driver Configuration

- Python method: `save_driver_configuration`
- Signature: `Save Driver Configuration(profile_name, overwrite=${FALSE})`
- Return: `str`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-096`

Persist the current host profile only after explicit authorization.

## Select Connection

- Python method: `select_connection`
- Signature: `Select Connection(alias)`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-097`

Select an existing connection and return its state.

## Select DMM

- Python method: `select_dmm`
- Signature: `Select DMM(alias)`
- Return: `str`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-098`

Execute Select DMM.

## Send DMM Bus Trigger

- Python method: `send_dmm_bus_trigger`
- Signature: `Send DMM Bus Trigger(alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-099`

Execute Send DMM Bus Trigger.

## Set Communication Timeout

- Python method: `set_communication_timeout`
- Signature: `Set Communication Timeout(timeout_s, alias=${NONE})`
- Return: `float`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-100`

Set a positive finite session or default communication timeout.

## Set DMM Trigger Source

- Python method: `set_dmm_trigger_source`
- Signature: `Set DMM Trigger Source(source, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-101`

Execute Set DMM Trigger Source.

## Set Raw I/O Enabled

- Python method: `set_raw_io_enabled`
- Signature: `Set Raw I/O Enabled(enabled)`
- Return: `bool`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-102`

Explicitly enable or disable guarded raw SCPI access for this instance.

## Stable Resistance Should Be Between

- Python method: `stable_resistance_should_be_between`
- Signature: `Stable Resistance Should Be Between(result, minimum, maximum)`
- Return: `None`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-103`

Execute Stable Resistance Should Be Between.

## Try Read Stable Resistance

- Python method: `try_read_stable_resistance`
- Signature: `Try Read Stable Resistance(expected_ohm=${NONE}, range_value=AUTO, nplc=10, final_nplc=100, min_settle=500 ms, max_wait=20 s, sample_interval=200 ms, window_size=5, max_stdev_ohm=${NONE}, max_relative_stdev=0.0005, max_slope_relative_per_s=0.0005, four_wire=${FALSE}, alias=${NONE})`
- Return: `dict[str, Any]`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-104`

Execute Try Read Stable Resistance.

## Validate Driver Capabilities

- Python method: `validate_driver_capabilities`
- Signature: `Validate Driver Capabilities()`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-105`

Validate static capability bindings against the intended public keywords.

## Validate Driver Configuration

- Python method: `validate_driver_configuration`
- Signature: `Validate Driver Configuration(configuration, strict=${TRUE})`
- Return: `dict[str, Any]`
- Device-facing: `false`
- Protocol vector: `HP34401A-KW-106`

Validate configuration without applying or persisting it.

## Write DMM Command

- Python method: `write_dmm_command`
- Signature: `Write DMM Command(command, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-107`

Execute Write DMM Command.

## Write Raw Command

- Python method: `write_raw_command`
- Signature: `Write Raw Command(command, alias=${NONE})`
- Return: `None`
- Device-facing: `true`
- Protocol vector: `HP34401A-KW-108`

Write a guarded raw SCPI command after explicit raw-I/O opt-in.

