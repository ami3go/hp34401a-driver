[CmdletBinding()]
param(
    [string]$OutputRoot,
    [ValidateSet('simulator')]
    [string]$Profile = 'simulator'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Arguments = @("$ProjectRoot\scripts\run_call_protocol_conformance.py", '--profile', $Profile)
if ($OutputRoot) { $Arguments += @('--output-root', $OutputRoot) }
& python @Arguments
exit $LASTEXITCODE
