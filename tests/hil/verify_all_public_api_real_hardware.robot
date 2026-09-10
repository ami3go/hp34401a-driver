*** Settings ***
Documentation     RFDS real-hardware verification for every exported rf_hp34401a public API.
...               All APIs receive PASS, FAIL, or an explicit EXCLUDED result; no API may remain NOT RUN.
...               HIL never falls back to simulation for hardware profiles. The simulator-only API is tested separately and identified as such.
Library           rf_hp34401a.Hp34401ALibrary    default_timeout_s=10.0    allow_raw_io=${FALSE}
Library           OperatingSystem
Library           Collections
Library           ${CURDIR}${/}support${/}RealHardwareApiCoverage.py
Suite Setup       Initialize Full API Hardware Verification
Suite Teardown    Finalize Full API Hardware Verification
Test Tags         hil    real_hardware    rfds002    rfds009    rfds019    all_api

*** Variables ***
${HIL_ENABLED}                    ${FALSE}
${FAIL_ON_EXCLUSIONS}             ${FALSE}
${COVERAGE_STARTED}               ${FALSE}
${VISA_RESOURCE}                  ${EMPTY}
${VISA_LIBRARY}                   ${NONE}
${SERIAL_PORT}                    ${EMPTY}
${DMM_ALIAS}                      dut
${EXPECTED_TERMINAL}              FRONT
${COMMUNICATION_TIMEOUT_S}        10.0
${SELF_TEST_TIMEOUT_S}            60.0

# Every physical profile defaults to disabled. Enable only after the stated fixture is safe.
${RUN_DC_VOLTAGE_PROFILE}         ${FALSE}
${RUN_AC_VOLTAGE_PROFILE}         ${FALSE}
${RUN_CURRENT_PROFILE}            ${FALSE}
${RUN_RESISTANCE_PROFILE}         ${FALSE}
${RUN_FREQUENCY_PROFILE}          ${FALSE}
${RUN_DIODE_CONTINUITY_PROFILE}   ${FALSE}
${RUN_TRIGGER_PROFILE}            ${FALSE}
${RUN_SELF_TEST_PROFILE}          ${FALSE}
${RUN_RESET_PROFILE}              ${FALSE}
${RUN_RAW_IO_PROFILE}             ${FALSE}
${RUN_SERIAL_PROFILE}             ${FALSE}

# Conservative example settings; the approved bench profile owns actual limits and fixture wiring.
${DC_VOLTAGE_RANGE_V}             10
${AC_VOLTAGE_RANGE_V}             10
${CURRENT_RANGE_A}                1
${RESISTANCE_RANGE_OHM}           10000
${FREQUENCY_RANGE_V}              10
${NPLC}                           10
${AC_FILTER_HZ}                   20
${APERTURE_S}                     0.1
${STABLE_EXPECTED_OHM}            1000
${STABLE_MIN_OHM}                 900
${STABLE_MAX_OHM}                 1100

