*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary
Suite Teardown    Disconnect All

*** Test Cases ***
Canonical Universal API Is Callable
    ${state}=    Connect    resource=SIM::HP34401A    alias=dut
    Should Be True    ${state}[connected]
    ${is_connected}=    Is Connected    alias=dut
    Should Be True    ${is_connected}
    ${connection}=    Get Connection State    alias=dut
    ${communication_ok}=    Check Communication    alias=dut
    Should Be True    ${communication_ok}
    ${identity}=    Get Identity    alias=dut
    ${information}=    Get Driver Information
    ${capabilities}=    Get Driver Capabilities
    ${timeout}=    Set Communication Timeout    5.0    alias=dut
    ${timeout}=    Get Communication Timeout    alias=dut
    Disconnect    alias=dut
