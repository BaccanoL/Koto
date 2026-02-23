#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音快捷交互模块 - 提供快速、便捷的语音输入体验
特性：
  • 全局快捷键 - 任何时候都能开始录音
  • 快捷语音命令 - 常用操作快速执行
  • 实时状态显示 - Windows托盘通知
  • 语音反馈 - 识别结果语音播放
  • 支持自定义命令 - 用户可扩展
"""

import os
import json
import threading
import time
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum
import queue


@dataclass
class VoiceCommand:
    """语音命令定义"""
    name: str  # 命令名称
    keywords: List[str]  # 关键词列表
    action: Callable  # 执行函数
    description: str = ""
    enabled: bool = True


class VoiceCommandProcessor:
    """语音命令处理器 - 快捷语音交互"""
    
    def __init__(self):
        self.commands: Dict[str, VoiceCommand] = {}
        self.command_queue = queue.Queue()
        
        # 内置命令
        self._register_builtin_commands()
    
    def _register_builtin_commands(self):
        """注册内置命令"""
        
        # 📝 文档命令
        self.register_command(
            "new_document",
            ["新建文档", "创建文档", "打开编辑"],
            lambda: self._action_result("已新建文档"),
            "新建一个文档"
        )
        
        self.register_command(
            "open_document",
            ["打开文档", "打开文件", "加载文档"],
            lambda: self._action_result("已打开文档"),
            "打开最近的文档"
        )
        
        self.register_command(
            "save_document",
            ["保存文档", "保存文件", "保存"],
            lambda: self._action_result("文档已保存"),
            "保存当前文档"
        )
        
        # 🎬 批注命令
        self.register_command(
            "annotate_document",
            ["批注文档", "开始批注", "智能批注", "生成批注"],
            lambda: self._action_result("正在批注文档，请稍候..."),
            "对文档进行智能批注"
        )
        
        self.register_command(
            "review_changes",
            ["查看修改", "审查修改", "查看批注", "查看意见"],
            lambda: self._action_result("已加载修改内容"),
            "查看文档修改意见"
        )
        
        # 🔍 搜索命令
        self.register_command(
            "search",
            ["搜索", "查找", "搜一下", "找一下"],
            lambda: self._action_result("搜索模式已启动，请说出要查找的内容"),
            "搜索文档内容"
        )
        
        # 📋 复制粘贴命令
        self.register_command(
            "copy",
            ["复制", "复制到剪贴板", "复制选中"],
            lambda: self._action_result("已复制到剪贴板"),
            "复制选中内容"
        )
        
        self.register_command(
            "paste",
            ["粘贴", "粘贴内容", "从剪贴板粘贴"],
            lambda: self._action_result("已粘贴"),
            "粘贴剪贴板内容"
        )
        
        # 🔊 语音命令
        self.register_command(
            "voice_record",
            ["语音输入", "开始录音", "录音", "语音笔记"],
            lambda: self._action_result("录音已开始"),
            "开始语音输入"
        )
        
        self.register_command(
            "voice_transcribe",
            ["转写", "语音转文字", "转录", "语音转录"],
            lambda: self._action_result("正在转写音频..."),
            "将语音转写为文字"
        )
        
        # ⚙️ 系统命令
        self.register_command(
            "undo",
            ["撤销", "撤销上一步", "反悔"],
            lambda: self._action_result("已撤销"),
            "撤销上一步操作"
        )
        
        self.register_command(
            "redo",
            ["重做", "重复", "恢复"],
            lambda: self._action_result("已重做"),
            "重做上一步操作"
        )
        
        self.register_command(
            "help",
            ["帮助", "怎么用", "有什么功能", "命令列表"],
            self._show_help,
            "显示帮助信息"
        )
    
    def register_command(
        self,
        name: str,
        keywords: List[str],
        action: Callable,
        description: str = ""
    ):
        """注册自定义命令"""
        command = VoiceCommand(
            name=name,
            keywords=keywords,
            action=action,
            description=description
        )
        self.commands[name] = command
    
    def match_command(self, text: str) -> Optional[VoiceCommand]:
        """根据文本匹配命令"""
        text_lower = text.lower().strip()
        
        for cmd in self.commands.values():
            if not cmd.enabled:
                continue
            
            for keyword in cmd.keywords:
                if keyword.lower() in text_lower:
                    return cmd
        
        return None
    
    def execute_command(self, text: str) -> Dict:
        """执行命令"""
        command = self.match_command(text)
        
        if not command:
            return {
                "success": False,
                "command": None,
                "result": "未识别的命令",
                "message": f"无法理解: {text}，请说出有效的命令"
            }
        
        try:
            result = command.action()
            return {
                "success": True,
                "command": command.name,
                "result": result,
                "message": f"已执行命令: {command.description}"
            }
        except Exception as e:
            return {
                "success": False,
                "command": command.name,
                "result": None,
                "message": f"执行命令失败: {str(e)}"
            }
    
    def _action_result(self, message: str) -> str:
        """生成操作结果"""
        return message
    
    def _show_help(self) -> str:
        """显示帮助"""
        help_text = "可用命令:\n"
        for cmd in sorted(self.commands.values(), key=lambda x: x.name):
            if cmd.enabled:
                keywords = "、".join(cmd.keywords)
                help_text += f"• {cmd.description}: {keywords}\n"
        return help_text
    
    def list_commands(self) -> List[Dict]:
        """列出所有命令"""
        return [
            {
                "name": cmd.name,
                "keywords": cmd.keywords,
                "description": cmd.description,
                "enabled": cmd.enabled
            }
            for cmd in self.commands.values()
        ]


class GlobalHotkeyListener:
    """全局快捷键监听器 - 任何时候开始录音"""
    
    def __init__(self, hotkey: str = "ctrl+shift+v", on_activate: Optional[Callable] = None):
        """
        Args:
            hotkey: 快捷键组合
            on_activate: 激活时的回调
        """
        self.hotkey = hotkey
        self.on_activate = on_activate
        self.listener_thread: Optional[threading.Thread] = None
        self.is_running = False
    
    def start(self):
        """启动监听"""
        if self.is_running:
            return
        
        self.is_running = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        print(f"✅ 全局快捷键监听已启动: {self.hotkey}")
    
    def stop(self):
        """停止监听"""
        self.is_running = False
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
    
    def _listen_loop(self):
        """监听循环"""
        try:
            import keyboard
            
            while self.is_running:
                try:
                    # 注册快捷键
                    keyboard.add_hotkey(self.hotkey, self._on_hotkey_press)
                    
                    # 保持监听
                    while self.is_running:
                        time.sleep(0.1)
                    
                    keyboard.remove_all_hotkeys()
                except Exception as e:
                    print(f"⚠️ 快捷键监听错误: {e}")
                    time.sleep(1)
        
        except ImportError:
            print("❌ 未安装 keyboard 库，请运行: pip install keyboard")
    
    def _on_hotkey_press(self):
        """快捷键被按下"""
        if self.on_activate:
            self.on_activate()


class VoiceInteractionManager:
    """语音交互管理器 - 统合快捷键、命令、反馈"""
    
    def __init__(self):
        self.command_processor = VoiceCommandProcessor()
        self.hotkey_listener: Optional[GlobalHotkeyListener] = None
        self.state_callbacks: List[Callable] = []
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        config_file = "config/voice_interaction.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # 默认配置
        return {
            "hotkey": "ctrl+shift+v",
            "hotkey_enabled": True,
            "auto_play_result": False,
            "show_notifications": True,
            "cache_enabled": True,
            "max_retries": 3,
            "language": "zh-CN",
            "timeout": 10
        }
    
    def save_config(self):
        """保存配置"""
        os.makedirs("config", exist_ok=True)
        with open("config/voice_interaction.json", 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def register_hotkey(self, hotkey: str = "ctrl+shift+v"):
        """注册全局快捷键"""
        self.config["hotkey"] = hotkey
        
        self.hotkey_listener = GlobalHotkeyListener(
            hotkey=hotkey,
            on_activate=self.on_hotkey_pressed
        )
        
        if self.config.get("hotkey_enabled", True):
            self.hotkey_listener.start()
    
    def on_hotkey_pressed(self):
        """快捷键被按下的回调"""
        for callback in self.state_callbacks:
            callback("hotkey_pressed", {"hotkey": self.config["hotkey"]})
    
    def register_state_callback(self, callback: Callable):
        """注册状态回调"""
        self.state_callbacks.append(callback)
    
    def get_command_processor(self) -> VoiceCommandProcessor:
        """获取命令处理器"""
        return self.command_processor
    
    def get_config(self) -> Dict:
        """获取配置"""
        return self.config
    
    def set_config(self, key: str, value: any):
        """设置配置"""
        self.config[key] = value
        self.save_config()
    
    def cleanup(self):
        """清理资源"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()


# 全局实例
_manager: Optional[VoiceInteractionManager] = None


def get_interaction_manager() -> VoiceInteractionManager:
    """获取交互管理器实例"""
    global _manager
    
    if _manager is None:
        _manager = VoiceInteractionManager()
        _manager.register_hotkey(_manager.config.get("hotkey", "ctrl+shift+v"))
    
    return _manager


if __name__ == "__main__":
    print("🎤 语音快捷交互系统\n")
    
    manager = get_interaction_manager()
    processor = manager.get_command_processor()
    
    # 显示可用命令
    print("📋 可用命令:")
    for cmd in processor.list_commands():
        print(f"  • {cmd['name']}: {cmd['keywords']}")
    
    # 测试命令
    print("\n🧪 测试命令匹配:")
    test_texts = [
        "打开文档",
        "请为我批注这个文件",
        "撤销",
        "帮助"
    ]
    
    for text in test_texts:
        result = processor.execute_command(text)
        print(f"  输入: {text}")
        print(f"  结果: {result}")
        print()
    
    # 显示配置
    print("⚙️ 配置:")
    config = manager.get_config()
    for key, value in config.items():
        print(f"  • {key}: {value}")
    
    # 清理
    manager.cleanup()
