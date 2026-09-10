*** Settings ***
Documentation     Measure AC voltage with a 20 Hz detector bandwidth.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=230.1
Suite Teardown    Close All DMMs

*** Test Cases ***
Measure Mains Voltage
    ${voltage}=    Measure AC Voltage    range_value=750    ac_filter_hz=20
    Should Be True    220 < ${voltage} < 240
