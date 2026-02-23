#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Koto 应用 - Windows 安装包生成器
自动化构建独立的可执行文件和安装程序
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

# 配置
APP_NAME = "Koto"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Koto - AI 助手与文件处理系统"
AUTHOR = "Koto Team"
COMPANY = "Koto"

# 目录配置
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
INSTALLER_DIR = PROJECT_ROOT / "installer"

# 源文件
MAIN_SCRIPT = PROJECT_ROOT / "koto_app.py"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"

# PyInstaller 配置
HIDDEN_IMPORTS = [
    "web",
    "adaptive_agent",
    "adaptive_agent_api",
    "google.genai",
    "PySide6",
    "flask",
    "requests",
    "httpx",
]

COLLECT_DIRS = [
    "config",
    "assets",
    "web",
    "models",
    "docs",
]

class InstallerBuilder:
    """Windows 安装包生成器"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = PROJECT_ROOT / f"build_{self.timestamp}.log"
        
    def log(self, message):
        """记录日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
    
    def step(self, title):
        """打印步骤标题"""
        self.log("")
        self.log("=" * 60)
        self.log(f"  {title}")
        self.log("=" * 60)
    
    def check_prerequisites(self):
        """检查前置条件"""
        self.step("1. 检查前置条件")
        
        # 检查 Python
        self.log(f"✅ Python 版本: {sys.version}")
        
        # 检查必需的要求文件
        if not REQUIREMENTS_FILE.exists():
            self.log(f"❌ 错误: 找不到 {REQUIREMENTS_FILE}")
            return False
        self.log(f"✅ 找到 requirements.txt")
        
        # 检查主脚本
        if not MAIN_SCRIPT.exists():
            self.log(f"❌ 错误: 找不到 {MAIN_SCRIPT}")
            return False
        self.log(f"✅ 找到主脚本: {MAIN_SCRIPT}")
        
        # 检查 PyInstaller
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "pyinstaller"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log("✅ PyInstaller 已安装")
            else:
                self.log("⚠️  PyInstaller 未安装，正在安装...")
                self._run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
        except Exception as e:
            self.log(f"❌ 检查 PyInstaller 失败: {e}")
            return False
        
        # 检查 NSIS (可选)
        nsis_path = Path("C:\\Program Files (x86)\\NSIS\\makensis.exe")
        if nsis_path.exists():
            self.log(f"✅ 找到 NSIS: {nsis_path}")
        else:
            self.log("⚠️  NSIS 未安装 (可选，用于生成 .exe 安装程序)")
        
        return True
    
    def clean_previous_builds(self):
        """清理之前的构建"""
        self.step("2. 清理之前的构建")
        
        for dir_path in [BUILD_DIR, DIST_DIR, INSTALLER_DIR]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                self.log(f"✅ 删除 {dir_path}")
        
        # 清理 .spec 文件
        for spec_file in PROJECT_ROOT.glob("*.spec"):
            spec_file.unlink()
            self.log(f"✅ 删除 {spec_file.name}")
    
    def install_dependencies(self):
        """安装依赖"""
        self.step("3. 安装依赖")
        
        self.log(f"从 {REQUIREMENTS_FILE} 安装依赖...")
        
        try:
            self._run_command([
                sys.executable, "-m", "pip", "install",
                "-r", str(REQUIREMENTS_FILE),
                "--upgrade"
            ])
            self.log("✅ 依赖安装完成")
            return True
        except Exception as e:
            self.log(f"❌ 安装依赖失败: {e}")
            return False
    
    def build_executable(self):
        """构建独立可执行文件"""
        self.step("4. 构建可执行文件 (.exe)")
        
        # 准备集合目录参数
        collect_args = []
        for dir_name in COLLECT_DIRS:
            dir_path = PROJECT_ROOT / dir_name
            if dir_path.exists():
                collect_args.extend(["--collect-all", dir_name])
        
        # 准备隐藏导入参数
        hidden_imports_args = []
        for import_name in HIDDEN_IMPORTS:
            hidden_imports_args.extend(["--hidden-import", import_name])
        
        # 构建 PyInstaller 命令
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", APP_NAME,
            "--onefile",  # 单个可执行文件
            "--windowed",  # 无控制台窗口
            "--add-data", f"{PROJECT_ROOT / 'config'}:config",
            "--add-data", f"{PROJECT_ROOT / 'assets'}:assets",
            "--add-data", f"{PROJECT_ROOT / 'web'}:web",
            "--icon", str(PROJECT_ROOT / "assets" / "icon.ico") if (PROJECT_ROOT / "assets" / "icon.ico").exists() else None,
            "--distpath", str(DIST_DIR),
            "--buildpath", str(BUILD_DIR),
            "--specpath", str(PROJECT_ROOT),
            "--console",  # 允许调试时显示控制台
        ]
        
        # 添加可选的参数
        cmd.extend(collect_args)
        cmd.extend(hidden_imports_args)
        
        # 添加主脚本
        cmd.append(str(MAIN_SCRIPT))
        
        # 移除 None 值
        cmd = [x for x in cmd if x is not None]
        
        self.log(f"执行命令: PyInstaller")
        self.log(f"  参数数量: {len(cmd)}")
        
        try:
            self._run_command(cmd)
            
            exe_path = DIST_DIR / f"{APP_NAME}.exe"
            if exe_path.exists():
                file_size = exe_path.stat().st_size / (1024 * 1024)
                self.log(f"✅ 可执行文件已生成")
                self.log(f"   位置: {exe_path}")
                self.log(f"   大小: {file_size:.2f} MB")
                return True
            else:
                self.log(f"❌ 可执行文件构建失败")
                return False
                
        except Exception as e:
            self.log(f"❌ 构建失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def create_package_structure(self):
        """创建安装包结构"""
        self.step("5. 创建安装包结构")
        
        # 创建安装包目录
        package_dir = INSTALLER_DIR / f"Koto_v{APP_VERSION}"
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制可执行文件
        exe_src = DIST_DIR / f"{APP_NAME}.exe"
        exe_dst = package_dir / f"{APP_NAME}.exe"
        if exe_src.exists():
            shutil.copy2(exe_src, exe_dst)
            self.log(f"✅ 复制可执行文件")
        
        # 创建批处理启动脚本
        batch_file = package_dir / "run.bat"
        batch_content = f"""@echo off
REM Koto 应用启动脚本
SetLocal EnableDelayedExpansion

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0

REM 启动应用
start "" "!SCRIPT_DIR!{APP_NAME}.exe"

REM 等待程序启动
timeout /t 2 /nobreak
"""
        batch_file.write_text(batch_content, encoding="utf-8")
        self.log(f"✅ 创建启动脚本: {batch_file.name}")
        
        # 创建快速启动脚本 (PowerShell)
        ps_file = package_dir / "run.ps1"
        ps_content = f"""# Koto 应用启动脚本
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "{APP_NAME}.exe"

if (Test-Path $exePath) {{
    Start-Process -FilePath $exePath -WorkingDirectory $scriptDir -WindowStyle Normal
    Write-Host "Koto 应用已启动。"
}} else {{
    Write-Host "错误: 找不到 $exePath"
}}
"""
        ps_file.write_text(ps_content, encoding="utf-8")
        self.log(f"✅ 创建 PowerShell 启动脚本")
        
        # 创建 README
        readme_path = package_dir / "README.txt"
        readme_content = f"""╔════════════════════════════════════════════════════════════╗
║                                                            ║
║                  {APP_NAME} 应用 v{APP_VERSION}                           ║
║                  {APP_DESCRIPTION}      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

📖 使用说明
═════════════════════════════════════════════════════════════

1️⃣  启动应用
   双击 {APP_NAME}.exe 即可启动应用

   或运行: run.bat 或 run.ps1

2️⃣  系统要求
   • Windows 7 SP1 或更高版本
   • 1 GB RAM 最低要求
   • 100 MB 磁盘空间
   • .NET Runtime (如需要)

3️⃣  功能
   ✅ AI 助手集成
   ✅ 文件自动处理
   ✅ Web 界面
   ✅ 多模型支持
   ✅ 实时任务处理

4️⃣  常见问题

   Q: 如何重装应用？
   A: 删除整个文件夹，重新提取包

   Q: 如何卸载？
   A: 直接删除应用文件夹即可

   Q: 应用无法启动？
   A: 确保 Windows 系统补丁已安装
      检查是否有防火墙拦截
      查看日志文件获取详细信息

5️⃣  日志文件
   应用运行日志保存在: logs 文件夹

6️⃣  配置
   配置文件位置: config 文件夹

═════════════════════════════════════════════════════════════

🔗 更多信息: 访问应用内帮助菜单

祝您使用愉快! 🎉
"""
        readme_path.write_text(readme_content, encoding="utf-8-sig")
        self.log(f"✅ 创建 README 文件")
        
        # 创建快捷方式创建脚本
        shortcut_ps = package_dir / "CreateShortcut.ps1"
        shortcut_content = f"""# 为 Koto 创建桌面快捷方式
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "{APP_NAME}.exe"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktopPath\\{APP_NAME}.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = $exePath
$shortcut.Save()

Write-Host "快捷方式已创建: $shortcutPath"
"""
        shortcut_ps.write_text(shortcut_content, encoding="utf-8")
        self.log(f"✅ 创建快捷方式脚本")
        
        return package_dir
    
    def create_installer_script(self, package_dir):
        """创建 NSIS 安装程序脚本"""
        self.step("6. 创建 NSIS 安装程序定义")
        
        nsis_file = INSTALLER_DIR / "Koto.nsi"
        
        nsis_content = f"""; Koto 安装程序脚本 (NSIS)
; 用 NSIS 3.0+ 编译

!include "MUI2.nsh"
!include "x64.nsh"

SetCompress force
SetDatablockOptimize on
SetOverwrite try

; 基本信息
Name "{APP_NAME} v{APP_VERSION}"
OutFile "${{INSTALLER_DIR}}\\Koto_v{APP_VERSION}_Installer.exe"
InstallDir "$PROGRAMFILES\\{COMPANY}\\{APP_NAME}"
InstallDirRegKey HKCU "Software\\{COMPANY}\\{APP_NAME}" ""

; 版本信息
VIProductVersion "{APP_VERSION}.0"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "ProductName" "{APP_NAME}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "Comments" "{APP_DESCRIPTION}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "CompanyName" "{COMPANY}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "FileDescription" "{APP_DESCRIPTION}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "FileVersion" "{APP_VERSION}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "ProductVersion" "{APP_VERSION}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "InternalName" "{APP_NAME}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "LegalCopyright" "© 2024 {COMPANY}"
VIAddVersionKey /LANG=${{LANG_ENGLISH}} "OriginalFilename" "Koto_Installer.exe"

; MUI 设置
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; 安装程序初始化
Function .onInit
    !insertmacro MUI_INSTALLOPTIONS_EXTRACT "NSIS.ini"
FunctionEnd

; 安装文件
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; 从源目录复制文件
    File /r "{package_dir}\\*.*"
    
    ; 创建开始菜单快捷方式
    CreateDirectory "$SMPROGRAMS\\{COMPANY}\\{APP_NAME}"
    CreateShortcut "$SMPROGRAMS\\{COMPANY}\\{APP_NAME}\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    CreateShortcut "$SMPROGRAMS\\{COMPANY}\\{APP_NAME}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"
    
    ; 创建桌面快捷方式
    CreateShortcut "$DESKTOP\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    
    ; 创建卸载程序
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
    
    ; 写入注册表
    WriteRegStr HKCU "Software\\{COMPANY}\\{APP_NAME}" "" "$INSTDIR"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayName" "{APP_NAME} v{APP_VERSION}"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayVersion" "{APP_VERSION}"
    
SectionEnd

; 卸载程序
Section "Uninstall"
    Delete "$INSTDIR\\Uninstall.exe"
    RMDir /r "$INSTDIR"
    
    Delete "$SMPROGRAMS\\{COMPANY}\\{APP_NAME}\\{APP_NAME}.lnk"
    Delete "$SMPROGRAMS\\{COMPANY}\\{APP_NAME}\\Uninstall.lnk"
    RMDir "$SMPROGRAMS\\{COMPANY}\\{APP_NAME}"
    RMDir "$SMPROGRAMS\\{COMPANY}"
    
    Delete "$DESKTOP\\{APP_NAME}.lnk"
    
    DeleteRegKey HKCU "Software\\{COMPANY}\\{APP_NAME}"
    DeleteRegKey HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}"
SectionEnd
"""
        
        nsis_file.write_text(nsis_content, encoding="utf-8")
        self.log(f"✅ 创建 NSIS 脚本: {nsis_file.name}")
        
        return nsis_file
    
    def create_portable_zip(self, package_dir):
        """创建便携式 ZIP 包"""
        self.step("7. 创建便携式 ZIP 包")
        
        zip_path = INSTALLER_DIR / f"Koto_v{APP_VERSION}_Portable.zip"
        
        try:
            import zipfile
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in package_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(INSTALLER_DIR)
                        zipf.write(file_path, arcname)
            
            zip_size = zip_path.stat().st_size / (1024 * 1024)
            self.log(f"✅ ZIP 包已创建")
            self.log(f"   位置: {zip_path}")
            self.log(f"   大小: {zip_size:.2f} MB")
            return zip_path
            
        except Exception as e:
            self.log(f"❌ 创建 ZIP 包失败: {e}")
            return None
    
    def create_installer_exe(self):
        """使用 NSIS 创建安装程序"""
        self.step("8. 创建 NSIS 安装程序")
        
        nsis_exe = Path("C:\\Program Files (x86)\\NSIS\\makensis.exe")
        
        if not nsis_exe.exists():
            self.log("⚠️  NSIS 未安装，跳过 .exe 安装程序生成")
            self.log("   提示: 可从 https://nsis.sourceforge.io 下载 NSIS")
            return None
        
        nsis_script = INSTALLER_DIR / "Koto.nsi"
        
        try:
            self._run_command([str(nsis_exe), str(nsis_script)])
            
            installer_exe = INSTALLER_DIR / f"Koto_v{APP_VERSION}_Installer.exe"
            if installer_exe.exists():
                installer_size = installer_exe.stat().st_size / (1024 * 1024)
                self.log(f"✅ 安装程序已生成")
                self.log(f"   位置: {installer_exe}")
                self.log(f"   大小: {installer_size:.2f} MB")
                return installer_exe
            else:
                self.log(f"⚠️  NSIS 编译完成但未找到输出文件")
                return None
                
        except FileNotFoundError:
            self.log(f"⚠️  NSIS 编译器未找到")
            return None
        except Exception as e:
            self.log(f"⚠️  NSIS 编译失败: {e}")
            return None
    
    def create_build_summary(self, package_dir, zip_path, installer_exe):
        """创建构建总结"""
        self.step("9. 构建总结")
        
        summary_file = INSTALLER_DIR / "BUILD_SUMMARY.txt"
        
        summary = f"""╔════════════════════════════════════════════════════════════╗
║                   Koto 构建总结                          ║
╚════════════════════════════════════════════════════════════╝

📦 构建信息
═════════════════════════════════════════════════════════════
应用名称: {APP_NAME}
版本: {APP_VERSION}
描述: {APP_DESCRIPTION}
作者: {AUTHOR}
构建时间: {self.timestamp}

📁 输出文件
═════════════════════════════════════════════════════════════

1. 便携式包 (推荐用于新电脑)
   ✅ {zip_path.name if zip_path else "未生成"}
   位置: {ZIP_PATH if zip_path else "N/A"}
   说明: 解压即用，无需安装

2. 安装程序 (需要 NSIS)
   {'✅' if installer_exe else '⚠️'} {installer_exe.name if installer_exe else "未生成 (NSIS 未安装)"}
   位置: {str(installer_exe) if installer_exe else "N/A"}
   说明: 向导式安装，自动配置开始菜单

3. 可执行程序
   位置: {DIST_DIR / f'{APP_NAME}.exe'}
   大小: 详见上方日志

📋 使用指南
═════════════════════════════════════════════════════════════

方案 A: 使用 ZIP 包 (推荐)
────────────────────────
1. 下载: Koto_v{APP_VERSION}_Portable.zip
2. 解压到任意位置
3. 双击 run.bat 或 {APP_NAME}.exe 启动

方案 B: 使用安装程序
────────────────────
1. 运行 Koto_v{APP_VERSION}_Installer.exe
2. 按照向导完成安装
3. 从开始菜单或桌面快捷方式启动

方案 C: 仅使用可执行文件
────────────────────
1. 从 dist 文件夹复制 {APP_NAME}.exe
2. 双击启动 (需要依赖已安装)

🔧 依赖说明
═════════════════════════════════════════════════════════════
所有依赖已打包进可执行文件中
可以在无 Python 环境的电脑上运行

💾 系统要求
═════════════════════════════════════════════════════════════
• Windows 7 SP1 或更高版本
• 1 GB RAM 最低要求
• 100 MB 磁盘空间
• 无需安装 Python

📌 注意事项
═════════════════════════════════════════════════════════════
✓ 便携式包可直接复制到 U 盘使用
✓ 支持离线使用（部分功能）
✓ 无管理员权限也能运行
✓ 支持升级 (备份配置后更新)

🆘 故障排查
═════════════════════════════════════════════════════════════
问题: 应用无法启动
解决: 1. 确认 Windows 系统补丁已安装
      2. 检查防火墙是否拦截
      3. 查看 logs 文件夹中的日志文件

问题: 功能无法使用
解决: 检查网络连接和 API 密钥配置

═════════════════════════════════════════════════════════════
构建完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
═════════════════════════════════════════════════════════════
"""
        
        summary_file.write_text(summary, encoding="utf-8-sig")
        self.log(f"✅ 构建总结已生成: {summary_file.name}")
        
        # 打印总结到控制台
        print("\n" + summary)
    
    def _run_command(self, cmd):
        """运行命令"""
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=False,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            raise Exception(f"命令执行失败: {' '.join(cmd)}\n{e}")
    
    def build(self):
        """执行完整的构建过程"""
        self.log("🚀 Koto 应用安装包生成器")
        self.log(f"版本: {APP_VERSION}")
        self.log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 检查前置条件
            if not self.check_prerequisites():
                self.log("❌ 前置条件检查失败")
                return False
            
            # 清理之前的构建
            self.clean_previous_builds()
            
            # 安装依赖
            if not self.install_dependencies():
                self.log("❌ 依赖安装失败")
                return False
            
            # 构建可执行文件
            if not self.build_executable():
                self.log("❌ 可执行文件构建失败")
                return False
            
            # 创建安装包结构
            package_dir = self.create_package_structure()
            
            # 创建便携式 ZIP 包
            zip_path = self.create_portable_zip(package_dir)
            
            # 创建 NSIS 安装程序脚本
            self.create_installer_script(package_dir)
            
            # 尝试创建安装程序
            installer_exe = self.create_installer_exe()
            
            # 创建构建总结
            self.create_build_summary(package_dir, zip_path, installer_exe)
            
            self.step("✅ 构建完成！")
            self.log(f"所有文件位置: {INSTALLER_DIR}")
            self.log(f"构建日志: {self.log_file}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ 构建失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False


def main():
    """主函数"""
    builder = InstallerBuilder()
    success = builder.build()
    
    if success:
        print("\n✅ 安装包构建成功！")
        print(f"📁 输出目录: {INSTALLER_DIR}")
        return 0
    else:
        print("\n❌ 安装包构建失败！")
        print(f"📋 查看日志: {builder.log_file}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
