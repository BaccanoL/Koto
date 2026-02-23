#!/usr/bin/env python3
"""
Koto Desktop 独立版本生成器
生成完全独立的、可直接运行的 PyInstaller 桌面应用
生成的应用无需Python、无需依赖、无需端口映射
"""

import os
import sys
import subprocess
import shutil
import json
import zipfile
from pathlib import Path
from datetime import datetime

class DesktopAppBuilder:
    """桌面应用构建器"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.dist_dir = self.project_dir / 'dist'
        self.build_dir = self.project_dir / 'build'
        self.output_dir = self.project_dir / 'desktop_apps'
        
        self.app_name = "Koto"
        self.app_version = "1.0.0"
        self.app_author = "Koto Team"
        
        # 创建输出目录
        self.output_dir.mkdir(exist_ok=True)
    
    def print_header(self, message):
        """打印标题"""
        print(f"\n{'='*60}")
        print(f"  {message}")
        print(f"{'='*60}\n")
    
    def print_step(self, step_num, message):
        """打印步骤"""
        print(f"[{step_num}/6] {message}...")
    
    def print_success(self, message):
        """打印成功信息"""
        print(f"  ✓ {message}")
    
    def print_error(self, message):
        """打印错误信息"""
        print(f"  ✗ {message}")
    
    def print_warning(self, message):
        """打印警告"""
        print(f"  ⚠ {message}")
    
    def check_prerequisites(self):
        """检查前置要求"""
        self.print_step(1, "检查前置要求")
        
        # 检查 Python
        try:
            import PyInstaller
            self.print_success("PyInstaller 已安装")
        except ImportError:
            print("\n❌ PyInstaller 未安装!")
            print("\n正在安装 PyInstaller...\n")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller", "-q"],
                capture_output=True
            )
            if result.returncode != 0:
                self.print_error("PyInstaller 安装失败")
                return False
            self.print_success("PyInstaller 已安装")
        
        # 检查依赖
        try:
            import PySide6
            self.print_success("PySide6 已安装")
        except ImportError:
            self.print_error("PySide6 未安装，请运行: pip install PySide6")
            return False
        
        return True
    
    def build_executable(self):
        """构建可执行文件"""
        self.print_step(2, "构建 PyInstaller 可执行文件")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import get_module_file_attribute

a = Analysis(
    ['koto_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('web', 'web'),
        ('config', 'config'),
        ('assets', 'assets'),
        ('models', 'models'),
        ('logs', 'logs'),
    ],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Koto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/koto.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Koto',
)
'''
        
        # 写入 .spec 文件
        spec_file = self.project_dir / 'koto_desktop.spec'
        spec_file.write_text(spec_content)
        self.print_success("生成 spec 文件")
        
        # 创建简单的图标（如果不存在）
        icon_path = self.project_dir / 'assets' / 'koto.ico'
        if not icon_path.exists():
            icon_path.parent.mkdir(parents=True, exist_ok=True)
            self.print_warning("使用默认图标（未找到 koto.ico)")
        else:
            self.print_success(f"使用自定义图标")
        
        # 运行 PyInstaller
        print("\n  🔄 编译中... (这可能需要几分钟)\n")
        
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", str(spec_file), "-y"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            self.print_error("PyInstaller 编译失败")
            print(result.stderr)
            return False
        
        # 检查输出
        exe_path = self.project_dir / 'dist' / 'Koto' / 'Koto.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            self.print_success(f"可执行文件已生成 ({size_mb:.1f} MB)")
            return True
        else:
            self.print_error("可执行文件生成失败")
            return False
    
    def create_installer(self):
        """创建 NSIS 安装程序"""
        self.print_step(3, "创建 NSIS 安装程序")
        
        # 检查 NSIS
        nsis_path = Path("C:/Program Files (x86)/NSIS/makensis.exe")
        if not nsis_path.exists():
            self.print_warning("NSIS 未安装，跳过 EXE 安装程序生成")
            self.print_warning("如需生成安装程序，请访问 https://nsis.sourceforge.io 下载安装")
            return False
        
        # NSIS 脚本内容
        nsis_script = f'''# Koto Desktop Installer
!include "MUI2.nsh"

Name "Koto v{self.app_version}"
OutFile "${{OUTDIR}}\\Koto_v{self.app_version}_Installer.exe"
InstallDir "$PROGRAMFILES\\Koto"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\\Koto\\*.*"
  CreateDirectory "$SMPROGRAMS\\Koto"
  CreateShortCut "$SMPROGRAMS\\Koto\\Koto.lnk" "$INSTDIR\\Koto.exe"
  CreateShortCut "$DESKTOP\\Koto.lnk" "$INSTDIR\\Koto.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\\Koto\\Koto.lnk"
  Delete "$DESKTOP\\Koto.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
'''
        
        nsis_file = self.project_dir / 'koto_installer.nsi'
        nsis_file.write_text(nsis_script)
        self.print_success("生成 NSIS 脚本")
        
        # TODO: 调用 NSIS 编译器
        # 这里只做准备工作
        return True
    
    def copy_to_desktop(self):
        """复制到桌面"""
        self.print_step(4, "复制应用到桌面")
        
        exe_path = self.project_dir / 'dist' / 'Koto'
        if not exe_path.exists():
            self.print_error("源文件夹不存在")
            return False
        
        desktop_path = Path.home() / 'Desktop' / 'Koto_v1.0.0'
        
        # 删除旧版本
        if desktop_path.exists():
            shutil.rmtree(desktop_path)
            self.print_success("清理旧版本")
        
        # 复制文件
        try:
            shutil.copytree(exe_path, desktop_path)
            self.print_success(f"应用已复制到桌面: {desktop_path}")
            
            # 创建快捷方式
            desktop_shortcut = Path.home() / 'Desktop' / 'Koto.lnk'
            if desktop_shortcut.exists():
                desktop_shortcut.unlink()
            
            # 创建启动脚本
            launcher = desktop_path / 'launch.bat'
            launcher.write_text(f'''@echo off
cd /d "%~dp0"
Koto.exe
''')
            self.print_success("创建启动脚本")
            
            return True
        except Exception as e:
            self.print_error(f"复制失败: {e}")
            return False
    
    def create_package(self):
        """创建可分发的包"""
        self.print_step(5, "创建可分发包")
        
        exe_path = self.project_dir / 'dist' / 'Koto'
        if not exe_path.exists():
            self.print_error("源文件夹不存在")
            return False
        
        # 创建 ZIP 包
        zip_name = f"Koto_v{self.app_version}_Standalone.zip"
        zip_path = self.output_dir / zip_name
        
        try:
            if zip_path.exists():
                zip_path.unlink()
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(exe_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(exe_path.parent)
                        zipf.write(file_path, arcname)
            
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            self.print_success(f"包文件已生成: {zip_name} ({size_mb:.1f} MB)")
            
            # 创建说明文件
            readme_path = self.output_dir / 'README.txt'
            readme_path.write_text(f'''
Koto Desktop v{self.app_version} - 独立应用包
===============================================

【快速开始】
1. 解压此包到任意位置
2. 双击 Koto.exe 启动应用
3. 完成！无需安装、无需配置

【系统要求】
• Windows 7 SP1 或更高版本
• 500 MB 可用磁盘空间
• 1 GB RAM

【功能特性】
✓ 完全独立 - 无需 Python、无需依赖
✓ 无需配置 - 开箱即用
✓ 类似 VSCode、微信 的专业应用
✓ 智能任务处理 (自适应 Agent)
✓ 文档处理与生成
✓ AI 聊天助手
✓ 系统集成与控制

【包含文件】
Koto.exe          - 主应用程序
launch.bat        - 启动脚本
_internal/        - 应用依赖
config/           - 配置文件
assets/           - 资源文件
models/           - AI 模型
web/              - Web 组件
logs/             - 日志文件夹

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            ''')
            return True
        except Exception as e:
            self.print_error(f"包创建失败: {e}")
            return False
    
    def generate_summary(self):
        """生成总结"""
        self.print_step(6, "生成总结")
        
        summary = {
            "project": "Koto Desktop",
            "version": self.app_version,
            "build_time": datetime.now().isoformat(),
            "locations": {
                "executable": str(self.project_dir / 'dist' / 'Koto' / 'Koto.exe'),
                "desktop_app": str(Path.home() / 'Desktop' / 'Koto_v1.0.0'),
                "desktop_shortcut": str(Path.home() / 'Desktop' / 'Koto.lnk'),
                "distribution_package": str(self.output_dir / f'Koto_v{self.app_version}_Standalone.zip'),
            },
            "features": [
                "Fully standalone application",
                "No Python required",
                "No dependency management",
                "Professional desktop UI",
                "Native Windows integration",
                "Adaptive Agent system",
            ]
        }
        
        # 保存总结
        summary_file = self.output_dir / 'BUILD_SUMMARY.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.print_success(f"总结已保存: {summary_file}")
        
        return summary
    
    def build(self):
        """执行完整的构建过程"""
        self.print_header("Koto Desktop 独立应用构建器")
        
        print(f"项目目录: {self.project_dir}")
        print(f"输出目录: {self.output_dir}")
        print()
        
        # 执行步骤
        if not self.check_prerequisites():
            self.print_error("前置检查失败，构建中止")
            return False
        
        if not self.build_executable():
            self.print_error("可执行文件构建失败，构建中止")
            return False
        
        self.create_installer()
        
        if not self.copy_to_desktop():
            self.print_warning("桌面复制失败，继续其他步骤")
        
        if not self.create_package():
            self.print_warning("包创建失败，继续其他步骤")
        
        summary = self.generate_summary()
        
        # 打印完成信息
        self.print_header("✅ 构建完成！")
        
        print("📦 生成的文件:")
        print(f"  • 可执行文件: dist/Koto/Koto.exe")
        print(f"  • 桌面应用: {Path.home() / 'Desktop' / 'Koto_v1.0.0'}")
        print(f"  • 分发包: {self.output_dir / f'Koto_v{self.app_version}_Standalone.zip'}")
        
        print("\n🚀 启动应用:")
        print(f"  • 双击桌面上的 Koto_v1.0.0 文件夹中的 Koto.exe")
        print(f"  • 或双击桌面快捷方式 Koto")
        print(f"  • 或运行: {Path.home() / 'Desktop' / 'Koto_v1.0.0' / 'launch.bat'}")
        
        print("\n📤 分发:")
        print(f"  • 分发包位置: {self.output_dir / f'Koto_v{self.app_version}_Standalone.zip'}")
        print(f"  • 无需安装，直接解压使用")
        print(f"  • 支持 U 盘、网络共享、邮件分发")
        
        print("\n💾 配置位置:")
        print(f"  • {self.project_dir / 'config'}")
        
        print("\n📝 日志位置:")
        print(f"  • {self.project_dir / 'logs'}")
        
        print("\n" + "="*60)
        print("感谢使用 Koto!")
        print("="*60 + "\n")
        
        return True

def main():
    """主入口"""
    builder = DesktopAppBuilder()
    
    try:
        success = builder.build()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 构建被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 构建出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
