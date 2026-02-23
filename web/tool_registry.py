#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 工具注册系统 - 统一管理所有可供 Agent 调用的工具
支持 Gemini Function Calling API
"""

import os
import sys
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from google.genai import types

# 确保可以导入 web 目录下的模块
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# 延迟导入工具模块 —— 避免循环依赖
_lazy_imports = {}


def _lazy_import(module_name: str, attr_name: str = None):
    """延迟导入模块或属性"""
    global _lazy_imports
    
    if module_name not in _lazy_imports:
        if module_name == "wechat_automation":
            try:
                from web.wechat_automation import get_wechat_automation
            except ImportError:
                from wechat_automation import get_wechat_automation
            _lazy_imports[module_name] = get_wechat_automation()
        elif module_name == "browser_automation":
            try:
                from web.browser_automation import get_browser_automation
            except ImportError:
                from browser_automation import get_browser_automation
            _lazy_imports[module_name] = get_browser_automation
        elif module_name == "calendar_manager":
            try:
                from web.calendar_manager import get_calendar_manager
            except ImportError:
                from calendar_manager import get_calendar_manager
            _lazy_imports[module_name] = get_calendar_manager()
        elif module_name == "reminder_manager":
            try:
                from web.reminder_manager import get_reminder_manager
            except ImportError:
                from reminder_manager import get_reminder_manager
            _lazy_imports[module_name] = get_reminder_manager()
        elif module_name == "search_engine":
            try:
                from web.search_engine import get_search_engine
            except ImportError:
                from search_engine import get_search_engine
            _lazy_imports[module_name] = get_search_engine()
        elif module_name == "windows_notifier":
            try:
                import web.windows_notifier as notifier
            except ImportError:
                import windows_notifier as notifier
            _lazy_imports[module_name] = notifier
        elif module_name == "clipboard_manager":
            try:
                from web.clipboard_manager import get_clipboard_manager
            except ImportError:
                from clipboard_manager import get_clipboard_manager
            _lazy_imports[module_name] = get_clipboard_manager()
        else:
            raise ImportError(f"Unknown lazy module: {module_name}")
    
    if attr_name:
        return getattr(_lazy_imports[module_name], attr_name)
    return _lazy_imports[module_name]


class ToolRegistry:
    """工具注册中心 - 管理所有 Agent 可用的工具"""
    
    def __init__(self):
        self._tools: Dict[str, Dict] = {}
        self._station_code_cache: Dict[str, str] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        
        # ========== 微信工具 ==========
        self.register(
            name="send_wechat_message",
            description="发送微信消息给指定联系人",
            parameters={
                "type": "object",
                "properties": {
                    "contact_name": {
                        "type": "string",
                        "description": "联系人姓名（必须完全匹配微信通讯录中的名称）"
                    },
                    "message": {
                        "type": "string",
                        "description": "要发送的消息内容"
                    }
                },
                "required": ["contact_name", "message"]
            },
            handler=self._handle_send_wechat
        )
        
        self.register(
            name="read_wechat_message",
            description="读取微信聊天记录（通过截图+OCR或Gemini Vision）",
            parameters={
                "type": "object",
                "properties": {
                    "contact_name": {
                        "type": "string",
                        "description": "联系人姓名"
                    }
                },
                "required": ["contact_name"]
            },
            handler=self._handle_read_wechat
        )
        
        # ========== 日程和提醒工具 ==========
        self.register(
            name="add_calendar_event",
            description="添加日程安排（支持会议、约会、任务等）",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "日程标题"},
                    "description": {"type": "string", "description": "详细描述"},
                    "start_time": {
                        "type": "string",
                        "description": "开始时间（ISO格式，如 '2026-02-10T14:00:00'）"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "结束时间（可选，ISO格式）"
                    },
                    "remind_before_minutes": {
                        "type": "integer",
                        "description": "提前多少分钟提醒（默认15分钟）"
                    }
                },
                "required": ["title", "start_time"]
            },
            handler=self._handle_add_calendar
        )
        
        self.register(
            name="list_calendar_events",
            description="查看日程列表",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回的最大数量（默认10）"
                    }
                }
            },
            handler=self._handle_list_calendar
        )
        
        self.register(
            name="add_reminder",
            description="设置定时提醒（用于稍后提醒、重要事项通知等）",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "提醒标题"},
                    "message": {"type": "string", "description": "提醒内容"},
                    "remind_at": {
                        "type": "string",
                        "description": "提醒时间（ISO格式）或从现在起的秒数"
                    }
                },
                "required": ["title", "message", "remind_at"]
            },
            handler=self._handle_add_reminder
        )
        
        # ========== 网络搜索工具 ==========
        self.register(
            name="web_search",
            description="通过 Google 搜索实时获取信息（新闻、天气、价格、事实等）",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_web_search
        )

        self.register(
            name="get_12306_ticket_url",
            description="生成 12306 车票查询链接（含车站与日期），用于让用户直接打开查看车次信息",
            parameters={
                "type": "object",
                "properties": {
                    "from_station": {
                        "type": "string",
                        "description": "出发车站名称（如 南京南）"
                    },
                    "to_station": {
                        "type": "string",
                        "description": "到达车站名称（如 北京南）"
                    },
                    "date": {
                        "type": "string",
                        "description": "出发日期（YYYY-MM-DD）"
                    },
                    "open_in_browser": {
                        "type": "boolean",
                        "description": "是否直接打开浏览器（默认 false）"
                    }
                },
                "required": ["from_station", "to_station", "date"]
            },
            handler=self._handle_get_12306_ticket_url
        )
        
        # ========== 浏览器自动化工具 ==========
        self.register(
            name="open_url",
            description="在浏览器中打开指定网址",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要打开的网址（完整URL）"
                    }
                },
                "required": ["url"]
            },
            handler=self._handle_open_url
        )
        
        self.register(
            name="browser_get_page_info",
            description="获取当前浏览器页面的信息（标题、URL、源代码）",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_browser_get_info
        )
        
        # ========== 本地搜索工具 ==========
        self.register(
            name="search_local_files",
            description="搜索本地工作区的文件、聊天记录、笔记",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数（默认10）"
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_search_local
        )
        
        # ========== 系统操作工具 ==========
        self.register(
            name="open_application",
            description="打开本地应用程序（如 Chrome、记事本、计算器等）",
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "应用程序名称（如 'chrome', 'notepad', 'calc'）"
                    }
                },
                "required": ["app_name"]
            },
            handler=self._handle_open_app
        )
        
        self.register(
            name="notify_user",
            description="发送系统通知提醒用户",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "通知标题"},
                    "message": {"type": "string", "description": "通知内容"},
                    "duration": {
                        "type": "integer",
                        "description": "显示时长（秒，默认5）"
                    }
                },
                "required": ["title", "message"]
            },
            handler=self._handle_notify
        )
        
        # ========== 文件生成工具 ==========
        self.register(
            name="generate_document",
            description="生成文档文件（PDF 或 Word）。内容参数应包含完整的文档正文，而非摘要描述。",
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "文档的完整正文内容（Markdown 格式），不是描述"
                    },
                    "title": {
                        "type": "string",
                        "description": "文档标题（用于文件命名）"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "文件类型（pdf 或 docx），默认 docx",
                        "enum": ["pdf", "docx"]
                    }
                },
                "required": ["content"]
            },
            handler=self._handle_generate_document
        )
        
        # ========== P1: 剪贴板工具 ==========
        self.register(
            name="read_clipboard",
            description="读取用户最近的剪贴板历史记录",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回的最大条数（默认5）"
                    }
                }
            },
            handler=self._handle_read_clipboard
        )
        
        self.register(
            name="search_clipboard",
            description="搜索剪贴板历史中包含关键词的内容",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_search_clipboard
        )
        
        # ========== P1: 文件读取工具 ==========
        self.register(
            name="read_file",
            description="读取本地文件内容（文本、代码等纯文本文件）",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（绝对路径或相对于工作区的路径）"
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "最大读取字符数（默认5000，防止过大文件）"
                    }
                },
                "required": ["file_path"]
            },
            handler=self._handle_read_file
        )
        
        self.register(
            name="read_document",
            description="读取文档文件内容（Word、Excel、PPT、PDF）",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文档文件路径"
                    }
                },
                "required": ["file_path"]
            },
            handler=self._handle_read_document
        )
        
        # ========== Excel数据分析工具 ==========
        self.register(
            name="analyze_excel_data",
            description="分析Excel文件数据，支持多种分析类型：提取前N名客户、分组汇总、统计分析等。适用于销售数据、财务数据等表格分析",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Excel文件路径（相对于workspace目录或绝对路径）"
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "分析类型：top_customers(提取前N名客户)、group_aggregate(分组汇总)、statistics(统计分析)、smart(智能分析)",
                        "enum": ["top_customers", "group_aggregate", "statistics", "smart"]
                    },
                    "customer_col": {
                        "type": "string",
                        "description": "客户名称列名（用于top_customers，留空自动识别）"
                    },
                    "amount_col": {
                        "type": "string",
                        "description": "金额列名（用于top_customers，留空自动识别）"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "提取前N名（用于top_customers，默认10）"
                    },
                    "group_by": {
                        "type": "string",
                        "description": "分组依据列名（用于group_aggregate）"
                    },
                    "agg_col": {
                        "type": "string",
                        "description": "聚合目标列名（用于group_aggregate）"
                    },
                    "agg_func": {
                        "type": "string",
                        "description": "聚合函数（用于group_aggregate）：sum/mean/count/max/min",
                        "enum": ["sum", "mean", "count", "max", "min"]
                    },
                    "question": {
                        "type": "string",
                        "description": "分析需求描述（用于smart智能分析）"
                    }
                },
                "required": ["file_path"]
            },
            handler=self._handle_analyze_excel
        )
        
        # ========== P1: 浏览器交互工具 ==========
        self.register(
            name="browser_click",
            description="点击浏览器页面中的元素（按钮、链接等）",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS选择器或XPath（如 '#submit-btn', '//button[text()=\"提交\"]'）"
                    },
                    "by": {
                        "type": "string",
                        "description": "选择器类型（css/xpath/id/name/text），默认 css",
                        "enum": ["css", "xpath", "id", "name", "text"]
                    }
                },
                "required": ["selector"]
            },
            handler=self._handle_browser_click
        )
        
        self.register(
            name="browser_input_text",
            description="在浏览器页面的输入框中输入文本",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "输入框的CSS选择器或XPath"
                    },
                    "text": {
                        "type": "string",
                        "description": "要输入的文本内容"
                    },
                    "by": {
                        "type": "string",
                        "description": "选择器类型（css/xpath/id/name），默认 css",
                        "enum": ["css", "xpath", "id", "name"]
                    }
                },
                "required": ["selector", "text"]
            },
            handler=self._handle_browser_input
        )
        
        self.register(
            name="browser_screenshot",
            description="截取当前浏览器页面的截图",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_browser_screenshot
        )
        
        self.register(
            name="browser_get_text",
            description="获取浏览器页面中指定元素的文本内容",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS选择器或XPath"
                    },
                    "by": {
                        "type": "string",
                        "description": "选择器类型（css/xpath/id/name），默认 css",
                        "enum": ["css", "xpath", "id", "name"]
                    }
                },
                "required": ["selector"]
            },
            handler=self._handle_browser_get_text
        )
        
        # ========== P1: 增强日程/提醒工具 ==========
        self.register(
            name="list_reminders",
            description="列出所有待执行的提醒",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_list_reminders
        )
        
        self.register(
            name="cancel_reminder",
            description="取消一个待执行的提醒",
            parameters={
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "string",
                        "description": "提醒ID"
                    }
                },
                "required": ["reminder_id"]
            },
            handler=self._handle_cancel_reminder
        )
        
        self.register(
            name="delete_calendar_event",
            description="删除一个日程事件",
            parameters={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "日程事件ID"
                    }
                },
                "required": ["event_id"]
            },
            handler=self._handle_delete_calendar
        )
        
        # ========== P2: 实用工具 ==========
        self.register(
            name="get_current_datetime",
            description="获取当前系统日期和时间，用于创建提醒、日程或回答与时间相关的问题",
            parameters={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区名称，如 'Asia/Shanghai'（默认使用系统本地时区）"
                    }
                },
                "required": []
            },
            handler=self._handle_get_datetime
        )
        
        self.register(
            name="run_python_code",
            description="在沙盒环境中执行一段 Python 代码，适合数据计算、格式转换、文本处理等任务。代码在独立子进程中运行，有超时限制。",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的 Python 代码字符串"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒），默认 10 秒，最大 30 秒"
                    }
                },
                "required": ["code"]
            },
            handler=self._handle_run_python_code
        )
        
        # ========== 文件格式转换工具 ==========
        self.register(
            name="convert_file",
            description="将文件转换为其他格式。支持: Word↔PDF, Word↔TXT, PDF→Word, PDF→TXT, Excel→PDF, Markdown→Word/PDF, TXT→Word/PDF 等。用户上传文件后可请求转换。",
            parameters={
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "源文件路径（相对于工作区或绝对路径）"
                    },
                    "target_format": {
                        "type": "string",
                        "description": "目标格式",
                        "enum": ["pdf", "docx", "txt", "md", "html"]
                    },
                    "output_name": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名，可选）"
                    }
                },
                "required": ["source_path", "target_format"]
            },
            handler=self._handle_convert_file
        )

        # ========== P1: 文件写入工具 ==========
        self.register(
            name="write_file",
            description="将文本内容写入本地文件（可创建新文件或覆盖已有文件）",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对于工作区根目录的路径）"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的文本内容"
                    },
                    "append": {
                        "type": "boolean",
                        "description": "是否追加到文件末尾（默认 false，覆盖写入）"
                    }
                },
                "required": ["file_path", "content"]
            },
            handler=self._handle_write_file
        )
    
    def register(self, name: str, description: str, parameters: Dict, handler: Callable):
        """注册一个工具"""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler
        }
        print(f"[ToolRegistry] 已注册工具: {name}")
    
    def get_declarations(self) -> List[Dict]:
        """获取 Gemini Function Calling 格式的工具声明列表"""
        declarations = []
        for tool_name, tool_info in self._tools.items():
            declarations.append({
                "name": tool_info["name"],
                "description": tool_info["description"],
                "parameters": tool_info["parameters"]
            })
        return declarations
    
    def execute(self, name: str, args: Dict) -> Dict[str, Any]:
        """执行工具调用"""
        if name not in self._tools:
            return {
                "success": False,
                "error": f"工具 '{name}' 不存在"
            }
        
        tool = self._tools[name]
        handler = tool["handler"]
        
        try:
            print(f"[ToolRegistry] 执行工具: {name}({json.dumps(args, ensure_ascii=False)[:100]}...)")
            result = handler(**args)
            print(f"[ToolRegistry] 工具 {name} 执行完成: {result.get('success', False)}")
            return result
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[ToolRegistry] 工具 {name} 执行失败: {e}\n{error_detail}")
            return {
                "success": False,
                "error": str(e),
                "traceback": error_detail
            }
    
    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有可用工具（用于调试和展示）"""
        return [
            {"name": tool["name"], "description": tool["description"]}
            for tool in self._tools.values()
        ]
    
    # ========== 工具处理函数 ==========
    
    def _handle_send_wechat(self, contact_name: str, message: str) -> Dict:
        """发送微信消息"""
        try:
            wechat = _lazy_import("wechat_automation")
            result = wechat.send_message_to_contact(contact_name, message)
            # 规范化上游返回格式
            if not isinstance(result, dict):
                return {"success": False, "error": "微信模块返回格式异常"}
            if "success" not in result:
                result["success"] = True
            if "message" not in result:
                result["message"] = f"已发送消息给 {contact_name}"
            return result
        except Exception as e:
            return {"success": False, "error": f"发送微信消息失败: {str(e)}"}
    
    def _handle_read_wechat(self, contact_name: str) -> Dict:
        """读取微信消息（截图+OCR）"""
        wechat = _lazy_import("wechat_automation")
        
        # 截图
        screenshot_result = wechat.get_chat_window_screenshot(contact_name)
        if not screenshot_result.get("success"):
            return screenshot_result
        
        # OCR 识别
        image_path = screenshot_result.get("image_path")
        if image_path:
            ocr_result = wechat.extract_text_from_screenshot(image_path)
            return {
                "success": True,
                "contact": contact_name,
                "text": ocr_result.get("text", ""),
                "image_path": image_path,
                "message": f"已读取 {contact_name} 的聊天记录"
            }
        else:
            return {"success": False, "error": "截图失败"}
    
    def _handle_add_calendar(self, title: str, start_time: str, 
                            description: str = "", end_time: str = None, 
                            remind_before_minutes: int = 15) -> Dict:
        """添加日程"""
        calendar = _lazy_import("calendar_manager")
        
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time) if end_time else None
            
            event_id = calendar.add_event(
                title=title,
                description=description,
                start=start_dt,
                end=end_dt,
                remind_before_minutes=remind_before_minutes
            )
            
            return {
                "success": True,
                "event_id": event_id,
                "message": f"已添加日程: {title}",
                "start_time": start_time,
                "remind_before": f"{remind_before_minutes}分钟"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"添加日程失败: {str(e)}"
            }
    
    def _handle_list_calendar(self, limit: int = 10) -> Dict:
        """查看日程列表"""
        calendar = _lazy_import("calendar_manager")
        events = calendar.list_events(limit=limit)
        
        return {
            "success": True,
            "events": events,
            "count": len(events),
            "message": f"找到 {len(events)} 个日程"
        }
    
    def _handle_add_reminder(self, title: str, message: str, remind_at: str) -> Dict:
        """添加提醒"""
        reminder = _lazy_import("reminder_manager")
        
        try:
            # 如果是数字，表示从现在起的秒数
            if remind_at.isdigit():
                reminder_id = reminder.add_reminder_in(
                    title=title,
                    message=message,
                    seconds_from_now=int(remind_at)
                )
            else:
                # ISO 格式时间
                remind_dt = datetime.fromisoformat(remind_at)
                reminder_id = reminder.add_reminder(
                    title=title,
                    message=message,
                    remind_at=remind_dt
                )
            
            return {
                "success": True,
                "reminder_id": reminder_id,
                "message": f"已设置提醒: {title}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"设置提醒失败: {str(e)}"
            }
    
    def _handle_web_search(self, query: str) -> Dict:
        """网络搜索（通过 Gemini Grounding）"""
        try:
            from web_searcher import search_with_grounding
        except ImportError:
            from web.web_searcher import search_with_grounding
        
        result = search_with_grounding(query)
        
        # 规范化返回格式
        if not isinstance(result, dict):
            return {"success": False, "error": "搜索返回格式异常"}
        
        # 确保 success/message 字段存在
        if "success" not in result:
            result["success"] = bool(result.get("response"))
        if "message" not in result:
            result["message"] = result.get("response", result.get("error", ""))
        
        return result

    def _handle_get_12306_ticket_url(
        self,
        from_station: str,
        to_station: str,
        date: str,
        open_in_browser: bool = False
    ) -> Dict:
        """生成 12306 车票查询链接"""
        try:
            import json as _json
            from urllib.parse import quote
            from urllib.request import urlopen
        except Exception as e:
            return {"success": False, "error": f"初始化失败: {str(e)}"}

        def _get_station_code(name: str) -> str:
            cached = self._station_code_cache.get(name)
            if cached:
                return cached

            try:
                url = f"https://search.12306.cn/search/v1/station?station_name={quote(name)}"
                with urlopen(url, timeout=6) as resp:
                    data = _json.loads(resp.read().decode("utf-8"))
                items = data.get("data", []) if isinstance(data, dict) else []
                if not items:
                    return ""

                exact = next((i for i in items if i.get("station_name") == name), None)
                chosen = exact or items[0]
                code = chosen.get("station_code", "")
                if code:
                    self._station_code_cache[name] = code
                return code
            except Exception:
                return ""

        from_code = _get_station_code(from_station)
        to_code = _get_station_code(to_station)

        if not from_code or not to_code:
            return {
                "success": False,
                "error": "无法解析车站代码，请确认车站名称是否正确",
                "from_station": from_station,
                "to_station": to_station
            }

        url = (
            "https://kyfw.12306.cn/otn/leftTicket/init?"
            f"linktypeid=dc&fs={quote(from_station)},{from_code}"
            f"&ts={quote(to_station)},{to_code}"
            f"&date={quote(date)}&flag=N,N,Y"
        )

        if open_in_browser:
            opened = self._handle_open_url(url)
            if not opened.get("success"):
                return {"success": False, "error": opened.get("error", "打开失败"), "url": url}

        return {
            "success": True,
            "url": url,
            "from_station": from_station,
            "to_station": to_station,
            "date": date,
            "message": "已生成 12306 车票查询链接"
        }
    
    def _handle_open_url(self, url: str) -> Dict:
        """打开网址"""
        try:
            browser_getter = _lazy_import("browser_automation")
            browser = browser_getter(headless=False)
            
            success = browser.open_url(url)
            if success:
                return {
                    "success": True,
                    "url": url,
                    "message": f"已在浏览器中打开: {url}"
                }
            else:
                return {
                    "success": False,
                    "error": f"无法打开网址: {url}"
                }
        except Exception as e:
            return {"success": False, "error": f"打开网址失败: {str(e)}"}
    
    def _handle_browser_get_info(self) -> Dict:
        """获取当前浏览器页面信息"""
        try:
            browser_getter = _lazy_import("browser_automation")
            browser = browser_getter(headless=False)
            
            url = browser.get_current_url()
            title = browser.get_text("title") or "Unknown"
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "message": f"当前页面: {title}"
            }
        except Exception as e:
            return {"success": False, "error": f"获取浏览器信息失败: {str(e)}"}
    
    def _handle_search_local(self, query: str, max_results: int = 10) -> Dict:
        """搜索本地文件"""
        try:
            search_engine = _lazy_import("search_engine")
            results = search_engine.search_all(query, max_results=max_results)
            
            total = sum(len(v) for v in results.values()) if isinstance(results, dict) else 0
            
            return {
                "success": True,
                "results": results,
                "total": total,
                "message": f"找到 {total} 个相关结果"
            }
        except Exception as e:
            return {"success": False, "error": f"搜索失败: {str(e)}"}
    
    # 应用程序白名单（名称 -> 可执行文件候选列表，按优先级排列）
    _APP_WHITELIST = {
        # 社交通讯
        "微信": ["WeChat", r"C:\Program Files\Tencent\WeChat\WeChat.exe", r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"],
        "wechat": ["WeChat", r"C:\Program Files\Tencent\WeChat\WeChat.exe", r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"],
        "qq": ["QQ", r"C:\Program Files\Tencent\QQ\Bin\QQ.exe", r"C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe", r"C:\Program Files\Tencent\QQNT\QQ.exe"],
        "钉钉": ["DingTalk", "dingtalk"],
        "飞书": ["Feishu", "Lark"],
        "telegram": ["Telegram"],
        "discord": ["Discord"],
        # 浏览器
        "chrome": ["chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
        "谷歌浏览器": ["chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
        "浏览器": ["chrome", "msedge", "firefox"],
        "edge": ["msedge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
        "firefox": ["firefox", r"C:\Program Files\Mozilla Firefox\firefox.exe"],
        # 开发工具
        "vscode": ["code"], "vs code": ["code"], "code": ["code"],
        "terminal": ["wt", "cmd", "powershell"], "终端": ["wt", "cmd", "powershell"],
        # 办公
        "记事本": ["notepad"], "notepad": ["notepad"],
        "计算器": ["calc"], "calc": ["calc"],
        "word": ["winword", "WINWORD"], "excel": ["excel", "EXCEL"],
        "powerpoint": ["powerpnt"], "ppt": ["powerpnt"],
        "wps": ["wps", "wpsoffice", r"C:\Users\12524\AppData\Local\Kingsoft\WPS Office\ksolaunch.exe"],
        # 系统
        "资源管理器": ["explorer"], "explorer": ["explorer"],
        "设置": ["ms-settings:"], "控制面板": ["control"],
        "任务管理器": ["taskmgr"], "画图": ["mspaint"],
        # 媒体
        "网易云": ["cloudmusic", r"C:\Program Files (x86)\Netease\CloudMusic\cloudmusic.exe"],
        "网易云音乐": ["cloudmusic", r"C:\Program Files (x86)\Netease\CloudMusic\cloudmusic.exe"],
        "spotify": ["Spotify"],
        # 游戏
        "steam": ["steam", r"C:\Program Files (x86)\Steam\steam.exe", r"D:\Steam\steam.exe"],
    }

    def _find_app_executable(self, app_key: str) -> Optional[str]:
        """智能查找应用程序可执行路径（多级回退）"""
        import shutil
        import glob

        candidates = self._APP_WHITELIST.get(app_key, [])

        # 1. 遍历候选列表：完整路径 → shutil.which
        for c in candidates:
            if os.path.isabs(c) and os.path.exists(c):
                return c
            found = shutil.which(c)
            if found:
                return found

        # 2. 从开始菜单搜索 .lnk 快捷方式
        start_menu_paths = [
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
        ]
        for sm_path in start_menu_paths:
            if not os.path.exists(sm_path):
                continue
            for lnk in glob.glob(os.path.join(sm_path, "**", "*.lnk"), recursive=True):
                lnk_name = os.path.basename(lnk).lower().replace(".lnk", "")
                if app_key in lnk_name or lnk_name in app_key:
                    return lnk
                # 也对候选名称做匹配
                for c in candidates:
                    c_lower = os.path.basename(c).lower().replace(".exe", "")
                    if c_lower in lnk_name or lnk_name in c_lower:
                        return lnk

        # 3. 最后用 shell=True 尝试（会在 PATH 和 App Paths 注册表中查找）
        return None

    def _handle_open_app(self, app_name: str) -> Dict:
        """打开应用程序（白名单 + 智能路径查找）"""
        import subprocess
        import sys

        app_key = app_name.lower().strip()
        if app_key not in self._APP_WHITELIST:
            allowed = sorted(set(self._APP_WHITELIST.keys()))
            return {
                "success": False,
                "error": f"安全限制：应用 '{app_name}' 不在白名单中。可用应用: {', '.join(allowed)}"
            }

        exe_path = self._find_app_executable(app_key)

        # 尝试启动
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        errors = []

        if exe_path:
            try:
                if exe_path.endswith(".lnk"):
                    os.startfile(exe_path)
                elif ":" in exe_path and not os.path.isabs(exe_path):
                    # URI 方案，如 ms-settings:
                    os.startfile(exe_path)
                else:
                    subprocess.Popen([exe_path], creationflags=creation_flags)
                return {"success": True, "app": app_name, "message": f"已打开应用: {app_name}"}
            except Exception as e:
                errors.append(f"{exe_path}: {e}")

        # 回退：用 shell=True 尝试第一个候选名称
        for c in self._APP_WHITELIST[app_key]:
            if os.path.isabs(c):
                continue
            try:
                subprocess.Popen(c, shell=True, creationflags=creation_flags)
                return {"success": True, "app": app_name, "message": f"已打开应用: {app_name}"}
            except Exception as e:
                errors.append(f"shell({c}): {e}")

        return {
            "success": False,
            "error": f"无法打开应用 '{app_name}'，已尝试多种方式均失败: {'; '.join(errors)}"
        }
    
    def _handle_notify(self, title: str, message: str, duration: int = 5) -> Dict:
        """发送系统通知"""
        try:
            notifier = _lazy_import("windows_notifier")
            notifier.show_toast(title, message, duration)
            return {
                "success": True,
                "message": "通知已发送"
            }
        except Exception as e:
            return {"success": False, "error": f"发送通知失败: {str(e)}"}
    
    def _handle_generate_document(self, content: str, title: str = "", file_type: str = "docx", enable_quality_check: bool = True, progress_callback: Optional[Callable] = None) -> Dict:
        """生成文档 — content 是完整正文，不是描述
        
        Args:
            content: 完整正文内容
            title: 文档标题
            file_type: pdf 或 docx
            enable_quality_check: 是否启用质量检查和改进（默认启用）
            progress_callback: 进度回调函数，签名：callback(stage, message, details=None)
        """
        try:
            from document_generator import save_docx, save_pdf
        except ImportError:
            try:
                from web.document_generator import save_docx, save_pdf
            except ImportError:
                return {
                    "success": False,
                    "error": "文档生成模块不可用"
                }
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            workspace_docs = os.path.join(project_root, 'workspace', 'documents')
            os.makedirs(workspace_docs, exist_ok=True)
            
            # 第1步：质量评估（如果启用）
            final_content = content
            evaluation_result = None
            improvement_result = None
            
            if enable_quality_check:
                # 通知：开始评估
                if progress_callback:
                    try:
                        progress_callback("evaluating", "正在评估文档质量...")
                    except:
                        pass
                
                try:
                    from quality_evaluator import DocumentEvaluator
                    evaluator = DocumentEvaluator()
                    eval_obj = evaluator.evaluate_document(content, file_type)
                    evaluation_result = {
                        "overall_score": eval_obj.overall_score,
                        "category_scores": eval_obj.category_scores,
                        "issues": eval_obj.issues,
                        "suggestions": eval_obj.suggestions,
                        "needs_improvement": eval_obj.needs_improvement,
                        "improvement_priority": eval_obj.improvement_priority
                    }
                    
                    # 通知：评估完成
                    if progress_callback:
                        try:
                            progress_callback("evaluated", f"评估完成 (评分: {eval_obj.overall_score:.1f}/100)", {
                                "score": eval_obj.overall_score,
                                "needs_improvement": eval_obj.needs_improvement
                            })
                        except:
                            pass
                    
                    # 第2步：如果需要改进，尝试改进
                    if eval_obj.needs_improvement:
                        if progress_callback:
                            try:
                                progress_callback("improving", "正在改进内容质量...")
                            except:
                                pass
                        
                        try:
                            # 获取 Gemini 客户端
                            from app import get_client
                            client = get_client()
                            
                            from feedback_loop import FeedbackLoopManager
                            manager = FeedbackLoopManager(lambda: client)
                            
                            improvement_result = manager.improve_document_content(
                                final_content,
                                evaluation_result,
                                title or "文档",
                                progress_callback=progress_callback,
                                model_id="gemini-3-flash-preview"
                            )
                            
                            final_content = improvement_result.get("improved_content", final_content)
                            
                            if progress_callback:
                                try:
                                    progress_callback("improved", f"改进完成 (共 {improvement_result.get('iterations', 0)} 轮)", {
                                        "iterations": improvement_result.get("iterations", 0),
                                        "final_score": improvement_result.get("final_score")
                                    })
                                except:
                                    pass
                        
                        except Exception as e:
                            print(f"[文档生成] 改进失败: {e}")
                            # 即使改进失败，继续使用原始内容生成文档
                            if progress_callback:
                                try:
                                    progress_callback("improvement_failed", f"改进失败: {str(e)}")
                                except:
                                    pass
                
                except Exception as e:
                    print(f"[文档生成] 质量评估失败: {e}")
                    # 评估失败不影响文档生成
                    if progress_callback:
                        try:
                            progress_callback("evaluation_failed", f"评估失败: {str(e)}")
                        except:
                            pass
            
            # 第3步：生成文件
            if progress_callback:
                try:
                    progress_callback("generating", f"正在生成 {file_type.upper()} 文件...")
                except:
                    pass
            
            # 文件名：使用 title 或时间戳
            import re
            safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '_', title)[:30] if title else ""
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            basename = f"{safe_title}_{timestamp}" if safe_title else f"doc_{timestamp}"
            
            if file_type == "pdf":
                file_path = os.path.join(workspace_docs, f"{basename}.pdf")
                result = save_pdf(final_content, file_path)
            else:
                file_path = os.path.join(workspace_docs, f"{basename}.docx")
                result = save_docx(final_content, file_path)
            
            if result:
                # 通知：生成完成
                if progress_callback:
                    try:
                        progress_callback("completed", f"文档已生成: {os.path.basename(file_path)}", {
                            "file_path": file_path,
                            "file_type": file_type
                        })
                    except:
                        pass
                
                response = {
                    "success": True,
                    "file_path": file_path,
                    "file_type": file_type,
                    "message": f"已生成 {file_type.upper()} 文档: {os.path.basename(file_path)}"
                }
                
                # 附加质量评估信息
                if evaluation_result:
                    response["quality_assessment"] = {
                        "initial_score": evaluation_result.get("overall_score", 0),
                        "was_improved": improvement_result is not None,
                        "improvement_iterations": improvement_result.get("iterations", 0) if improvement_result else 0,
                        "final_score": improvement_result.get("final_score") if improvement_result else evaluation_result.get("overall_score"),
                        "issues": evaluation_result.get("issues", []),
                        "suggestions": evaluation_result.get("suggestions", [])
                    }
                
                return response
            else:
                if progress_callback:
                    try:
                        progress_callback("error", "文档生成返回空结果")
                    except:
                        pass
                
                return {
                    "success": False,
                    "error": "文档生成返回空结果"
                }
        except Exception as e:
            if progress_callback:
                try:
                    progress_callback("error", f"文档生成失败: {str(e)}")
                except:
                    pass
            
            return {
                "success": False,
                "error": f"文档生成失败: {str(e)}"
            }
    
    # ========== P1: 剪贴板工具处理函数 ==========
    
    def _handle_read_clipboard(self, limit: int = 5) -> Dict:
        """读取剪贴板历史"""
        try:
            clipboard = _lazy_import("clipboard_manager")
            history = clipboard.get_recent(limit=limit)
            return {
                "success": True,
                "items": history,
                "count": len(history),
                "message": f"读取到 {len(history)} 条剪贴板记录"
            }
        except Exception as e:
            return {"success": False, "error": f"读取剪贴板失败: {str(e)}"}
    
    def _handle_search_clipboard(self, query: str) -> Dict:
        """搜索剪贴板历史"""
        try:
            clipboard = _lazy_import("clipboard_manager")
            results = clipboard.search_history(query)
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "message": f"在剪贴板历史中找到 {len(results)} 条匹配记录"
            }
        except Exception as e:
            return {"success": False, "error": f"搜索剪贴板失败: {str(e)}"}
    
    # ========== P1: 文件读取工具处理函数 ==========
    
    def _handle_read_file(self, file_path: str, max_chars: int = 5000) -> Dict:
        """读取文本文件内容"""
        try:
            # 解析路径 — 支持相对路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            workspace_root = os.path.join(project_root, 'workspace')
            
            if not os.path.isabs(file_path):
                file_path = os.path.join(workspace_root, file_path)
            
            # 安全检查：只允许读取 workspace 目录下的文件
            normalized = os.path.normpath(file_path)
            if not normalized.startswith(os.path.normpath(workspace_root)):
                return {"success": False, "error": "安全限制：只能读取 workspace 目录下的文件"}
            
            if not os.path.exists(file_path):
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(max_chars)
            
            truncated = file_size > max_chars
            
            return {
                "success": True,
                "content": content,
                "file_path": file_path,
                "file_size": file_size,
                "truncated": truncated,
                "message": f"已读取文件: {os.path.basename(file_path)} ({file_size} bytes)"
                           + (" [已截断]" if truncated else "")
            }
        except Exception as e:
            return {"success": False, "error": f"读取文件失败: {str(e)}"}
    
    def _handle_read_document(self, file_path: str) -> Dict:
        """读取文档（Word/Excel/PPT/PDF）"""
        try:
            try:
                from document_reader import DocumentReader
            except ImportError:
                from web.document_reader import DocumentReader
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            workspace_root = os.path.join(project_root, 'workspace')
            
            if not os.path.isabs(file_path):
                file_path = os.path.join(workspace_root, file_path)
            
            # 安全检查：只允许读取 workspace 目录下的文件
            normalized = os.path.normpath(file_path)
            if not normalized.startswith(os.path.normpath(workspace_root)):
                return {"success": False, "error": "安全限制：只能读取 workspace 目录下的文件"}
            
            if not os.path.exists(file_path):
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            reader = DocumentReader()
            doc_data = reader.read_document(file_path)
            
            # 截取文本防止过长
            formatted = reader.format_for_ai(doc_data)
            if len(formatted) > 8000:
                formatted = formatted[:8000] + "\n\n... [内容已截断]"
            
            return {
                "success": True,
                "content": formatted,
                "file_path": file_path,
                "message": f"已读取文档: {os.path.basename(file_path)}"
            }
        except Exception as e:
            return {"success": False, "error": f"读取文档失败: {str(e)}"}
    
    def _handle_analyze_excel(self, 
                             file_path: str, 
                             analysis_type: str = "smart",
                             **kwargs) -> Dict:
        """分析Excel文件数据"""
        try:
            try:
                from excel_analyzer import ExcelAnalyzer
            except ImportError:
                from web.excel_analyzer import ExcelAnalyzer
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            workspace_root = os.path.join(project_root, 'workspace')
            
            # 处理路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(workspace_root, file_path)
            
            # 安全检查：只允许读取 workspace 目录下的文件
            normalized = os.path.normpath(file_path)
            if not normalized.startswith(os.path.normpath(workspace_root)):
                return {"success": False, "error": "安全限制：只能分析 workspace 目录下的文件"}
            
            if not os.path.exists(file_path):
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            # 执行分析
            analyzer = ExcelAnalyzer()
            
            if analysis_type == "top_customers":
                result = analyzer.analyze_top_customers(
                    file_path=file_path,
                    customer_col=kwargs.get('customer_col'),
                    amount_col=kwargs.get('amount_col'),
                    top_n=kwargs.get('top_n', 10)
                )
            elif analysis_type == "group_aggregate":
                if not kwargs.get('group_by') or not kwargs.get('agg_col'):
                    return {
                        "success": False,
                        "error": "group_aggregate 需要指定 group_by 和 agg_col 参数"
                    }
                result = analyzer.group_and_aggregate(
                    file_path=file_path,
                    group_by=kwargs.get('group_by'),
                    agg_col=kwargs.get('agg_col'),
                    agg_func=kwargs.get('agg_func', 'sum')
                )
            elif analysis_type == "statistics":
                columns = kwargs.get('columns')
                result = analyzer.calculate_statistics(file_path=file_path, columns=columns)
            elif analysis_type == "smart":
                question = kwargs.get('question', '')
                result = analyzer.smart_analyze(file_path=file_path, question=question)
            else:
                return {"success": False, "error": f"不支持的分析类型: {analysis_type}"}
            
            # 如果生成了文件，转换为相对路径
            if result.get('success') and result.get('result_file'):
                result_file = result['result_file']
                if os.path.isabs(result_file):
                    try:
                        rel_path = os.path.relpath(result_file, workspace_root)
                        result['result_file_relative'] = rel_path.replace('\\', '/')
                    except Exception:
                        pass
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"Excel分析失败: {str(e)}"}
    
    # ========== P1: 浏览器交互工具处理函数 ==========
    
    def _handle_browser_click(self, selector: str, by: str = "css") -> Dict:
        """点击浏览器元素"""
        try:
            browser_getter = _lazy_import("browser_automation")
            browser = browser_getter(headless=False)
            
            result = browser.click(selector, by=by)
            if result:
                return {
                    "success": True,
                    "message": f"已点击元素: {selector}"
                }
            else:
                return {
                    "success": False,
                    "error": f"无法点击元素: {selector}"
                }
        except Exception as e:
            return {"success": False, "error": f"点击失败: {str(e)}"}
    
    def _handle_browser_input(self, selector: str, text: str, by: str = "css") -> Dict:
        """在浏览器输入框中输入文本"""
        try:
            browser_getter = _lazy_import("browser_automation")
            browser = browser_getter(headless=False)
            
            result = browser.input_text(selector, text, by=by)
            if result:
                return {
                    "success": True,
                    "message": f"已在元素 {selector} 中输入文本"
                }
            else:
                return {
                    "success": False,
                    "error": f"无法在元素 {selector} 中输入文本"
                }
        except Exception as e:
            return {"success": False, "error": f"输入失败: {str(e)}"}
    
    def _handle_browser_screenshot(self) -> Dict:
        """截取浏览器页面截图"""
        try:
            browser_getter = _lazy_import("browser_automation")
            browser = browser_getter(headless=False)
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            screenshots_dir = os.path.join(project_root, 'workspace', 'images')
            os.makedirs(screenshots_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = os.path.join(screenshots_dir, f"browser_{timestamp}.png")
            
            success = browser.take_screenshot(screenshot_path)
            if success:
                return {
                    "success": True,
                    "image_path": screenshot_path,
                    "message": f"已保存截图: {os.path.basename(screenshot_path)}"
                }
            else:
                return {
                    "success": False,
                    "error": "截图失败"
                }
        except Exception as e:
            return {"success": False, "error": f"截图失败: {str(e)}"}
    
    def _handle_browser_get_text(self, selector: str, by: str = "css") -> Dict:
        """获取浏览器元素的文本"""
        try:
            browser_getter = _lazy_import("browser_automation")
            browser = browser_getter(headless=False)
            
            text = browser.get_text(selector, by=by)
            if text is not None:
                return {
                    "success": True,
                    "text": text,
                    "selector": selector,
                    "message": f"已获取元素文本（{len(text)} 字符）"
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到元素: {selector}"
                }
        except Exception as e:
            return {"success": False, "error": f"获取文本失败: {str(e)}"}
    
    # ========== P1: 增强日程/提醒工具处理函数 ==========
    
    def _handle_list_reminders(self) -> Dict:
        """列出所有提醒"""
        try:
            reminder = _lazy_import("reminder_manager")
            reminders = reminder.list_reminders()
            return {
                "success": True,
                "reminders": reminders,
                "count": len(reminders),
                "message": f"共 {len(reminders)} 个待执行提醒"
            }
        except Exception as e:
            return {"success": False, "error": f"获取提醒列表失败: {str(e)}"}
    
    def _handle_cancel_reminder(self, reminder_id: str) -> Dict:
        """取消提醒"""
        try:
            reminder = _lazy_import("reminder_manager")
            success = reminder.cancel_reminder(reminder_id)
            if success:
                return {
                    "success": True,
                    "message": f"已取消提醒: {reminder_id}"
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到提醒: {reminder_id}"
                }
        except Exception as e:
            return {"success": False, "error": f"取消提醒失败: {str(e)}"}
    
    def _handle_delete_calendar(self, event_id: str) -> Dict:
        """删除日程"""
        try:
            calendar = _lazy_import("calendar_manager")
            success = calendar.delete_event(event_id)
            if success:
                return {
                    "success": True,
                    "message": f"已删除日程: {event_id}"
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到日程: {event_id}"
                }
        except Exception as e:
            return {"success": False, "error": f"删除日程失败: {str(e)}"}
    
    # ========== P2: 实用工具处理函数 ==========
    
    def _handle_get_datetime(self, timezone: str = None) -> Dict:
        """获取当前日期时间"""
        try:
            from datetime import datetime, timezone as tz
            import zoneinfo
            
            if timezone:
                try:
                    zi = zoneinfo.ZoneInfo(timezone)
                    now = datetime.now(zi)
                    tz_name = timezone
                except Exception:
                    # 回退到本地时间
                    now = datetime.now()
                    tz_name = "系统本地时区（请求的时区无效）"
            else:
                now = datetime.now()
                tz_name = "系统本地时区"
            
            return {
                "success": True,
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
                "timestamp": int(now.timestamp()),
                "timezone": tz_name
            }
        except Exception as e:
            return {"success": False, "error": f"获取时间失败: {str(e)}"}
    
    def _handle_run_python_code(self, code: str, timeout: int = 10) -> Dict:
        """在沙盒子进程中执行 Python 代码"""
        try:
            import subprocess
            import sys
            import tempfile
            
            # 限制超时范围
            timeout = max(1, min(timeout, 30))
            
            # 安全检查：禁止危险操作
            dangerous_patterns = [
                'os.system', 'subprocess', 'shutil.rmtree',
                '__import__("os")', "__import__('os')",
                'eval(', 'exec(', 'compile(',
                'open(', 'pathlib',  # 禁止文件操作（应使用专用文件工具）
                'socket', 'http.client', 'urllib',  # 禁止网络（应使用搜索工具）
                'ctypes', 'cffi',
            ]
            code_lower = code.lower()
            for pattern in dangerous_patterns:
                if pattern.lower() in code_lower:
                    return {
                        "success": False,
                        "error": f"安全限制：代码中不允许使用 '{pattern}'。文件操作请使用 read_file/write_file 工具，网络请求请使用 web_search 工具。"
                    }
            
            # 在临时文件中执行
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            workspace_root = os.path.join(project_root, 'workspace')
            
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', dir=workspace_root,
                delete=False, encoding='utf-8'
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            
            try:
                result = subprocess.run(
                    [sys.executable, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=workspace_root,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
                )
                
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                
                # 截断过长输出
                max_len = 4000
                if len(stdout) > max_len:
                    stdout = stdout[:max_len] + f"\n... (输出已截断，共 {len(result.stdout)} 字符)"
                if len(stderr) > max_len:
                    stderr = stderr[:max_len] + f"\n... (错误已截断，共 {len(result.stderr)} 字符)"
                
                return {
                    "success": result.returncode == 0,
                    "stdout": stdout or "(无输出)",
                    "stderr": stderr or "",
                    "return_code": result.returncode,
                    "message": "代码执行成功" if result.returncode == 0 else "代码执行出错"
                }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"代码执行超时（{timeout}秒限制）"
                }
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            
        except Exception as e:
            return {"success": False, "error": f"执行代码失败: {str(e)}"}
    
    # ========== 文件格式转换处理函数 ==========

    def _handle_convert_file(self, source_path: str, target_format: str, output_name: str = "") -> Dict:
        """文件格式转换助手"""
        try:
            from file_converter import FileConverter
        except ImportError:
            try:
                from web.file_converter import FileConverter
            except ImportError:
                return {"success": False, "error": "文件转换模块不可用"}

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        workspace_root = os.path.join(project_root, 'workspace')

        # 解析源文件路径
        if not os.path.isabs(source_path):
            # 在多个常见目录中搜索
            search_dirs = [
                workspace_root,
                os.path.join(workspace_root, 'documents'),
                os.path.join(workspace_root, 'uploads'),
                os.path.join(script_dir, 'uploads'),
                project_root,
            ]
            found = None
            for d in search_dirs:
                candidate = os.path.join(d, source_path)
                if os.path.exists(candidate):
                    found = candidate
                    break
            if not found:
                # 模糊搜索：文件名包含关键词
                import glob
                for d in search_dirs:
                    if os.path.exists(d):
                        for f in glob.glob(os.path.join(d, '**', '*'), recursive=True):
                            if os.path.basename(source_path).lower() in os.path.basename(f).lower():
                                found = f
                                break
                    if found:
                        break
            if not found:
                return {"success": False, "error": f"找不到源文件: {source_path}"}
            source_path = found

        if not os.path.exists(source_path):
            return {"success": False, "error": f"源文件不存在: {source_path}"}

        # 输出目录
        out_dir = os.path.join(workspace_root, 'documents')
        os.makedirs(out_dir, exist_ok=True)

        try:
            result = FileConverter.convert(source_path, target_format, output_dir=out_dir, output_name=output_name)
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"文件转换失败: {str(e)}"}

    # ========== P1: 文件写入工具处理函数 ==========
    
    def _handle_write_file(self, file_path: str, content: str, append: bool = False) -> Dict:
        """写入文件"""
        try:
            # 解析路径 — 仅允许写入到工作区目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            workspace_root = os.path.join(project_root, 'workspace')
            
            if not os.path.isabs(file_path):
                file_path = os.path.join(workspace_root, file_path)
            
            # 安全检查：只允许写入 workspace 目录下
            normalized = os.path.normpath(file_path)
            if not normalized.startswith(os.path.normpath(workspace_root)):
                return {
                    "success": False,
                    "error": "安全限制：只能写入 workspace 目录下的文件"
                }
            
            # 创建父目录
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "file_path": file_path,
                "mode": "追加" if append else "覆盖",
                "chars_written": len(content),
                "message": f"已{'追加到' if append else '写入'}文件: {os.path.basename(file_path)}"
            }
        except Exception as e:
            return {"success": False, "error": f"写入文件失败: {str(e)}"}


# 单例
_registry_instance = None

def get_tool_registry() -> ToolRegistry:
    """获取工具注册中心单例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance
