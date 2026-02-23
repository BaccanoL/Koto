#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 Koto 自适应 Agent 系统 - 自动任务理解、规划、执行

功能:
1. 自动任务分析和拆分
2. 动态工具发现和加载
3. 自动依赖管理（自动安装缺失的包）
4. 流式执行反馈
5. 错误恢复和重试机制
6. 执行上下文记忆
"""

import json
import os
import sys
import subprocess
import importlib
import traceback
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import threading
import queue


# ============================================================================
# 数据结构定义
# ============================================================================

class TaskType(Enum):
    """任务类型分类"""
    CODE_GEN = "code_generation"      # 代码生成
    DATA_PROCESS = "data_processing"   # 数据处理
    FILE_CONVERT = "file_conversion"   # 文件转换
    WEB_SCRAPE = "web_scraping"       # 网页爬取
    IMAGE_PROC = "image_processing"   # 图像处理
    MATH_SOLVE = "math_solving"       # 数学计算
    TEXT_PROC = "text_processing"     # 文本处理
    SYSTEM_OP = "system_operation"    # 系统操作
    UNKNOWN = "unknown"               # 未知


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 执行中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    PARTIAL = "partial"       # 部分成功


@dataclass
class Dependency:
    """依赖项"""
    name: str                  # 包名
    import_name: str          # 导入时的名称
    version: Optional[str] = None
    optional: bool = False    # 是否可选
    description: str = ""     # 描述
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str                  # 工具名称
    description: str           # 工具描述
    dependencies: List[Dependency] = field(default_factory=list)
    file_handler: bool = False  # 是否处理文件
    file_extensions: List[str] = field(default_factory=list)  # 支持的文件扩展名
    can_chain: bool = True     # 是否支持链式调用
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "file_handler": self.file_handler,
            "file_extensions": self.file_extensions,
            "can_chain": self.can_chain
        }


@dataclass
class TaskStep:
    """任务步骤"""
    step_id: int
    description: str           # 步骤描述
    action: str               # 执行的操作
    required_tools: List[str] = field(default_factory=list)
    required_packages: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "action": self.action,
            "required_tools": self.required_tools,
            "required_packages": self.required_packages,
            "inputs": self.inputs,
            "expected_output": self.expected_output,
            "status": self.status.value,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "duration": self.duration
        }


@dataclass
class AdaptiveTask:
    """自适应任务"""
    task_id: str
    user_request: str          # 用户请求
    task_type: TaskType = TaskType.UNKNOWN
    task_description: str = ""
    steps: List[TaskStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    duration: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "user_request": self.user_request,
            "task_type": self.task_type.value,
            "task_description": self.task_description,
            "steps": [s.to_dict() for s in self.steps],
            "context": self.context,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "errors": self.errors
        }


# ============================================================================
# 工具系统 - 动态加载和管理
# ============================================================================

class ToolRegistry:
    """工具注册表 - 管理所有可用的工具"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_defs: Dict[str, ToolDefinition] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        
        # 工具 1: Python 代码执行
        self.register_tool(
            "python_exec",
            self._python_exec,
            ToolDefinition(
                name="python_exec",
                description="执行 Python 代码片段",
                file_handler=False,
                can_chain=True
            )
        )
        
        # 工具 2: 文件操作
        self.register_tool(
            "file_ops",
            self._file_ops,
            ToolDefinition(
                name="file_ops",
                description="通用文件操作（读写、转换等）",
                file_handler=True,
                file_extensions=[".txt", ".json", ".csv", ".md"],
                can_chain=True
            )
        )
        
        # 工具 3: 包管理
        self.register_tool(
            "package_mgmt",
            self._package_mgmt,
            ToolDefinition(
                name="package_mgmt",
                description="自动安装和管理 Python 包",
                can_chain=True
            )
        )
        
        # 工具 4: 数据处理
        self.register_tool(
            "data_process",
            self._data_process,
            ToolDefinition(
                name="data_process",
                description="数据处理和转换（支持 pandas）",
                dependencies=[
                    Dependency("pandas", "pd", description="数据处理库"),
                    Dependency("numpy", "np", description="数值计算库")
                ],
                file_handler=True,
                file_extensions=[".csv", ".xlsx", ".json"],
                can_chain=True
            )
        )
        
        # 工具 5: 图像处理
        self.register_tool(
            "image_proc",
            self._image_proc,
            ToolDefinition(
                name="image_proc",
                description="图像处理（支持 PIL/Pillow）",
                dependencies=[
                    Dependency("pillow", "PIL", description="图像处理库")
                ],
                file_handler=True,
                file_extensions=[".png", ".jpg", ".jpeg", ".gif", ".bmp"],
                can_chain=True
            )
        )
        
        # 工具 6: 网络操作
        self.register_tool(
            "network_ops",
            self._network_ops,
            ToolDefinition(
                name="network_ops",
                description="网络请求和数据爬取",
                dependencies=[
                    Dependency("requests", "requests", description="HTTP 库"),
                    Dependency("beautifulsoup4", "bs4", description="HTML 解析库")
                ],
                can_chain=True
            )
        )
    
    def register_tool(self, tool_id: str, tool_func: Callable, definition: ToolDefinition):
        """注册一个工具"""
        self.tools[tool_id] = tool_func
        self.tool_defs[tool_id] = definition
        print(f"[ToolRegistry] ✅ 已注册工具: {tool_id}")
    
    def get_tool(self, tool_id: str) -> Optional[Callable]:
        """获取工具函数"""
        return self.tools.get(tool_id)
    
    def get_tool_def(self, tool_id: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self.tool_defs.get(tool_id)
    
    def list_tools(self) -> Dict[str, Dict]:
        """列出所有工具"""
        return {tid: tdef.to_dict() for tid, tdef in self.tool_defs.items()}
    
    # ========== 内置工具实现 ==========
    
    @staticmethod
    def _python_exec(code: str, context: Dict = None) -> Dict[str, Any]:
        """执行 Python 代码"""
        try:
            exec_context = context or {}
            exec(code, exec_context)
            return {
                "success": True,
                "output": "代码执行成功",
                "context": exec_context
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    @staticmethod
    def _file_ops(operation: str, filepath: str, content: str = None) -> Dict[str, Any]:
        """文件操作"""
        try:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            
            if operation == "read":
                with open(filepath, 'r', encoding='utf-8') as f:
                    return {"success": True, "content": f.read()}
            
            elif operation == "write":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content or "")
                return {"success": True, "message": f"文件已保存: {filepath}"}
            
            elif operation == "append":
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(content or "")
                return {"success": True, "message": f"内容已追加"}
            
            elif operation == "exists":
                return {"success": True, "exists": os.path.exists(filepath)}
            
            else:
                return {"success": False, "error": f"未知操作: {operation}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _package_mgmt(action: str, package: str = None, packages: List[str] = None) -> Dict[str, Any]:
        """包管理"""
        try:
            pkgs = packages or ([package] if package else [])
            
            if action == "install":
                for pkg in pkgs:
                    print(f"[PackageMgmt] 正在安装 {pkg}...")
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", pkg],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode != 0:
                        return {"success": False, "error": f"安装失败: {result.stderr}"}
                
                return {"success": True, "message": f"已安装: {', '.join(pkgs)}"}
            
            elif action == "check":
                missing = []
                for pkg in pkgs:
                    try:
                        importlib.import_module(pkg)
                    except ImportError:
                        missing.append(pkg)
                
                return {
                    "success": True,
                    "missing": missing,
                    "all_available": len(missing) == 0
                }
            
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _data_process(operation: str, filepath: str = None, **kwargs) -> Dict[str, Any]:
        """数据处理"""
        try:
            import pandas as pd
            
            if operation == "load":
                ext = os.path.splitext(filepath)[1].lower()
                if ext == ".csv":
                    df = pd.read_csv(filepath)
                elif ext in [".xlsx", ".xls"]:
                    df = pd.read_excel(filepath)
                elif ext == ".json":
                    df = pd.read_json(filepath)
                else:
                    return {"success": False, "error": f"不支持的格式: {ext}"}
                
                return {
                    "success": True,
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "preview": df.head().to_dict(orient="records")
                }
            
            elif operation == "save":
                df = kwargs.get("dataframe")
                ext = os.path.splitext(filepath)[1].lower()
                
                if ext == ".csv":
                    df.to_csv(filepath, index=False)
                elif ext in [".xlsx", ".xls"]:
                    df.to_excel(filepath, index=False)
                elif ext == ".json":
                    df.to_json(filepath, orient="records", force_ascii=False)
                
                return {"success": True, "message": f"数据已保存: {filepath}"}
            
            else:
                return {"success": False, "error": f"未知操作: {operation}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _image_proc(operation: str, filepath: str = None, **kwargs) -> Dict[str, Any]:
        """图像处理"""
        try:
            from PIL import Image
            
            if operation == "resize":
                img = Image.open(filepath)
                width = kwargs.get("width", 800)
                height = kwargs.get("height", 600)
                img_resized = img.resize((width, height))
                output_path = kwargs.get("output", filepath.replace(".", "_resized."))
                img_resized.save(output_path)
                return {"success": True, "message": f"图片已缩放: {output_path}"}
            
            elif operation == "convert":
                img = Image.open(filepath)
                format = kwargs.get("format", "PNG").upper()
                output_path = kwargs.get("output", filepath.replace(".", f"_converted.{format.lower()}"))
                img.save(output_path, format=format)
                return {"success": True, "message": f"格式已转换: {output_path}"}
            
            elif operation == "info":
                img = Image.open(filepath)
                return {
                    "success": True,
                    "format": img.format,
                    "size": img.size,
                    "mode": img.mode
                }
            
            else:
                return {"success": False, "error": f"未知操作: {operation}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _network_ops(operation: str, url: str = None, **kwargs) -> Dict[str, Any]:
        """网络操作"""
        try:
            import requests
            
            if operation == "fetch":
                response = requests.get(url, timeout=10)
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "content": response.text[:1000],
                    "headers": dict(response.headers)
                }
            
            elif operation == "parse":
                from bs4 import BeautifulSoup
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                selector = kwargs.get("selector", "a")
                elements = soup.select(selector)
                return {
                    "success": True,
                    "count": len(elements),
                    "elements": [str(e)[:200] for e in elements[:5]]
                }
            
            else:
                return {"success": False, "error": f"未知操作: {operation}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================================
# 任务分析引擎 - 理解和拆分任务
# ============================================================================

class TaskAnalyzer:
    """任务分析器 - 理解用户请求并拆分为步骤"""
    
    TASK_KEYWORDS = {
        TaskType.CODE_GEN: ["代码", "脚本", "写", "生成", "函数", "实现"],
        TaskType.DATA_PROCESS: ["数据", "处理", "分析", "统计", "CSV", "Excel", "JSON"],
        TaskType.FILE_CONVERT: ["转换", "导出", "保存", "格式", "PDF", "图片"],
        TaskType.WEB_SCRAPE: ["爬取", "提取", "URL", "网页", "网站", "下载"],
        TaskType.IMAGE_PROC: ["图片", "图像", "图像处理", "缩放", "转换", "编辑"],
        TaskType.MATH_SOLVE: ["计算", "求解", "方程", "数学", "运算"],
        TaskType.TEXT_PROC: ["文本", "提取", "替换", "分析", "NLP"],
        TaskType.SYSTEM_OP: ["打开", "运行", "执行", "启动", "系统"]
    }
    
    def __init__(self, client=None):
        self.client = client  # Gemini 客户端（可选）
    
    def analyze(self, user_request: str, context: Dict = None) -> AdaptiveTask:
        """分析用户请求并生成任务计划"""
        
        task_id = f"task_{int(time.time() * 1000)}"
        task = AdaptiveTask(
            task_id=task_id,
            user_request=user_request,
            context=context or {}
        )
        
        # 步骤 1: 分类任务类型
        task.task_type = self._classify_task_type(user_request)
        
        # 步骤 2: 如果有 Gemini 客户端，使用 AI 进行深度分析
        if self.client:
            analysis = self._ai_analyze(user_request, task.task_type)
            task.task_description = analysis.get("description", "")
            steps_data = analysis.get("steps", [])
        else:
            task.task_description = user_request
            steps_data = self._heuristic_split(user_request, task.task_type)
        
        # 步骤 3: 生成任务步骤
        task.steps = self._create_steps(steps_data, task.task_type)
        
        print(f"[TaskAnalyzer] ✅ 任务分析完成: {task.task_type.value}")
        print(f"[TaskAnalyzer]    - 任务ID: {task_id}")
        print(f"[TaskAnalyzer]    - 步骤数: {len(task.steps)}")
        
        return task
    
    def _classify_task_type(self, text: str) -> TaskType:
        """对任务进行分类"""
        text_lower = text.lower()
        
        for task_type, keywords in self.TASK_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return task_type
        
        return TaskType.UNKNOWN
    
    def _ai_analyze(self, user_request: str, task_type: TaskType) -> Dict[str, Any]:
        """使用 AI 进行深度分析"""
        try:
            prompt = f"""
            你是一个智能任务规划助手。分析以下用户请求，生成详细的执行步骤。
            
            用户请求: {user_request}
            任务类型: {task_type.value}
            
            请返回 JSON 格式的分析结果，包含:
            {{
                "description": "任务描述（一句话）",
                "steps": [
                    {{"action": "步骤动作", "description": "步骤描述", "required_tools": ["工具列表"], "required_packages": ["包列表"]}},
                    ...
                ],
                "required_packages": ["完整包列表"]
            }}
            
            只返回 JSON，不要其他内容。
            """
            
            # 调用 Gemini API
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                # 如果解析失败，返回启发式分析结果
                return {
                    "description": user_request,
                    "steps": []
                }
        
        except Exception as e:
            print(f"[TaskAnalyzer] AI 分析失败: {e}")
            return {"description": user_request, "steps": []}
    
    def _heuristic_split(self, user_request: str, task_type: TaskType) -> List[Dict]:
        """启发式任务拆分（没有 AI 时的备选方案）"""
        steps = []
        
        if task_type == TaskType.CODE_GEN:
            steps = [
                {"action": "understand", "description": "理解代码需求"},
                {"action": "design", "description": "设计代码结构"},
                {"action": "implement", "description": "实现代码"},
                {"action": "test", "description": "测试代码"}
            ]
        
        elif task_type == TaskType.DATA_PROCESS:
            steps = [
                {"action": "load_data", "description": "加载数据文件"},
                {"action": "analyze", "description": "分析数据"},
                {"action": "process", "description": "处理和转换数据"},
                {"action": "save_result", "description": "保存结果"}
            ]
        
        elif task_type == TaskType.FILE_CONVERT:
            steps = [
                {"action": "identify", "description": "识别文件类型"},
                {"action": "prepare", "description": "准备转换环境"},
                {"action": "convert", "description": "执行格式转换"},
                {"action": "save", "description": "保存转换结果"}
            ]
        
        elif task_type == TaskType.IMAGE_PROC:
            steps = [
                {"action": "load", "description": "加载图像"},
                {"action": "process", "description": "应用图像处理"},
                {"action": "save", "description": "保存处理结果"}
            ]
        
        else:
            steps = [
                {"action": "analyze", "description": "分析需求"},
                {"action": "execute", "description": "执行操作"},
                {"action": "verify", "description": "验证结果"}
            ]
        
        return steps
    
    def _create_steps(self, steps_data: List[Dict], task_type: TaskType) -> List[TaskStep]:
        """创建任务步骤对象"""
        steps = []
        
        for idx, step_data in enumerate(steps_data, 1):
            step = TaskStep(
                step_id=idx,
                description=step_data.get("description", ""),
                action=step_data.get("action", ""),
                required_tools=step_data.get("required_tools", []),
                required_packages=step_data.get("required_packages", [])
            )
            steps.append(step)
        
        return steps


# ============================================================================
# 执行引擎 - 执行任务并处理依赖
# ============================================================================

class ExecutionEngine:
    """执行引擎 - 执行任务步骤并管理依赖"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.installed_packages = set()
        self.context = {}
        self.callbacks = []
    
    def register_callback(self, callback: Callable):
        """注册执行回调"""
        self.callbacks.append(callback)
    
    def _emit_event(self, event_type: str, data: Dict):
        """发送事件"""
        for callback in self.callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                print(f"[ExecutionEngine] 回调错误: {e}")
    
    def execute(self, task: AdaptiveTask) -> AdaptiveTask:
        """执行任务"""
        task.status = ExecutionStatus.RUNNING
        start_time = time.time()
        
        self._emit_event("task_started", {"task_id": task.task_id, "request": task.user_request})
        
        for step in task.steps:
            try:
                # 检查和安装依赖
                self._ensure_dependencies(step)
                
                # 执行步骤
                self._execute_step(step, task)
                
                # 检查结果
                if step.status == ExecutionStatus.FAILED and not step.error:
                    step.error = "Unknown error"
                    task.errors.append(f"步骤 {step.step_id}: {step.error}")
            
            except Exception as e:
                step.status = ExecutionStatus.FAILED
                step.error = str(e)
                task.errors.append(f"步骤 {step.step_id}: {str(e)}")
                print(f"[ExecutionEngine] ❌ 步骤 {step.step_id} 失败: {e}")
                
                # 如果步骤失败，尝试恢复
                if not self._try_recover(step, task):
                    break
        
        # 完成任务
        task.status = ExecutionStatus.SUCCESS if not task.errors else ExecutionStatus.PARTIAL
        task.duration = time.time() - start_time
        task.completed_at = datetime.now().isoformat()
        
        self._emit_event("task_completed", {
            "task_id": task.task_id,
            "status": task.status.value,
            "duration": task.duration,
            "errors": task.errors
        })
        
        return task
    
    def _ensure_dependencies(self, step: TaskStep):
        """确保所有依赖已安装"""
        missing_packages = []
        
        for pkg in step.required_packages:
            if pkg not in self.installed_packages:
                # 检查包是否已安装
                result = self.tool_registry.get_tool("package_mgmt")(
                    action="check",
                    packages=[pkg]
                )
                
                if result.get("missing"):
                    missing_packages.extend(result["missing"])
        
        if missing_packages:
            print(f"[ExecutionEngine] 正在安装缺失包: {missing_packages}")
            self._emit_event("installing_packages", {"packages": missing_packages})
            
            result = self.tool_registry.get_tool("package_mgmt")(
                action="install",
                packages=missing_packages
            )
            
            if result.get("success"):
                self.installed_packages.update(missing_packages)
                print(f"[ExecutionEngine] ✅ 包安装成功")
            else:
                raise Exception(f"包安装失败: {result.get('error')}")
    
    def _execute_step(self, step: TaskStep, task: AdaptiveTask):
        """执行单个步骤"""
        step.status = ExecutionStatus.RUNNING
        start_time = time.time()
        
        self._emit_event("step_started", {
            "task_id": task.task_id,
            "step_id": step.step_id,
            "description": step.description
        })
        
        try:
            # 根据步骤动作选择执行方式
            if step.action == "python_exec" or any(tool in ["python_exec"] for tool in step.required_tools):
                result = self.tool_registry.get_tool("python_exec")(
                    code=step.inputs.get("code", ""),
                    context=self.context
                )
            
            elif step.action == "load_file":
                result = self.tool_registry.get_tool("file_ops")(
                    operation="read",
                    filepath=step.inputs.get("filepath", "")
                )
            
            else:
                # 通用执行：调用相对应的工具
                tool_name = step.required_tools[0] if step.required_tools else "python_exec"
                tool_func = self.tool_registry.get_tool(tool_name)
                
                if tool_func:
                    result = tool_func(**step.inputs)
                else:
                    result = {
                        "success": False,
                        "error": f"未找到工具: {tool_name}"
                    }
            
            # 处理结果
            if result.get("success"):
                step.status = ExecutionStatus.SUCCESS
                step.result = result
                self.context[f"step_{step.step_id}"] = result
                print(f"[ExecutionEngine] ✅ 步骤 {step.step_id} 完成: {step.description}")
            else:
                step.status = ExecutionStatus.FAILED
                step.error = result.get("error", "Unknown error")
                print(f"[ExecutionEngine] ❌ 步骤 {step.step_id} 失败: {step.error}")
        
        except Exception as e:
            step.status = ExecutionStatus.FAILED
            step.error = str(e)
            print(f"[ExecutionEngine] ❌ 执行异常: {e}")
        
        step.duration = time.time() - start_time
        
        self._emit_event("step_completed", {
            "task_id": task.task_id,
            "step_id": step.step_id,
            "status": step.status.value,
            "duration": step.duration,
            "result": str(step.result)[:200] if step.result else None
        })
    
    def _try_recover(self, step: TaskStep, task: AdaptiveTask) -> bool:
        """尝试从失败中恢复"""
        if step.step_id == 1:
            # 第一步失败，停止执行
            return False
        
        # 尝试继续执行后续步骤
        print(f"[ExecutionEngine] 尝试继续执行后续步骤...")
        return True


# ============================================================================
# 主 Agent 类
# ============================================================================

class AdaptiveAgent:
    """自适应 Agent - 整合所有组件"""
    
    def __init__(self, gemini_client=None):
        self.client = gemini_client
        self.tool_registry = ToolRegistry()
        self.task_analyzer = TaskAnalyzer(client=gemini_client)
        self.execution_engine = ExecutionEngine(self.tool_registry)
        self.task_history = []
    
    def process(self, user_request: str, context: Dict = None, 
                callback: Callable = None) -> AdaptiveTask:
        """处理用户请求（主入口）"""
        
        print("\n" + "=" * 70)
        print(f"🤖 Koto Agent 处理请求: {user_request[:50]}...")
        print("=" * 70)
        
        # 步骤 1: 分析任务
        print("\n[Phase 1] 📋 任务分析...")
        task = self.task_analyzer.analyze(user_request, context)
        
        # 步骤 2: 注册回调
        if callback:
            self.execution_engine.register_callback(callback)
        
        # 步骤 3: 执行任务
        print("\n[Phase 2] 🚀 执行任务...")
        task = self.execution_engine.execute(task)
        
        # 步骤 4: 保存到历史
        self.task_history.append(task)
        
        # 步骤 5: 总结结果
        self._summarize_result(task)
        
        return task
    
    def _summarize_result(self, task: AdaptiveTask):
        """总结结果"""
        print("\n" + "=" * 70)
        print(f"✅ 任务完成: {task.task_id}")
        print(f"   状态: {task.status.value}")
        print(f"   耗时: {task.duration:.2f}s")
        print(f"   步骤: {len(task.steps)} 个")
        
        if task.errors:
            print(f"\n❌ 错误信息:")
            for error in task.errors:
                print(f"   - {error}")
        else:
            print(f"\n✅ 所有步骤执行成功！")
        
        print("=" * 70 + "\n")
    
    def get_tools(self) -> Dict[str, Dict]:
        """获取所有可用工具"""
        return self.tool_registry.list_tools()
    
    def get_task_history(self) -> List[Dict]:
        """获取任务历史"""
        return [task.to_dict() for task in self.task_history]


# ============================================================================
# 示例和测试
# ============================================================================

def test_adaptive_agent():
    """测试自适应 Agent"""
    
    # 创建 Agent
    agent = AdaptiveAgent()
    
    # 定义回调处理事件
    def event_handler(event_type: str, data: Dict):
        if event_type == "task_started":
            print(f"\n🚀 任务开始: {data['request'][:50]}")
        elif event_type == "step_started":
            print(f"  → 步骤 {data['step_id']}: {data['description']}")
        elif event_type == "installing_packages":
            print(f"  📦 安装包: {', '.join(data['packages'])}")
        elif event_type == "step_completed":
            print(f"  ✓ 步骤 {data['step_id']}: {data['status']} ({data['duration']:.2f}s)")
        elif event_type == "task_completed":
            print(f"\n✅ 任务完成: {data['status']}")
    
    # 测试请求 1: 数据处理
    task1 = agent.process(
        "帮我读取 data.csv 并计算每列的平均值，然后保存到 result.json",
        callback=event_handler
    )
    
    # 测试请求 2: 代码生成
    task2 = agent.process(
        "写一个 Python 函数，计算斐波那契数列的前 n 项",
        callback=event_handler
    )
    
    # 显示工具列表
    print("\n📚 可用工具:")
    tools = agent.get_tools()
    for tool_id, tool_def in tools.items():
        print(f"  - {tool_id}: {tool_def.get('description', 'N/A')}")
    
    # 显示任务历史
    print("\n📋 任务历史:")
    history = agent.get_task_history()
    for task in history:
        print(f"  - {task['task_id']}: {task['task_type']} ({task['status']})")


if __name__ == "__main__":
    test_adaptive_agent()
