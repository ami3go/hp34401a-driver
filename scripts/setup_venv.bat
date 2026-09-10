@echo off
setlocal
set "ROOT=%~dp0.."
py -3 -m venv "%ROOT%\.venv" || exit /b 1
"%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip || exit /b 1
"%ROOT%\.venv\Scripts\python.exe" -m pip install -e "%ROOT%[dev,hardware]" || exit /b 1
"%ROOT%\.venv\Scripts\python.exe" --version
"%ROOT%\.venv\Scripts\python.exe" -m robot --version
