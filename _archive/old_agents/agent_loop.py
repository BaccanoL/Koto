#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 执行循环 - ReAct 模式实现 (P2)
支持自主工具调用、用户确认、错误恢复、超时保护、中断传播
"""

import os
import json
import time
import threading
import concurrent.futures
from typing import Generator, Dict, List, Any, Optional
from datetime import datetime

from google import genai
from google.genai import types

from tool_registry import get_tool_registry


class AgentLoop:
    """Agent 执行引擎 - ReAct 循环 (P2)"""
    
    MAX_STEPS = 15  # 最大执行步数，防止无限循环
    STEP_TIMEOUT = 60  # 单步超时（秒）— 包含 API 调用 + 工具执行
    TOOL_TIMEOUT = 30  # 单个工具执行超时（秒）
    MAX_TOOL_RETRIES = 2  # 单个工具最大重试次数
    
    # 需要用户确认的工具（涉及外部操作）
    CONFIRMATION_REQUIRED_TOOLS = {
        "send_wechat_message",
        "add_calendar_event",
        "open_application"
    }
    
    def __init__(self, client: genai.Client, session_manager=None):
        self.client = client
        self.session_manager = session_manager
        self.registry = get_tool_registry()
        self.interrupt_flags = {}  # session → bool
        self._confirm_events = {}  # session → threading.Event
        self._confirm_results = {}  # session → bool
        self._choice_events = {}   # session → threading.Event
        self._choice_results = {}  # session → str
        self._tool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="tool")
    
    def set_interrupt_flag(self, session: str, value: bool = True):
        """设置中断标志（用户点击停止按钮）"""
        self.interrupt_flags[session] = value
    
    def check_interrupt(self, session: str) -> bool:
        """检查是否应该中断"""
        return self.interrupt_flags.get(session, False)
    
    def submit_confirmation(self, session: str, confirmed: bool):
        """用户提交确认结果（由 /api/agent/confirm 调用）"""
        self._confirm_results[session] = confirmed
        event = self._confirm_events.get(session)
        if event:
            event.set()
    
    def _wait_for_confirmation(self, session: str, timeout: float = 60.0) -> Optional[bool]:
        """等待用户确认，返回 True/False/None(超时)"""
        event = threading.Event()
        self._confirm_events[session] = event
        self._confirm_results.pop(session, None)
        
        confirmed = event.wait(timeout=timeout)
        
        # 清理
        self._confirm_events.pop(session, None)
        
        if not confirmed:
            return None  # 超时
        return self._confirm_results.pop(session, False)
    
    def submit_choice(self, session: str, selected: str):
        """用户提交选择结果（由 /api/agent/choice 调用）"""
        self._choice_results[session] = selected
        event = self._choice_events.get(session)
        if event:
            event.set()
    
    def _wait_for_choice(self, session: str, timeout: float = 120.0) -> Optional[str]:
        """等待用户选择，返回选择内容或 None(超时)"""
        event = threading.Event()
        self._choice_events[session] = event
        self._choice_results.pop(session, None)
        
        got_choice = event.wait(timeout=timeout)
        self._choice_events.pop(session, None)
        
        if not got_choice:
            return None
        return self._choice_results.pop(session, None)
    
    def cleanup_session(self, session: str):
        """清理会话相关的所有状态，防止内存泄漏"""
        self.interrupt_flags.pop(session, None)
        self._confirm_events.pop(session, None)
        self._confirm_results.pop(session, None)
        self._choice_events.pop(session, None)
        self._choice_results.pop(session, None)
    
    def run(
        self,
        user_input: str,
        session: str,
        history: List[Dict],
        model_id: str = "gemini-3-flash-preview"
    ) -> Generator[Dict, None, None]:
        """
        执行 Agent 任务（流式生成器）
        
        Yields SSE 事件 (P1 统一格式):
            - agent_step:    {"type":"agent_step", "step_number": N, "total_steps": M, "tool_name":"...", "tool_args":{...}}
            - agent_thought: {"type":"agent_thought", "thought": "..."}
            - progress:      {"type":"progress", "message":"...", "detail":"..."}
            - token:         {"type":"token", "content":"..."}
            - done:          {"type":"done", "steps": N, "elapsed_time":"Xs"}
            - error:         {"type":"error", "message":"..."}
            - user_confirm:  {"type":"user_confirm", "tool_name":"...", "tool_args":{...}, "reason":"..."}
        """
        
        # 重置中断标志
        self.set_interrupt_flag(session, False)
        
        # 构建 System Instruction - Agent 角色定义
        system_instruction = self._build_system_instruction()
        
        # 构建工具声明
        tool_declarations = self.registry.get_declarations()
        tools = [types.Tool(function_declarations=tool_declarations)]
        
        # 构建对话历史 - Gemini API 格式
        contents = self._build_contents(user_input, history)
        
        # 开始 Agent 循环
        step_count = 0
        final_response = None
        working_memory = {}  # 工作记忆（中间结果）
        tool_retry_counts = {}  # 工具重试计数器: tool_name → int
        
        start_time = time.time()
        
        try:
            while step_count < self.MAX_STEPS:
                step_count += 1
                step_start = time.time()
                
                # 检查中断
                if self.check_interrupt(session):
                    yield {
                        "type": "error",
                        "message": "⚠️ 用户已取消任务"
                    }
                    return
                
                try:
                    # 调用 Gemini API（支持 function calling）
                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            tools=tools,
                            system_instruction=system_instruction,
                            temperature=0.3,  # 较低温度保证稳定行为
                            max_output_tokens=2048,
                        )
                    )
                except Exception as e:
                    yield {
                        "type": "error",
                        "message": f"❌ API 调用失败: {str(e)}"
                    }
                    return
                
                # 超时检查（API 调用结束后）
                if time.time() - step_start > self.STEP_TIMEOUT:
                    yield {
                        "type": "error",
                        "message": f"⚠️ 步骤 {step_count} 超时 ({self.STEP_TIMEOUT}s)"
                    }
                    return
                
                # 解析响应
                if not response.candidates or len(response.candidates) == 0:
                    # 检查是否被安全过滤器拦截
                    block_reason = getattr(response, 'prompt_feedback', None)
                    if block_reason:
                        yield {
                            "type": "error",
                            "message": f"❌ 内容被安全过滤器拦截: {block_reason}"
                        }
                    else:
                        yield {
                            "type": "error",
                            "message": "❌ 模型未返回有效响应"
                        }
                    return
                
                candidate = response.candidates[0]
                
                # 检查 finish_reason
                finish_reason = getattr(candidate, 'finish_reason', None)
                if finish_reason and str(finish_reason) not in ('STOP', 'FinishReason.STOP', 'MAX_TOKENS', 'FinishReason.MAX_TOKENS'):
                    # SAFETY, RECITATION 等非正常终止
                    if 'SAFETY' in str(finish_reason):
                        yield {
                            "type": "error",
                            "message": "⚠️ 回复被安全策略拦截，请尝试换一种方式描述任务"
                        }
                        return
                
                # 安全检查 content.parts
                if not hasattr(candidate, 'content') or not candidate.content or not candidate.content.parts:
                    yield {
                        "type": "error",
                        "message": "❌ 模型返回了空响应"
                    }
                    return
                
                # === 检查是否有 function_call ===
                has_function_call = False
                function_responses = []
                
                # ⭐ 先扫描一次，确认是否有 function_call
                # 只有在有工具调用时，才把文本作为"思考过程"输出
                # 否则文本作为最终回复，不需要提前输出（避免重复）
                _has_any_fc = any(
                    hasattr(p, 'function_call') and p.function_call
                    for p in candidate.content.parts
                )
                
                for part in candidate.content.parts:
                    # 如果有文本内容 且 本轮也有工具调用 → 作为推理过程显示
                    if part.text and _has_any_fc:
                        thought = part.text.strip()
                        if thought:
                            yield {
                                "type": "agent_thought",
                                "thought": thought
                            }
                    
                    # 如果有 function_call
                    if part.function_call:
                        has_function_call = True
                        fn_call = part.function_call
                        fn_name = fn_call.name
                        fn_args = dict(fn_call.args) if fn_call.args else {}
                        
                        # === 发送 agent_step 事件（包含工具信息） ===
                        yield {
                            "type": "agent_step",
                            "step_number": step_count,
                            "total_steps": self.MAX_STEPS,
                            "tool_name": fn_name,
                            "tool_args": fn_args
                        }
                        
                        # === 检查是否需要用户确认 ===
                        if fn_name in self.CONFIRMATION_REQUIRED_TOOLS:
                            yield {
                                "type": "user_confirm",
                                "tool_name": fn_name,
                                "tool_args": fn_args,
                                "reason": f"即将执行工具 {fn_name}，请确认是否继续"
                            }
                            
                            # 等待用户确认（最多 60 秒）
                            confirmed = self._wait_for_confirmation(session, timeout=60.0)
                            
                            if confirmed is None:
                                # 超时，默认跳过
                                yield {
                                    "type": "progress",
                                    "message": f"⏰ 确认超时，跳过 {fn_name}",
                                    "detail": ""
                                }
                                function_responses.append(
                                    types.Part.from_function_response(
                                        name=fn_name,
                                        response={"result": {"success": False, "error": "用户确认超时，已跳过"}}
                                    )
                                )
                                continue
                            elif not confirmed:
                                # 用户拒绝
                                yield {
                                    "type": "progress",
                                    "message": f"❌ 用户取消了 {fn_name}",
                                    "detail": ""
                                }
                                function_responses.append(
                                    types.Part.from_function_response(
                                        name=fn_name,
                                        response={"result": {"success": False, "error": "用户取消了此操作"}}
                                    )
                                )
                                continue
                            else:
                                yield {
                                    "type": "progress",
                                    "message": f"✅ 用户已确认 {fn_name}",
                                    "detail": ""
                                }
                        
                        # === 执行工具（带超时 + 错误恢复） ===
                        yield {
                            "type": "progress",
                            "message": f"⏳ 正在执行 {fn_name}...",
                            "detail": ""
                        }
                        
                        tool_result = self._execute_tool_with_recovery(
                            fn_name, fn_args, tool_retry_counts, step_count
                        )
                        
                        # 存入工作记忆（用 step_count 避免 key 冲突）
                        wm_key = f"{fn_name}_{step_count}" if fn_name in working_memory else fn_name
                        working_memory[wm_key] = tool_result
                        
                        # 显示执行结果
                        if tool_result.get("success"):
                            result_msg = tool_result.get("message", "执行成功")
                            yield {
                                "type": "progress",
                                "message": f"✅ {result_msg}",
                                "detail": ""
                            }
                        else:
                            error_msg = tool_result.get("error", "未知错误")
                            yield {
                                "type": "progress",
                                "message": f"⚠️ {fn_name} 失败: {error_msg}",
                                "detail": ""
                            }
                        
                        # 构造 function_response 反馈给模型
                        function_responses.append(
                            types.Part.from_function_response(
                                name=fn_name,
                                response={"result": tool_result}
                            )
                        )
                
                # === 将响应和工具结果追加到对话历史 ===
                if has_function_call:
                    # 追加模型的 function_call 响应
                    contents.append(candidate.content)
                    
                    # 追加工具执行结果
                    contents.append(
                        types.Content(
                            role="user",
                            parts=function_responses
                        )
                    )
                    
                    # 继续循环，让模型根据工具结果决定下一步
                    continue
                
                # === 没有 function_call，说明模型已经完成任务 ===
                else:
                    # 提取最终文本回复 — 合并所有 text parts
                    text_parts = []
                    if candidate.content and candidate.content.parts:
                        for p in candidate.content.parts:
                            if hasattr(p, 'text') and p.text:
                                text_parts.append(p.text)
                    final_text = "\n".join(text_parts)
                    
                    if not final_text:
                        yield {
                            "type": "error",
                            "message": "❌ 模型未返回最终回复"
                        }
                        return
                    
                    # ⭐ 去除重复段落：按换行分块，移除完全相同的段落
                    final_text = self._deduplicate_text(final_text)
                    
                    # 输出最终回复
                    yield {
                        "type": "token",
                        "content": final_text
                    }
                    
                    final_response = final_text
                    break  # 退出循环
            
            # === 循环结束 ===
            elapsed = time.time() - start_time
            
            if step_count >= self.MAX_STEPS:
                yield {
                    "type": "error",
                    "message": f"⚠️ 达到最大步数限制 ({self.MAX_STEPS} 步)"
                }
            
            # 发送 done 事件（字段与前端对齐）
            # 序列化 working_memory，过滤不可序列化的值
            safe_memory = {}
            for k, v in working_memory.items():
                try:
                    json.dumps(v, ensure_ascii=False)
                    safe_memory[k] = v
                except (TypeError, ValueError):
                    safe_memory[k] = str(v)[:200]
            
            yield {
                "type": "done",
                "steps": step_count,
                "elapsed_time": f"{elapsed:.1f}",
                "working_memory": safe_memory
            }
            
            # 清理会话状态
            self.cleanup_session(session)
            
            # 保存对话历史
            if self.session_manager and final_response:
                try:
                    self.session_manager.append_and_save(
                        f"{session}.json",
                        user_input,
                        final_response,
                        task_type="AGENT",
                        steps=step_count
                    )
                except Exception as e:
                    print(f"[AgentLoop] ⚠️ 保存历史失败: {e}")
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[AgentLoop] ❌ Agent 执行失败:\n{error_detail}")
            
            yield {
                "type": "error",
                "message": f"❌ Agent 执行失败: {str(e)}"
            }
    
    def _execute_tool_with_recovery(
        self,
        tool_name: str,
        tool_args: Dict,
        retry_counts: Dict[str, int],
        step_count: int = 0,
    ) -> Dict[str, Any]:
        """
        执行工具，带超时保护 + 自动重试 + 错误恢复
        """
        retry_key = f"{tool_name}_{step_count}"
        attempt = retry_counts.get(retry_key, 0)
        
        try:
            # 在线程池中执行工具，强制 TOOL_TIMEOUT
            future = self._tool_executor.submit(self.registry.execute, tool_name, tool_args)
            try:
                result = future.result(timeout=self.TOOL_TIMEOUT)
            except concurrent.futures.TimeoutError:
                future.cancel()
                return {
                    "success": False,
                    "error": f"工具 {tool_name} 执行超时 ({self.TOOL_TIMEOUT}s)"
                }
            
            if not result.get("success") and attempt < self.MAX_TOOL_RETRIES:
                error_msg = result.get("error", "")
                recovery = AgentErrorRecovery.handle_tool_failure(
                    tool_name, error_msg, attempt, self.MAX_TOOL_RETRIES
                )
                
                if recovery["action"] == "retry":
                    retry_counts[retry_key] = attempt + 1
                    print(f"[AgentLoop] 🔄 重试工具 {tool_name} (第 {attempt + 1} 次)")
                    time.sleep(1)  # 短暂等待后重试
                    return self._execute_tool_with_recovery(tool_name, tool_args, retry_counts, step_count)
                else:
                    # skip / ask_user — 返回带恢复建议的错误
                    result["recovery_hint"] = recovery["message"]
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _deduplicate_text(text: str) -> str:
        """去除回复中的重复段落
        
        将文本按空行分段，移除完全相同或高度相似的重复段落。
        保留第一次出现的段落。
        """
        if not text or len(text) < 100:
            return text
        
        # 按两个以上换行分段
        import re
        paragraphs = re.split(r'\n{2,}', text)
        
        if len(paragraphs) <= 1:
            return text
        
        seen = []
        result = []
        
        for para in paragraphs:
            stripped = para.strip()
            if not stripped:
                continue
            
            # 比较核心内容（移除空白和标点后的前200字符）
            core = re.sub(r'[\s\*\#\-\|]', '', stripped)[:200]
            
            # 检查是否与已见段落高度重复
            is_duplicate = False
            for seen_core in seen:
                # 完全相同 或 一个包含另一个的80%以上
                if core == seen_core:
                    is_duplicate = True
                    break
                shorter = min(len(core), len(seen_core))
                if shorter > 30:
                    # 检查较短的是否被较长的包含
                    if core[:shorter] == seen_core[:shorter]:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                seen.append(core)
                result.append(para)
        
        deduped = '\n\n'.join(result)
        
        if len(deduped) < len(text) * 0.8:
            print(f"[AGENT] ⚠️ 去重: {len(text)} → {len(deduped)} 字符 (移除了 {len(paragraphs) - len(result)} 个重复段落)")
        
        return deduped

    def _build_system_instruction(self) -> str:
        """构建 Agent 的 System Instruction (P1 增强版)"""
        tools_list = "\n".join([
            f"- **{tool['name']}**: {tool['description']}"
            for tool in self.registry.list_tools()
        ])
        
        instruction = f"""你是 Koto，一个智能助手 Agent，能够通过调用工具来完成用户的任务。

