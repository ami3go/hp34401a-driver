*** Settings ***
Documentation     Use the safe INITiate, bus trigger, and FETCh sequence.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=5.0
Suite Teardown    Close All DMMs

*** Test Cases ***
Bus Triggered DC Voltage
    Configure DC Voltage    range_value=10    nplc=1
    ${value}=    Read DMM Once With Bus Trigger
    Should Be Equal As Numbers    ${value}    5.0
