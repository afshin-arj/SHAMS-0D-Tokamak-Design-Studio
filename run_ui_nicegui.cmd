@echo off

setlocal ENABLEDELAYEDEXPANSION



REM SHAMS NiceGUI — double-click safe (persistent window + browser)



cd /d "%~dp0"

title SHAMS NiceGUI



set "VENV_DIR=.venv"

set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

set "PYTHONDONTWRITEBYTECODE=1"

set "PYTHONUNBUFFERED=1"



where python >nul 2>&1

if errorlevel 1 goto :no_python



if not exist "%PY_EXE%" goto :create_venv

goto :deps_check



:create_venv

echo .venv not found. Creating virtual environment...

python -m venv "%VENV_DIR%"

if errorlevel 1 goto :venv_fail

goto :deps_check



:deps_check

if /I "%SHAMS_SKIP_DEPS%"=="1" goto :launch



echo Updating pip...

call "%PY_EXE%" -m pip install --upgrade pip

if errorlevel 1 goto :pip_fail



echo Installing/updating requirements...

call "%PY_EXE%" -m pip install -r requirements.txt

if errorlevel 1 goto :req_fail



if not exist "scripts\hygiene_clean.py" goto :launch

echo Cleaning repo hygiene artifacts...

call "%PY_EXE%" scripts\hygiene_clean.py --root "%CD%" --report hygiene_clean_report.json

if errorlevel 1 echo WARNING: hygiene_clean reported issues - continuing anyway.



:launch

echo.

echo ============================================================

echo  Starting SHAMS NiceGUI

echo  Default URL: http://127.0.0.1:8080 - auto-fallback if busy

echo  Browser opens automatically - close this window to stop.

echo ============================================================

echo.



call "%PY_EXE%" -u ui_nicegui\launch.py

set "EXITCODE=%ERRORLEVEL%"



if "%EXITCODE%"=="0" goto :end_pause

echo.

echo ERROR: NiceGUI exited with code %EXITCODE%.

echo If port 8080 is busy, try: set SHAMS_NICEGUI_PORT=8090

goto :end_pause



:no_python

echo ERROR: Python is not on PATH. Install Python 3.10+ and re-run.

echo Tip: install from python.org and check Add python.exe to PATH.

goto :end_pause



:venv_fail

echo ERROR: Failed to create virtual environment.

goto :end_pause



:pip_fail

echo ERROR: pip upgrade failed.

goto :end_pause



:req_fail

echo ERROR: requirements install failed.

goto :end_pause



:end_pause

echo.

echo Press any key to close this window...

pause >nul

exit /b 0

