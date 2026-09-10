@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
python "%PROJECT_ROOT%\scripts\run_call_protocol_conformance.py" %*
exit /b %ERRORLEVEL%
