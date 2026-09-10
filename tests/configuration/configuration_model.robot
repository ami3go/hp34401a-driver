*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary

*** Test Cases ***
Default Configuration Validates Without Hardware
    ${default}=    Get Driver Default Configuration
    ${result}=    Validate Driver Configuration    ${default}
    Should Be True    ${result}[valid]
