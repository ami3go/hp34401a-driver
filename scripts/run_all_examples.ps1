$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "$Root\.venv\Scripts\python.exe"; if (-not (Test-Path $Python)) { $Python = "python" }
New-Item -ItemType Directory -Force "$Root\results\examples" | Out-Null
$env:PYTHONPATH = $Root
& $Python -m robot --exclude hardware --outputdir "$Root\results\examples" "$Root\examples"
