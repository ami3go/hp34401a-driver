@echo off
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if not exist "%ROOT%\results\tests" mkdir "%ROOT%\results\tests"
pushd "%ROOT%"
set "PYTHONPATH=%ROOT%"
"%PY%" scripts\validate_ai_contract.py || (popd & exit /b 1)
"%PY%" scripts\validate_call_protocol_conformance.py || (popd & exit /b 1)
"%PY%" -m pytest || (popd & exit /b 1)
"%PY%" scripts\run_call_protocol_conformance.py || (popd & exit /b 1)
"%PY%" -m robot --outputdir "%ROOT%\results\tests" tests\robot
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
