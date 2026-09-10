$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "$Root\.venv\Scripts\python.exe"; if (-not (Test-Path $Python)) { $Python = "python" }
New-Item -ItemType Directory -Force "$Root\results\tests" | Out-Null
Push-Location $Root
try {
    $env:PYTHONPATH = $Root
    & $Python scripts\validate_ai_contract.py; if ($LASTEXITCODE) { exit $LASTEXITCODE }
    & $Python scripts\validate_call_protocol_conformance.py; if ($LASTEXITCODE) { exit $LASTEXITCODE }
    & $Python -m pytest; if ($LASTEXITCODE) { exit $LASTEXITCODE }
    & $Python scripts\run_call_protocol_conformance.py; if ($LASTEXITCODE) { exit $LASTEXITCODE }
    & $Python -m robot --outputdir "$Root\results\tests" tests\robot
    exit $LASTEXITCODE
} finally { Pop-Location }