## 可用工具
{tools_list}

## 工作流程
1. **理解任务**：分析用户的请求，确定需要完成的目标
2. **规划步骤**：思考需要调用哪些工具、以什么顺序调用
3. **执行工具**：逐步调用工具，每次只调用 1~2 个必要的工具
4. **根据结果决策**：
   - 成功 → 继续下一步或总结结果
   - 失败 → 分析原因，尝试其他方案或告知用户
5. **完成任务**：当所有必要步骤完成后，给出清晰的最终回复

## 重要原则
- **必须调用工具来完成任务**，不要仅凭猜测回答
- 在调用工具前，简要说明你的思考过程（如 "我将先搜索信息，然后..."）
- 如果遇到问题，主动告知用户并提出替代方案
- 不要假设工具执行结果，必须等待工具返回后再继续
- 对于多个选项（如多个车次、搜索结果），**必须使用表格**展示关键信息
- 对于需要额外信息的任务（如日程时间不明确），主动询问用户
- 如果一个工具不可用或失败，尝试用其他工具达成同样目的
- **禁止输出重复段落**，不要把同样的信息输出两遍

## 价格/票务查询格式 🎫
当用户查询**价格、票务**（如高铁票、机票等）时，**必须遵循以下格式**：
- ✅ 提供**具体价格**（例如：二等座 ¥524.5），禁止使用区间（如"500-600元"）
- ✅ 列出**具体车次/班次号**
- ✅ 列出**发车时间和到达时间**，方便用户对比选择
- ✅ **使用Markdown表格**展示，格式如下：

