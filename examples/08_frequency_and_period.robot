*** Settings ***
Documentation     Demonstrate frequency and period modes.
Library           rf_hp34401a.Hp34401ALibrary
Suite Teardown    Close All DMMs

*** Test Cases ***
Measure Frequency
    Open Simulated DMM    reading=1000
    ${frequency}=    Measure Frequency    voltage_range=10    aperture=0.1
    Should Be Equal As Numbers    ${frequency}    1000

Measure Period
    Close All DMMs
    Open Simulated DMM    reading=0.001
    ${period}=    Measure Period    voltage_range=10    aperture=0.1
    Should Be Equal As Numbers    ${period}    0.001
