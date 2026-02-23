#!/usr/bin/env python3
"""测量 Koto 真实启动时间（模拟 koto_app.py 的启动流程）"""
import time
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

print("=" * 60)
print("Koto 真实启动流程性能测试")
print("=" * 60)

start_total = time.perf_counter()

# 1. 导入 Flask
t1 = time.perf_counter()
from flask import Flask
t1_elapsed = (time.perf_counter() - t1) * 1000
print(f"✓ Flask 导入............................ {t1_elapsed:>7.1f} ms")

# 2. 导入 pywebview
t2 = time.perf_counter()
import webview
t2_elapsed = (time.perf_counter() - t2) * 1000
print(f"✓ pywebview 导入......................... {t2_elapsed:>7.1f} ms")

# 3. 导入 web.app 模块（主应用）
t3 = time.perf_counter()
from web import app as web_app
t3_elapsed = (time.perf_counter() - t3) * 1000
print(f"✓ web.app 模块导入....................... {t3_elapsed:>7.1f} ms")

# 4. 启动 Flask 应用（不启动服务器）
t4 = time.perf_counter()
flask_app = web_app.app
t4_elapsed = (time.perf_counter() - t4) * 1000
print(f"✓ Flask 应用初始化....................... {t4_elapsed:>7.1f} ms")

total_elapsed = (time.perf_counter() - start_total) * 1000

print("=" * 60)
print(f"总启动时间: {total_elapsed:.1f} ms ({total_elapsed/1000:.2f} 秒)")
print("=" * 60)

# 模拟创建窗口的准备工作（不真正创建窗口）
print("\n预估完整启动时间（含窗口创建）:")
window_creation_time = 500  # pywebview 创建窗口约需 500ms
estimated_total = total_elapsed + window_creation_time
print(f"  应用初始化: {total_elapsed:.0f} ms")
print(f"  窗口创建:   {window_creation_time:.0f} ms (pywebview)")
print(f"  ─────────────────────────")
print(f"  预估总计:   {estimated_total:.0f} ms ({estimated_total/1000:.1f} 秒)")
print("=" * 60)
