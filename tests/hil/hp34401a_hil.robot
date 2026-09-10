*** Settings ***
Documentation     Opt-in HP 34401A hardware validation. Supply connection and safe limits explicitly.
Library           rf_hp34401a.Hp34401ALibrary
Library           Collections
Suite Setup       Open Hardware DMM
Suite Teardown    Close All DMMs
Test Tags         hardware    hil

*** Variables ***
${TRANSPORT}          VISA
${VISA_RESOURCE}      ${EMPTY}
${SERIAL_PORT}        ${EMPTY}
${LOW_LIMIT}          -1.0E-6
${HIGH_LIMIT}         1.0E-6
${RUN_SELF_TEST}      ${FALSE}

*** Keywords ***
Open Hardware DMM
    IF    '${TRANSPORT}' == 'VISA'
        Should Not Be Empty    ${VISA_RESOURCE}    VISA_RESOURCE must be supplied
        Open DMM Via VISA    ${VISA_RESOURCE}
    ELSE IF    '${TRANSPORT}' == 'SERIAL'
        Should Not Be Empty    ${SERIAL_PORT}    SERIAL_PORT must be supplied
        Open DMM Via Serial    ${SERIAL_PORT}
    ELSE
        Fail    TRANSPORT must be VISA or SERIAL
    END
    Log    Python and Robot versions are recorded in Robot output metadata
    Log    RF HP34401A version: ${EMPTY}

*** Test Cases ***
Identity And Terminal
    ${identity}=    Identify DMM
    Log Dictionary    ${identity}
    DMM Model Should Be 34401A
    ${terminal}=    Get DMM Input Terminal
    Log    Active terminal: ${terminal}

Optional Self Test
    IF    ${RUN_SELF_TEST}
        DMM Self Test Should Pass
    ELSE
        Skip    Self-test disabled by default for bench safety
    END

Safe DC Voltage Measurement
    ${value}=    Measure DC Voltage    range_value=AUTO    nplc=10
    DMM Reading Should Be Between    ${LOW_LIMIT}    ${HIGH_LIMIT}
    ${reading}=    Get Last DMM Reading
    Log Dictionary    ${reading}

Error Queue
    DMM Error Queue Should Be Empty
