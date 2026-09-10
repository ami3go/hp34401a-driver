*** Settings ***
Documentation     Canonical RFDS-002 lifecycle, RFDS-013 capability discovery, and RFDS-014 configuration example.
...               Mode: deterministic simulation. Expected result: all metadata, discovery, configuration, and measurement checks pass.
Library           rf_hp34401a.Hp34401ALibrary
Suite Teardown    Disconnect All

*** Test Cases ***
Use Canonical Driver API
    ${information}=    Get Driver Information
    Should Be Equal    ${information}[package_version]    26.07

    ${capability_ids}=    Get Driver Capabilities
    Should Contain    ${capability_ids}    dc_voltage_measurement

    ${model}=    Get Driver Capability Model    mode=static
    Should Be Equal    ${model}[source][discovery_mode]    static

    ${default}=    Get Driver Default Configuration
    ${validation}=    Validate Driver Configuration    ${default}
    Should Be True    ${validation}[valid]

    ${state}=    Connect    resource=SIM::HP34401A    alias=dmm    timeout_s=2 s
    Should Be True    ${state}[connected]
    Should Be True    ${state}[simulated]

    ${identity}=    Get Identity    alias=dmm
    Should Contain    ${identity}    34401A

    ${voltage}=    Measure DC Voltage    range_value=100    nplc=10    alias=dmm
    DMM Reading Should Be Between    11.5    12.5    alias=dmm
