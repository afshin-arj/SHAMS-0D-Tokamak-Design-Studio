@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ------------------------------------------------------------
REM Run HH UI (Streamlit) with automatic dependency install
REM ------------------------------------------------------------

REM Go to project root (folder containing this script)
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

REM Prevent __pycache__ creation (repo hygiene law)
set "PYTHONDONTWRITEBYTECODE=1"

REM Ensure Python is available to create the venv (if needed)
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not on PATH. Please install Python 3.10+ and re-run.
    echo Tip: Install from https://www.python.org/ and check "Add python.exe to PATH".
    pause
    exit /b 1
)

REM Create virtual environment if missing
if not exist "%PY_EXE%" (
    echo .venv not found. Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Always ensure pip is up-to-date and install requirements
echo Updating pip...
"%PY_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    pause
    exit /b 1
)

echo Installing/updating requirements...
"%PY_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements.
    pause
    exit /b 1
)

REM Start Streamlit (blocking, visible)
echo Cleaning repo hygiene artifacts (caches/pyc)...
"%PY_EXE%" scripts\hygiene_clean.py --root . --report hygiene_clean_report.json

echo Starting Streamlit...
"%PY_EXE%" -m streamlit run ui/app.py --server.port 8501

echo Streamlit stopped.
exit /b 0
