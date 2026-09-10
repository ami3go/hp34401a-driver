@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all_api_hil.ps1" %*
exit /b %ERRORLEVEL%
