#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 规划模块 - Phase 4A
提供：计划生成 → 执行 → 验证 → 修订 循环
支持结构化任务执行和错误恢复
"""

import json
import time
from typing import Generator, Dict, List, Any, Optional, Tuple
from datetime import datetime

from google import genai
from google.genai import types


class TaskPlan:
    """任务计划结构"""
    
    def __init__(self, user_request: str, steps: List[Dict[str, Any]]):
        self.user_request = user_request
        self.steps = steps
        self.executed_steps = []
        self.current_step_index = 0
        self.status = "new"  # new, executing, succeeded, failed, revised
        self.error_message = None
        self.revision_count = 0
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dict for serialization"""
        return {
            "user_request": self.user_request,
            "steps": self.steps,
            "executed_steps": self.executed_steps,
            "current_step_index": self.current_step_index,
            "status": self.status,
            "error_message": self.error_message,
            "revision_count": self.revision_count,
            "created_at": self.created_at
        }
    
    def __repr__(self):
        return f"TaskPlan(status={self.status}, steps={len(self.steps)}, executed={len(self.executed_steps)})"


class AgentPlanner:
    """
    Agent 规划器 - 处理多步任务执行
    
    工作流程：
    1. 生成计划 (generate_plan) - 分解用户请求为具体步骤
    2. 执行计划 (execute_plan) - 逐步执行，使用 agent_loop 执行每一步
    3. 验证计划 (verify_plan) - 检查是否达成目标
    4. 修订计划 (revise_plan) - 如果失败，修改策略重试
    """
    
    MAX_REVISIONS = 2  # 最多修订 2 次
    PLAN_TIMEOUT = 300  # 整个计划执行超时（秒）
    
    def __init__(self, client: genai.Client, agent_loop=None, memory_manager=None, kb=None):
        """
        初始化规划器
        
        Args:
            client: Gemini API 客户端
            agent_loop: AgentLoop 实例（用于执行单个步骤）
            memory_manager: MemoryManager 实例（可选，用于提供上下文）
            kb: KnowledgeBase 实例（可选，用于知识查询）
        """
        self.client = client
        self.agent_loop = agent_loop
        self.memory_manager = memory_manager
        self.kb = kb
        self.active_plans = {}  # session → TaskPlan
    
    def generate_plan(self, user_request: str, context: Dict = None) -> TaskPlan:
        """
        生成任务执行计划
        
        Args:
            user_request: 用户请求
            context: 上下文信息 (来自 memory_manager, kb 等)
        
        Returns:
            TaskPlan 实例
        """
        
        # 构建提示词
        prompt = self._build_planning_prompt(user_request, context)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                )
            )
            
            # 解析响应
            response_text = response.text if response.text else ""
            steps = self._parse_plan_response(response_text)
            
            if not steps:
                # 降级：创建单步计划
                steps = [{"step": 1, "action": user_request, "description": "执行用户请求"}]
            
            plan = TaskPlan(user_request, steps)
            plan.status = "generated"
            
            return plan
            
        except Exception as e:
            print(f"[AgentPlanner] 计划生成失败: {e}")
            # 降级：创建单步计划
            plan = TaskPlan(user_request, [{"step": 1, "action": user_request, "description": "执行用户请求"}])
            plan.error_message = str(e)
            return plan
    
    def execute_plan(
        self,
        plan: TaskPlan,
        session: str,
        history: List[Dict],
        model_id: str = "gemini-3-flash-preview"
    ) -> Generator[Dict, None, None]:
        """
        执行任务计划
        
        Yields:
            SSE 事件，结构：
            - plan_started: {"type":"plan_started", "total_steps":N, "plan":{...}}
            - plan_step_start: {"type":"plan_step_start", "step_num":N, "action":"..."}
            - agent_output: {"type":"agent_output", "content":"..."}  (来自 agent_loop)
            - plan_step_done: {"type":"plan_step_done", "step_num":N, "result":"..."}
            - plan_done: {"type":"plan_done", "status":"success/failed", "summary":"..."}
            - plan_error: {"type":"plan_error", "message":"..."}
        """
        
        plan.status = "executing"
        self.active_plans[session] = plan
        start_time = time.time()
        
        # 发送计划开始事件
        yield {
            "type": "plan_started",
            "total_steps": len(plan.steps),
            "plan": plan.to_dict()
        }
        
        try:
            for step_index, step in enumerate(plan.steps):
                plan.current_step_index = step_index
                
                # 检查超时
                if time.time() - start_time > self.PLAN_TIMEOUT:
                    plan.status = "failed"
                    plan.error_message = f"计划执行超时 ({self.PLAN_TIMEOUT}s)"
                    yield {
                        "type": "plan_error",
                        "message": plan.error_message
                    }
                    return
                
                # 发送步骤开始事件
                yield {
                    "type": "plan_step_start",
                    "step_num": step_index + 1,
                    "action": step.get("action", ""),
                    "description": step.get("description", "")
                }
                
                # 执行单个步骤
                if self.agent_loop:
                    # 使用 agent_loop 执行
                    step_result = []
                    for event in self.agent_loop.run(
                        user_input=step.get("action", ""),
                        session=session,
                        history=history,
                        model_id=model_id
                    ):
                        # 转发 agent 输出
                        if event.get("type") in ["token", "agent_thought", "agent_step"]:
                            yield {
                                "type": "agent_output",
                                "event": event
                            }
                        step_result.append(event)
                    
                    # 记录步骤执行结果
                    plan.executed_steps.append({
                        "step_num": step_index + 1,
                        "action": step.get("action", ""),
                        "result": step_result,
                        "completed_at": datetime.now().isoformat()
                    })
                else:
                    # 没有 agent_loop，直接模拟
                    plan.executed_steps.append({
                        "step_num": step_index + 1,
                        "action": step.get("action", ""),
                        "result": {"type": "success", "message": "步骤完成"},
                        "completed_at": datetime.now().isoformat()
                    })
                
                # 发送步骤完成事件
                yield {
                    "type": "plan_step_done",
                    "step_num": step_index + 1,
                    "result": "completed"
                }
            
            # 计划执行完成
            plan.status = "succeeded"
            yield {
                "type": "plan_done",
                "status": "success",
                "summary": f"计划完成，执行了 {len(plan.executed_steps)}/{len(plan.steps)} 步"
            }
            
        except Exception as e:
            plan.status = "failed"
            plan.error_message = str(e)
            yield {
                "type": "plan_error",
                "message": f"执行失败: {str(e)}"
            }
        
        finally:
            self.active_plans.pop(session, None)
    
    def verify_plan(self, plan: TaskPlan) -> Tuple[bool, str]:
        """
        验证计划是否成功
        
        Returns:
            (success: bool, reason: str)
        """
        
        if plan.status == "succeeded" and len(plan.executed_steps) == len(plan.steps):
            return True, "所有步骤已完成"
        
        if plan.status == "failed":
            return False, plan.error_message or "计划执行失败"
        
        return False, f"计划状态异常: {plan.status}"
    
    def revise_plan(self, plan: TaskPlan, error_info: str = None) -> Optional[TaskPlan]:
        """
        根据执行结果修订计划
        
        Args:
            plan: 原始计划
            error_info: 错误信息
        
        Returns:
            修订后的新计划，如果达到最大修订次数则返回 None
        """
        
        plan.revision_count += 1
        
        if plan.revision_count > self.MAX_REVISIONS:
            return None
        
        # 构建修订提示词
        revision_prompt = self._build_revision_prompt(plan, error_info)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=revision_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,  # 稍高温度用于创新
                    max_output_tokens=2048,
                )
            )
            
            response_text = response.text if response.text else ""
            new_steps = self._parse_plan_response(response_text)
            
            if not new_steps:
                return None
            
            # 创建新计划
            revised_plan = TaskPlan(plan.user_request, new_steps)
            revised_plan.revision_count = plan.revision_count
            revised_plan.status = "revised"
            
            return revised_plan
            
        except Exception as e:
            print(f"[AgentPlanner] 计划修订失败: {e}")
            return None
    
    def plan_with_retry(
        self,
        user_request: str,
        session: str,
        history: List[Dict],
        model_id: str = "gemini-3-flash-preview",
        context: Dict = None
    ) -> Generator[Dict, None, None]:
        """
        带重试的计划执行全流程
        
        流程：
        1. 生成计划
        2. 尝试执行计划
        3. 验证结果
        4. 如果失败且未达最大修订次，修订后重试
        """
        
        # Step 1: 生成初始计划
        yield {"type": "planning", "message": "正在生成执行计划..."}
        plan = self.generate_plan(user_request, context)
        yield {
            "type": "plan_generated",
            "plan": plan.to_dict()
        }
        
        attempt = 1
        while attempt <= self.MAX_REVISIONS + 1:
            # Step 2: 执行计划
            yield {"type": "execution_start", "attempt": attempt}
            for event in self.execute_plan(plan, session, history, model_id):
                yield event
            
            # Step 3: 验证计划
            success, reason = self.verify_plan(plan)
            yield {
                "type": "verification",
                "success": success,
                "reason": reason
            }
            
            if success:
                yield {
                    "type": "final_result",
                    "status": "success",
                    "plan": plan.to_dict()
                }
                return
            
            # Step 4: 尝试修订
            if attempt < self.MAX_REVISIONS + 1:
                yield {"type": "plan_revision", "attempt": attempt, "message": "计划修订中..."}
                revised_plan = self.revise_plan(plan, plan.error_message)
                
                if revised_plan:
                    plan = revised_plan
                    yield {
                        "type": "plan_updated",
                        "plan": plan.to_dict()
                    }
                    attempt += 1
                else:
                    break
            else:
                break
        
        # 失败
        yield {
            "type": "final_result",
            "status": "failed",
            "reason": f"在 {plan.revision_count} 次修订后仍未成功",
            "plan": plan.to_dict()
        }
    
    # ==================== 私有方法 ====================
    
    def _build_planning_prompt(self, user_request: str, context: Dict = None) -> str:
        """构建计划生成提示词"""
        
        context_str = ""
        if context:
            if context.get("memories"):
                context_str += f"\n用户记忆:\n"
                for mem in context["memories"]:
                    context_str += f"- {mem}\n"
            
            if context.get("kb_results"):
                context_str += f"\n相关知识:\n"
                for result in context["kb_results"]:
                    context_str += f"- {result}\n"
        
        prompt = f"""你是一个专业的任务规划助手。用户有以下任务请求：

"{user_request}"

{context_str}

请分析这个任务，并制定一个详细的执行计划。计划应该包括：
1. 任务分解 - 将任务分为若干具体步骤
2. 步骤顺序 - 明确每一步的执行顺序
3. 关键检查点 - 标识需要验证的地方

请按照以下 JSON 格式输出计划。不要包含除 JSON 之外的任何文本：

{{
  "analysis": "对任务的分析说明",
  "steps": [
    {{
      "step": 1,
      "action": "具体要执行的操作或提问",
      "description": "步骤说明",
      "success_criteria": "判断此步骤成功的标准"
    }},
    {{
      "step": 2,
      "action": "...",
      "description": "...",
      "success_criteria": "..."
    }}
  ],
  "estimated_time": "估计耗时（分钟）",
  "critical_points": ["关键检查点1", "关键检查点2"]
}}

只输出 JSON 对象，不要包含其他文本。"""
        
        return prompt
    
    def _build_revision_prompt(self, plan: TaskPlan, error_info: str = None) -> str:
        """构建计划修订提示词"""
        
        error_str = ""
        if error_info:
            error_str = f"\n\n前次执行错误：{error_info}"
        
        executed_str = ""
        if plan.executed_steps:
            executed_str = "\n\n已执行的步骤结果：\n"
            for step in plan.executed_steps[:3]:  # 只显示前3步
                executed_str += f"- 步骤 {step['step_num']}: {step['action']}\n"
        
        prompt = f"""原始任务请求："{plan.user_request}"

原始计划的问题是未能成功完成任务。{error_str}{executed_str}

请重新分析这个任务，制定一个新的执行计划来改进。新计划应该：
1. 考虑前次失败的原因
2. 用不同的方法或顺序处理
3. 更加谨慎和周密

请按照以下 JSON 格式输出新计划（不要包含除 JSON 之外的任何文本）：

{{
  "analysis": "新的分析",
  "steps": [
    {{
      "step": 1,
      "action": "...",
      "description": "...",
      "success_criteria": "..."
    }}
  ]
}}

只输出 JSON 对象，不要包含其他文本。"""
        
        return prompt
    
    def _parse_plan_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        解析计划响应
        
        从响应文本中提取 JSON 并获取 steps 数组
        """
        
        try:
            # 尝试找到 JSON 对象
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx == -1 or end_idx <= start_idx:
                return []
            
            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)
            
            steps = data.get("steps", [])
            
            # 验证步骤格式
            valid_steps = []
            for step in steps:
                if isinstance(step, dict) and "action" in step:
                    valid_steps.append(step)
            
            return valid_steps
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[AgentPlanner] 解析计划失败: {e}")
            return []