*** Test Cases ***
Verify Offline Metadata Capability And Configuration APIs
    [Documentation]    Verify all connection-independent public APIs and explicit profile persistence.
    ${core_version}=    Get DMM Driver Version
    ${library_version}=    Get Robot DMM Library Version
    ${information}=    Get Driver Information
    ${metadata}=    Get Driver Metadata
    ${capability_ids}=    Get Driver Capabilities
    ${model}=    Get Driver Capability Model    mode=static
    ${capability}=    Get Driver Capability    measure.voltage.dc    mode=static
    ${matches}=    Find Driver Capabilities    capability_id=measure.    maximum_risk=low    mode=static
    ${features}=    Get Driver Features    mode=static
    ${refreshed}=    Refresh Driver Capabilities    mode=static
    ${validation}=    Validate Driver Capabilities
    Should Be Equal    ${information}[package_version]    26.07
    Should Not Be Empty    ${capability_ids}
    Should Be True    ${validation}[valid]

    ${schema}=    Get Driver Configuration Schema
    ${default}=    Get Driver Default Configuration
    ${effective}=    Get Driver Configuration    include_sources=${TRUE}
    ${validated}=    Validate Driver Configuration    ${default}
    ${validated_import}=    Import Driver Configuration    ${default}    validate_only=${TRUE}
    ${applied}=    Import Driver Configuration    ${default}
    ${json_text}=    Export Driver Configuration    ${OUTPUT DIR}${/}driver_configuration.json
    ${diagnostic_bundle}=    Export Diagnostic Bundle    ${OUTPUT DIR}${/}hil_diagnostic_bundle.zip
    Should Not Be Empty    ${diagnostic_bundle}
    File Should Exist    ${diagnostic_bundle}
    ${saved_path}=    Save Driver Configuration    hil_all_api    overwrite=${TRUE}
    ${profiles}=    List Driver Configuration Profiles
    ${loaded}=    Load Driver Configuration    hil_all_api
    Delete Driver Configuration Profile    hil_all_api
    ${reset}=    Reset Driver Configuration
    Should Contain    ${profiles}    hil_all_api

    ${unknown_connected}=    Is Connected    alias=never_opened
    ${unknown_state}=    Get Connection State    alias=never_opened
    ${active}=    Get Active Connection
    ${active_legacy}=    Get Active DMM Alias
    ${connections}=    List Connections
    ${legacy_aliases}=    Get Open DMM Aliases
    ${default_timeout}=    Get Communication Timeout
    ${applied_timeout}=    Set Communication Timeout    11.0
    ${updated_timeout}=    Get Communication Timeout
    Should Be Equal    ${unknown_connected}    ${FALSE}
    Should Be Equal    ${unknown_state}[state]    disconnected

Verify VISA Discovery And Legacy Connection APIs
    [Documentation]    Exercise VISA discovery and both legacy hardware-open paths before the canonical session.
    ${resources}=    List VISA Resources    visa_library=${VISA_LIBRARY}
    Log To Console    VISA resources: ${resources}

    Open DMM Via VISA
    ...    ${VISA_RESOURCE}
    ...    alias=legacy_visa
    ...    timeout=${COMMUNICATION_TIMEOUT_S}
    ...    visa_library=${VISA_LIBRARY}
    ...    verify_identity=${TRUE}
    Close DMM    alias=legacy_visa

    Connect DMM
    ...    ${VISA_RESOURCE}
    ...    transport=VISA
    ...    alias=legacy_connect
    ...    timeout=${COMMUNICATION_TIMEOUT_S}
    ...    visa_library=${VISA_LIBRARY}
    Disconnect DMM    alias=legacy_connect

Verify Canonical Connection Identity And Session APIs
    [Documentation]    Establish the main real-hardware session and verify canonical and compatibility state calls.
    ${state}=    Connect
    ...    resource=${VISA_RESOURCE}
    ...    alias=${DMM_ALIAS}
    ...    timeout_s=${COMMUNICATION_TIMEOUT_S}
    ...    transport=VISA
    ...    visa_library=${VISA_LIBRARY}
    Should Be True    ${state}[connected]
    Should Be Equal    ${state}[simulated]    ${FALSE}

    ${connected}=    Is Connected    alias=${DMM_ALIAS}
    ${refreshed_state}=    Get Connection State    alias=${DMM_ALIAS}    refresh=${TRUE}
    ${communication_ok}=    Check Communication    alias=${DMM_ALIAS}
    ${identity}=    Get Identity    alias=${DMM_ALIAS}
    ${identity_live}=    Get Identity    alias=${DMM_ALIAS}    refresh=${TRUE}
    ${legacy_identity}=    Identify DMM    alias=${DMM_ALIAS}
    ${identity_record}=    Record Real Hardware Device Identity
    ...    ${identity}
    ...    ${VISA_RESOURCE}
    ...    transport=VISA
    ...    alias=${DMM_ALIAS}
    DMM Model Should Be 34401A    alias=${DMM_ALIAS}
    DMM Should Be Connected    alias=${DMM_ALIAS}
    ${selected}=    Select Connection    ${DMM_ALIAS}
    ${selected_legacy}=    Select DMM    ${DMM_ALIAS}
    ${active}=    Get Active Connection
    ${active_legacy}=    Get Active DMM Alias
    ${connections}=    List Connections
    ${aliases}=    Get Open DMM Aliases
    ${state_name}=    Get DMM State    alias=${DMM_ALIAS}
    ${metadata}=    Get Driver Metadata    alias=${DMM_ALIAS}
    ${timeout}=    Set Communication Timeout    ${COMMUNICATION_TIMEOUT_S}    alias=${DMM_ALIAS}
    ${timeout_readback}=    Get Communication Timeout    alias=${DMM_ALIAS}
    ${terminal}=    Get DMM Input Terminal    alias=${DMM_ALIAS}
    Require DMM Input Terminal    ${EXPECTED_TERMINAL}    alias=${DMM_ALIAS}
    Should Be True    ${connected}
    Should Be True    ${communication_ok}
    Should Contain    ${identity}    34401A

