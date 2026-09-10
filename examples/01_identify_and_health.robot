*** Settings ***
Documentation     Identify a simulated HP 34401A and collect health information.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=12.0
Suite Teardown    Close All DMMs

*** Test Cases ***
Identify And Check Health
    ${identity}=    Identify DMM
    Should Be Equal    ${identity}[model]    34401A
    DMM Model Should Be 34401A
    DMM Self Test Should Pass
    ${health}=    Get DMM Health
    Should Be True    ${health}[connected]
