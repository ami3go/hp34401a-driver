*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary
Suite Teardown    Disconnect All

*** Test Cases ***
Effective Capability Availability Changes With Connection
    ${before}=    Get Driver Capability    measure.voltage.dc    mode=static
    Connect    resource=SIM::HP34401A    alias=dut
    ${after}=    Refresh Driver Capabilities    mode=effective
    Should Be True    ${after}[source][connected]
