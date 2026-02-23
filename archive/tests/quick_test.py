#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick validation of P1 fixes"""
import requests, json, sys, threading, time

BASE = "http://localhost:5000"

def test_one(session, message, label, auto_confirm=False):
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  Input: {message}")
    
    try:
        r = requests.post(
            f"{BASE}/api/chat/stream",
            json={"session": session, "message": message, "locked_task": None, "locked_model": "auto"},
            stream=True, timeout=90
        )
    except Exception as e:
        print(f"  ERROR connecting: {e}")
        return False
    
    events = []
    for line in r.iter_lines():
        if not line:
            continue
        s = line.decode("utf-8")
        if not s.startswith("data: "):
            continue
        try:
            d = json.loads(s[6:])
        except json.JSONDecodeError:
            continue
        
        events.append(d)
        t = d.get("type")
        
        if t == "classification":
            tt = d.get("task_type")
            print(f"  Classification: {tt}  {'OK' if tt == 'AGENT' else 'FAIL'}")
        elif t == "agent_step":
            tool = d.get("tool_name", "?")
            args_str = json.dumps(d.get("tool_args", {}), ensure_ascii=False)[:60]
            print(f"  Tool: {tool}  args={args_str}")
        elif t == "agent_thought":
            thought = d.get("thought", "")[:80]
            print(f"  Thought: {thought}")
        elif t == "done":
            print(f"  Done: {d.get('steps')} steps, {d.get('elapsed_time')}s")
        elif t == "user_confirm":
            tool = d.get("tool_name", "?")
            print(f"  CONFIRM requested for: {tool}")
            if auto_confirm:
                def _confirm():
                    time.sleep(0.3)
                    try:
                        requests.post(f"{BASE}/api/agent/confirm",
                            json={"session": session, "confirmed": True}, timeout=5)
                        print(f"  -> Auto confirmed!")
                    except Exception as ex:
                        print(f"  -> Confirm failed: {ex}")
                threading.Thread(target=_confirm, daemon=True).start()
        elif t == "error":
            print(f"  ERROR: {d.get('message')}")
    
    passed = any(e.get("type") == "done" for e in events)
    has_agent = any(e.get("type") == "classification" and e.get("task_type") == "AGENT" for e in events)
    
    print(f"\n  Result: {'PASS' if (passed and has_agent) else 'FAIL'}")
    return passed and has_agent


if __name__ == "__main__":
    # Write output to file for stable capture
    import io
    output = io.StringIO()
    def pout(msg):
        print(msg)
        output.write(msg + "\n")
        sys.stdout.flush()
    
    pout("\n=== P1 Quick Validation ===\n")
    
    test_num = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    results = {}
    
    if test_num == 0 or test_num == 1:
        results["T1-Reminder"] = test_one("qt1", "提醒我5秒后喝水", "Test 1: Reminder")
    
    if test_num == 0 or test_num == 2:
        results["T2-FileRead"] = test_one("qt2", "帮我读取 workspace 目录下有什么文件", "Test 2: File Read")
    
    if test_num == 0 or test_num == 3:
        results["T3-Clipboard"] = test_one("qt3", "看看我最近复制了什么", "Test 3: Clipboard")
    
    if test_num == 0 or test_num == 4:
        results["T4-MultiStep"] = test_one("qt4", "搜索一下今天的黄金价格，然后把结果保存到 gold_price.txt 文件里", "Test 4: Multi-step")
    
    if test_num == 0 or test_num == 5:
        results["T5-Confirm"] = test_one("qt5", "发微信给张三说明天开会", "Test 5: WeChat Confirm", auto_confirm=True)
    
    summary = []
    summary.append(f"\n{'='*50}")
    summary.append("  SUMMARY")
    summary.append(f"{'='*50}")
    for name, passed in results.items():
        summary.append(f"  {'PASS' if passed else 'FAIL'}  {name}")
    summary.append(f"\n  Total: {sum(1 for v in results.values() if v)}/{len(results)}")
    
    for line in summary:
        pout(line)
    
    # Save results to file
    with open("test_output.txt", "w", encoding="utf-8") as f:
        f.write(output.getvalue())
