@echo off
setlocal
if "%~1"=="" (echo Usage: %~nx0 example.robot [robot arguments] & exit /b 2)
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set "EXAMPLE=%~1"
shift
if not exist "%EXAMPLE%" set "EXAMPLE=%ROOT%\examples\%EXAMPLE%"
if not exist "%ROOT%\results" mkdir "%ROOT%\results"
set "PYTHONPATH=%ROOT%"
"%PY%" -m robot --outputdir "%ROOT%\results" %* "%EXAMPLE%"
