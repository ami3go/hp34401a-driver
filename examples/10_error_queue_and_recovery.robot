*** Settings ***
Documentation     Check the SCPI error queue and request a recovery report.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM
Suite Teardown    Close All DMMs

*** Test Cases ***
Check Instrument State
    DMM Error Queue Should Be Empty
    DMM Should Have No Errors    example validation
    ${recovery}=    Recover DMM
    Should Be True    ${recovery}[succeeded]
