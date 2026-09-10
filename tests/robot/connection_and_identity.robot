*** Settings ***
Library           rf_hp34401a.Hp34401ALibrary
Library           Collections
Suite Teardown    Close All DMMs

*** Test Cases ***
Open Simulated DMM And Identify
    Open Simulated DMM    reading=12.0
    ${identity}=    Identify DMM
    Should Be Equal    ${identity}[model]    34401A

Model Assertion Passes
    DMM Model Should Be 34401A

Self Test Passes
    DMM Self Test Should Pass

Health Is Available
    ${health}=    Get DMM Health
    Should Be True    ${health}[connected]

Terminal Can Be Verified
    ${terminal}=    Get DMM Input Terminal
    Should Be Equal    ${terminal}    FRONT
    Require DMM Input Terminal    FRONT

Versions Are Exposed
    ${library_version}=    Get Robot DMM Library Version
    ${driver_version}=    Get DMM Driver Version
    Should Be Equal    ${library_version}    26.07
    Should Be Equal    ${driver_version}    1.2.8

Runtime Metadata Is Exposed
    ${metadata}=    Get Driver Metadata
    Should Be Equal    ${metadata}[model]    34401A
    Should Be Equal    ${metadata}[driver_version]    26.07
    ${capabilities}=    Get Driver Capabilities
    List Should Contain Value    ${capabilities}    connection
    List Should Contain Value    ${capabilities}    dc_voltage_measurement
    ${model}=    Get Driver Capability Model    mode=static
    Should Be Equal    ${model}[driver][id]    rf_hp34401a
    Should Be True    ${model}[validation][valid]

Multiple Aliases Work
    Open Simulated DMM    alias=second    reading=2.0
    ${aliases}=    Get Open DMM Aliases
    List Should Contain Value    ${aliases}    default
    List Should Contain Value    ${aliases}    second
    Select DMM    default
    ${active}=    Get Active DMM Alias
    Should Be Equal    ${active}    default

Duplicate Alias Is Rejected
    Run Keyword And Expect Error    *already open*    Open Simulated DMM    alias=default

Unknown Alias Is Rejected
    Run Keyword And Expect Error    *not open*    Select DMM    missing

Error Queue Is Empty
    DMM Error Queue Should Be Empty
    DMM Should Have No Errors
