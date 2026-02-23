#!/usr/bin/env python3
"""
Koto Desktop 快速启动器
无需打包 PyInstaller，直接运行 Python 版本
用于开发和快速测试
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    # 获取项目路径
    project_root = Path(__file__).parent
    
    # 进入项目目录
    os.chdir(project_root)
    
    print("\n" + "="*60)
    print("  Koto Desktop 快速启动器")
    print("="*60 + "\n")
    
    # 检查 Python
    print("[1/3] 检查 Python 环境...")
    try:
        import PySide6
        print("  ✓ PySide6 已就绪")
    except ImportError:
        print("  ⚠ PySide6 未安装")
        print("\n  正在安装依赖...\n")
        
        if not (project_root / 'requirements.txt').exists():
            print("  ✗ requirements.txt 不存在")
            return False
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=project_root
        )
        
        if result.returncode != 0:
            print("\n  ✗ 依赖安装失败")
            return False
        
        print("  ✓ 依赖已安装")
    
    # 创建日志目录
    print("\n[2/3] 准备环境...")
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    print("  ✓ 日志目录已就绪")
    
    # 启动应用
    print("\n[3/3] 启动 Koto Desktop...")
    print("  ⏳ 应用正在启动，请稍候...\n")
    
    try:
        subprocess.run(
            [sys.executable, str(project_root / 'koto_desktop.py')],
            cwd=project_root
        )
    except KeyboardInterrupt:
        print("\n\n应用已关闭")
    except Exception as e:
        print(f"\n✗ 启动失败: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
