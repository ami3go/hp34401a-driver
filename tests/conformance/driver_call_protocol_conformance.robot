*** Settings ***
Documentation     RFDS-019 v1.1 public-call and SCPI protocol conformance.
Library           rf_hp34401a.Hp34401ALibrary
Library           ${CURDIR}${/}support${/}ConformanceHarness.py
Resource          ${CURDIR}${/}resources${/}conformance_variables.resource
Resource          ${CURDIR}${/}resources${/}conformance_keywords.resource
Suite Teardown    Close All DMMs

*** Test Cases ***
All Public Driver Calls And Protocol Vectors Shall Conform
    Execute RFDS-019 Software Conformance    ${CONFORMANCE_OUTPUT_DIR}
