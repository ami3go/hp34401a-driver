*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary
Suite Teardown    Disconnect All

*** Test Cases ***
Named Sessions Are Independent
    Connect    resource=SIM::A    alias=a
    Connect    resource=SIM::B    alias=b
    ${connections}=    List Connections
    Length Should Be    ${connections}    2
