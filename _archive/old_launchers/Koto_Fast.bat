@echo off
title Koto 极速启动器 v2.0
color 0f
cls
echo.
echo  ============================================================
echo     Koto 智能 极速启动 v2.0 (Powered by Gemini)
echo  ============================================================
echo.
echo  正在清理临时环境...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Koto - *" >nul 2>&1
echo.

if exist ".venv\Scripts\python.exe" (
    echo  [Info] 检测到专用虚拟环境 .venv
    echo  [Init] 启动 Koto_Fast_Launch.py ...
    echo.
    ".venv\Scripts\python.exe" "Koto_Fast_Launch.py"
) else (
    echo  [Info] 未检测到 .venv，尝试使用系统 Python
    python "Koto_Fast_Launch.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [Error] 启动似乎遇到问题，错误代码: %ERRORLEVEL%
    pause
)
