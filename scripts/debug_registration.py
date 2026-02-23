#!/usr/bin/env python
"""Debug tool registration at each stage."""

from app.core.agent.tool_registry import ToolRegistry
from app.core.agent.plugins.trend_analysis_plugin import TrendAnalysisPlugin
from app.core.agent.plugins.alerting_plugin import AlertingPlugin

def main():
    registry = ToolRegistry()
    
    print("=== Before Registration ===")
    print(f"Tools in registry: {len(registry._tools)}")
    
    print("\n=== Registering AlertingPlugin ===")
    alerting = AlertingPlugin()
    alerting_tools = alerting.get_tools()
    print(f"AlertingPlugin.get_tools() returns: {len(alerting_tools)} tools")
    for tool in alerting_tools:
        print(f"  - {tool['name']}")
    registry.register_plugin(alerting)
    print(f"Tools in registry after AlertingPlugin: {len(registry._tools)}")
    
    print("\n=== Registering TrendAnalysisPlugin ===")
    trend = TrendAnalysisPlugin()
    trend_tools = trend.get_tools()
    print(f"TrendAnalysisPlugin.get_tools() returns: {len(trend_tools)} tools")
    for tool in trend_tools:
        print(f"  - {tool['name']}")
    registry.register_plugin(trend)
    print(f"Tools in registry after TrendAnalysisPlugin: {len(registry._tools)}")
    
    print("\n=== Registered tool definitions ===")
    defs = registry.get_definitions()
    alerting_count = sum(1 for d in defs if 'alert' in d['name'])
    trend_count = sum(1 for d in defs if 'anomaly' in d['name'] or 'trend' in d['name'] or 'compare' in d['name'] or 'predict' in d['name'])
    print(f"Total definitions: {len(defs)}")
    print(f"Alerting tools in definitions: {alerting_count}")
    print(f"Trend tools in definitions: {trend_count}")
    
    print("\n=== Trend Analysis Tools in Registry ===")
    for name in registry._tools:
        if 'anomaly' in name or 'trend' in name or 'compare' in name or 'predict' in name:
            print(f"  ✓ {name}")

if __name__ == '__main__':
    main()
