#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Agent 系统 (P1) — 验证事件格式、工具调用、错误恢复
"""

import requests
import json
import time
import threading

BASE_URL = "http://localhost:5000"


def stream_agent_request(session: str, message: str, display: bool = True, timeout: int = 60, auto_confirm: bool = False) -> list:
    """发送消息并收集所有SSE事件
    
    Args:
        timeout: 单个请求的超时时间（秒）
        auto_confirm: 如果为True，遇到 user_confirm 事件后自动发送确认
    """
    payload = {
        "session": session,
        "message": message,
        "locked_task": None,
        "locked_model": "auto"
    }
    
    if display:
        print(f"\n📤 发送: {message}")
        print("-" * 60)
    
    response = requests.post(f"{BASE_URL}/api/chat/stream", json=payload, stream=True, timeout=timeout)
    events = []
    final_text = ""
    
    for line in response.iter_lines():
        if not line:
            continue
        line_str = line.decode('utf-8')
        if not line_str.startswith('data: '):
            continue
        
        try:
            data = json.loads(line_str[6:])
        except json.JSONDecodeError:
            continue
        
        events.append(data)
        event_type = data.get('type', 'unknown')
        
        if not display:
            continue
        
        if event_type == 'classification':
            print(f"🎯 分类: {data.get('task_type')}")
        
        elif event_type == 'agent_step':
            step = data.get('step_number', '?')
            total = data.get('total_steps', '?')
            tool = data.get('tool_name', '?')
            args_str = json.dumps(data.get('tool_args', {}), ensure_ascii=False)
            print(f"🤖 步骤 {step}/{total}: {tool}  参数={args_str[:80]}")
        
        elif event_type == 'agent_thought':
            thought = data.get('thought', '')
            print(f"💭 思考: {thought[:120]}")
        
        elif event_type == 'progress':
            print(f"   ⏳ {data.get('message', '')}")
        
        elif event_type == 'token':
            final_text += data.get('content', '')
        
        elif event_type == 'done':
            elapsed = data.get('elapsed_time', '?')
            steps = data.get('steps', '?')
            print(f"✅ 完成 — {steps} 步, {elapsed}s")
        
        elif event_type == 'error':
            print(f"❌ 错误: {data.get('message')}")
        
        elif event_type == 'user_confirm':
            tool = data.get('tool_name', '?')
            reason = data.get('reason', '')
            print(f"⚠️ 确认请求: {tool} — {reason}")
            # 自动确认
            if auto_confirm:
                def _do_confirm():
                    time.sleep(0.5)
                    try:
                        requests.post(f"{BASE_URL}/api/agent/confirm", json={
                            "session": session,
                            "confirmed": True
                        }, timeout=5)
                        print("   🔄 已自动确认")
                    except Exception as ex:
                        print(f"   ⚠️ 自动确认失败: {ex}")
                threading.Thread(target=_do_confirm, daemon=True).start()
    
    if display and final_text:
        print(f"\n📝 回复: {final_text[:200]}{'...' if len(final_text) > 200 else ''}")
    
    return events


def validate_event_fields(events: list, test_name: str) -> bool:
    """验证事件字段是否正确"""
    ok = True
    
    for data in events:
        t = data.get('type')
        
        if t == 'agent_step':
            for field in ['step_number', 'total_steps', 'tool_name']:
                if field not in data or data[field] is None:
                    print(f"  ⚠️ [{test_name}] agent_step 缺少字段: {field}")
                    ok = False
        
        elif t == 'agent_thought':
            if 'thought' not in data or data['thought'] is None:
                print(f"  ⚠️ [{test_name}] agent_thought 缺少 'thought' 字段")
                ok = False
        
        elif t == 'done':
            if 'elapsed_time' not in data:
                print(f"  ⚠️ [{test_name}] done 缺少 'elapsed_time' 字段")
                ok = False
        
        elif t == 'user_confirm':
            for field in ['tool_name', 'tool_args', 'reason']:
                if field not in data:
                    print(f"  ⚠️ [{test_name}] user_confirm 缺少字段: {field}")
                    ok = False
    
    if ok:
        print(f"  ✅ [{test_name}] 所有事件字段格式正确")
    
    return ok


def test_1_reminder():
    """测试 1: 提醒功能 — 验证工具调用和事件格式"""
    print("\n" + "=" * 60)
    print("测试 1: 提醒功能 (add_reminder)")
    print("=" * 60)
    
    events = stream_agent_request("p1_test_reminder", "提醒我5秒后喝水")
    validate_event_fields(events, "reminder")
    
    # 统计
    types_count = {}
    for e in events:
        t = e.get('type', 'unknown')
        types_count[t] = types_count.get(t, 0) + 1
    
    print(f"\n📊 事件统计: {types_count}")
    print(f"   agent_step 数量: {types_count.get('agent_step', 0)} (期望 >= 1)")
    print(f"   agent_thought 数量: {types_count.get('agent_thought', 0)} (期望 >= 0)")
    
    success = types_count.get('done', 0) > 0
    print(f"\n{'✅ 通过' if success else '❌ 失败'}")
    return success


def test_2_file_read():
    """测试 2: 文件读取 — 验证新 P1 工具"""
    print("\n" + "=" * 60)
    print("测试 2: 文件读取 (read_file)")
    print("=" * 60)
    
    events = stream_agent_request("p1_test_file", "帮我读取 workspace 目录下有什么文件")
    validate_event_fields(events, "file_read")
    
    success = any(e.get('type') == 'done' for e in events)
    print(f"\n{'✅ 通过' if success else '❌ 失败'}")
    return success


def test_3_clipboard():
    """测试 3: 剪贴板 — 验证新 P1 工具"""
    print("\n" + "=" * 60)
    print("测试 3: 剪贴板读取 (read_clipboard)")
    print("=" * 60)
    
    events = stream_agent_request("p1_test_clipboard", "看看我最近复制了什么")
    validate_event_fields(events, "clipboard")
    
    success = any(e.get('type') == 'done' for e in events)
    print(f"\n{'✅ 通过' if success else '❌ 失败'}")
    return success


def test_4_multi_step():
    """测试 4: 多步骤任务 — 验证 Agent 连续调用多个工具"""
    print("\n" + "=" * 60)
    print("测试 4: 多步骤任务 (搜索 + 写入文件)")
    print("=" * 60)
    
    events = stream_agent_request(
        "p1_test_multi", 
        "搜索一下今天的黄金价格，然后把结果保存到 gold_price.txt 文件里"
    )
    validate_event_fields(events, "multi_step")
    
    tool_names = [e.get('tool_name') for e in events if e.get('type') == 'agent_step']
    print(f"\n   调用的工具: {tool_names}")
    
    success = any(e.get('type') == 'done' for e in events) and len(tool_names) >= 2
    print(f"{'✅ 通过' if success else '❌ 失败'}")
    return success


def test_5_notification_confirm():
    """测试 5: 需要确认的工具 — 验证 user_confirm 事件"""
    print("\n" + "=" * 60)
    print("测试 5: 用户确认流程 (send_wechat_message)")
    print("=" * 60)
    
    events = stream_agent_request("p1_test_confirm", "发微信给张三说明天开会", auto_confirm=True, timeout=90)
    validate_event_fields(events, "confirm")
    
    has_confirm = any(e.get('type') == 'user_confirm' for e in events)
    print(f"\n   是否触发确认: {'是' if has_confirm else '否'} (期望: 是)")
    
    success = has_confirm
    print(f"{'✅ 通过' if success else '⚠️ 需要确认事件未触发（可能被超时处理）'}")
    return success


if __name__ == "__main__":
    try:
        print("\n🚀 开始 P1 Agent 系统测试\n")
        
        results = {}
        results['提醒功能'] = test_1_reminder()
        results['文件读取'] = test_2_file_read()
        results['剪贴板'] = test_3_clipboard()
        results['多步骤'] = test_4_multi_step()
        results['用户确认'] = test_5_notification_confirm()
        
        print("\n" + "=" * 60)
        print("📋 测试结果汇总")
        print("=" * 60)
        for name, passed in results.items():
            status = '✅' if passed else '❌'
            print(f"  {status} {name}")
        
        passed_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        print(f"\n  总计: {passed_count}/{total_count} 通过")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保 Koto 正在运行 (http://localhost:5000)")
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
