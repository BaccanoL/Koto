#!/usr/bin/env python3
"""测试 Koto 应用实际启动时间（模拟 koto_app.py）"""
import time
import subprocess
import sys
from pathlib import Path

print("=" * 60)
print("Koto 完整启动性能测试")
print("=" * 60)

start_time = time.perf_counter()

# 启动 Koto 应用（不等待窗口显示）
koto_script = Path(__file__).parent.parent / "koto_app.py"
print(f"\n启动命令: pythonw {koto_script}")
print("（应用将在后台启动，请观察窗口出现时间）\n")

# 使用 pythonw 静默启动（避免控制台窗口）
subprocess.Popen(
    [sys.executable.replace("python.exe", "pythonw.exe"), str(koto_script)],
    cwd=str(koto_script.parent),
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
)

print("✓ 应用已启动")
print("\n请观察：")
print("  1. 窗口从启动到可见的时间")
print("  2. 启动页面消失的时间")
print("  3. 主界面完全显示的时间")
print("\n建议用秒表手动计时，或查看 logs/startup.log")
print("=" * 60)
