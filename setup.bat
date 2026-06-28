@echo off
rem ============================================================
rem OmniFuse one-shot environment setup script (Windows)
rem Usage:  double-click setup.bat, or run it in Command Prompt
rem ============================================================
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================
echo  Starting OmniFuse setup
echo ============================================

rem --- 1. Check Python ----------------------------------------
set "PYTHON="
where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
    where py >nul 2>nul && set "PYTHON=py -3"
)
if not defined PYTHON (
    echo [ERROR] Python was not found.
    echo   Install it from https://www.python.org/downloads/
    echo   Be sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
%PYTHON% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.10 or later is required.
    pause
    exit /b 1
)
echo [OK] Detected Python

rem --- 2. Create the virtual environment ----------------------
if not exist ".venv" (
    echo Creating the virtual environment (.venv)...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
)
set "VENV_PY=.venv\Scripts\python.exe"

rem --- 3. Install dependencies in one go ----------------------
echo Installing dependencies (this may take a few minutes)...
"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install libraries.
    echo   Check your network connection and try again.
    pause
    exit /b 1
)
echo [OK] Installed dependencies

rem --- 4. Sanity check ----------------------------------------
"%VENV_PY%" -c "import pandas, openpyxl, matplotlib, requests, yaml, omnifuse.cli"
if errorlevel 1 (
    echo [ERROR] The sanity check failed.
    pause
    exit /b 1
)
echo [OK] All dependencies imported successfully

rem --- 5. Prepare the config file and launch command ----------
if not exist "config.yaml" if exist "config.example.yaml" (
    copy /y config.example.yaml config.yaml >nul
    echo [OK] Created config.yaml from config.example.yaml
)
(
    echo @echo off
    echo "%%~dp0.venv\Scripts\python.exe" -m omnifuse %%*
) > omnifuse.bat
echo [OK] Created the launch command omnifuse.bat

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo  Usage:
echo    omnifuse              ... launch the interactive menu
echo    omnifuse chart data.csv   ... format a chart
echo    omnifuse tone report.md   ... generate 3 tones of text
echo.
echo  See USER_GUIDE.md for how to configure API keys.
pause
