@echo off
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if not exist "%ROOT%\results\hil" mkdir "%ROOT%\results\hil"
set "PYTHONPATH=%ROOT%"
"%PY%" -m robot --outputdir "%ROOT%\results\hil" %* "%ROOT%\tests\hil"