| 车次 | 发车  | 到达  | 座位   | 价格    | 时长  |
|------|-------|-------|--------|---------|-------|
| G12  | 09:00 | 13:24 | 商务座 | ¥1,748  | 4h24m |
| G12  | 09:00 | 13:24 | 一等座 | ¥933    | 4h24m |
| G12  | 09:00 | 13:24 | 二等座 | ¥524.5  | 4h24m |

💡 购票方式：访问 12306.cn 搜索对应车次购买。

## 工具使用技巧
- `web_search`: 搜索实时信息时使用（天气、新闻、价格等）
- `get_12306_ticket_url`: 生成 12306 车票查询链接（含车站与日期）
- `read_clipboard` / `search_clipboard`: 获取用户最近复制的内容
- `read_file` / `read_document`: 读取用户本地文件
- `browser_click` / `browser_input_text`: 与网页交互时使用
- `browser_screenshot`: 需要查看页面内容时使用
- `search_local_files`: 查找用户工作区中的文件
- `get_current_datetime`: 获取当前精确日期/时间/星期几（设置提醒、日程前务必调用）
- `run_python_code`: 执行 Python 代码进行数据计算、格式转换等

## 回复风格
- 使用中文
- 简洁清晰，避免冗长
- 对成功的操作给予确认（如 "✅ 已发送消息给张三"）
- 对失败的操作说明原因并给出建议

