@echo off
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if not exist "%ROOT%\generated\libdoc" mkdir "%ROOT%\generated\libdoc"
set "PYTHONPATH=%ROOT%"
"%PY%" -m robot.libdoc rf_hp34401a.Hp34401ALibrary "%ROOT%\generated\libdoc\Hp34401ALibrary.html" || exit /b 1
"%PY%" -m robot.libdoc -f XML rf_hp34401a.Hp34401ALibrary "%ROOT%\generated\libdoc\Hp34401ALibrary.xml"
