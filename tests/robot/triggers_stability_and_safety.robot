*** Settings ***
Library           rf_hp34401a.Hp34401ALibrary
Suite Teardown    Close All DMMs

*** Test Cases ***
Bus Trigger Measurement
    Open Simulated DMM    reading=3.3
    Configure DC Voltage
    ${value}=    Read DMM Once With Bus Trigger
    Should Be Equal As Numbers    ${value}    3.3

Manual Trigger Sequence
    Set DMM Trigger Source    BUS
    Initiate DMM Measurement
    Send DMM Bus Trigger
    ${readings}=    Fetch DMM Readings
    Length Should Be    ${readings}    1
    Should Be Equal As Numbers    ${readings}[0][value]    3.3

Stable Resistance Succeeds
    Close All DMMs
    Open Simulated DMM    reading=1000
    ${result}=    Try Read Stable Resistance    min_settle=0    sample_interval=1 ms    max_wait=100 ms    window_size=3    final_nplc=${NONE}
    Should Be True    ${result}[stable]
    Stable Resistance Should Be Between    ${result}    999    1001

Strict Stable Resistance Returns Scalar
    ${value}=    Read Stable Resistance    min_settle=0    sample_interval=1 ms    max_wait=100 ms    window_size=3    final_nplc=${NONE}
    Should Be Equal As Numbers    ${value}    1000

Invalid NPLC Is Rejected Before SCPI
    Run Keyword And Expect Error    *nplc must be one of*    Measure DC Voltage    nplc=2

Invalid Range Is Rejected Before SCPI
    Run Keyword And Expect Error    *must be positive*    Measure DC Voltage    range_value=0

Raw Query Uses Core Driver After Explicit Authorization
    Set Raw I/O Enabled    ${TRUE}
    ${idn}=    Query DMM Command    *IDN?
    Should Contain    ${idn}    34401A

Calibration Guard Remains Independent Of Raw I/O Authorization
    Run Keyword And Expect Error    *Calibration commands are blocked by default*    Write DMM Command    CALibration:SECure:STATe OFF
    Set Raw I/O Enabled    ${FALSE}

Overload Is Never Returned As Scalar
    Close All DMMs
    Open Simulated DMM    reading=9.9e37
    Run Keyword And Expect Error    *overload*    Measure DC Voltage
    ${reading}=    Get Last DMM Reading
    Should Be True    ${reading}[is_overload]
