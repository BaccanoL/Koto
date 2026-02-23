#!/usr/bin/env python
"""Debug Phase 5d tool registration."""

from app.core.agent.plugins.trend_analysis_plugin import TrendAnalysisPlugin

def main():
    plugin = TrendAnalysisPlugin()
    tools = plugin.get_tools()
    
    print(f"TrendAnalysisPlugin.get_tools() returns {len(tools)} tools:\n")
    for tool in tools:
        print(f"  - {tool['name']}")
    
    print("\nExpected 4 tools:")
    print("  - analyze_event_trends")
    print("  - predict_potential_issues")
    print("  - compare_with_historical")
    print("  - get_anomaly_score")

if __name__ == '__main__':
    main()
