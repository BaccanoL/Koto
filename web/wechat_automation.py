#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信自动化模块 - 支持消息发送、联系人搜索、OCR 识别
"""

import os
import sys
import time
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 可选依赖检查
HAS_PYAUTOGUI = False
HAS_UIAUTOMATION = False
HAS_PYOCR = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    pass

try:
    import uiautomation as auto
    HAS_UIAUTOMATION = True
except ImportError:
    pass

try:
    import pytesseract
    from PIL import Image
    HAS_PYOCR = True
except ImportError:
    pass


@dataclass
class WeChatContact:
    """微信联系人"""
    name: str
    note_name: str = ""
    remark: str = ""
    is_group: bool = False


class WeChatAutomation:
    """
    微信自动化控制器
    支持消息发送、联系人管理、截图等
    """
    
    # 微信窗口特征
    WECHAT_CLASS = "WeChatMainWndForPC"
    WECHAT_WINDOW_TITLE = "微信"
    
    # 历史坐标仅作保底兜底，主流程尽量通过控件聚焦完成
    SEARCH_BOX_POS = (100, 100)  # 兼容旧逻辑
    CHAT_INPUT_POS = (500, 700)  # 兼容旧逻辑
    SEND_BTN_POS = (550, 720)    # 兼容旧逻辑
    
    def __init__(self):
        self.wechat_process = None
        self.window_hwnd = None
        self._last_contact = None
    
    def launch_wechat(self, timeout: int = 10) -> bool:
        """启动微信"""
        try:
            # 尝试多种启动方式
            try:
                # 方式1: 从标准安装路径
                subprocess.Popen(
                    r"C:\Program Files\Tencent\WeChat\WeChat.exe",
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except:
                try:
                    # 方式2: 从 AppData
                    subprocess.Popen(
                        r"C:\Users\{}\AppData\Local\Tencent\WeChat\WeChat.exe".format(os.getenv("USERNAME")),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except:
                    # 方式3: 直接命令
                    subprocess.Popen(
                        "wechat",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
            
            # 等待微信启动
            time.sleep(timeout)
            return True
        
        except Exception as e:
            print(f"❌ 启动微信失败: {e}")
            return False
    
    def find_wechat_window(self) -> Optional[int]:
        """查找微信窗口句柄"""
        if not HAS_UIAUTOMATION:
            print("⚠️ 未安装 uiautomation，无法查找窗口")
            return None
        
        try:
            # 查找微信窗口
            window = auto.FindWindow(className=self.WECHAT_CLASS, Name=self.WECHAT_WINDOW_TITLE)
            if window:
                self.window_hwnd = window
                return window
        except:
            pass
        
        return None
    
    def is_wechat_running(self) -> bool:
        """检查微信是否运行"""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'].lower() in ['wechat.exe', 'wechat']:
                    return True
        except:
            pass
        
        return False
    
    def send_message_to_contact(self, contact_name: str, message: str) -> Dict[str, any]:
        """
        发送消息给指定联系人
        
        使用 pyautogui 模拟用户操作：
        1. 启动微信（如果未运行）
        2. 搜索联系人
        3. 进入聊天窗口
        4. 输入消息
        5. 发送
        """
        result = {
            "success": False,
            "message": "",
            "contact": contact_name,
            "text": message
        }
        
        if not HAS_PYAUTOGUI:
            result["message"] = "❌ 需要安装 pyautogui: pip install pyautogui"
            return result
        
        try:
            # 步骤1: 启动/激活微信
            if not self.is_wechat_running():
                print(f"   📱 启动微信...")
                if not self.launch_wechat(timeout=5):
                    result["message"] = "❌ 无法启动微信"
                    return result
            else:
                # 激活窗口
                if HAS_UIAUTOMATION and self.find_wechat_window():
                    auto.SetFocus(self.window_hwnd)
            
            time.sleep(1)
            
            # 步骤2: 搜索联系人（优先 UIAutomation，退回键盘热键）
            print(f"   🔍 搜索联系人: {contact_name}")
            search_done = False
            if HAS_UIAUTOMATION and self.find_wechat_window():
                try:
                    search_edit = self.window_hwnd.EditControl(searchDepth=8, Name="搜索")
                    if search_edit and search_edit.Exists(1, 0.2):
                        search_edit.SetFocus()
                        search_edit.GetValuePattern().SetValue('')
                        time.sleep(0.2)
                        search_edit.GetValuePattern().SetValue(contact_name)
                        time.sleep(0.8)
                        pyautogui.press('enter')
                        search_done = True
                except Exception:
                    pass

            if not search_done:
                pyautogui.hotkey('ctrl', 'k')
                time.sleep(0.6)
                pyautogui.typewrite(contact_name, interval=0.05)
                time.sleep(1.0)
                pyautogui.press('enter')
                time.sleep(1.2)

            # 步骤4: 校验已经进入目标会话
            chat_window = None
            if HAS_UIAUTOMATION:
                chat_window = self.find_wechat_window()
                if chat_window:
                    try:
                        chat_header = chat_window.TextControl(searchDepth=8, SubName=contact_name)
                        if not chat_header.Exists(3, 0.5):
                            result["message"] = f"❌ 未找到联系人 {contact_name} 的聊天窗口"
                            return result
                    except Exception:
                        pass

            # 步骤5: 聚焦输入框（优先使用 UIAutomation，其次回退坐标点击）
            input_focused = False
            edit_control = None
            if HAS_UIAUTOMATION and chat_window:
                try:
                    edit_control = chat_window.EditControl(searchDepth=12)
                    if edit_control and edit_control.Exists(1, 0.2):
                        edit_control.SetFocus()
                        input_focused = True
                except Exception:
                    pass

            if not input_focused:
                pyautogui.click(self.CHAT_INPUT_POS[0], self.CHAT_INPUT_POS[1])
                time.sleep(0.3)

            # 步骤6: 将消息写入输入框（剪贴板粘贴避免输入法干扰）
            import subprocess
            p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
            p.communicate(message.encode('utf-8'))

            if HAS_UIAUTOMATION and edit_control:
                try:
                    value_pattern = edit_control.GetValuePattern()
                    value_pattern.SetValue('')
                    time.sleep(0.1)
                except Exception:
                    pass

            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.6)

            # 步骤7: 发送并确认输入框清空
            pyautogui.press('enter')
            time.sleep(1.0)

            if HAS_UIAUTOMATION and edit_control:
                try:
                    value_pattern = edit_control.GetValuePattern()
                    if value_pattern.Value.strip():
                        result["message"] = "❌ 消息可能未发送成功：输入框内容未清空"
                        return result
                except Exception:
                    pass
            
            result["success"] = True
            result["message"] = f"✅ 已向 {contact_name} 发送消息"
            self._last_contact = contact_name
        
        except Exception as e:
            result["message"] = f"❌ 发送失败: {str(e)}"
            import traceback
            traceback.print_exc()
        
        return result
    
    def get_chat_window_screenshot(self, contact_name: str) -> Dict[str, any]:
        """
        获取与指定联系人的聊天窗口截图
        """
        result = {
            "success": False,
            "message": "",
            "image_path": None,
            "contact": contact_name
        }
        
        if not HAS_PYAUTOGUI:
            result["message"] = "❌ 需要安装 pyautogui"
            return result
        
        try:
            # 导航到联系人（如前所述）
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            pyautogui.typewrite(contact_name, interval=0.05)
            time.sleep(1)
            pyautogui.press('down')
            pyautogui.press('enter')
            time.sleep(2)
            
            # 截图
            screenshot = pyautogui.screenshot()
            
            # 保存到文件
            import uuid
            filename = f"wechat_{contact_name}_{uuid.uuid4().hex[:8]}.png"
            save_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
            screenshot.save(save_path)
            
            result["success"] = True
            result["message"] = f"✅ 已截图: {save_path}"
            result["image_path"] = save_path
        
        except Exception as e:
            result["message"] = f"❌ 截图失败: {str(e)}"
        
        return result
    
    def extract_text_from_screenshot(self, image_path: str) -> Dict[str, any]:
        """
        使用 OCR 从截图中提取文本
        """
        result = {
            "success": False,
            "message": "",
            "text": "",
            "image_path": image_path
        }
        
        if not HAS_PYOCR:
            result["message"] = "❌ 需要安装 pytesseract 和 Tesseract-OCR"
            return result
        
        if not os.path.exists(image_path):
            result["message"] = f"❌ 图片不存在: {image_path}"
            return result
        
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            
            result["success"] = True
            result["message"] = f"✅ 已提取文本 ({len(text)} 字符)"
            result["text"] = text
        
        except Exception as e:
            result["message"] = f"❌ OCR 失败: {str(e)}"
        
        return result


# 全局实例
_wechat = None

def get_wechat_automation() -> WeChatAutomation:
    """获取微信自动化实例"""
    global _wechat
    if _wechat is None:
        _wechat = WeChatAutomation()
    return _wechat