Verify Health Error Recovery And Status APIs
    [Documentation]    Exercise non-destructive status, error queue, health, and recovery calls.
    Clear DMM Status    alias=${DMM_ALIAS}
    Clear Device Errors    alias=${DMM_ALIAS}
    ${one_error}=    Get Device Error    alias=${DMM_ALIAS}
    ${legacy_error}=    Read DMM Error    alias=${DMM_ALIAS}
    ${all_errors}=    Get All Device Errors    max_count=25    alias=${DMM_ALIAS}
    ${legacy_queue}=    Get DMM Error Queue    max_errors=25    alias=${DMM_ALIAS}
    Device Error Queue Should Be Empty    alias=${DMM_ALIAS}
    DMM Error Queue Should Be Empty    alias=${DMM_ALIAS}
    DMM Should Have No Errors    context=HIL health check    alias=${DMM_ALIAS}
    ${health}=    Get DMM Health    alias=${DMM_ALIAS}
    ${recovery}=    Recover DMM    alias=${DMM_ALIAS}

Verify DC Voltage Measurement And Assertion APIs
    [Documentation]    Requires a verified voltage fixture within the selected range.
    IF    not ${RUN_DC_VOLTAGE_PROFILE}
        Exclude Real Hardware API Keywords
        ...    DC-voltage fixture profile was not explicitly enabled.
        ...    Configure DC Voltage
        ...    Read DMM
        ...    Measure DC Voltage
        ...    Get Last DMM Reading
        ...    Get Last DMM Reading Value
        ...    DMM Reading Should Be Valid
        ...    DMM Reading Should Not Be Overload
        ...    DMM Reading Should Be Between
        ...    DMM Reading Should Be Close To
        ...    DMM Reading Should Be Greater Than
        ...    DMM Reading Should Be Less Than
        Pass Execution    DC-voltage profile disabled; APIs recorded as EXCLUDED
    END
    Configure DC Voltage    range_value=${DC_VOLTAGE_RANGE_V}    nplc=${NPLC}    autozero=ON    alias=${DMM_ALIAS}
    ${read_value}=    Read DMM    alias=${DMM_ALIAS}
    ${value}=    Measure DC Voltage    range_value=${DC_VOLTAGE_RANGE_V}    nplc=${NPLC}    alias=${DMM_ALIAS}
    ${reading}=    Get Last DMM Reading    alias=${DMM_ALIAS}
    ${last_value}=    Get Last DMM Reading Value    alias=${DMM_ALIAS}
    DMM Reading Should Be Valid    alias=${DMM_ALIAS}
    DMM Reading Should Not Be Overload    alias=${DMM_ALIAS}
    DMM Reading Should Be Between    ${value}    ${value}    alias=${DMM_ALIAS}
    DMM Reading Should Be Close To    ${value}    absolute_tolerance=0.0    relative_tolerance=0.0    alias=${DMM_ALIAS}
    ${below}=    Evaluate    $value - max(abs($value) * 1e-9, 1e-12)
    ${above}=    Evaluate    $value + max(abs($value) * 1e-9, 1e-12)
    DMM Reading Should Be Greater Than    ${below}    alias=${DMM_ALIAS}
    DMM Reading Should Be Less Than    ${above}    alias=${DMM_ALIAS}

