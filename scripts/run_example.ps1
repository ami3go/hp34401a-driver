param([Parameter(Mandatory=$true)][string]$Example, [Parameter(ValueFromRemainingArguments=$true)][string[]]$RobotArgs)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "$Root\.venv\Scripts\python.exe"; if (-not (Test-Path $Python)) { $Python = "python" }
if (-not [IO.Path]::IsPathRooted($Example)) { $Example = Join-Path "$Root\examples" $Example }
New-Item -ItemType Directory -Force "$Root\results" | Out-Null
$env:PYTHONPATH = $Root
& $Python -m robot --outputdir "$Root\results" @RobotArgs $Example