当任务完成后，直接输出最终结果文本，不要再调用工具。
"""
        return instruction
    
    def _build_contents(self, user_input: str, history: List[Dict]) -> List:
        """将历史记录转换为 Gemini API 的 contents 格式（带验证）"""
        contents = []
        
        # 添加历史记录（最多取最近 10 轮）
        recent_history = history[-10:] if len(history) > 10 else history
        
        # 总字符预算，防止超出上下文窗口
        MAX_HISTORY_CHARS = 30000
        total_chars = 0
        last_role = None
        
        for item in recent_history:
            role = item.get("role", "")
            content = item.get("content", "")
            
            # 跳过无效条目：空内容、无效角色
            if not content or not content.strip():
                continue
            if role not in ("user", "model"):
                continue
            
            # 避免连续相同角色（Gemini 要求交替）
            if role == last_role:
                # 合并到上一条
                if contents:
                    prev_text = contents[-1].parts[0].text
                    contents[-1] = types.Content(
                        role=role,
                        parts=[types.Part(text=prev_text + "\n" + content)]
                    )
                    total_chars += len(content) + 1
                    continue
            
            # 字符预算检查
            if total_chars + len(content) > MAX_HISTORY_CHARS:
                break
            
            contents.append(
                types.Content(role=role, parts=[types.Part(text=content)])
            )
            total_chars += len(content)
            last_role = role
        
        # 添加当前用户输入
        # 如果最后也是 user 角色，需要合并
        if contents and last_role == "user":
            prev_text = contents[-1].parts[0].text
            contents[-1] = types.Content(
                role="user",
                parts=[types.Part(text=prev_text + "\n" + user_input)]
            )
        else:
            contents.append(
                types.Content(role="user", parts=[types.Part(text=user_input)])
            )
        
        return contents


# === 错误恢复策略 ===

class AgentErrorRecovery:
    """Agent 错误恢复策略"""
    
    @staticmethod
    def handle_tool_failure(
        tool_name: str,
        error: str,
        attempt: int,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        处理工具执行失败
        
        返回：
            - action: "retry" | "skip" | "ask_user" | "abort"
            - message: 给 LLM 的反馈消息
        """
        
        # 常见错误分析
        if "timeout" in error.lower() or "超时" in error:
            if attempt < max_retries:
                return {
                    "action": "retry",
                    "message": f"工具 {tool_name} 执行超时，正在重试（{attempt + 1}/{max_retries}）..."
                }
            else:
                return {
                    "action": "ask_user",
                    "message": f"工具 {tool_name} 多次超时，可能是网络问题。是否继续重试？"
                }
        
        elif "not found" in error.lower() or "未找到" in error:
            return {
                "action": "skip",
                "message": f"工具 {tool_name} 未找到目标，建议尝试其他方案"
            }
        
        elif "permission" in error.lower() or "权限" in error:
            return {
                "action": "ask_user",
                "message": f"工具 {tool_name} 权限不足，需要用户授权或手动操作"
            }
        
        elif "module" in error.lower() or "import" in error.lower():
            return {
                "action": "skip",
                "message": f"工具 {tool_name} 依赖模块不可用: {error[:80]}"
            }
        
        else:
            # 未知错误
            if attempt < max_retries:
                return {
                    "action": "retry",
                    "message": f"工具 {tool_name} 执行失败（{error[:50]}），正在重试..."
                }
            else:
                return {
                    "action": "skip",
                    "message": f"工具 {tool_name} 执行失败（{error}），已跳过"
                }


# 单例
_agent_loop_instance = None

def get_agent_loop(client=None, session_manager=None) -> Optional[AgentLoop]:
    """获取/创建 Agent Loop 单例
    
    - 首次调用必须传入 client 来创建实例
    - 后续调用可不传参数来获取已有实例
    - 如果传入新的 client，会更新实例的 client（支持 API key 变更等）
    """
    global _agent_loop_instance
    if _agent_loop_instance is None:
        if client is None:
            return None  # 尚未创建，且未提供 client
        _agent_loop_instance = AgentLoop(client, session_manager)
    elif client is not None:
        # 更新 client（支持热更换，如 API key 变更）
        _agent_loop_instance.client = client
        if session_manager is not None:
            _agent_loop_instance.session_manager = session_manager
    return _agent_loop_instance
