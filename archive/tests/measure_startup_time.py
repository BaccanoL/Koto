#!/usr/bin/env python3
"""测量 Koto 启动各阶段耗时"""
import time
import sys
from pathlib import Path

# 确保能导入 web 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

def measure(name, func):
    """测量函数执行时间"""
    start = time.perf_counter()
    result = func()
    elapsed = (time.perf_counter() - start) * 1000  # 转换为毫秒
    print(f"{name:.<50} {elapsed:>8.1f} ms")
    return result

print("=" * 60)
print("Koto 启动性能分析")
print("=" * 60)

# 1. 测量标准库导入
measure("导入标准库 (os, sys, json等)", lambda: __import__('json'))

# 2. 测量 Flask 导入
measure("导入 Flask", lambda: __import__('flask'))

# 3. 测量 Flask-CORS
measure("导入 Flask-CORS", lambda: __import__('flask_cors'))

# 4. 测量 dotenv
measure("导入 python-dotenv", lambda: __import__('dotenv'))

# 5. 测量 httpx
measure("导入 httpx", lambda: __import__('httpx'))

# 6. 测量 google.genai (重头戏)
measure("导入 google.genai", lambda: __import__('google.genai'))

# 7. 测量 PIL
try:
    measure("导入 PIL (Pillow)", lambda: __import__('PIL'))
except ImportError:
    print("PIL (Pillow) 未安装")

# 8. 测量 python-docx
try:
    measure("导入 python-docx", lambda: __import__('docx'))
except ImportError:
    print("python-docx 未安装")

# 9. 测量 python-pptx
try:
    measure("导入 python-pptx", lambda: __import__('pptx'))
except ImportError:
    print("python-pptx 未安装")

# 10. 测量 psutil
try:
    measure("导入 psutil", lambda: __import__('psutil'))
except ImportError:
    print("psutil 未安装")

# 11. 测量整个 web.app 模块
print("\n" + "=" * 60)
print("完整模块导入测试")
print("=" * 60)

def import_web_app():
    # 临时禁用懒加载，测量真实导入时间
    import web.app
    return web.app

total_start = time.perf_counter()
measure("导入 web.app (完整)", import_web_app)
total_elapsed = (time.perf_counter() - total_start) * 1000
print("=" * 60)
print(f"总计: {total_elapsed:.1f} ms")
print("=" * 60)
