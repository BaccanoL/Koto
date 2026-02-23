#!/usr/bin/env python
"""Quick health check for deployed Koto system."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import os
    os.chdir(PROJECT_ROOT)
except Exception:
    pass

def check_structure():
    """Verify project structure is correct."""
    checks = {
        'Root structure': [
            ('koto_app.py', Path('koto_app.py').exists()),
            ('launch.py', Path('launch.py').exists()),
            ('Koto.bat', Path('Koto.bat').exists()),
        ],
        'Core directories': [
            ('app/', Path('app').is_dir()),
            ('web/', Path('web').is_dir()),
            ('config/', Path('config').is_dir()),
            ('data/', Path('data').is_dir()),
        ],
        'Organization': [
            ('tests/', Path('tests').is_dir()),
            ('docs/', Path('docs').is_dir()),
            ('scripts/', Path('scripts').is_dir()),
        ],
    }
    
    print("=" * 60)
    print("KOTO SYSTEM HEALTH CHECK")
    print("=" * 60)
    
    all_good = True
    for section, items in checks.items():
        print(f"\n{section}:")
        for name, exists in items:
            status = "✓" if exists else "✗"
            print(f"  {status} {name}")
            if not exists:
                all_good = False
    
    return all_good

def check_imports():
    """Verify core imports work."""
    print(f"\nCore Modules:")
    
    try:
        from app.core.agent.factory import create_agent
        agent = create_agent('test')
        tools = agent.registry.get_definitions()
        print(f"  ✓ Agent Factory ({len(tools)} tools)")
    except Exception as e:
        print(f"  ✗ Agent Factory: {e}")
        return False
    
    try:
        from app.core.monitoring.system_event_monitor import get_system_event_monitor
        monitor = get_system_event_monitor()
        print(f"  ✓ Event Monitor")
    except Exception as e:
        print(f"  ✗ Event Monitor: {e}")
        return False
    
    try:
        from app.core.monitoring.alert_manager import get_alert_manager
        alerts = get_alert_manager()
        print(f"  ✓ Alert Manager")
    except Exception as e:
        print(f"  ✗ Alert Manager: {e}")
        return False
    
    return True

def main():
    print()
    structure_ok = check_structure()
    imports_ok = check_imports()
    
    print("\n" + "=" * 60)
    if structure_ok and imports_ok:
        print("✅ SYSTEM HEALTH: READY")
        print("All components verified and functional")
        return 0
    else:
        print("⚠️  SYSTEM HEALTH: ISSUES DETECTED")
        print("Check errors above for details")
        return 1

if __name__ == '__main__':
    sys.exit(main())
