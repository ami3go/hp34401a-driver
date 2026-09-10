*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary
Suite Teardown    Disconnect All

*** Test Cases ***
Legacy Connection Keywords Remain Callable
    Open Simulated DMM    alias=dut
    ${identity}=    Identify DMM    alias=dut
    Close DMM    alias=dut
