from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import os
import logging
import time
from app.core.agent.factory import create_agent
from app.core.agent.types import AgentStepType

logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__)

# ------------------------------------------------------------------
# Session history helpers — reuse chats/ directory for persistence
# ------------------------------------------------------------------
_CHATS_DIR = None

def _get_chats_dir() -> str:
    """Lazily resolve chats/ directory (same as web/app.py uses)."""
    global _CHATS_DIR
    if _CHATS_DIR is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _CHATS_DIR = os.path.join(project_root, "chats")
        os.makedirs(_CHATS_DIR, exist_ok=True)
    return _CHATS_DIR


def _load_history(session_id: str, max_turns: int = 20):
    """Load recent history from chats/<session_id>.json, compatible with
    SessionManager format {role, parts}. Converts to agent-compatible
    {role, content} dicts."""
    if not session_id:
        return []
    fname = session_id if session_id.endswith(".json") else f"{session_id}.json"
    path = os.path.join(_get_chats_dir(), fname)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = json.load(f)
        # Convert {role, parts} → {role, content}
        history = []
        for msg in raw[-max_turns:]:
            role = msg.get("role", "user")
            parts = msg.get("parts", [])
            content = parts[0] if parts else msg.get("content", "")
            history.append({"role": role, "content": content})
        return history
    except Exception as exc:
        logger.warning(f"Failed to load history for {session_id}: {exc}")
        return []


def _save_history(session_id: str, user_msg: str, model_msg: str):
    """Append a turn (user + model) to chats/<session_id>.json in
    SessionManager-compatible format."""
    if not session_id:
        return
    fname = session_id if session_id.endswith(".json") else f"{session_id}.json"
    path = os.path.join(_get_chats_dir(), fname)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                history = json.load(f)
        else:
            history = []
        history.append({"role": "user", "parts": [user_msg]})
        history.append({"role": "model", "parts": [model_msg]})
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.warning(f"Failed to save history for {session_id}: {exc}")


# ------------------------------------------------------------------
# Phase3: Session state snapshots for cross-turn system context reuse
# ------------------------------------------------------------------
_SYSTEM_TOOL_TO_STATE_KEY = {
    "query_cpu_status": "cpu",
    "query_memory_status": "memory",
    "query_disk_usage": "disk",
    "query_network_status": "network",
    "query_python_env": "python_env",
    "list_running_apps": "processes",
    "get_system_warnings": "warnings",
}


def _get_state_path(session_id: str) -> str:
    """Get path for session state snapshot file."""
    safe_id = (session_id or "").replace(".json", "").strip()
    return os.path.join(_get_chats_dir(), f"{safe_id}.state.json")


def _load_session_state(session_id: str) -> dict:
    """Load session state snapshot containing system info summary."""
    if not session_id:
        return {"system_snapshot": {}, "updated_at": None}
    path = _get_state_path(session_id)
    if not os.path.exists(path):
        return {"system_snapshot": {}, "updated_at": None}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"system_snapshot": {}, "updated_at": None}
        data.setdefault("system_snapshot", {})
        data.setdefault("updated_at", None)
        return data
    except Exception as exc:
        logger.warning(f"Failed to load session state for {session_id}: {exc}")
        return {"system_snapshot": {}, "updated_at": None}


