#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Koto 快捷助手 - 悬浮小窗口
支持快速对话和语音输入的迷你版Koto
"""

import os
import sys
import threading
import webview
import subprocess

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MiniKotoAPI:
    """迷你窗口的Python API"""
    
    def __init__(self, window):
        self.window = window
        self.main_window = None
    
    def close_window(self):
        """关闭窗口"""
        self.window.destroy()
    
    def minimize_window(self):
        """最小化窗口"""
        self.window.minimize()
    
    def open_main_window(self):
        """打开完整版Koto并关闭迷你窗口"""
        try:
            import subprocess
            # 在新进程中启动完整版
            koto_app = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'koto_app.py')
            if os.path.exists(koto_app):
                subprocess.Popen(
                    [sys.executable, koto_app], 
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                    cwd=os.path.dirname(os.path.dirname(__file__))
                )
                # 延迟关闭迷你窗口，让主窗口有时间启动
                import time
                time.sleep(0.5)
                self.window.destroy()
        except Exception as e:
            print(f"启动完整版失败: {e}")
    
    def set_always_on_top(self, value: bool):
        """设置窗口置顶"""
        self.window.on_top = value


def start_flask_server():
    """在后台启动Flask服务器（如果没有运行）"""
    import socket
    
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0
    
    if not is_port_in_use(5000):
        print("🚀 启动后台Flask服务...")
        from web.app import app
        
        def run_flask():
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # 等待服务器启动
        import time
        for _ in range(30):  # 最多等3秒
            if is_port_in_use(5000):
                print("✅ Flask服务已就绪")
                break
            time.sleep(0.1)
    else:
        print("✅ Flask服务已在运行")


def get_screen_size():
    """获取屏幕尺寸"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except:
        return 1920, 1080


def main():
    """启动迷你Koto窗口"""
    print("=" * 50)
    print("🤖 Koto 快捷助手")
    print("=" * 50)
    
    # 启动Flask服务
    start_flask_server()
    
    # 计算窗口位置（右下角）
    screen_width, screen_height = get_screen_size()
    window_width = 360
    window_height = 480
    x = screen_width - window_width - 20
    y = screen_height - window_height - 80  # 留出任务栏空间
    
    # 获取HTML模板路径
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'mini_koto.html')
    
    if not os.path.exists(template_path):
        print(f"❌ 找不到模板文件: {template_path}")
        return
    
    # 创建窗口
    window = webview.create_window(
        title='Koto',
        url=template_path,
        width=window_width,
        height=window_height,
        x=x,
        y=y,
        resizable=True,
        frameless=True,  # 无边框，自定义标题栏
        easy_drag=True,
        on_top=True,  # 默认置顶
        background_color='#1a1a2e',
        min_size=(300, 400)
    )
    
    # 绑定API
    api = MiniKotoAPI(window)
    window.expose(api.close_window)
    window.expose(api.minimize_window)
    window.expose(api.open_main_window)
    window.expose(api.set_always_on_top)
    
    print(f"📍 窗口位置: ({x}, {y})")
    print("💡 提示: 拖动标题栏可移动窗口")
    print("🎙️ 点击麦克风按钮开始语音输入")
    print()
    
    # 启动窗口
    webview.start(debug=False)


if __name__ == '__main__':
    main()
