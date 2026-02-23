@echo off
setlocal EnableDelayedExpansion
title Koto Starter
cd /d "%~dp0"

echo ==========================================
echo        Starting Koto Application...
echo ==========================================

REM 1. Check for Virtual Environment
if exist ".venv\Scripts\pythonw.exe" (
    echo [INFO] Using Virtual Environment (.venv)
    start "" ".venv\Scripts\pythonw.exe" koto_app.py
    exit
)

REM 2. Check for System Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Using System Python
    start "" pythonw koto_app.py
    exit
)

REM 3. Error Handling
echo [ERROR] Python environment not found!
echo Please insure Python 3.10+ is installed and added to PATH.
echo Or run "Koto_Launcher.bat" to inspect environment.
pause
