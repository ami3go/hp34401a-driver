*** Settings ***
Documentation     Measure simulated DC load current.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=0.245
Suite Teardown    Close All DMMs

*** Test Cases ***
Measure Load Current
    ${current}=    Measure DC Current    range_value=1    nplc=1
    DMM Reading Should Be Between    0.2    0.3
