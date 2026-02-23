#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Koto 桌面应用入口 - 简化版
使用新的 launcher 模块统一管理启动流程

📌 使用方法:
  python koto_app.py           # 桌面模式（默认）
  python koto_app.py --server  # 服务模式（无 UI）
  python koto_app.py --repair  # 修复模式
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def main():
    """主入口 - 调用新的启动器"""
    try:
        from launcher.core import Launcher
        launcher = Launcher()
        launcher.run()
    except ImportError as e:
        # 如果 launcher 模块不可用，显示错误
        print(f"❌ 启动器模块加载失败: {e}")
        print("📋 请确保 launcher 目录存在且包含所有必要文件")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
