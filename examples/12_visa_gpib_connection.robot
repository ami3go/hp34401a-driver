*** Settings ***
Documentation     Real hardware example. Supply VISA_RESOURCE on the command line.
Library           rf_hp34401a.Hp34401ALibrary
Suite Teardown    Close All DMMs
Test Tags         hardware    visa

*** Variables ***
${VISA_RESOURCE}    GPIB0::22::INSTR

*** Test Cases ***
Measure Through VISA GPIB
    Open DMM Via VISA    ${VISA_RESOURCE}
    ${identity}=    Identify DMM
    Log    Connected to ${identity}[manufacturer] ${identity}[model]
    ${value}=    Measure DC Voltage    range_value=AUTO    nplc=10
    Log    Measured ${value} V
