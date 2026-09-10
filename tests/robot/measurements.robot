*** Settings ***
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=12.5
Suite Teardown    Close All DMMs

*** Test Cases ***
DC Voltage Measurement
    ${value}=    Measure DC Voltage    range_value=100    nplc=10
    Should Be Equal As Numbers    ${value}    12.5

AC Voltage Measurement
    ${value}=    Measure AC Voltage    ac_filter_hz=20
    Should Be Equal As Numbers    ${value}    12.5

DC Current Measurement
    ${value}=    Measure DC Current    range_value=1    nplc=1
    Should Be Equal As Numbers    ${value}    12.5

AC Current Measurement
    ${value}=    Measure AC Current    range_value=1    ac_filter_hz=20
    Should Be Equal As Numbers    ${value}    12.5

Two Wire Resistance Measurement
    ${value}=    Measure 2 Wire Resistance    range_value=AUTO    nplc=10
    Should Be Equal As Numbers    ${value}    12.5

Four Wire Resistance Measurement
    ${value}=    Measure 4 Wire Resistance    range_value=AUTO    nplc=10
    Should Be Equal As Numbers    ${value}    12.5

Frequency Measurement
    ${value}=    Measure Frequency    aperture=0.1
    Should Be Equal As Numbers    ${value}    12.5

Period Measurement
    ${value}=    Measure Period    aperture=0.1
    Should Be Equal As Numbers    ${value}    12.5

Continuity Measurement
    ${value}=    Measure Continuity
    Should Be Equal As Numbers    ${value}    12.5

Diode Measurement
    ${value}=    Measure Diode
    Should Be Equal As Numbers    ${value}    12.5

Metadata Is Complete
    ${reading}=    Get Last DMM Reading
    Should Be Equal    ${reading}[alias]    default
    Should Be Equal    ${reading}[library_version]    26.07
    Should Be Equal    ${reading}[driver_version]    1.2.8
    Should Be True    ${reading}[is_valid]

Reading Assertions Pass
    DMM Reading Should Be Valid
    DMM Reading Should Not Be Overload
    DMM Reading Should Be Between    12    13
    DMM Reading Should Be Close To    12.4    absolute_tolerance=0.2
    DMM Reading Should Be Greater Than    12
    DMM Reading Should Be Less Than    13

Reading Assertion Failure Is Clear
    Run Keyword And Expect Error    *outside*    DMM Reading Should Be Between    20    30