def _save_session_state(session_id: str, state: dict):
    """Save session state snapshot."""
    if not session_id:
        return
    path = _get_state_path(session_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.warning(f"Failed to save session state for {session_id}: {exc}")


def _parse_observation_json(text: str):
    """Try to parse JSON from observation text."""
    if not isinstance(text, str):
        return None
    content = text.strip()
    if not content or content[0] not in ("{", "["):
        return None
    try:
        return json.loads(content)
    except Exception:
        return None


def _merge_system_snapshot_from_steps(session_state: dict, steps_payload: list):
    """Extract system tool results from steps and merge into state snapshot."""
    if not isinstance(session_state, dict):
        session_state = {"system_snapshot": {}, "updated_at": None}
    snapshot = session_state.get("system_snapshot") or {}

    last_tool_name = None
    for step in steps_payload or []:
        step_type = str(step.get("step_type", "")).lower()
        if step_type == "action":
            action = step.get("action") or {}
            last_tool_name = action.get("tool_name")
            continue

        if step_type != "observation" or not last_tool_name:
            continue

        state_key = _SYSTEM_TOOL_TO_STATE_KEY.get(last_tool_name)
        if not state_key:
            continue

        obs_text = step.get("observation") or step.get("content") or ""
        obs_data = _parse_observation_json(obs_text)
        snapshot[state_key] = {
            "tool": last_tool_name,
            "captured_at": int(time.time()),
            "data": obs_data if obs_data is not None else {"raw": str(obs_text)[:1200]},
        }

    session_state["system_snapshot"] = snapshot
    session_state["updated_at"] = int(time.time())
    return session_state


def _build_snapshot_context_text(session_state: dict) -> str:
    """Build human-readable context string from system snapshot."""
    snapshot = (session_state or {}).get("system_snapshot") or {}
    if not snapshot:
        return ""

    lines = [
        "Session context: latest local system snapshot (may be stale, use tools if needed):"
    ]
    for key in ["cpu", "memory", "disk", "network", "python_env", "processes", "warnings"]:
        item = snapshot.get(key)
        if not item:
            continue
        data = item.get("data")
        if isinstance(data, dict):
            compact = json.dumps(data, ensure_ascii=False)[:280]
        elif isinstance(data, list):
            compact = json.dumps(data, ensure_ascii=False)[:280]
        else:
            compact = str(data)[:280]
        lines.append(f"- {key}: {compact}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Agent instance management
# ------------------------------------------------------------------
_agent_instance = None

def get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_agent()
    return _agent_instance


def _run_agent_collect(agent, message, history=None):
    """Run agent once and collect steps/final answer for sync APIs."""
    steps_payload = []
    final_answer = ""

    for step in agent.run(input_text=message, history=history or []):
        step_data = step.to_dict()
        steps_payload.append(step_data)
        if step.step_type == AgentStepType.ANSWER:
            final_answer = step.content or ""

    if not final_answer and steps_payload:
        final_answer = steps_payload[-1].get("content", "")

    return {
        "id": f"task_{int(time.time() * 1000)}",
        "status": "success",
        "result": final_answer,
        "steps": steps_payload,
    }

@agent_bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    session_id = data.get('session_id') or data.get('session', '')
    history = data.get('history') or _load_history(session_id)
    model_id = data.get('model', 'gemini-3-flash-preview')
    
    # Phase3: load system state snapshot and inject into history
    session_state = _load_session_state(session_id)
    snapshot_ctx = _build_snapshot_context_text(session_state)
    if snapshot_ctx:
        history = (history or []) + [{"role": "model", "content": snapshot_ctx}]
    
    if not message:
        return jsonify({"error": "Message is required"}), 400

    agent = get_agent()
    if agent.model_id != model_id:
        agent.model_id = model_id

    def generate():
        collected_steps = []
        final_answer = ""
        try:
            for step in agent.run(input_text=message, history=history):
                step_data = step.to_dict()
                collected_steps.append(step_data)
                if step.step_type == AgentStepType.ANSWER:
                    final_answer = step.content or ""
                yield f"data: {json.dumps({'type': 'agent_step', 'data': step_data}, ensure_ascii=False)}\n\n"

            if not final_answer and collected_steps:
                final_answer = collected_steps[-1].get("content", "")

            task_payload = {
                "id": f"task_{int(time.time() * 1000)}",
                "status": "success",
                "result": final_answer,
                "steps": collected_steps,
            }
            yield f"data: {json.dumps({'type': 'task_final', 'data': task_payload}, ensure_ascii=False)}\n\n"

            # Persist turn to disk + phase3 state snapshot
            _save_history(session_id, message, final_answer or '[Agent task completed]')
            merged_state = _merge_system_snapshot_from_steps(session_state, collected_steps)
            _save_session_state(session_id, merged_state)
        except Exception as e:
            logger.exception("/chat stream failed")
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}}, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@agent_bp.route('/tools', methods=['GET'])
def list_tools():
    """List available tools for the agent."""
    agent = get_agent()
    definitions = agent.registry.get_definitions()
    return jsonify(definitions)


