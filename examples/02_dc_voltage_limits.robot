*** Settings ***
Documentation     Measure simulated DC voltage and validate production limits.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=12.08
Suite Teardown    Close All DMMs

*** Test Cases ***
Validate 12 Volt Rail
    ${voltage}=    Measure DC Voltage    range_value=100    nplc=10
    Should Be Equal As Numbers    ${voltage}    12.08
    DMM Reading Should Be Between    11.5    12.5
