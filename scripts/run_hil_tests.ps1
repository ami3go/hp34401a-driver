param([Parameter(ValueFromRemainingArguments=$true)][string[]]$RobotArgs)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "$Root\.venv\Scripts\python.exe"; if (-not (Test-Path $Python)) { $Python = "python" }
New-Item -ItemType Directory -Force "$Root\results\hil" | Out-Null
$env:PYTHONPATH = $Root
& $Python -m robot --outputdir "$Root\results\hil" @RobotArgs "$Root\tests\hil"
