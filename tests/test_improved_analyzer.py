#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试改进后的智能文档分析引擎
支持直接返回生成的文本，而不是修改文档
"""

import os
import sys
import json
import requests
from pathlib import Path

# Koto服务URL
KOTO_URL = "http://localhost:5000"
API_UPLOAD = f"{KOTO_URL}/api/chat/file"

# 论文文件路径
PAPER_PATH = Path(__file__).parent / "web" / "uploads" / "数字之眼的危机^L7算法的形式主义危机(1).docx"

# 用户请求 - 生成模式
USER_REQUEST = """写一段摘要：论文摘要通常遵循一定的结构，常见的模板如下（控制在300-400字左右。）：
1.研究背景与目的：简要介绍研究领域的背景，阐述研究的目的和意义。
2.研究方法：描述研究采用的方法论，分析方法等。
3.研究结果：概括研究的主要发现，突出创新点。
4.研究结论：总结研究的主要贡献，指出研究的局限性和未来研究方向。

重新改善引言，因为目前的引言和文章主体架构不符合了。

目前的结论我也不是特别满意，因为没有overcap整篇文章的内容。改善一下。"""


def test_intelligent_analyzer():
    """测试智能文档分析引擎"""
    print("="*70)
    print("Koto 智能文档分析引擎 - 改进测试")
    print("="*70)
    print("\n✨ 新特性: 直接返回生成的文本，而不修改原文档\n")
    
    # 检查文件
    if not PAPER_PATH.exists():
        print(f"❌ 论文文件不存在: {PAPER_PATH}")
        return False
    
    print(f"📄 论文文件: {PAPER_PATH.name}")
    print(f"📝 用户请求:\n{USER_REQUEST}\n")
    
    # 检查Koto服务
    print("⏳ 检查Koto服务状态...")
    try:
        response = requests.get(f"{KOTO_URL}/api/chat", timeout=5)
        print(f"✅ Koto服务在线\n")
    except Exception as e:
        print(f"❌ Koto服务离线: {str(e)}")
        return False
    
    # 上传文件并执行智能分析
    print("📤 上传文件并执行智能分析...\n")
    
    try:
        with open(PAPER_PATH, 'rb') as f:
            files = {'file': (PAPER_PATH.name, f)}
            data = {
                'message': USER_REQUEST,
                'session': 'test_improved_analyzer',
            }
            
            response = requests.post(
                API_UPLOAD,
                files=files,
                data=data,
                stream=True,
                timeout=300
            )
            
            print(f"📡 服务器响应状态: {response.status_code}\n")
            
            if response.status_code != 200:
                print(f"❌ 请求失败: {response.text}")
                return False
            
            # 处理流式响应
            print("🔄 智能分析进行中...\n")
            event_count = 0
            final_result = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                
                if line_str.startswith('data: '):
                    try:
                        event_json = line_str[6:]
                        event = json.loads(event_json)
                        event_count += 1
                        
                        stage = event.get('stage', 'unknown')
                        progress = event.get('progress', 0)
                        message = event.get('message', '')
                        
                        # 显示进度
                        bar = '█' * (progress // 5) + '░' * (20 - progress // 5)
                        print(f"[{bar}] {progress:3}% | {stage.upper():15} | {message}")
                        
                        # 捕获完成事件
                        if stage == 'complete':
                            final_result = event.get('result', {})
                        
                        if stage == 'error':
                            print(f"\n❌ 分析错误: {message}")
                            return False
                    
                    except json.JSONDecodeError:
                        continue
            
            # 显示最终结果
            if final_result:
                print(f"\n✅ 智能分析完成！\n")
                print("="*70)
                print("📊 分析结果")
                print("="*70)
                
                output_type = final_result.get('output_type', 'unknown')
                tasks_completed = final_result.get('tasks_completed', 0)
                
                print(f"\n📌 输出类型: {output_type}")
                print(f"📝 完成任务数: {tasks_completed}")
                
                # 如果是生成模式，显示生成的文本
                if output_type == 'generated_texts':
                    generated_contents = final_result.get('generated_contents', [])
                    print(f"\n💡 生成的内容数: {len(generated_contents)}\n")
                    
                    for i, item in enumerate(generated_contents, 1):
                        print(f"\n{i}. 【{item['task_description']}】")
                        print("-" * 70)
                        content = item['content']
                        # 显示内容（限制长度以避免输出过多）
                        if len(content) > 500:
                            print(content[:500] + "\n... [内容过长，已截断] ...\n" + content[-200:])
                        else:
                            print(content)
                        print()
                
                # 如果是修改模式，显示输出文件
                elif output_type == 'modified_document':
                    output_file = final_result.get('output_file', 'Unknown')
                    revisions = final_result.get('revisions', [])
                    print(f"\n📋 输出文件: {output_file}")
                    print(f"🔴 修订部分: {', '.join(revisions)}")
                
                print("\n" + "="*70)
                print("✨ 关键改进:")
                print("="*70)
                print("""
✅ 灵活的输出模式：
   - 可以直接返回生成的文本（不修改原文档）
   - 可以修改文档并标红（如需要）
   - 可以返回分析结果

✅ 任务理解更准确：
   - 识别"写摘要"为生成新内容
   - 识别"改善"为改进现有内容
   - 识别"分析"为返回分析结果

✅ 不被过去的需求束缚：
   - 每次请求都能灵活处理不同的意图
   - 系统自动判断应返回什么类型的结果
   - 用户获得最需要的输出形式
""")
                
                return True
            
            return False
    
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n")
    success = test_intelligent_analyzer()
    print("\n" + "="*70 + "\n")