@agent_bp.route('/process', methods=['POST'])
def process_compat():
    """Phase2 compatibility endpoint for legacy AdaptiveAgent clients."""
    data = request.json or {}
    user_request = data.get('request', '')
    session_id = data.get('session_id') or data.get('session', '')
    context = data.get('context', {})
    history = context.get('history', []) if isinstance(context, dict) else []

    # Phase3: load and inject system state snapshot
    session_state = _load_session_state(session_id)
    snapshot_ctx = _build_snapshot_context_text(session_state)
    if snapshot_ctx:
        history = (history or []) + [{"role": "model", "content": snapshot_ctx}]

    if not user_request:
        return jsonify({"success": False, "error": "缺少请求内容"}), 400

    try:
        agent = get_agent()
        task = _run_agent_collect(agent, user_request, history=history)
        merged_state = _merge_system_snapshot_from_steps(session_state, task.get("steps", []))
        _save_session_state(session_id, merged_state)
        return jsonify({"success": True, "task": task})
    except Exception as exc:
        logger.exception("/process failed")
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route('/process-stream', methods=['POST'])
def process_stream_compat():
    """Phase2 compatibility SSE endpoint for legacy AdaptiveAgent clients."""
    data = request.json or {}
    user_request = data.get('request', '')
    session_id = data.get('session_id') or data.get('session', '')
    context = data.get('context', {})
    # Prefer explicit history from request, fall back to disk
    history = (context.get('history', []) if isinstance(context, dict) else []) or _load_history(session_id)

    # Phase3: load and inject system state snapshot
    session_state = _load_session_state(session_id)
    snapshot_ctx = _build_snapshot_context_text(session_state)
    if snapshot_ctx:
        history = (history or []) + [{"role": "model", "content": snapshot_ctx}]

    if not user_request:
        return jsonify({"success": False, "error": "缺少请求内容"}), 400

    agent = get_agent()

    def generate():
        collected_steps = []
        final_answer = ""
        try:
            for step in agent.run(input_text=user_request, history=history):
                step_data = step.to_dict()
                collected_steps.append(step_data)
                if step.step_type == AgentStepType.ANSWER:
                    final_answer = step.content or ""

                yield f"data: {json.dumps({'type': 'agent_step', 'data': step_data}, ensure_ascii=False)}\n\n"

            if not final_answer and collected_steps:
                final_answer = collected_steps[-1].get("content", "")

            task_payload = {
                "id": f"task_{int(time.time() * 1000)}",
                "status": "success",
                "result": final_answer,
                "steps": collected_steps,
            }
            yield f"data: {json.dumps({'type': 'task_final', 'data': task_payload}, ensure_ascii=False)}\n\n"

            # Persist turn to disk + phase3 state snapshot
            _save_history(session_id, user_request, final_answer or '[Agent task completed]')
            merged_state = _merge_system_snapshot_from_steps(session_state, collected_steps)
            _save_session_state(session_id, merged_state)
        except Exception as exc:
            logger.exception("/process-stream failed")
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}}, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# ======================================================================
# Legacy compatibility routes — proxy confirm / choice to old
# agent_loop module when available, otherwise return a stub response.
# These were originally defined directly in web/app.py.
# ======================================================================

def _get_legacy_agent():
    """Try to import the old agent_loop singleton."""
    try:
        from agent_loop import get_agent_loop
        return get_agent_loop()
    except Exception:
        return None


@agent_bp.route('/confirm', methods=['POST'])
def agent_confirm():
    """User confirmation callback (legacy compat)."""
    data = request.json or {}
    session = data.get('session', '')
    confirmed = data.get('confirmed', False)

    agent = _get_legacy_agent()
    if agent is None:
        return jsonify({"success": False, "error": "Agent 尚未初始化"}), 400

    try:
        agent.submit_confirmation(session, confirmed)
        return jsonify({"success": True, "confirmed": confirmed})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route('/choice', methods=['POST'])
def agent_choice():
    """User choice callback (legacy compat)."""
    data = request.json or {}
    session = data.get('session', '')
    selected = data.get('selected', '')

    agent = _get_legacy_agent()
    if agent is None:
        return jsonify({"success": False, "error": "Agent 尚未初始化"}), 400

    try:
        agent.submit_choice(session, selected)
        return jsonify({"success": True, "selected": selected})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route('/plan', methods=['POST'])
