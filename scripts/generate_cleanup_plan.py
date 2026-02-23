#!/usr/bin/env python
"""Identify and organize files for folder cleanup."""

from pathlib import Path
import json

def main():
    root = Path('.')
    
    print("=" * 70)
    print("FILE ORGANIZATION PLAN")
    print("=" * 70)
    
    # Categorize root-level files
    test_files = list(root.glob('test_*.py'))
    doc_files = list(root.glob('*.md'))
    py_files = [f for f in root.glob('*.py') if f.name not in [tf.name for tf in test_files]]
    
    # Remove core entry points and special files
    entry_points = {'koto_app.py', 'launch.py', 'main.py', 'app.py'}
    script_files = [f for f in py_files if f.name not in entry_points and not f.name.startswith('test_')]
    
    print(f"\n📁 FILES TO MOVE:\n")
    
    print(f"  🧪 TEST FILES ({len(test_files)}):")
    for f in sorted(test_files)[:10]:
        print(f"    - {f.name}")
    if len(test_files) > 10:
        print(f"    ... and {len(test_files) - 10} more")
    
    print(f"\n  📄 DOCUMENTATION ({len(doc_files)}):")
    for f in sorted(doc_files)[:10]:
        print(f"    - {f.name}")
    if len(doc_files) > 10:
        print(f"    ... and {len(doc_files) - 10} more")
    
    print(f"\n  📝 UTILITY SCRIPTS ({len(script_files)}):")
    for f in sorted(script_files):
        print(f"    - {f.name}")
    
    print(f"\n✅ TO KEEP IN ROOT:")
    print(f"  - koto_app.py (or equivalent entry point)")
    print(f"  - launch.py")
    print(f"  - Koto.bat, Koto.vbs")
    print(f"  - koto.spec")
    
    print(f"\n📊 SUMMARY:")
    print(f"  Files to move: {len(test_files) + len(doc_files) + len(script_files)}")
    print(f"  Directories to create: tests/, docs/, scripts/")
    print(f"  Root files after cleanup: ~5 (launcher files only)")
    
    # Create organization plan
    plan = {
        "test_files": [f.name for f in test_files],
        "doc_files": [f.name for f in doc_files],
        "script_files": [f.name for f in script_files],
        "keep_in_root": ['koto_app.py', 'launch.py', 'Koto.bat', 'Koto.vbs', 'koto.spec']
    }
    
    with open('CLEANUP_PLAN.json', 'w') as f:
        json.dump(plan, f, indent=2)
    
    print(f"\n💾 Cleanup plan saved to: CLEANUP_PLAN.json")

if __name__ == '__main__':
    main()
