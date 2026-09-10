#!/usr/bin/env pwsh
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $ScriptDir "validate_evidence.py") @args
exit $LASTEXITCODE
