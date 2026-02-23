#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Koto 全局快捷键管理器
支持系统级快捷键注册和回调
"""
import threading
import time
from typing import Callable, Dict
import keyboard  # pip install keyboard


class GlobalHotkeyManager:
    """全局快捷键管理器"""
    
    def __init__(self):
        self.hotkeys: Dict[str, Callable] = {}
        self.running = False
        self._thread = None
        
    def register(self, hotkey: str, callback: Callable, description: str = ""):
        """
        注册全局快捷键
        
        Args:
            hotkey: 快捷键组合，如 'ctrl+alt+k'
            callback: 回调函数
            description: 功能描述
        """
        try:
            keyboard.add_hotkey(hotkey, callback)
            self.hotkeys[hotkey] = {
                'callback': callback,
                'description': description
            }
            print(f"[快捷键] 已注册: {hotkey} - {description}")
            return True
        except Exception as e:
            print(f"[快捷键] 注册失败 {hotkey}: {e}")
            return False
    
    def unregister(self, hotkey: str):
        """取消注册快捷键"""
        try:
            keyboard.remove_hotkey(hotkey)
            if hotkey in self.hotkeys:
                del self.hotkeys[hotkey]
            print(f"[快捷键] 已取消: {hotkey}")
            return True
        except Exception as e:
            print(f"[快捷键] 取消失败 {hotkey}: {e}")
            return False
    
    def start(self):
        """启动快捷键监听（在后台线程）"""
        if self.running:
            print("[快捷键] 已在运行中")
            return
        
        self.running = True
        print("[快捷键] 监听已启动")
        
    def stop(self):
        """停止快捷键监听"""
        self.running = False
        keyboard.unhook_all()
        print("[快捷键] 监听已停止")
    
    def list_hotkeys(self):
        """列出所有已注册的快捷键"""
        if not self.hotkeys:
            print("[快捷键] 无已注册的快捷键")
            return
        
        print("\n[快捷键] 已注册列表:")
        for hotkey, info in self.hotkeys.items():
            print(f"  {hotkey:20s} - {info.get('description', 'N/A')}")


# 全局实例
_hotkey_manager = None


def get_hotkey_manager() -> GlobalHotkeyManager:
    """获取全局快捷键管理器单例"""
    global _hotkey_manager
    if _hotkey_manager is None:
        _hotkey_manager = GlobalHotkeyManager()
    return _hotkey_manager
