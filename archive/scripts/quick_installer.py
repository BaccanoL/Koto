#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速 Windows 安装包生成器 - 简化版本
跳过耗时的编译，直接打包必需文件
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          Koto 应用 - 快速安装包生成器                      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # 配置
    project_root = Path(__file__).parent
    installer_dir = project_root / "installer"
    package_dir = installer_dir / "Koto_v1.0.0"
    
    # 清理旧的安装包
    if installer_dir.exists():
        shutil.rmtree(installer_dir)
    
    # 创建目录
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print("[1/5] 准备应用文件...")
    
    # 需要包含的文件和文件夹
    include_items = [
        ("koto_app.py", "file"),
        ("requirements.txt", "file"),
        ("RunSource.bat", "file"),
        ("config", "dir"),
        ("assets", "dir"),
        ("web", "dir"),
        ("models", "dir"),
    ]
    
    for item, item_type in include_items:
        src = project_root / item
        if not src.exists():
            print(f"  ⚠️  {item} 不存在，跳过")
            continue
        
        dst = package_dir / item
        
        if item_type == "file":
            shutil.copy2(src, dst)
            print(f"  ✅ 复制文件: {item}")
        elif item_type == "dir":
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  ✅ 复制目录: {item}")
    
    print()
    print("[2/5] 创建启动脚本...")
    
    # run.bat
    run_bat = package_dir / "run.bat"
    run_bat.write_text("""@echo off
REM Koto 应用启动脚本
SetLocal EnableDelayedExpansion

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python
    echo 请先安装 Python 3.8+ 从 https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt -q

REM 启动应用
echo 启动 Koto 应用...
python koto_app.py

pause
""", encoding='utf-8')
    print("  ✅ 创建 run.bat")
    
    # run-fast.bat (简化版，假设已安装依赖)
    run_fast = package_dir / "run-fast.bat"
    run_fast.write_text("""@echo off
REM Koto 应用快速启动脚本 (假设依赖已安装)
SetLocal EnableDelayedExpansion

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

python koto_app.py
""", encoding='utf-8')
    print("  ✅ 创建 run-fast.bat")
    
    # run.ps1
    run_ps1 = package_dir / "run.ps1"
    run_ps1.write_text("""# Koto 应用 PowerShell 启动脚本
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 检查 Python
python --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 未找到 Python"
    Write-Host "请先安装 Python 3.8+ 从 https://www.python.org/downloads/"
    exit 1
}

# 安装依赖
Write-Host "安装依赖..."
pip install -r requirements.txt -q

# 启动应用
Write-Host "启动 Koto 应用..."
python koto_app.py
""", encoding='utf-8')
    print("  ✅ 创建 run.ps1")
    
    print()
    print("[3/5] 创建说明文档...")
    
    # README
    readme = package_dir / "README.txt"
    readme.write_text("""╔════════════════════════════════════════════════════════════╗
║                                                            ║
║                  Koto 应用 v1.0.0                          ║
║              AI 助手与文件处理系统                         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

📖 快速开始
═════════════════════════════════════════════════════════════

1️⃣  首次启动
   双击 run.bat 文件
   或在 PowerShell 中运行: .\\run.ps1

   首次启动会自动安装必需的 Python 包，可能需要 2-5 分钟

2️⃣  后续启动（依赖已安装）
   双击 run.bat
   或在 PowerShell 中运行: .\\run-fast.bat

3️⃣  手动启动
   python koto_app.py

═════════════════════════════════════════════════════════════

⚠️  系统要求
═════════════════════════════════════════════════════════════

必需:
✓ Windows 7 SP1 或更高版本
✓ Python 3.8 或更高版本
  下载: https://www.python.org/downloads/
  安装时勾选 "Add Python to PATH"

内存 & 磁盘:
✓ 最少 1 GB RAM
✓ 最少 500 MB 磁盘空间（包括 Python）

═════════════════════════════════════════════════════════════

🔧 故障排查
═════════════════════════════════════════════════════════════

问题: "Python 未找到"
->  安装 Python 3.8+
->  确保在安装时勾选 "Add Python to PATH"
->  重启 Windows

问题: "pip 失败"
->  python -m pip install --upgrade pip
->  重试

问题: 应用无法启动
->  查看命令行窗口中的错误信息
->  检查 logs 文件夹中的日志文件

═════════════════════════════════════════════════════════════

📋 文件说明
═════════════════════════════════════════════════════════════

koto_app.py          - 主应用脚本
requirements.txt     - Python 依赖列表
run.bat             - Windows 启动脚本（推荐）
run.ps1             - PowerShell 启动脚本
run-fast.bat        - 快速启动脚本（依赖已安装）
config/             - 配置文件
assets/             - 资源文件
web/                - Web 组件
models/             - AI 模型

═════════════════════════════════════════════════════════════

💡 提示
═════════════════════════════════════════════════════════════

• 首次运行需要安装 Python 包，请耐心等待
• 应用会在浏览器中打开本地 Web 界面
• 详细日志保存在 logs/ 文件夹中
• 配置文件保存在 config/ 文件夹中

═════════════════════════════════════════════════════════════

祝您使用愉快! 🎉

更多帮助: 查看应用内帮助菜单或项目文档
""", encoding='utf-8-sig')
    print("  ✅ 创建 README.txt")
    
    # INSTALL.txt
    install_txt = package_dir / "INSTALL.txt"
    install_txt.write_text("""Koto 应用 - 安装和运行指南

═════════════════════════════════════════════════════════════
第一步: 安装 Python (仅需一次)
═════════════════════════════════════════════════════════════

1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.10 或更高版本 (Windows 版)
3. 运行安装程序
4. ⚠️ 重要: 勾选 "Add Python to PATH" ✅
5. 点击 "Install Now"
6. 等待安装完成
7. 重启电脑

验证安装:
  打开命令提示符，输入: python --version
  应该看到: Python 3.x.x

═════════════════════════════════════════════════════════════
第二步: 运行 Koto 应用
═════════════════════════════════════════════════════════════

方式一: 批处理脚本 (推荐)
  1. 双击 run.bat
  2. 首次运行会自动安装依赖 (耐心等待)
  3. 应用会自动启动

方式二: PowerShell
  1. 右键点击文件夹空白处
  2. 选择 "在此处打开 PowerShell"
  3. 输入: .\\run.ps1
  4. 确认权限提示

方式三: 命令提示符
  1. 按 Win+R
  2. 输入: cmd
  3. 进入应用目录
  4. 输入: python koto_app.py

═════════════════════════════════════════════════════════════
其他信息
═════════════════════════════════════════════════════════════

日志文件:    logs/ 文件夹
配置文件:    config/ 文件夹
问题反馈:    查看 README.txt

═════════════════════════════════════════════════════════════
""", encoding='utf-8-sig')
    print("  ✅ 创建 INSTALL.txt")
    
    print()
    print("[4/5] 创建 ZIP 包...")
    
    # 创建 ZIP
    zip_path = installer_dir / "Koto_v1.0.0_Portable.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(installer_dir)
                zipf.write(file_path, arcname)
    
    zip_size = zip_path.stat().st_size / (1024 * 1024)
    print(f"  ✅ 创建 ZIP: {zip_path.name} ({zip_size:.2f} MB)")
    
    print()
    print("[5/5] 生成总结...")
    
    # 生成总结
    summary = installer_dir / "README.txt"
    summary.write_text("""╔════════════════════════════════════════════════════════════╗
║                   Koto 安装包已生成                       ║
╚════════════════════════════════════════════════════════════╝

📦 文件说明
═════════════════════════════════════════════════════════════

1. Koto_v1.0.0_Portable.zip
   • 完整的便携式包
   • 解压即用，适合分发和携带
   • 支持离线使用（部分功能）

2. Koto_v1.0.0/ 文件夹
   • 解压后的应用文件夹
   • 可直接运行 (无需 ZIP)

═════════════════════════════════════════════════════════════

🚀 使用方式
═════════════════════════════════════════════════════════════

方式 A: 使用 ZIP 包 (推荐)
--------
1. 将 Koto_v1.0.0_Portable.zip 复制到目标电脑
2. 右键 -> 解压到此处
3. 打开解压后的文件夹
4. 双击 run.bat 启动

方式 B: 直接使用文件夹
--------
1. 复制整个 Koto_v1.0.0 文件夹到目标位置
2. 打开文件夹
3. 双击 run.bat 启动

═════════════════════════════════════════════════════════════

✅ 特点
═════════════════════════════════════════════════════════════

✓ 无需安装程序
✓ 无需管理员权限
✓ 可复制到 U 盘随处使用
✓ 支持多个版本共存
✓ 自动安装 Python 依赖
✓ 完全离线可用

═════════════════════════════════════════════════════════════

⚙️ 系统要求
═════════════════════════════════════════════════════════════

✓ Windows 7 SP1 或更高版本
✓ Python 3.8 或更高版本（会自动提示安装）
✓ 1 GB RAM 最低要求
✓ 500 MB 磁盘空间

═════════════════════════════════════════════════════════════

下一步: 打开 Koto_v1.0.0 文件夹，查看 README.txt

═════════════════════════════════════════════════════════════
""", encoding='utf-8-sig')
    print("  ✅ 创建总结文档")
    
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                  ✅ 安装包生成完成！                        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print(f"📁 位置: {installer_dir}")
    print()
    print("📦 输出文件:")
    print(f"   1. {zip_path.name} ({zip_size:.2f} MB) - 便携式包")
    print(f"   2. {package_dir.name}/ - 解压后的文件夹")
    print()
    print("🚀 下一步:")
    print("   1. 复制 ZIP 文件到目标电脑")
    print("   2. 解压文件")
    print("   3. 打开文件夹，双击 run.bat")
    print()
    print("✨ 准备好分发到任何 Windows 电脑！")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
