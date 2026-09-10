# Quick start

## Simulation

```robotframework
*** Settings ***
Library           rf_hp34401a.Hp34401ALibrary
Suite Teardown    Close All DMMs

*** Test Cases ***
Verify Driver Offline
    Open Simulated DMM    alias=dmm
    ${metadata}=    Get Driver Metadata    alias=dmm
    Log    ${metadata}
    ${voltage}=    Measure DC Voltage    alias=dmm
    DMM Reading Should Be Valid    alias=dmm
```

## Real VISA hardware

```robotframework
*** Settings ***
Library           rf_hp34401a.Hp34401ALibrary
Suite Teardown    Close All DMMs

*** Variables ***
${DMM_RESOURCE}    GPIB0::22::INSTR

*** Test Cases ***
Verify 12 V Rail
    Connect DMM    ${DMM_RESOURCE}    transport=AUTO    alias=dmm
    DMM Model Should Be 34401A    alias=dmm
    ${voltage}=    Measure DC Voltage    range_value=100    nplc=10    alias=dmm
    DMM Reading Should Be Between    11.5    12.5    alias=dmm
```

Use `Open DMM Via VISA` or `Open DMM Via Serial` when the transport must be explicit. Always use suite teardown so the session closes after failures.
