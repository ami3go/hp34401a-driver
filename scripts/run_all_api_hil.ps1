param(
    [Parameter(Mandatory=$true)][string]$VisaResource,
    [string]$OutputRoot = "results/real_hardware_all_api",
    [string]$SerialPort = "",
    [switch]$FailOnExclusions,
    [string[]]$ExtraRobotArgs = @()
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$out = Join-Path $root "$OutputRoot/rf_hp34401a/$stamp"
$listener = Join-Path $root "tests/hil/support/RealHardwareApiListener.py"
$stateFile = Join-Path $out ".real_hardware_api_state.json"
New-Item -ItemType Directory -Force $out | Out-Null
$previousState = $env:RF_HP34401A_HIL_COVERAGE_STATE
$exitCode = 1
try {
    $env:RF_HP34401A_HIL_COVERAGE_STATE = $stateFile
    $args = @(
        "--listener", $listener,
        "--outputdir", $out,
        "--variable", "HIL_ENABLED:True",
        "--variable", "VISA_RESOURCE:$VisaResource",
        "--variable", "SERIAL_PORT:$SerialPort",
        "--variable", "FAIL_ON_EXCLUSIONS:$($FailOnExclusions.IsPresent.ToString())"
    ) + $ExtraRobotArgs + @("$root/tests/hil/verify_all_public_api_real_hardware.robot")
    & robot @args
    $exitCode = $LASTEXITCODE
}
finally {
    if ($null -eq $previousState) {
        Remove-Item Env:RF_HP34401A_HIL_COVERAGE_STATE -ErrorAction SilentlyContinue
    }
    else {
        $env:RF_HP34401A_HIL_COVERAGE_STATE = $previousState
    }
}
exit $exitCode
