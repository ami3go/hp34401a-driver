*** Settings ***
Library    rf_hp34401a.Hp34401ALibrary

*** Test Cases ***
Discover Static Measurement Capabilities
    ${caps}=    Find Driver Capabilities    capability_id=measure.    maximum_risk=low
    Should Not Be Empty    ${caps}
