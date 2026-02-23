#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Koto 自适应 Agent API - Flask 集成
为主应用提供 REST 和 WebSocket 接口
"""

from flask import Blueprint, request, jsonify, Response
from flask_cors import CORS
import json
import threading
import queue
from typing import Dict, Any
import traceback

try:
    from adaptive_agent import AdaptiveAgent, ExecutionStatus
except ImportError:
    from web.adaptive_agent import AdaptiveAgent, ExecutionStatus

# 创建蓝图（Phase2: 避免与统一 Agent API 冲突）
agent_api = Blueprint('agent_api', __name__, url_prefix='/api/adaptive-agent')

# 全局 Agent 实例
_adaptive_agent = None
_event_queues = {}  # session_id -> event_queue


def get_adaptive_agent(gemini_client=None) -> AdaptiveAgent:
    """获取或创建 Adaptive Agent 实例"""
    global _adaptive_agent
    
    if _adaptive_agent is None:
        print("[AdaptiveAgent API] 初始化 Adaptive Agent...")
        _adaptive_agent = AdaptiveAgent(gemini_client=gemini_client)
    
    return _adaptive_agent


# ============================================================================
# REST API 端点
# ============================================================================

@agent_api.route('/tools', methods=['GET'])
def get_tools():
    """获取所有可用工具"""
    try:
        agent = get_adaptive_agent()
        tools = agent.get_tools()
        
        return jsonify({
            "success": True,
            "tools": tools,
            "count": len(tools)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@agent_api.route('/process', methods=['POST'])
def process_request():
    """处理用户请求（同步版本）"""
    try:
        data = request.json
        user_request = data.get('request', '')
        context = data.get('context', {})
        
        if not user_request:
            return jsonify({
                "success": False,
                "error": "缺少请求内容"
            }), 400
        
        agent = get_adaptive_agent()
        
        # 处理请求
        task = agent.process(user_request, context=context)
        
        return jsonify({
            "success": task.status.value == "success",
            "task": task.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@agent_api.route('/process-stream', methods=['POST'])
def process_stream():
    """处理用户请求（流式版本 - SSE）"""
    try:
        data = request.json
        user_request = data.get('request', '')
        context = data.get('context', {})
        session_id = data.get('session_id', 'default')
        
        if not user_request:
            return jsonify({
                "success": False,
                "error": "缺少请求内容"
            }), 400
        
        agent = get_adaptive_agent()
        
        # 创建事件队列
        event_queue = queue.Queue()
        _event_queues[session_id] = event_queue
        
        # 定义事件回调
        def event_callback(event_type: str, data: Dict[str, Any]):
            event_queue.put({
                "type": event_type,
                "data": data
            })
        
        # 在后台线程执行
        def run_task():
            try:
                task = agent.process(user_request, context=context, callback=event_callback)
                event_queue.put({
                    "type": "task_final",
                    "data": task.to_dict()
                })
            except Exception as e:
                event_queue.put({
                    "type": "error",
                    "data": {"error": str(e)}
                })
            finally:
                event_queue.put(None)  # 标记结束
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        
        # SSE 流式响应
        def generate():
            while True:
                try:
                    event = event_queue.get(timeout=30)
                    
                    if event is None:
                        # 任务完成
                        break
                    
                    # 发送 SSE 格式
                    yield f"data: {json.dumps(event)}\n\n"
                
                except queue.Empty:
                    # 超时，继续等待
                    continue
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
    finally:
        # 清理队列
        if session_id in _event_queues:
            del _event_queues[session_id]


@agent_api.route('/history', methods=['GET'])
def get_history():
    """获取任务历史"""
    try:
        agent = get_adaptive_agent()
        history = agent.get_task_history()
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history)
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@agent_api.route('/status', methods=['GET'])
def get_status():
    """获取 Agent 状态"""
    try:
        agent = get_adaptive_agent()
        
        return jsonify({
            "success": True,
            "agent": {
                "initialized": agent is not None,
                "tools_available": len(agent.get_tools()),
                "tasks_completed": len(agent.task_history)
            }
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# 高级功能
# ============================================================================

@agent_api.route('/analyze', methods=['POST'])
def analyze_only():
    """仅分析任务，不执行"""
    try:
        data = request.json
        user_request = data.get('request', '')
        
        if not user_request:
            return jsonify({
                "success": False,
                "error": "缺少请求内容"
            }), 400
        
        agent = get_adaptive_agent()
        
        # 仅分析
        task = agent.task_analyzer.analyze(user_request)
        
        return jsonify({
            "success": True,
            "task_type": task.task_type.value,
            "description": task.task_description,
            "steps": [s.to_dict() for s in task.steps],
            "required_packages": list(set(
                pkg for step in task.steps for pkg in step.required_packages
            ))
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@agent_api.route('/register-tool', methods=['POST'])
def register_tool():
    """注册自定义工具"""
    try:
        data = request.json
        # TODO: 实现自定义工具注册
        
        return jsonify({
            "success": True,
            "message": "自定义工具注册功能开发中"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# 初始化函数
# ============================================================================

def init_adaptive_agent_api(app, gemini_client=None):
    """初始化自适应 Agent API"""
    
    # 注册蓝图
    app.register_blueprint(agent_api)
    
    # 初始化全局 Agent
    global _adaptive_agent
    _adaptive_agent = AdaptiveAgent(gemini_client=gemini_client)
    
    print("[AdaptiveAgent API] ✅ 自适应 Agent API 已初始化")
    
    # 列出所有可用工具
    tools = _adaptive_agent.get_tools()
    print(f"[AdaptiveAgent API] 📚 可用工具: {len(tools)}")
    for tool_id in tools.keys():
        print(f"                      - {tool_id}")
