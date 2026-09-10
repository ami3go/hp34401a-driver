@echo off
setlocal
python "%~dp0validate_evidence.py" %*
if errorlevel 1 exit /b %errorlevel%