def agent_plan():
    """Multi-step planning endpoint — uses UnifiedAgent ReAct loop with an
    explicit planning system instruction."""
    data = request.json or {}
    user_request = data.get('request', '')
    session_name = data.get('session', '')
    context = data.get('context', {})
    history = context.get('history', []) if isinstance(context, dict) else []

    if not user_request:
        return jsonify({"success": False, "error": "缺少请求内容"}), 400

    agent = get_agent()
    # Override system instruction for planning mode
    original_instruction = agent.base_system_instruction
    agent.base_system_instruction = (
        "You are Koto, an intelligent AI assistant in planning mode. "
        "Break the user's request into logical steps. For each step, think carefully, "
        "choose the right tool, execute it, and verify the result before moving on. "
        "When all steps are complete, provide a comprehensive final answer summarizing "
        "what was done and any produced results."
    )

    def generate():
        collected_steps = []
        final_answer = ""
        try:
            for step in agent.run(input_text=user_request, history=history):
                step_data = step.to_dict()
                collected_steps.append(step_data)
                if step.step_type == AgentStepType.ANSWER:
                    final_answer = step.content or ""
                yield f"data: {json.dumps({'type': 'agent_step', 'data': step_data}, ensure_ascii=False)}\n\n"

            if not final_answer and collected_steps:
                final_answer = collected_steps[-1].get("content", "")

            task_payload = {
                "id": f"task_{int(time.time() * 1000)}",
                "status": "success",
                "result": final_answer,
                "steps": collected_steps,
            }
            yield f"data: {json.dumps({'type': 'task_final', 'data': task_payload}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("/plan failed")
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}}, ensure_ascii=False)}\n\n"
        finally:
            # Restore original instruction
            agent.base_system_instruction = original_instruction

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@agent_bp.route('/optimize', methods=['POST'])
def agent_optimize():
    """Phase4: System performance optimization advisor.
    
    Analyzes current system metrics and provides actionable optimization
    recommendations in a single turn.
    """
    data = request.json or {}
    user_request = data.get('request') or "Analyze my system and suggest optimizations"
    session_id = data.get('session_id') or data.get('session', '')
    context = data.get('context', {})
    history = context.get('history', []) if isinstance(context, dict) else []

    # Phase3: load and inject system state snapshot
    session_state = _load_session_state(session_id)
    snapshot_ctx = _build_snapshot_context_text(session_state)
    if snapshot_ctx:
        history = (history or []) + [{"role": "model", "content": snapshot_ctx}]

    agent = get_agent()
    # Override system instruction for optimization mode
    original_instruction = agent.base_system_instruction
    agent.base_system_instruction = (
        "You are a system performance optimization advisor. "
        "Analyze the current system metrics and provide specific, actionable recommendations. "
        "Use the analyze_system_performance and suggest_optimizations tools to gather data. "
        "Focus on: (1) Identifying bottlenecks, (2) Prioritizing issues by severity, "
        "(3) Providing step-by-step solutions. Be concise but thorough."
    )

    def generate():
        collected_steps = []
        final_answer = ""
        try:
            for step in agent.run(input_text=user_request, history=history):
                step_data = step.to_dict()
                collected_steps.append(step_data)
                if step.step_type == AgentStepType.ANSWER:
                    final_answer = step.content or ""
                yield f"data: {json.dumps({'type': 'agent_step', 'data': step_data}, ensure_ascii=False)}\n\n"

            if not final_answer and collected_steps:
                final_answer = collected_steps[-1].get("content", "")

            task_payload = {
                "id": f"task_{int(time.time() * 1000)}",
                "status": "success",
                "result": final_answer,
                "steps": collected_steps,
            }
            yield f"data: {json.dumps({'type': 'task_final', 'data': task_payload}, ensure_ascii=False)}\n\n"

            # Persist turn to disk + phase3 state snapshot
            _save_history(session_id, user_request, final_answer or '[Optimization analysis completed]')
            merged_state = _merge_system_snapshot_from_steps(session_state, collected_steps)
            _save_session_state(session_id, merged_state)
        except Exception as exc:
            logger.exception("/optimize failed")
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}}, ensure_ascii=False)}\n\n"
        finally:
            # Restore original instruction
            agent.base_system_instruction = original_instruction

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# ------------------------------------------------------------------
# Phase 4b: Monitoring Control Endpoints
# ------------------------------------------------------------------

@agent_bp.route('/monitor/start', methods=['POST'])
def start_monitoring():
    """Start background system monitoring."""
    try:
        from app.core.monitoring.system_event_monitor import get_system_event_monitor
        
        data = request.get_json() or {}
        check_interval = data.get('check_interval', 30)
        
        monitor = get_system_event_monitor(check_interval=check_interval)
        
        if monitor.is_running():
            return jsonify({
                "status": "already_running",
                "message": "System monitoring is already active",
                "check_interval": monitor.check_interval
            })
        
        monitor.start()
        
        return jsonify({
            "status": "success",
            "message": "System monitoring started",
            "check_interval": monitor.check_interval
        })
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to start monitoring: {str(e)}"
        }), 500


