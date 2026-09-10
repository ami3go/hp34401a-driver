*** Settings ***
Documentation     Measure low resistance using the 4-wire function.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=0.1008
Suite Teardown    Close All DMMs

*** Test Cases ***
Measure Shunt
    ${resistance}=    Measure 4 Wire Resistance    range_value=100    nplc=100
    DMM Reading Should Be Between    0.099    0.102
