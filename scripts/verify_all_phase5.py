#!/usr/bin/env python
"""Verify all Phase 5 plugins are properly integrated."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.agent.factory import create_agent

def main():
    print("Creating agent with all Phase 5 plugins...\n")
    agent = create_agent('test_key')
    
    tools = agent.registry.get_definitions()
    print(f"Total tools registered: {len(tools)}\n")
    
    # Group tools by phase
    phase5_tools = {}
    
    for tool in tools:
        name = tool['name']
        if 'alert' in name:
            phase = '5b'
        elif 'remediation' in name or 'remedial' in name:
            phase = '5c'
        elif 'anomaly' in name or 'trend' in name or 'predict' in name or 'compare' in name:
            phase = '5d'
        elif 'threshold' in name or 'configuration' in name or 'validate' in name:
            phase = '5e'
        else:
            continue
        
        if phase not in phase5_tools:
            phase5_tools[phase] = []
        phase5_tools[phase].append(name)
    
    # Display results
    total_phase5 = 0
    for phase in sorted(phase5_tools.keys()):
        tools_list = phase5_tools[phase]
        total_phase5 += len(tools_list)
        print(f"Phase {phase}: {len(tools_list)} tools")
        for tool_name in sorted(tools_list):
            print(f"  ✓ {tool_name}")
        print()
    
    print(f"Total Phase 5 tools: {total_phase5}")
    
    # Summary check
    expected = {
        '5b': 8,  # AlertingPlugin
        '5c': 7,  # AutoRemediationPlugin
        '5d': 4,  # TrendAnalysisPlugin
        '5e': 5,  # ConfigurationPlugin
    }
    
    print("\nValidation:")
    all_ok = True
    for phase, expected_count in expected.items():
        actual = len(phase5_tools.get(phase, []))
        status = "✓" if actual == expected_count else "✗"
        print(f"  {status} Phase {phase}: {actual}/{expected_count} tools")
        if actual != expected_count:
            all_ok = False
    
    print()
    if all_ok and total_phase5 == 24:
        print("✅ ALL PHASE 5 PLUGINS SUCCESSFULLY INTEGRATED!")
        return True
    else:
        print("❌ Some Phase 5 tools are missing")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
