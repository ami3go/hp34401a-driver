*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary
Library    Collections

*** Test Cases ***
Disconnected State Uses Stable Schema
    ${state}=    Get Connection State    alias=missing
    Dictionary Should Contain Key    ${state}    connected
    Should Be Equal    ${state}[connected]    ${FALSE}
