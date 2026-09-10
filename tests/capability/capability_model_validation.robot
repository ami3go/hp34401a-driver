*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary

*** Test Cases ***
Static Capability Model Is Valid
    ${result}=    Validate Driver Capabilities
    Should Be True    ${result}[valid]