@agent_bp.route('/monitor/stop', methods=['POST'])
def stop_monitoring():
    """Stop background system monitoring."""
    try:
        from app.core.monitoring.system_event_monitor import get_system_event_monitor
        
        monitor = get_system_event_monitor()
        
        if not monitor.is_running():
            return jsonify({
                "status": "not_running",
                "message": "System monitoring is not currently active"
            })
        
        monitor.stop()
        
        return jsonify({
            "status": "success",
            "message": "System monitoring stopped"
        })
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to stop monitoring: {str(e)}"
        }), 500


@agent_bp.route('/monitor/status', methods=['GET'])
def monitoring_status():
    """Get current monitoring status and event summary."""
    try:
        from app.core.monitoring.system_event_monitor import get_system_event_monitor
        
        monitor = get_system_event_monitor()
        
        return jsonify({
            "status": "success",
            "monitoring_active": monitor.is_running(),
            "check_interval": monitor.check_interval if monitor.is_running() else None,
            "health": monitor.get_summary(),
            "recent_events": monitor.get_events(limit=5)
        })
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to get status: {str(e)}"
        }), 500


@agent_bp.route('/monitor/events', methods=['GET'])
def get_monitoring_events():
    """Get detected anomalies from monitoring."""
    try:
        from app.core.monitoring.system_event_monitor import get_system_event_monitor
        
        limit = request.args.get('limit', 20, type=int)
        event_type = request.args.get('event_type', None, type=str)
        
        monitor = get_system_event_monitor()
        events = monitor.get_events(limit=limit, event_type=event_type)
        
        return jsonify({
            "status": "success",
            "anomaly_count": len(events),
            "anomalies": events,
            "monitoring_active": monitor.is_running()
        })
    except Exception as e:
        logger.error(f"Error getting events: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to get events: {str(e)}"
        }), 500


@agent_bp.route('/monitor/clear', methods=['POST'])
def clear_monitoring_events():
    """Clear recorded anomalies from monitoring log."""
    try:
        from app.core.monitoring.system_event_monitor import get_system_event_monitor
        
        monitor = get_system_event_monitor()
        count = monitor.clear_events()
        
        return jsonify({
            "status": "success",
            "message": f"Cleared {count} events from monitoring log"
        })
    except Exception as e:
        logger.error(f"Error clearing events: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to clear events: {str(e)}"
        }), 500


# ------------------------------------------------------------------
# Phase 4c: Script Generation Endpoints
# ------------------------------------------------------------------

@agent_bp.route('/generate-script', methods=['POST'])
def generate_fix_script():
    """Generate an executable script to fix a detected system issue."""
    try:
        from app.core.agent.plugins.script_generation_plugin import ScriptGenerationPlugin
        
        data = request.get_json() or {}
        issue_type = data.get('issue_type')
        
        if not issue_type:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: issue_type"
            }), 400
        
        plugin = ScriptGenerationPlugin()
        result = plugin.generate_fix_script(
            issue_type=issue_type,
            process_name=data.get('process_name'),
            service_name=data.get('service_name'),
            min_gb=data.get('min_gb', 5)
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating script: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to generate script: {str(e)}"
        }), 500


@agent_bp.route('/generate-script/list', methods=['GET'])
def list_available_scripts():
    """List available fix script templates."""
    try:
        from app.core.agent.plugins.script_generation_plugin import ScriptGenerationPlugin
        
        plugin = ScriptGenerationPlugin()
        result = plugin.list_available_scripts()
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error listing scripts: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to list scripts: {str(e)}"
        }), 500


@agent_bp.route('/generate-script/save', methods=['POST'])
def save_generated_script():
    """Save a generated script to workspace."""
    try:
        from app.core.agent.plugins.script_generation_plugin import ScriptGenerationPlugin
        
        data = request.get_json() or {}
        script_content = data.get('script_content')
        filename = data.get('filename')
        
        if not script_content or not filename:
            return jsonify({
                "status": "error",
                "message": "Missing required parameters: script_content, filename"
            }), 400
        
        plugin = ScriptGenerationPlugin()
        result = plugin.save_script_to_file(
            script_content=script_content,
            filename=filename
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error saving script: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to save script: {str(e)}"
        }), 500

