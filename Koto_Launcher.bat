@echo off
setlocal EnableDelayedExpansion

REM ==========================================
REM Koto 独立启动器 v2.0
REM ==========================================

cd /d "%~dp0"
title Koto Launcher
color 0A

:MENU
cls
echo ==========================================
echo       Koto IDP 智能文档处理平台
echo ==========================================
echo.
echo  [1] 启动 Koto (桌面模式 - 推荐)
echo  [2] 启动 Koto (服务器模式 - 无窗口)
echo  [3] 修复/安装依赖环境
echo  [4] 清理缓存文件
echo  [5] 退出
echo.
echo ==========================================
set /p choice="请选择操作 [1-5]: "

if "%choice%"=="1" goto START_DESKTOP
if "%choice%"=="2" goto START_SERVER
if "%choice%"=="3" goto INSTALL_DEPS
if "%choice%"=="4" goto CLEAN_CACHE
if "%choice%"=="5" exit

goto MENU

:CHECK_ENV
echo.
echo [检查环境]...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    echo  - 检测到虚拟环境: .venv
) else (
    set "PYTHON_CMD=python"
    echo  - 未检测到虚拟环境，尝试使用系统 Python
    %PYTHON_CMD% --version >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python 环境！请安装 Python 3.10+ 或创建虚拟环境。
        pause
        goto MENU
    )
)
goto :eof

:START_DESKTOP
call :CHECK_ENV
echo.
echo [启动] 正在启动 Koto 桌面版...
echo 日志将保存在 logs/ 目录
echo.
"%PYTHON_CMD%" koto_app.py
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出 (代码: %errorlevel%)
    pause
)
goto MENU

:START_SERVER
call :CHECK_ENV
echo.
echo [启动] 正在启动 Koto 服务器模式...
echo 请在浏览器访问 http://127.0.0.1:5000
echo.
"%PYTHON_CMD%" koto_app.py --server
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出 (代码: %errorlevel%)
    pause
)
goto MENU

:INSTALL_DEPS
call :CHECK_ENV
echo.
echo [修复] 正在安装/更新依赖...
if exist "requirements.txt" (
    "%PYTHON_CMD%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [失败] 依赖安装失败
    ) else (
        echo [成功] 依赖安装完成
    )
) else (
    echo [错误] 未找到 requirements.txt
)
pause
goto MENU

:CLEAN_CACHE
echo.
echo [清理] 正在清理临时文件...
if exist "__pycache__" rmdir /s /q "__pycache__"
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
echo [成功] 清理完成
timeout /t 2 >nul
goto MENU
