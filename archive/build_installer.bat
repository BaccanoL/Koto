@echo off
REM ============================================================
REM Koto 应用 - 一键生成安装包
REM ============================================================
REM 
REM 功能: 自动为 Windows 电脑生成独立安装包
REM 使用: 双击运行此脚本
REM 
REM ============================================================

setlocal enabledelayedexpansion

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 打印标题
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║         Koto 应用 - Windows 安装包生成器                  ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 检查 Python
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未找到，请先安装 Python 3.8+
    echo 📌 访问: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo ✅ Python 环境就绪
echo.

REM 检查 pip
echo [2/5] 检查 pip 包管理器...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip 未找到
    pause
    exit /b 1
)
echo ✅ pip 就绪
echo.

REM 检查虚拟环境
echo [3/5] 配置虚拟环境...
if not exist .venv (
    echo 创建虚拟环境...
    python -m venv .venv
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 虚拟环境激活失败
    pause
    exit /b 1
)
echo ✅ 虚拟环境已激活
echo.

REM 安装/升级必需包
echo [4/5] 安装必需的包...
pip install --upgrade pip setuptools wheel >nul 2>&1

echo 安装关键依赖...
pip install pyinstaller nuitka >nul 2>&1
if errorlevel 1 (
    echo ⚠️  某些包安装失败，继续尝试...
)
echo ✅ 必需包已配置
echo.

REM 运行构建脚本
echo [5/5] 生成安装包...
echo.

python build_installer.py
if errorlevel 1 (
    echo.
    echo ❌ 安装包生成失败！
    echo 📋 错误信息已保存到日志文件
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    ✅ 完成！                              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📁 安装包位置: %SCRIPT_DIR%installer
echo.
echo 按任意键打开安装包文件夹...
pause

REM 打开安装包文件夹
if exist "%SCRIPT_DIR%installer" (
    start explorer "%SCRIPT_DIR%installer"
) else (
    echo ❌ 找不到安装包文件夹
    pause
)

endlocal
