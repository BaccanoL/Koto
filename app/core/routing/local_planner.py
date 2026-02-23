import json
import requests
from app.core.routing.local_model_router import LocalModelRouter

class LocalPlanner:
    """Local planner/controller using Ollama for multi-step task planning."""

    PLAN_PROMPT = '''你是一个多步任务规划器，只输出 JSON。

允许的任务类型（只从这里选）：
- WEB_SEARCH: 联网搜索获取最新信息
- RESEARCH: 深度分析/整理材料
- FILE_GEN: 生成文档/PPT/Word/PDF/Excel
- PAINTER: 生成配图

规则:
- 如果不需要多步，请输出 use_planner=false，steps=[]
- 如果需要多步，请输出 use_planner=true
- 每个步骤包含: task, input, description
- 只输出 JSON，不要输出其他文本

示例1:
输入: 收集最新信息并做一个PPT
输出: {{"use_planner":true,"steps":[
  {{"task":"WEB_SEARCH","input":"收集最新信息","description":"搜索最新资料"}},
  {{"task":"FILE_GEN","input":"基于资料生成PPT","description":"生成PPT"}}
]}}

示例2:
输入: 画一张猫图
输出: {{"use_planner":false,"steps":[]}}

用户输入: {input}

只输出 JSON:
{{"use_planner":true|false,"steps":[{{"task":"WEB_SEARCH|RESEARCH|FILE_GEN|PAINTER","input":"...","description":"..."}}]}}
'''

    CHECK_PROMPT = '''你是任务进度检查器，只输出 JSON。

输入包含:
- 用户需求
- 计划步骤及执行结果

请判断是否完成，并给出简短结论。

只输出 JSON:
{{"status":"complete|partial|failed","summary":"...","next_actions":["..."]}}
'''

    @classmethod
    def can_plan(cls, user_input: str) -> bool:
        """是否值得尝试多步规划"""
        text = user_input.lower()
        multi_markers = ["并", "然后", "再", "同时", "同时", "先", "之后", "并且"]
        search_markers = ["收集", "查询", "搜索", "查", "搜", "最新", "资料", "信息"]
        output_markers = ["ppt", "报告", "文档", "word", "pdf", "表格", "excel", "总结"]
        if any(m in text for m in multi_markers) and (any(s in text for s in search_markers) or any(o in text for o in output_markers)):
            return True
        if any(s in text for s in search_markers) and any(o in text for o in output_markers):
            return True
        return False

    @classmethod
    def plan(cls, user_input: str, timeout: float = 4.0) -> dict:
        """返回规划结果: {use_planner: bool, steps: list} 或 None"""
        try:
            if not LocalModelRouter.is_ollama_available():
                return None

            if not LocalModelRouter.init_model():
                return None
            
            # Access internal property via class (assuming _model_name is accessible or add getter)
            # Python 'protected' variables are accessible.
            model_name = getattr(LocalModelRouter, '_model_name', None) 
            if not model_name:
                return None

            prompt = cls.PLAN_PROMPT.format(input=user_input[:500])
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input[:500]},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 200,
                    }
                },
                timeout=timeout
            )
            if resp.status_code != 200:
                return None

            data_json = resp.json()
            raw = (data_json.get("message", {}) or {}).get("content", "")
            if not raw:
                raw = data_json.get("response", "")
            raw = (raw or "").strip()

            try:
                plan = json.loads(raw)
            except Exception:
                return None

            if not isinstance(plan, dict):
                return None

            use_planner = bool(plan.get("use_planner", False))
            steps = plan.get("steps", []) if isinstance(plan.get("steps", []), list) else []

            # 过滤非法步骤
            allowed = {"WEB_SEARCH", "RESEARCH", "FILE_GEN", "PAINTER"}
            cleaned = []
            for s in steps:
                task = str(s.get("task", "")).strip().upper()
                if task not in allowed:
                    continue
                cleaned.append({
                    "task_type": task,
                    "description": s.get("description", ""),
                    "input": s.get("input", ""),
                })

            return {"use_planner": use_planner and len(cleaned) > 0, "steps": cleaned}

        except Exception:
            return None

    @classmethod
    def self_check(cls, user_input: str, steps: list, results: list, timeout: float = 4.0) -> dict:
        """对执行结果进行自检"""
        try:
            if not LocalModelRouter.is_ollama_available():
                return {"status": "complete", "summary": "(本地模型不可用，跳过自检)", "next_actions": []}

            if not LocalModelRouter.init_model():
                return {"status": "complete", "summary": "(本地模型不可用，跳过自检)", "next_actions": []}
            
            model_name = getattr(LocalModelRouter, '_model_name', None)

            summary_lines = []
            for i, (s, r) in enumerate(zip(steps, results), start=1):
                ok = r.get("success") if isinstance(r, dict) else False
                out = (r.get("output") or r.get("error") or "")[:120] if isinstance(r, dict) else ""
                summary_lines.append(f"步骤{i}: {s.get('task_type')} - {'OK' if ok else 'FAIL'} - {out}")

            prompt = cls.CHECK_PROMPT + "\n用户需求:\n" + user_input + "\n\n执行摘要:\n" + "\n".join(summary_lines)

            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": cls.CHECK_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 120,
                    }
                },
                timeout=timeout
            )
            if resp.status_code != 200:
                return {"status": "partial", "summary": "(自检失败)", "next_actions": []}

            data_json = resp.json()
            raw = (data_json.get("message", {}) or {}).get("content", "")
            if not raw:
                raw = data_json.get("response", "")
            raw = (raw or "").strip()

            try:
                check = json.loads(raw)
                if isinstance(check, dict):
                    return {
                        "status": check.get("status", "partial"),
                        "summary": check.get("summary", ""),
                        "next_actions": check.get("next_actions", []) if isinstance(check.get("next_actions", []), list) else []
                    }
            except Exception:
                pass

            return {"status": "partial", "summary": raw[:200], "next_actions": []}

        except Exception:
            return {"status": "partial", "summary": "(自检异常)", "next_actions": []}
