import os
import logging
from typing import Optional

# 所有重型导入延迟到 create_agent() 内部，避免启动时加载 14 个插件 + google.genai (~4.7s)

logger = logging.getLogger(__name__)

def create_agent(api_key: Optional[str] = None, model_id: str = "gemini-3-flash-preview") -> "UnifiedAgent":
    """
    Factory function to create a fully configured UnifiedAgent.
    All heavy imports are deferred to this function call.
    """
    from app.core.llm.gemini import GeminiProvider
    from app.core.agent.unified_agent import UnifiedAgent
    from app.core.agent.tool_registry import ToolRegistry
    from app.core.agent.plugins.basic_tools_plugin import BasicToolsPlugin
    from app.core.agent.plugins.file_editor_plugin import FileEditorPlugin
    from app.core.agent.plugins.search_plugin import SearchPlugin
    from app.core.agent.plugins.system_tools_plugin import SystemToolsPlugin
    from app.core.agent.plugins.data_process_plugin import DataProcessPlugin
    from app.core.agent.plugins.network_plugin import NetworkPlugin
    from app.core.agent.plugins.image_process_plugin import ImageProcessPlugin
    from app.core.agent.plugins.system_info_plugin import SystemInfoPlugin
    from app.core.agent.plugins.performance_analysis_plugin import PerformanceAnalysisPlugin
    from app.core.agent.plugins.system_event_monitoring_plugin import SystemEventMonitoringPlugin
    from app.core.agent.plugins.script_generation_plugin import ScriptGenerationPlugin
    from app.core.agent.plugins.alerting_plugin import AlertingPlugin
    from app.core.agent.plugins.auto_remediation_plugin import AutoRemediationPlugin
    from app.core.agent.plugins.trend_analysis_plugin import TrendAnalysisPlugin
    from app.core.agent.plugins.configuration_plugin import ConfigurationPlugin
    
    # 1. Initialize LLM Provider
    # Try multiple env var names used across the project
    usage_api_key = (
        api_key
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    
    if not usage_api_key:
        logger.warning("No API Key provided for Agent. Agent will fail at generation.")
    
    llm_provider = GeminiProvider(api_key=usage_api_key)
    
    # 2. Initialize Registry & Plugins
    registry = ToolRegistry()
    
    # Basic Tools
    registry.register_plugin(BasicToolsPlugin())
    
    # File Editor (Workspace scoped)
    # Assuming workspace is at project root/workspace
    # We can make this configurable later
    registry.register_plugin(FileEditorPlugin())
    
    # Search Plugin
    registry.register_plugin(SearchPlugin(api_key=usage_api_key))
    
    # System Tools (Python exec, pip)
    registry.register_plugin(SystemToolsPlugin())
    
    # Data Processing (pandas-backed)
    registry.register_plugin(DataProcessPlugin())
    
    # Network (HTTP requests, HTML parsing)
    registry.register_plugin(NetworkPlugin())
    
    # Image Processing (Pillow-backed)
    registry.register_plugin(ImageProcessPlugin())

    # System Info (Phase 3 on-demand system status)
    registry.register_plugin(SystemInfoPlugin())
    
    # Performance Analysis (Phase 4 optimization suggestions)
    registry.register_plugin(PerformanceAnalysisPlugin())
    
    # System Event Monitoring (Phase 4b background monitoring)
    registry.register_plugin(SystemEventMonitoringPlugin())
    
    # Script Generation (Phase 4c auto-fix scripts)
    registry.register_plugin(ScriptGenerationPlugin())
    
    # Alerting (Phase 5b email/webhook notifications)
    registry.register_plugin(AlertingPlugin())
    
    # Auto-Remediation (Phase 5c approval workflow)
    registry.register_plugin(AutoRemediationPlugin())
    
    # Trend Analysis (Phase 5d historical insights)
    registry.register_plugin(TrendAnalysisPlugin())
    
    # Configuration (Phase 5e threshold management)
    registry.register_plugin(ConfigurationPlugin())
    
    # 3. Create Agent
    agent = UnifiedAgent(
        llm_provider=llm_provider,
        tool_registry=registry,
        model_id=model_id
    )
    
    return agent
