@echo off
setlocal
cd /d "%~dp0"
if not exist ".tmp" mkdir ".tmp"
set "TEMP=%~dp0.tmp"
set "TMP=%~dp0.tmp"
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))" || goto :fail
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv || goto :fail
)
".venv\Scripts\python.exe" -m pip --version >nul 2>&1 || (
  ".venv\Scripts\python.exe" -m ensurepip --upgrade || goto :fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
".venv\Scripts\python.exe" main.py
exit /b %errorlevel%
:fail
echo Setup failed. Check Python 3.12 and network access.
pause
exit /b 1
