@echo off
title Koto Stopper
cd /d "%~dp0"
echo Stopping Koto...

wmic process where "CommandLine like '%%koto_app.py%%'" call terminate >nul 2>&1

if %errorlevel% equ 0 (
    echo [SUCCESS] Koto has been stopped.
) else (
    echo [INFO] No running Koto process found.
)

timeout /t 2 >nul
exit
