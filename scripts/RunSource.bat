@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."

REM 兜底：如果上级目录没有 koto_app.py，则使用当前目录
if not exist "%ROOT_DIR%\koto_app.py" set "ROOT_DIR=%SCRIPT_DIR%"

cd /d "%ROOT_DIR%"
echo Starting Koto from Source Code...
echo Log will be saved to logs/runtime_*.log
echo Project Root: %CD%

if exist ".venv\Scripts\python.exe" (
    echo Using Virtual Environment .venv ...
    ".venv\Scripts\python.exe" koto_app.py
) else (
    echo No .venv found, trying system Python...
    python koto_app.py
)

if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)

endlocal
