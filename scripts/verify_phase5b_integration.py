#!/usr/bin/env python
"""Quick verification that Phase 5b AlertingPlugin is properly integrated."""

from app.core.agent.factory import create_agent

def main():
    # Create agent with all plugins
    print("Creating agent...")
    agent = create_agent('test_key')
    
    # Get all registered tools
    tools = agent.registry.get_definitions()
    print(f"Total tools registered: {len(tools)}")
    
    # Filter for alerting tools
    alert_tools = [t for t in tools if 'alert' in t['name'].lower()]
    print(f"\nAlerting tools: {len(alert_tools)}")
    for tool in alert_tools:
        print(f"  ✓ {tool['name']}")
    
    # Verify all expected alerting tools are present
    expected_tools = {
        'configure_email_alerts',
        'add_webhook_alert',
        'create_alert_rule',
        'disable_alert_rule',
        'enable_alert_rule',
        'get_alert_rules',
        'get_alert_history',
        'test_alert_rule'
    }
    
    actual_tools = {t['name'] for t in alert_tools}
    missing = expected_tools - actual_tools
    
    if missing:
        print(f"\n❌ Missing tools: {missing}")
        return False
    else:
        print(f"\n✓ All 8 alerting tools registered successfully!")
        return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
