@echo off
chcp 65001 >nul
echo ==========================================
echo   Ollama + Qwen 本地模型安装脚本
echo ==========================================
echo.
echo   本地模型是可选功能，用于加速任务分类
echo   如果不安装，Koto 会使用内置规则引擎
echo.

REM 检查 Ollama 是否已安装
where ollama >nul 2>&1
if %errorlevel%==0 (
    echo [✓] Ollama 已安装
    goto :check_model
)

echo [!] Ollama 未安装
echo.
echo 请选择安装方式：
echo   1. 自动下载安装（需要稳定网络，约1.2GB）
echo   2. 手动安装（推荐，打开下载页面）
echo   3. 跳过（使用内置规则引擎）
echo.
set /p choice=请输入选项 (1/2/3): 

if "%choice%"=="1" goto :auto_install
if "%choice%"=="2" goto :manual_install
if "%choice%"=="3" goto :skip_ollama
goto :manual_install

:auto_install
echo.
echo [*] 正在下载 Ollama...
echo     （如果下载很慢，建议按 Ctrl+C 取消，选择手动安装）
powershell -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe'"
if exist "%TEMP%\OllamaSetup.exe" (
    echo [*] 正在安装...
    start /wait "" "%TEMP%\OllamaSetup.exe" /S
    timeout /t 5 >nul
    goto :check_install
) else (
    echo [!] 下载失败，请尝试手动安装
    goto :manual_install
)

:manual_install
echo.
echo [*] 正在打开 Ollama 下载页面...
start https://ollama.com/download
echo.
echo 请完成以下步骤：
echo   1. 下载 Windows 版本
echo   2. 运行安装程序
echo   3. 安装完成后，重新运行此脚本
echo.
pause
exit /b 0

:check_install
where ollama >nul 2>&1
if %errorlevel%==0 (
    echo [✓] Ollama 安装成功
    goto :check_model
) else (
    echo [!] 安装后未检测到 ollama，可能需要重启终端
    echo     请重新打开命令行窗口后再次运行此脚本
    pause
    exit /b 1
)

:skip_ollama
echo.
echo [*] 跳过 Ollama 安装
echo     Koto 将使用内置规则引擎进行任务分类
echo     （功能完全正常，只是分类可能略慢）
echo.
pause
exit /b 0

:check_model
echo.
echo [*] 检查 Ollama 服务...

REM 启动 Ollama 服务（如果没运行）
tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul
if %errorlevel%==1 (
    echo [*] 启动 Ollama 服务...
    start "" ollama serve
    timeout /t 3 >nul
)

echo.
echo [*] 下载 Qwen2.5:0.5b 模型（约 400MB）...
echo     这是最快的中文模型，用于任务分类
ollama pull qwen2.5:0.5b

if %errorlevel%==0 (
    echo.
    echo [✓] 模型下载成功！
) else (
    echo.
    echo [!] 模型下载失败
    echo     可以稍后手动运行: ollama pull qwen2.5:0.5b
)

echo.
echo ==========================================
echo   安装完成！
echo ==========================================
echo.
echo   Koto 会自动检测并使用本地模型
echo   如果 Ollama 未运行，会自动使用内置引擎
echo.
pause
