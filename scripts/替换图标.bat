@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════╗
echo ║    Koto 图标替换工具                  ║
echo ╚════════════════════════════════════════╝
echo.

REM 检查是否有拖拽的文件
if "%~1"=="" (
    echo ❌ 请将图标文件拖拽到此批处理文件上
    echo.
    echo 📝 使用方法:
    echo    1. 找到你下载的图标文件（PNG、JPG、ICO等格式）
    echo    2. 将图标文件拖拽到这个批处理文件上
    echo    3. 松开鼠标，即可自动替换
    echo.
    pause
    exit /b 1
)

echo 📷 检测到图标文件: %~nx1
echo.
echo 正在替换图标...
python replace_icon.py "%~1"

if %errorlevel% equ 0 (
    echo.
    echo ╔════════════════════════════════════════╗
    echo ║  ✅ 图标替换完成！                    ║
    echo ╚════════════════════════════════════════╝
    echo.
    echo 💡 提示: 请重启Koto应用以应用新图标
    echo.
) else (
    echo.
    echo ❌ 替换失败，请检查文件格式
    echo.
)

pause
