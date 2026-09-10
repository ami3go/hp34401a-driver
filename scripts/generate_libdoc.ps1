$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "$Root\.venv\Scripts\python.exe"; if (-not (Test-Path $Python)) { $Python = "python" }
New-Item -ItemType Directory -Force "$Root\generated\libdoc" | Out-Null
$env:PYTHONPATH = $Root
& $Python -m robot.libdoc rf_hp34401a.Hp34401ALibrary "$Root\generated\libdoc\Hp34401ALibrary.html"
& $Python -m robot.libdoc -f XML rf_hp34401a.Hp34401ALibrary "$Root\generated\libdoc\Hp34401ALibrary.xml"
