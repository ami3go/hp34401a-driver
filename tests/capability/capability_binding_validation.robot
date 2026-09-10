*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary

*** Test Cases ***
DC Voltage Capability Binds To Public Keyword
    ${cap}=    Get Driver Capability    measure.voltage.dc    mode=static
    Should Be Equal    ${cap}[binding][robot_keyword]    Measure DC Voltage
