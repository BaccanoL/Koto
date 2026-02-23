#!/usr/bin/env python3
"""修复 SmartDispatcher 的 override 逻辑"""

with open('web/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find exact boundaries
start_marker = '            # 明确的系统操作优先走 SYSTEM\n'
end_marker = '\n        # === 深度文档请求直通 FILE_GEN'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print(f'ERROR: start={start_idx}, end={end_idx}')
    exit(1)

old_section = content[start_idx:end_idx]
print(f'Found section: {len(old_section)} chars')

new_section = """            # ═══ 仅对极少数高确定性场景进行 override ═══
            # 原则：尊重模型判断，只在模型明显错误时才覆盖
            
            # Override 1: 明确的系统命令（短句 + 动作词 + 具体应用名）
            if LocalExecutor.is_system_command(user_input) and local_task != "SYSTEM":
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"SYSTEM": 0.95},
                    reasons={"SYSTEM": ["local_override:system"]}
                )
                return "SYSTEM", "🖥️ Local-Override", context_info

            # Override 2: 明确的工具调用（微信发消息/浏览器自动化）
            import re
            agent_overrides = [
                r"发微信", r"回微信", r"微信发", r"微信回",
                r"给.{1,6}发消息", r"给.{1,6}发微信",
                r"浏览器打开", r"点击.{1,6}按钮",
            ]
            if any(re.search(p, user_lower) for p in agent_overrides):
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"AGENT": 0.95},
                    reasons={"AGENT": ["local_override:agent"]}
                )
                return "AGENT", "🤖 Local-Override", context_info

            # Override 3: 车票/12306 查询走 AGENT 工具
            ticket_keywords = ["12306", "火车票", "高铁票", "动车票"]
            if any(k in user_lower for k in ticket_keywords):
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"AGENT": 0.95},
                    reasons={"AGENT": ["local_override:ticket"]}
                )
                return "AGENT", "🤖 Local-Override", context_info

            # 不再 override search_verbs（"查/找/搜"是日常用词，模型已能区分）

            # 使用本地模型结果作为最终路由
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={local_task: 0.9},
                reasons={local_task: ["local_model"]}
            )
            return local_task, f"{local_confidence}", context_info
"""

content = content[:start_idx] + new_section + content[end_idx:]

with open('web/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Override section replaced successfully')
