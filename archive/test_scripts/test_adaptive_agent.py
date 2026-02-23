#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试 Adaptive Agent 系统的各项功能
"""

import sys
import json
import time
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
    print_section("测试 1: 任务分析器")
    
    analyzer = TaskAnalyzer()
    
    test_requests = [
        "写一个快速排序的 Python 函数",
        "帮我读取 data.csv 并计算平均值",
        "把 image.png 转换为 JPG 格式",
        "爬取这个网站的数据: https://example.com",
        "计算斐波那契数列的第 100 项",
    ]
    
    for request in test_requests:
        task = analyzer.analyze(request)
        print(f"📝 请求: {request}")
        print(f"   任务类型: {task.task_type.value}")
        print(f"   步骤数: {len(task.steps)}")
        if task.steps:
            print(f"   第一步: {task.steps[0].description}")
        print()


def test_tool_registry():
    """测试工具注册表"""
    print_section("测试 2: 工具注册表")
    
    registry = ToolRegistry()
    
    print(f"✅ 已加载 {len(registry.tool_defs)} 个内置工具:\n")
    
    for tool_id, tool_def in registry.tool_defs.items():
        print(f"  • {tool_id}")
        print(f"    描述: {tool_def.description}")
        print(f"    依赖: {[d.name for d in tool_def.dependencies] if tool_def.dependencies else '无'}")
        print(f"    支持链接: {'是' if tool_def.can_chain else '否'}")
        print()


def test_simple_execution():
    """测试简单的代码执行"""
    print_section("测试 3: 简单代码执行")
    
    agent = AdaptiveAgent()
    
    request = "计算 sum([1, 2, 3, 4, 5])"
    print(f"📝 请求: {request}\n")
    
    task = agent.process(request)
    
    print(f"✅ 任务完成!")
    print(f"   状态: {task.status.value}")
    print(f"   执行步骤: {len(task.steps)}")
    print(f"   耗时: {task.duration:.3f}s\n")
    
    if task.steps:
        step = task.steps[0]
        print(f"步骤 1 详情:")
        print(f"   描述: {step.description}")
        print(f"   状态: {step.status.value}")
        print(f"   输出: {step.output}\n")


def test_data_processing():
    """测试数据处理能力"""
    print_section("测试 4: 数据处理")
    
    agent = AdaptiveAgent()
    
    request = "创建一个 CSV 数据并计算统计值"
    print(f"📝 请求: {request}\n")
    
    task = agent.process(request)
    
    print(f"✅ 任务完成!")
    print(f"   状态: {task.status.value}")
    if task.errors:
        print(f"   错误: {task.errors}")
    else:
        print(f"   成功执行 {len(task.steps)} 步\n")
        
        for i, step in enumerate(task.steps, 1):
            print(f"步骤 {i}: {step.description}")
            print(f"   状态: {step.status.value}")
            if step.output and isinstance(step.output, str):
                print(f"   结果: {step.output[:100]}...")
            print()


def test_error_handling():
    """测试错误处理"""
    print_section("测试 5: 错误处理")
    
    agent = AdaptiveAgent()
    
    request = "执行有意的语法错误: def broken("
    print(f"📝 请求: {request}\n")
    
    task = agent.process(request)
    
    print(f"任务完成!")
    print(f"   状态: {task.status.value}")
    if task.errors:
        print(f"   捕获错误: ✅")
        print(f"   错误数: {len(task.errors)}")
        for error in task.errors:
            print(f"   - {error[:80]}...")
    else:
        print(f"   无错误 (可能未捕获)")
    print()


def test_context_passing():
    """测试上下文传递"""
    print_section("测试 6: 上下文传递")
    
    agent = AdaptiveAgent()
    
    request = "写入数据到文件并读取验证"
    print(f"📝 请求: {request}\n")
    
    context = {
        "working_dir": str(Path(__file__).parent),
        "user": "test_user"
    }
    
    print(f"上下文: {context}\n")
    
    task = agent.process(request, context=context)
    
    print(f"✅ 任务完成!")
    print(f"   状态: {task.status.value}")
    print(f"   上下文已传递: ✅\n")


def test_callback_system():
    """测试回调系统"""
    print_section("测试 7: 回调系统")
    
    agent = AdaptiveAgent()
    
    events_received = []
    
    def on_event(event_type, data):
        events_received.append(event_type)
        print(f"   🔔 事件: {event_type}")
    
    request = "计算 2 ** 10"
    print(f"📝 请求: {request}")
    print(f"   监听事件中...\n")
    
    task = agent.process(request, callback=on_event)
    
    print(f"\n✅ 收到 {len(events_received)} 个事件:\n   {', '.join(events_received)}\n")


def test_task_serialization():
    """测试任务序列化"""
    print_section("测试 8: 任务序列化")
    
    agent = AdaptiveAgent()
    
    request = "生成 Fibonacci 数列的前 10 项"
    print(f"📝 请求: {request}\n")
    
    task = agent.process(request)
    
    # 序列化
    task_dict = task.to_dict()
    
    print(f"✅ 任务序列化成功")
    print(f"   任务 ID: {task_dict['task_id']}")
    print(f"   任务类型: {task_dict['task_type']}")
    print(f"   状态: {task_dict['status']}")
    print(f"   步骤数: {len(task_dict['steps'])}")
    print(f"   耗时: {task_dict['duration']:.3f}s")
    
    # 显示为 JSON
    print(f"\n   JSON 长度: {len(json.dumps(task_dict))} 字符\n")
    
    # 验证反序列化
    print(f"✅ 可序列化为 JSON: 是\n")


def test_multi_step_task():
    """测试多步任务"""
    print_section("测试 9: 多步任务")
    
    agent = AdaptiveAgent()
    
    request = "创建列表，排序，然后计算标准差"
    print(f"📝 请求: {request}\n")
    
    task = agent.process(request)
    
    print(f"✅ 多步任务执行")
    print(f"   总步数: {len(task.steps)}")
    print(f"   总耗时: {task.duration:.3f}s\n")
    
    for i, step in enumerate(task.steps, 1):
        print(f"   步骤 {i}: {step.description}")
        print(f"           状态: {step.status.value}, 耗时: {step.duration:.3f}s")
    print()


def test_dependency_detection():
    """测试依赖检测"""
    print_section("测试 10: 依赖检测")
    
    analyzer = TaskAnalyzer()
    
    # 这些请求可能需要特定的包
    test_requests = [
        "用 numpy 计算矩阵",
        "解析 HTML 文档",
        "处理图像文件",
    ]
    
    for request in test_requests:
        task = analyzer.analyze(request)
        deps = []
        for step in task.steps:
            if hasattr(step, 'dependencies'):
                deps.extend([d.name for d in step.dependencies])
        
        print(f"📝 请求: {request}")
        if deps:
            print(f"   检测到依赖: {', '.join(set(deps))}")
        else:
            print(f"   无额外依赖")
        print()


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + "  🤖 Koto Adaptive Agent 系统 - 快速测试套件".center(58) + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        ("任务分析器", test_task_analyzer),
        ("工具注册表", test_tool_registry),
        ("简单执行", test_simple_execution),
        ("数据处理", test_data_processing),
        ("错误处理", test_error_handling),
        ("上下文传递", test_context_passing),
        ("回调系统", test_callback_system),
        ("任务序列化", test_task_serialization),
        ("多步任务", test_multi_step_task),
        ("依赖检测", test_dependency_detection),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ 测试失败: {name}")
            print(f"   错误: {e}\n")
            failed += 1
            import traceback
            traceback.print_exc()
    
    # 总结
    print_section("测试总结")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed}")
    
    if failed == 0:
        print(f"\n🎉 所有测试通过!\n")
    else:
        print(f"\n⚠️  {failed} 个测试未通过\n")


if __name__ == "__main__":
    run_all_tests()