Verify AC Voltage APIs
    [Documentation]    Requires a verified AC-voltage fixture.
    IF    not ${RUN_AC_VOLTAGE_PROFILE}
        Exclude Real Hardware API Keywords
        ...    AC-voltage fixture profile was not explicitly enabled.
        ...    Configure AC Voltage
        ...    Measure AC Voltage
        Pass Execution    AC-voltage profile disabled; APIs recorded as EXCLUDED
    END
    Configure AC Voltage    range_value=${AC_VOLTAGE_RANGE_V}    ac_filter_hz=${AC_FILTER_HZ}    alias=${DMM_ALIAS}
    ${value}=    Measure AC Voltage    range_value=${AC_VOLTAGE_RANGE_V}    ac_filter_hz=${AC_FILTER_HZ}    alias=${DMM_ALIAS}

Verify Current APIs
    [Documentation]    Requires a current-limited series fixture and the correct fused DMM input terminal.
    IF    not ${RUN_CURRENT_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Current fixture and fused-terminal profile were not explicitly enabled.
        ...    Configure DC Current
        ...    Configure AC Current
        ...    Measure DC Current
        ...    Measure AC Current
        Pass Execution    Current profile disabled; APIs recorded as EXCLUDED
    END
    Configure DC Current    range_value=${CURRENT_RANGE_A}    nplc=${NPLC}    autozero=ON    alias=${DMM_ALIAS}
    ${dc_current}=    Measure DC Current    range_value=${CURRENT_RANGE_A}    nplc=${NPLC}    alias=${DMM_ALIAS}
    Configure AC Current    range_value=${CURRENT_RANGE_A}    ac_filter_hz=${AC_FILTER_HZ}    alias=${DMM_ALIAS}
    ${ac_current}=    Measure AC Current    range_value=${CURRENT_RANGE_A}    ac_filter_hz=${AC_FILTER_HZ}    alias=${DMM_ALIAS}

Verify Resistance And Stability APIs
    [Documentation]    Requires approved 2-wire and 4-wire resistor paths and no external voltage.
    IF    not ${RUN_RESISTANCE_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Resistance fixture profile was not explicitly enabled.
        ...    Configure 2 Wire Resistance
        ...    Configure 4 Wire Resistance
        ...    Measure 2 Wire Resistance
        ...    Measure 4 Wire Resistance
        ...    Try Read Stable Resistance
        ...    Read Stable Resistance
        ...    Stable Resistance Should Be Between
        Pass Execution    Resistance profile disabled; APIs recorded as EXCLUDED
    END
    Configure 2 Wire Resistance    range_value=${RESISTANCE_RANGE_OHM}    nplc=${NPLC}    autozero=ON    alias=${DMM_ALIAS}
    ${r2}=    Measure 2 Wire Resistance    range_value=${RESISTANCE_RANGE_OHM}    nplc=${NPLC}    alias=${DMM_ALIAS}
    Configure 4 Wire Resistance    range_value=${RESISTANCE_RANGE_OHM}    nplc=${NPLC}    autozero=ON    alias=${DMM_ALIAS}
    ${r4}=    Measure 4 Wire Resistance    range_value=${RESISTANCE_RANGE_OHM}    nplc=${NPLC}    alias=${DMM_ALIAS}
    ${stable_try}=    Try Read Stable Resistance
    ...    expected_ohm=${STABLE_EXPECTED_OHM}
    ...    range_value=${RESISTANCE_RANGE_OHM}
    ...    nplc=${NPLC}
    ...    min_settle=0.5 s
    ...    max_wait=30 s
    ...    sample_interval=200 ms
    ...    window_size=5
    ...    alias=${DMM_ALIAS}
    ${stable}=    Read Stable Resistance
    ...    expected_ohm=${STABLE_EXPECTED_OHM}
    ...    range_value=${RESISTANCE_RANGE_OHM}
    ...    nplc=${NPLC}
    ...    min_settle=0.5 s
    ...    max_wait=30 s
    ...    sample_interval=200 ms
    ...    window_size=5
    ...    alias=${DMM_ALIAS}
    Stable Resistance Should Be Between    ${stable_try}    ${STABLE_MIN_OHM}    ${STABLE_MAX_OHM}

Verify Frequency And Period APIs
    [Documentation]    Requires a bounded periodic input accepted by the approved fixture.
    IF    not ${RUN_FREQUENCY_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Frequency fixture profile was not explicitly enabled.
        ...    Configure Frequency
        ...    Configure Period
        ...    Measure Frequency
        ...    Measure Period
        Pass Execution    Frequency profile disabled; APIs recorded as EXCLUDED
    END
    Configure Frequency    voltage_range=${FREQUENCY_RANGE_V}    aperture=${APERTURE_S}    alias=${DMM_ALIAS}
    ${frequency}=    Measure Frequency    voltage_range=${FREQUENCY_RANGE_V}    aperture=${APERTURE_S}    alias=${DMM_ALIAS}
    Configure Period    voltage_range=${FREQUENCY_RANGE_V}    aperture=${APERTURE_S}    alias=${DMM_ALIAS}
    ${period}=    Measure Period    voltage_range=${FREQUENCY_RANGE_V}    aperture=${APERTURE_S}    alias=${DMM_ALIAS}

Verify Continuity And Diode APIs
    [Documentation]    Requires a passive, de-energized continuity/diode fixture.
    IF    not ${RUN_DIODE_CONTINUITY_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Diode/continuity fixture profile was not explicitly enabled.
        ...    Configure Continuity
        ...    Configure Diode
        ...    Measure Continuity
        ...    Measure Diode
        Pass Execution    Diode/continuity profile disabled; APIs recorded as EXCLUDED
    END
    Configure Continuity    alias=${DMM_ALIAS}
    ${continuity}=    Measure Continuity    alias=${DMM_ALIAS}
    Configure Diode    alias=${DMM_ALIAS}
    ${diode}=    Measure Diode    alias=${DMM_ALIAS}

Verify Triggered Acquisition APIs
    [Documentation]    Requires a stable DC-voltage fixture and approved BUS-trigger operation.
    IF    not ${RUN_TRIGGER_PROFILE}
        Exclude Real Hardware API Keywords
        ...    BUS-trigger profile was not explicitly enabled.
        ...    Set DMM Trigger Source
        ...    Initiate DMM Measurement
        ...    Send DMM Bus Trigger
        ...    Fetch DMM Readings
        ...    Read DMM Once With Bus Trigger
        Pass Execution    Trigger profile disabled; APIs recorded as EXCLUDED
    END
    Configure DC Voltage    range_value=${DC_VOLTAGE_RANGE_V}    nplc=${NPLC}    alias=${DMM_ALIAS}
    Set DMM Trigger Source    BUS    alias=${DMM_ALIAS}
    Initiate DMM Measurement    alias=${DMM_ALIAS}
    Send DMM Bus Trigger    alias=${DMM_ALIAS}
    ${values}=    Fetch DMM Readings    alias=${DMM_ALIAS}
    ${single}=    Read DMM Once With Bus Trigger    alias=${DMM_ALIAS}

Verify Self Test APIs
    [Documentation]    Self-test may interrupt normal measurement and shall be enabled explicitly.
    IF    not ${RUN_SELF_TEST_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Instrument self-test was not explicitly authorized.
        ...    Run DMM Self Test
        ...    DMM Self Test Should Pass
        Pass Execution    Self-test profile disabled; APIs recorded as EXCLUDED
    END
    ${timeout_before}=    Get Communication Timeout    alias=${DMM_ALIAS}
    Set Communication Timeout    ${SELF_TEST_TIMEOUT_S}    alias=${DMM_ALIAS}
    ${result}=    Run DMM Self Test    alias=${DMM_ALIAS}
    DMM Self Test Should Pass    alias=${DMM_ALIAS}
    Set Communication Timeout    ${timeout_before}    alias=${DMM_ALIAS}

Verify Reset API
    [Documentation]    SCPI *RST clears volatile measurement configuration and requires explicit authorization.
    IF    not ${RUN_RESET_PROFILE}
        Exclude Real Hardware API Keywords
        ...    SCPI reset was not explicitly authorized.
        ...    Reset Device
        Pass Execution    Reset profile disabled; APIs recorded as EXCLUDED
    END
    ${result}=    Reset Device    alias=${DMM_ALIAS}    wait_until_ready=${TRUE}    timeout_s=${COMMUNICATION_TIMEOUT_S}

Verify Guarded Raw IO APIs
    [Documentation]    Raw SCPI bypasses high-level state tracking and is disabled unless explicitly authorized.
    IF    not ${RUN_RAW_IO_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Raw-I/O profile was not explicitly authorized.
        ...    Set Raw I/O Enabled
        ...    Write Raw Command
        ...    Query Raw Command
        ...    Read Raw Response
        ...    Write DMM Command
        ...    Query DMM Command
        Pass Execution    Raw-I/O profile disabled; APIs recorded as EXCLUDED
    END
    ${enabled}=    Set Raw I/O Enabled    ${TRUE}
    ${identity}=    Query Raw Command    *IDN?    alias=${DMM_ALIAS}    timeout_s=${COMMUNICATION_TIMEOUT_S}
    ${identity_legacy}=    Query DMM Command    *IDN?    alias=${DMM_ALIAS}
    Write Raw Command    *CLS    alias=${DMM_ALIAS}
    Write DMM Command    *CLS    alias=${DMM_ALIAS}
    Write Raw Command    *IDN?    alias=${DMM_ALIAS}
    ${raw}=    Read Raw Response    alias=${DMM_ALIAS}    timeout_s=${COMMUNICATION_TIMEOUT_S}
    Set Raw I/O Enabled    ${FALSE}

Verify Serial Hardware Open API
    [Documentation]    Requires the DMM to be configured for RS-232 and connected to the supplied serial port.
    IF    not ${RUN_SERIAL_PROFILE}
        Exclude Real Hardware API Keywords
        ...    A real RS-232 resource/profile was not supplied; VISA evidence does not prove serial hardware.
        ...    Open DMM Via Serial
        Pass Execution    Serial profile disabled; APIs recorded as EXCLUDED
    END
    Should Not Be Empty    ${SERIAL_PORT}    msg=SERIAL_PORT is mandatory when RUN_SERIAL_PROFILE is true
    Disconnect    alias=${DMM_ALIAS}
    Open DMM Via Serial
    ...    ${SERIAL_PORT}
    ...    alias=serial_hil
    ...    timeout=${COMMUNICATION_TIMEOUT_S}
    ...    verify_identity=${TRUE}
    ...    local_on_close=${TRUE}
    Close DMM    alias=serial_hil
    Connect Main VISA Session

Verify Explicit Simulation API Without Hardware Fallback
    [Documentation]    Open Simulated DMM is part of the public API but is explicitly classified as simulator evidence.
    Open Simulated DMM    alias=sim_api_check    reading=12.0
    ${sim_state}=    Get Connection State    alias=sim_api_check
    Should Be True    ${sim_state}[simulated]
    Close DMM    alias=sim_api_check

Verify Disconnect Variants And Aggregate Cleanup APIs
    [Documentation]    Exercise every public teardown spelling and reconnect explicitly between calls.
    Disconnect    alias=${DMM_ALIAS}
    Disconnect    alias=${DMM_ALIAS}

    Connect Main VISA Session
    Disconnect All

    Connect Main VISA Session
    Close All DMMs

*** Keywords ***
Initialize Full API Hardware Verification
    Normalize HIL Boolean Variables
    Should Be True    ${HIL_ENABLED}    msg=Set HIL_ENABLED:True explicitly; real-HIL never falls back to simulation.
    Should Not Be Empty    ${VISA_RESOURCE}    msg=VISA_RESOURCE is mandatory for real-hardware verification.
    Start Real Hardware API Coverage    ${OUTPUT DIR}    profile=REAL_HARDWARE_ALL_PUBLIC_API
    Set Suite Variable    \${COVERAGE_STARTED}    ${TRUE}
    Register Disabled Profile Exclusions
    Set Environment Variable    RF_HP34401A_PROFILE_DIR    ${OUTPUT DIR}${/}rf_hp34401a_hil_profiles

Register Disabled Profile Exclusions
    [Documentation]    Record every disabled hardware profile before test execution so no API can remain NOT RUN.
    IF    not ${RUN_DC_VOLTAGE_PROFILE}
        Exclude Real Hardware API Keywords
        ...    DC-voltage fixture profile was not explicitly enabled.
        ...    Configure DC Voltage
        ...    Read DMM
        ...    Measure DC Voltage
        ...    Get Last DMM Reading
        ...    Get Last DMM Reading Value
        ...    DMM Reading Should Be Valid
        ...    DMM Reading Should Not Be Overload
        ...    DMM Reading Should Be Between
        ...    DMM Reading Should Be Close To
        ...    DMM Reading Should Be Greater Than
        ...    DMM Reading Should Be Less Than
    END
    IF    not ${RUN_AC_VOLTAGE_PROFILE}
        Exclude Real Hardware API Keywords
        ...    AC-voltage fixture profile was not explicitly enabled.
        ...    Configure AC Voltage
        ...    Measure AC Voltage
    END
    IF    not ${RUN_CURRENT_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Current fixture and fused-terminal profile were not explicitly enabled.
        ...    Configure DC Current
        ...    Configure AC Current
        ...    Measure DC Current
        ...    Measure AC Current
    END
    IF    not ${RUN_RESISTANCE_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Resistance fixture profile was not explicitly enabled.
        ...    Configure 2 Wire Resistance
        ...    Configure 4 Wire Resistance
        ...    Measure 2 Wire Resistance
        ...    Measure 4 Wire Resistance
        ...    Try Read Stable Resistance
        ...    Read Stable Resistance
        ...    Stable Resistance Should Be Between
    END
    IF    not ${RUN_FREQUENCY_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Frequency fixture profile was not explicitly enabled.
        ...    Configure Frequency
        ...    Configure Period
        ...    Measure Frequency
        ...    Measure Period
    END
    IF    not ${RUN_DIODE_CONTINUITY_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Diode/continuity fixture profile was not explicitly enabled.
        ...    Configure Continuity
        ...    Configure Diode
        ...    Measure Continuity
        ...    Measure Diode
    END
    IF    not ${RUN_TRIGGER_PROFILE}
        Exclude Real Hardware API Keywords
        ...    BUS-trigger profile was not explicitly enabled.
        ...    Set DMM Trigger Source
        ...    Initiate DMM Measurement
        ...    Send DMM Bus Trigger
        ...    Fetch DMM Readings
        ...    Read DMM Once With Bus Trigger
    END
    IF    not ${RUN_SELF_TEST_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Instrument self-test was not explicitly authorized.
        ...    Run DMM Self Test
        ...    DMM Self Test Should Pass
    END
    IF    not ${RUN_RESET_PROFILE}
        Exclude Real Hardware API Keywords
        ...    SCPI reset was not explicitly authorized.
        ...    Reset Device
    END
    IF    not ${RUN_RAW_IO_PROFILE}
        Exclude Real Hardware API Keywords
        ...    Raw-I/O profile was not explicitly authorized.
        ...    Set Raw I/O Enabled
        ...    Write Raw Command
        ...    Query Raw Command
        ...    Read Raw Response
        ...    Write DMM Command
        ...    Query DMM Command
    END
    IF    not ${RUN_SERIAL_PROFILE}
        Exclude Real Hardware API Keywords
        ...    A real RS-232 resource/profile was not supplied; VISA evidence does not prove serial hardware.
        ...    Open DMM Via Serial
    END

Normalize HIL Boolean Variables
    ${normalized}=    Normalize Boolean Value    ${HIL_ENABLED}    HIL_ENABLED
    Set Suite Variable    \${HIL_ENABLED}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${FAIL_ON_EXCLUSIONS}    FAIL_ON_EXCLUSIONS
    Set Suite Variable    \${FAIL_ON_EXCLUSIONS}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_DC_VOLTAGE_PROFILE}    RUN_DC_VOLTAGE_PROFILE
    Set Suite Variable    \${RUN_DC_VOLTAGE_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_AC_VOLTAGE_PROFILE}    RUN_AC_VOLTAGE_PROFILE
    Set Suite Variable    \${RUN_AC_VOLTAGE_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_CURRENT_PROFILE}    RUN_CURRENT_PROFILE
    Set Suite Variable    \${RUN_CURRENT_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_RESISTANCE_PROFILE}    RUN_RESISTANCE_PROFILE
    Set Suite Variable    \${RUN_RESISTANCE_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_FREQUENCY_PROFILE}    RUN_FREQUENCY_PROFILE
    Set Suite Variable    \${RUN_FREQUENCY_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_DIODE_CONTINUITY_PROFILE}    RUN_DIODE_CONTINUITY_PROFILE
    Set Suite Variable    \${RUN_DIODE_CONTINUITY_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_TRIGGER_PROFILE}    RUN_TRIGGER_PROFILE
    Set Suite Variable    \${RUN_TRIGGER_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_SELF_TEST_PROFILE}    RUN_SELF_TEST_PROFILE
    Set Suite Variable    \${RUN_SELF_TEST_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_RESET_PROFILE}    RUN_RESET_PROFILE
    Set Suite Variable    \${RUN_RESET_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_RAW_IO_PROFILE}    RUN_RAW_IO_PROFILE
    Set Suite Variable    \${RUN_RAW_IO_PROFILE}    ${normalized}
    ${normalized}=    Normalize Boolean Value    ${RUN_SERIAL_PROFILE}    RUN_SERIAL_PROFILE
    Set Suite Variable    \${RUN_SERIAL_PROFILE}    ${normalized}

Connect Main VISA Session
    ${state}=    Connect
    ...    resource=${VISA_RESOURCE}
    ...    alias=${DMM_ALIAS}
    ...    timeout_s=${COMMUNICATION_TIMEOUT_S}
    ...    transport=VISA
    ...    visa_library=${VISA_LIBRARY}
    RETURN    ${state}

Finalize Full API Hardware Verification
    Run Keyword And Ignore Error    Disconnect All
    IF    ${COVERAGE_STARTED}
        ${summary}=    Finalize Real Hardware API Coverage    fail_on_exclusions=${FAIL_ON_EXCLUSIONS}
        Log To Console    Real-hardware API summary: ${summary}
        Assert Real Hardware API Coverage    ${summary}    fail_on_exclusions=${FAIL_ON_EXCLUSIONS}
    ELSE
        Log To Console    Real-hardware API coverage was not started because suite preflight failed.
    END
