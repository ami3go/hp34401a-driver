$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "py" }
if ($Python -eq "py") { & py -3 -m venv "$Root\.venv" } else { & $Python -m venv "$Root\.venv" }
& "$Root\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$Root\.venv\Scripts\python.exe" -m pip install -e "$Root[dev,hardware]"
& "$Root\.venv\Scripts\python.exe" --version
& "$Root\.venv\Scripts\python.exe" -m robot --version
