#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试 Adaptive Agent 系统的各项功能 - 简化版本
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "web"))

from adaptive_agent import (
    AdaptiveAgent, 
    TaskAnalyzer, 
    ToolRegistry,
    ExecutionStatus
)


def print_section(title):
    """打印分隔符"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_task_analyzer():
    """测试任务分析器"""
    print_section("✅ 测试 1: 任务分析器")
    
    analyzer = TaskAnalyzer()
    
    test_requests = [
        "写一个快速排序的 Python 函数",
        "帮我读取 data.csv 并计算平均值",
        "把 image.png 转换为 JPG 格式",
    ]
    
    for request in test_requests:
        task = analyzer.analyze(request)
        print(f"  📝 {request}")
        print(f"     → 任务类型: {task.task_type.value}, 步骤: {len(task.steps)}")
    
    print(f"\n✅ 分析器正常工作\n")
    return True


def test_tool_registry():
    """测试工具注册表"""
    print_section("✅ 测试 2: 工具注册表")
    
    registry = ToolRegistry()
    
    print(f"  已加载工具:\n")
    
    for tool_id, tool_def in registry.tool_defs.items():
        deps = [d.name for d in tool_def.dependencies] if tool_def.dependencies else []
        deps_str = ", ".join(deps) if deps else "无"
        print(f"    • {tool_id:15} - {tool_def.description:30} (依赖: {deps_str})")
    
    print(f"\n✅ 工具注册表正常工作\n")
    return True


def test_agent_creation():
    """测试 Agent 创建"""
    print_section("✅ 测试 3: Agent 初始化")
    
    try:
        agent = AdaptiveAgent()
        print(f"  ✅ Agent 创建成功")
        print(f"  ✅ 共注册 {len(agent.tool_registry.tool_defs)} 个工具")
        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def test_simple_analysis():
    """测试任务分析（无执行）"""
    print_section("✅ 测试 4: 任务分析")
    
    try:
        agent = AdaptiveAgent()
        request = "计算 2+2"
        
        # 仅分析，不执行
        analyzer = TaskAnalyzer()
        task = analyzer.analyze(request)
        
        print(f"  📝 请求: {request}")
        print(f"  📊 任务类型: {task.task_type.value}")
        print(f"  📋 识别步骤: {len(task.steps)} 步")
        
        if task.steps:
            print(f"\n  步骤详情:")
            for i, step in enumerate(task.steps, 1):
                print(f"    {i}. {step.description}")
        
        print(f"\n✅ 分析正常工作\n")
        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_callback():
    """测试事件回调"""
    print_section("✅ 测试 5: 事件系统")
    
    try:
        agent = AdaptiveAgent()
        events = []
        
        def on_event(event_type, data):
            events.append(event_type)
        
        request = "计算 10 * 5"
        print(f"  📝 请求: {request}")
        print(f"  📻 监听事件中...\n")
        
        task = agent.process(request, callback=on_event)
        
        print(f"  📊 收到 {len(events)} 个事件:")
        for ev in events:
            print(f"     • {ev}")
        
        print(f"\n✅ 事件系统正常工作\n")
        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_serialization():
    """测试任务序列化"""
    print_section("✅ 测试 6: 任务序列化")
    
    try:
        analyzer = TaskAnalyzer()
        task = analyzer.analyze("写一个函数")
        
        # 序列化
        task_dict = task.to_dict()
        
        print(f"  ✅ 任务序列化成功")
        print(f"     • 任务 ID: {task_dict['task_id']}")
        print(f"     • 任务类型: {task_dict['task_type']}")
        print(f"     • 步骤数: {len(task_dict['steps'])}")
        
        # JSON 格式验证
        json_str = json.dumps(task_dict)
        print(f"     • JSON 大小: {len(json_str)} 字符")
        
        print(f"\n✅ 序列化系统正常工作\n")
        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_passing():
    """测试上下文传递"""
    print_section("✅ 测试 7: 上下文系统")
    
    try:
        agent = AdaptiveAgent()
        
        context = {
            "working_dir": "/tmp",
            "user": "test_user",
            "env": "testing"
        }
        
        request = "简单计算"
        task = agent.process(request, context=context)
        
        print(f"  ✅ 上下文传递成功")
        print(f"     • 上下文变量数: {len(context)}")
        print(f"     任务状态: {task.status.value}")
        
        print(f"\n✅ 上下文系统正常工作\n")
        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + "  🤖 Koto Adaptive Agent - 功能验证".center(58) + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        ("任务分析器", test_task_analyzer),
        ("工具注册表", test_tool_registry),
        ("Agent 初始化", test_agent_creation),
        ("任务分析", test_simple_analysis),
        ("事件系统", test_event_callback),
        ("任务序列化", test_task_serialization),
        ("上下文系统", test_context_passing),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 异常: {name}")
            print(f"   错误: {e}")
            results.append((name, False))
    
    # 总结
    print_section("📊 测试总结")
    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print(f"\n  📈 通过: {passed}/{len(results)}")
    
    if failed == 0:
        print(f"\n  🎉 所有功能验证通过!\n")
    else:
        print(f"\n  ⚠️  {failed} 个功能未验证\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
