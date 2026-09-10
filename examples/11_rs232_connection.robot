*** Settings ***
Documentation     Real hardware example. Supply SERIAL_PORT on the command line.
Library           rf_hp34401a.Hp34401ALibrary
Suite Teardown    Close All DMMs
Test Tags         hardware    serial

*** Variables ***
${SERIAL_PORT}    COM3

*** Test Cases ***
Measure Through RS232
    Open DMM Via Serial    ${SERIAL_PORT}
    ...    baud_rate=9600
    ...    parity=none
    ...    data_bits=8
    ...    stop_bits=2
    ${value}=    Measure DC Voltage    range_value=AUTO    nplc=10
    Log    Measured ${value} V
