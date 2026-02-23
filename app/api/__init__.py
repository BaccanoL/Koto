# 延迟导入 agent_bp - 避免启动时加载 14 个插件 + google.genai
def __getattr__(name):
    if name == "agent_bp":
        from .agent_routes import agent_bp
        return agent_bp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
