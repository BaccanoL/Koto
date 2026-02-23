@echo off
REM ==================== Koto Desktop 启动脚本 ====================
REM 独立桌面应用启动器 - 无需Flask
REM 类似VSCode、微信的专业应用程序

setlocal enabledelayedexpansion

cd /d %~dp0

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║                                                        ║
echo ║          Koto Desktop 应用启动器 v1.0.0              ║
echo ║       智能、自适应、独立的桌面应用程序              ║
echo ║                                                        ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM 检查 Python
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo.
    echo 请从以下网址下载 Python 3.8+:
    echo   https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo ✓ Python 已找到
python --version

REM 创建虚拟环境（如果不存在）
if not exist ".venv" (
    echo.
    echo [2/4] 创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo ✓ 虚拟环境已创建
) else (
    echo [2/4] 虚拟环境已存在，跳过
)

REM 激活虚拟环境
echo.
echo [3/4] 激活虚拟环境...
call .venv\Scripts\activate.bat
echo ✓ 虚拟环境已激活

REM 检查依赖
echo.
echo [4/4] 检查依赖...
pip list | findstr /i pyside6 >nul 2>&1
if errorlevel 1 (
    echo ⏳ 正在安装依赖，请稍候...
    pip install -q -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
    echo ✓ 依赖已安装
) else (
    echo ✓ 所有依赖已就绪
)

REM 启动桌面应用
echo.
echo ✓ 所有检查完成，正在启动 Koto Desktop...
echo.

REM 创建日志目录
if not exist "logs" mkdir logs

REM 启动应用
python koto_desktop.py

if errorlevel 1 (
    echo.
    echo ❌ 应用启动失败，请检查日志
    pause
)

endlocal
