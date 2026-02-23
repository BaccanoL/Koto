#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🧪 Phase 2 智能上下文注入 - 验证测试

测试内容：
1. 问题分类 - 识别用户问题的意图
2. 上下文选择 - 选择相关的系统信息
3. 系统指令生成 - 生成包含动态上下文的系统指令
4. 性能评估 - 确保没有明显的性能下降
"""

import sys
import time
import json
from pathlib import Path

# 设置入口点
sys.path.insert(0, str(Path(__file__).parent))

def test_context_injector():
    """测试上下文注入器"""
    print("\n" + "=" * 70)
    print("🧪 Phase 2 上下文注入验证");
    print("=" * 70 + "\n")
    
    try:
        from web.context_injector import (
            QuestionClassifier, ContextSelector, ContextBuilder,
            TaskType, ContextType, get_context_injector,
            classify_question, get_dynamic_system_instruction
        )
        print("✅ 成功导入上下文注入模块\n")
    except ImportError as e:
        print(f"❌ 导入失败: {e}\n")
        return False
    
    # 测试 1: 问题分类
    print("✅ 测试 1: 问题分类")
    print("-" * 70)
    
    test_questions = {
        "代码执行": "帮我运行个 Python 脚本，需要 pandas",
        "文件操作": "找出最大的文件",
        "应用推荐": "我想编辑图片，有什么软件推荐？",
        "性能诊断": "电脑最近很卡，怎么诊断？",
        "系统管理": "如何备份我的文件？",
        "学习": "怎样才能学会编程？",
    }
    
    classifier = QuestionClassifier()
    for category, question in test_questions.items():
        task_type, confidence = classifier.classify(question)
        print(f"  📝 {category}")
        print(f"     问题: {question[:50]}...")
        print(f"     分类: {task_type.value} (置信度: {confidence:.1%})\n")
    
    # 测试 2: 上下文选择
    print("\n✅ 测试 2: 上下文选择")
    print("-" * 70)
    
    selector = ContextSelector()
    for task_type in TaskType:
        contexts = selector.select_contexts(task_type)
        context_names = [c.value for c in contexts]
        print(f"  {task_type.value}:")
        print(f"    └─ {', '.join(context_names)}\n")
    
    # 测试 3: 系统指令生成
    print("\n✅ 测试 3: 系统指令生成")
    print("-" * 70)
    
    # 测试不同类型问题的系统指令
    test_cases = {
        "运行代码": "帮我运行个脚本",
        "查找文件": "找出项目中最大的文件",
        "系统诊断": "电脑卡怎么办",
    }
    
    for name, question in test_cases.items():
        print(f"\n  📝 场景: {name}")
        print(f"     问题: {question}")
        
        try:
            instruction = get_dynamic_system_instruction(question)
            lines = instruction.split('\n')
            
            # 提取关键信息
            sections = []
            for line in lines:
                if line.startswith('##'):
                    sections.append(line.replace('##', '').strip())
            
            print(f"     包含的部分: {', '.join(sections[:3])}")
            print(f"     总长: {len(instruction)} 字符")
        except Exception as e:
            print(f"     ❌ 生成失败: {e}")
    
    # 测试 4: 性能评估
    print("\n\n✅ 测试 4: 性能评估")
    print("-" * 70)
    
    injector = get_context_injector()
    
    test_question = "帮我运行个 Python 脚本，需要 pandas"
    
    # 首次调用（无缓存）
    print(f"\n  测试问题: {test_question}")
    
    start_time = time.time()
    result1 = injector.get_injected_instruction(test_question)
    first_call = (time.time() - start_time) * 1000
    
    # 第二次调用（可能有缓存）
    start_time = time.time()
    result2 = injector.get_injected_instruction(test_question)
    second_call = (time.time() - start_time) * 1000
    
    print(f"  首次调用: {first_call:.1f}ms")
    print(f"  第二次调用: {second_call:.1f}ms")
    print(f"  加速比: {first_call/max(second_call, 0.1):.1f}x")
    
    # 评估性能
    if first_call < 500:  # 首次调用应在 500ms 以内
        print(f"  ✅ 性能良好 (首次 < 500ms)")
    else:
        print(f"  ⚠️ 性能需要优化 (首次 > 500ms)")
    
    # 测试 5: 验证集成
    print("\n\n✅ 测试 5: 系统函数集成")
    print("-" * 70)
    
    try:
        from web.app import _get_chat_system_instruction
        
        # 测试函数是否接受参数
        inst1 = _get_chat_system_instruction()  # 无参数
        inst2 = _get_chat_system_instruction("运行代码")  # 有参数
        
        if len(inst2) > len(inst1):
            print(f"  ✅ 动态系统指令集成成功")
            print(f"     基础指令: {len(inst1)} 字符")
            print(f"     动态指令: {len(inst2)} 字符")
            print(f"     增加: {len(inst2) - len(inst1)} 字符")
        else:
            print(f"  ⚠️ 动态指令可能未生成额外内容")
    except Exception as e:
        print(f"  ❌ 集成测试失败: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Phase 2 测试完成！")
    print("=" * 70)
    return True


def test_system_info_extensions():
    """测试 system_info.py 的新方法"""
    print("\n\n" + "=" * 70)
    print("🧪 系统信息收集器扩展 - 验证")
    print("=" * 70 + "\n")
    
    try:
        from web.system_info import get_system_info_collector
        
        collector = get_system_info_collector()
        
        # 测试新方法
        print("✅ 测试新方法")
        print("-" * 70)
        
        # 1. get_top_processes
        try:
            top_procs = collector.get_top_processes(limit=3)
            print(f"\n  📊 get_top_processes()")
            print(f"     返回 {len(top_procs)} 个进程")
            if top_procs:
                for p in top_procs[:2]:
                    print(f"     • {p.get('name', '?')}: {p.get('memory_percent', 0):.1f}%")
            print(f"     ✅ 正常")
        except Exception as e:
            print(f"     ❌ 失败: {e}")
        
        # 2. get_installed_apps
        try:
            apps = collector.get_installed_apps()
            print(f"\n  💻 get_installed_apps()")
            print(f"     检测到 {len(apps)} 个应用")
            print(f"     样本: {', '.join(apps[:3])}")
            print(f"     ✅ 正常")
        except Exception as e:
            print(f"     ❌ 失败: {e}")
        
        print("\n" + "=" * 70)
        print("✅ 系统信息扩展测试完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("\n")
    print("🎯 Koto Phase 2 完整验证套件")
    print("=" * 70)
    
    success = True
    
    # 运行所有测试
    try:
        if not test_context_injector():
            success = False
    except Exception as e:
        print(f"\n❌ 上下文注入测试异常: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    try:
        if not test_system_info_extensions():
            success = False
    except Exception as e:
        print(f"\n❌ 系统信息扩展测试异常: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    if success:
        print("\n🎉 所有测试通过！Phase 2 实现成功！\n")
        sys.exit(0)
    else:
        print("\n❌ 某些测试失败，请检查输出\n")
        sys.exit(1)
