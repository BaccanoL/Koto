#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔍 上下文注入 Debug 脚本

检查为什么生成的指令中没有包含完整的系统信息
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from web.context_injector import (
    QuestionClassifier,
    ContextSelector,
    ContextBuilder,
    TaskType,
    ContextType
)

print("\n" + "=" * 70)
print("🔍 Debug: 上下文注入细节检查")
print("=" * 70)

# 测试问题
question = "帮我运行个脚本"

# 1. 分类
classifier = QuestionClassifier()
task_type, confidence = classifier.classify(question)
print(f"\n1️⃣ 问题分类")
print(f"   问题: {question}")
print(f"   任务类型: {task_type.value}")
print(f"   置信度: {confidence:.1%}")

# 2. 上下文选择
selector = ContextSelector()
contexts = selector.select_contexts(task_type)
print(f"\n2️⃣ 上下文选择")
print(f"   需要的上下文: {[c.value for c in contexts]}")

# 3. 构建各个上下文
print(f"\n3️⃣ 上下文构建详情")

builder = ContextBuilder()

for context_type in sorted(contexts, key=lambda x: x.value):
    print(f"\n   {context_type.value}:")
    
    try:
        if context_type == ContextType.TIME:
            result = builder.build_time_context()
        elif context_type == ContextType.CPU_MEMORY:
            result = builder.build_cpu_memory_context()
        elif context_type == ContextType.DISK:
            result = builder.build_disk_context()
        elif context_type == ContextType.PROCESSES:
            result = builder.build_processes_context()
        elif context_type == ContextType.PYTHON_ENV:
            result = builder.build_python_env_context()
        elif context_type == ContextType.INSTALLED_APPS:
            result = builder.build_installed_apps_context()
        elif context_type == ContextType.WORKING_DIR:
            result = builder.build_working_dir_context()
        elif context_type == ContextType.FILESYSTEM:
            result = builder.build_filesystem_context()
        elif context_type == ContextType.NETWORK:
            result = builder.build_network_context()
        elif context_type == ContextType.WARNINGS:
            result = builder.build_warnings_context()
        else:
            result = "(Unknown)"
        
        if result:
            lines = result.split('\n')
            print(f"      ✅ 成功生成 ({len(result)} 字符)")
            print(f"      样本行数: {len(lines)}")
            # 打印前两行
            for line in lines[:2]:
                print(f"        > {line[:50]}")
        else:
            print(f"      ⚠️ 空结果")
    
    except Exception as e:
        print(f"      ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

# 4. 完整指令生成
print(f"\n4️⃣ 完整系统指令生成")

try:
    from web.context_injector import get_dynamic_system_instruction
    
    instruction = get_dynamic_system_instruction(question)
    
    print(f"   ✅ 生成成功")
    print(f"   总长: {len(instruction)} 字符")
    
    # 分析内容
    sections = []
    for line in instruction.split('\n'):
        if line.startswith('##'):
            sections.append(line.replace('##', '').strip())
    
    print(f"   包含的部分:")
    for sec in sections:
        print(f"     • {sec}")
    
    # 检查是否包含系统信息
    has_time = "📅" in instruction or "🕒" in instruction
    has_cpu = "📊" in instruction or "CPU" in instruction
    has_python = "🐍" in instruction or "Python" in instruction
    
    print(f"\n   内容检查:")
    print(f"     时间信息: {'✅' if has_time else '❌'}")
    print(f"     CPU信息: {'✅' if has_cpu else '❌'}")
    print(f"     Python信息: {'✅' if has_python else '❌'}")
    
except Exception as e:
    print(f"   ❌ 生成失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
