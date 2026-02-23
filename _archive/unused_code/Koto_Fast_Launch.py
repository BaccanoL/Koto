#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Koto 极速启动器 v2.0
优化启动流程，跳过非必要检查，提供更稳定的启动体验
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    print("\n" + "="*50)
    print("   🚀 Koto 智能启动器 v2.0")
    print("="*50 + "\n")
    
    # 1. 确定根目录
    root_dir = Path(__file__).parent.absolute()
    os.chdir(str(root_dir))
    
    # 2. 设置性能优化环境变量
    # 禁用语法预检查（我们在 koto_app.py 中已修改为仅 default=0，这里显式强化）
    os.environ["KOTO_DEBUG_SYNTAX"] = "0" 
    # 禁用 pywebview 的一些调试日志
    os.environ["PYWEBVIEW_LOG"] = "error"
    # 设置启动超时容忍度
    os.environ["KOTO_STARTUP_TIMEOUT_SEC"] = "20"
    
    # 3. 检查虚拟环境
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    system_python = sys.executable
    
    target_python = system_python
    if venv_python.exists():
        print(f"✅ 检测到虚拟环境: .venv")
        target_python = str(venv_python)
    else:
        print(f"ℹ️ 使用系统 Python: {system_python}")

    # 4. 清理旧的残留进程 (可选，避免端口占用)
    # 简单调用 taskkill 清理名为 koto_app.py 的僵尸进程 (仅 Windows)
    if sys.platform == "win32":
        try:
            # 注意：这可能会误杀其他 python 进程，稳妥起见我们只杀占用 5000 端口的
            # 但 koto_app.py 内部已有端口处理，这里只需确保没有卡死的前台窗口
            pass 
        except:
            pass

    # 5. 启动主程序
    print("\n⚡ 正在启动 Koto 核心服务...")
    print("   (首次启动可能需要几秒钟加载模型组件)\n")
    
    script_path = root_dir / "koto_app.py"
    
    try:
        # 使用 subprocess.Popen 启动，不阻塞当前窗口（如果是通过 bat 启动）
        # 但如果是直接双击 py，由于 sys.exit，控制台会关闭
        # 我们希望保留控制台如果有错误的话，或者如果是 Release 模式则隐藏
        
        # 构造命令
        cmd = [target_python, str(script_path)]
        
        # 启动
        proc = subprocess.Popen(cmd)
        
        # 如果启动器本身需要退出，解除注释
        # sys.exit(0)
        
        # 等待子进程（可选，如果希望保留启动器窗口直到应用关闭）
        try:
            proc.wait()
        except KeyboardInterrupt:
            #允许 Ctrl+C 终止
            proc.terminate()
            
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        input("按任意键退出...")

if __name__ == "__main__":
    main()
