*** Settings ***
Documentation     Measure a resistor using the 2-wire function.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=1002.4
Suite Teardown    Close All DMMs

*** Test Cases ***
Measure One Kilohm Resistor
    ${resistance}=    Measure 2 Wire Resistance    range_value=10000    nplc=10
    DMM Reading Should Be Close To    1000    absolute_tolerance=10
