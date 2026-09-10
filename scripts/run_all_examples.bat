@echo off
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if not exist "%ROOT%\results\examples" mkdir "%ROOT%\results\examples"
set "PYTHONPATH=%ROOT%"
"%PY%" -m robot --exclude hardware --outputdir "%ROOT%\results\examples" "%ROOT%\examples"
