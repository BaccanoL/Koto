#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Koto 启动器 - 直接启动源代码版本
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    koto_root = Path(__file__).parent
    os.chdir(str(koto_root))
    sys.path.insert(0, str(koto_root))
    
    # 直接导入并运行
    try:
        import koto_app
        koto_app.main()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
