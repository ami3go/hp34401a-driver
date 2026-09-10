*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary

*** Test Cases ***
Metadata Matches Canonical API
    ${info}=    Get Driver Information
    Should Be Equal    ${info}[api_spec]    RFDS-002
    Should Be Equal    ${info}[api_spec_version]    1.1
    Should Be Equal    ${info}[library_scope]    SUITE
