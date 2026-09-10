*** Settings ***
Documentation     Wait for a stable resistance without accepting an unstable final sample.
Library           rf_hp34401a.Hp34401ALibrary
Suite Setup       Open Simulated DMM    reading=10000
Suite Teardown    Close All DMMs

*** Test Cases ***
Read Stable Ten Kilohm Resistance
    ${result}=    Try Read Stable Resistance
    ...    range_value=100000
    ...    nplc=10
    ...    final_nplc=${NONE}
    ...    min_settle=0
    ...    sample_interval=1 ms
    ...    max_wait=100 ms
    ...    window_size=3
    Stable Resistance Should Be Between    ${result}    9990    10010
