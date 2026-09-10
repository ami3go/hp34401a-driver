*** Settings ***
Library    rf_hp34401a.plugin.Hp34401APluginProvider

*** Test Cases ***
Plugin Descriptor Is Available Without Hardware
    ${descriptor}=    Get Descriptor
    Should Be Equal    ${descriptor}[plugin_id]    rf_hp34401a
