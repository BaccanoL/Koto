"""Test: open_application tool with smart app finding"""
import requests
import json

BASE = "http://127.0.0.1:5000"
SESSION = "__app_test__"

# Test 1: Open WeChat (should use smart finder now)
print("Test 1: 打开微信 (Open WeChat)")
print("=" * 50)

resp = requests.post(
    f"{BASE}/api/chat/stream",
    json={"message": "打开微信", "session": SESSION},
    stream=True,
    timeout=60
)

found_app_msg = False
found_success_or_error = False

for line in resp.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data: "):
        continue
    try:
        data = json.loads(line[6:])
        msg_type = data.get("type")

        if msg_type == "classification":
            print(f"  📌 Task: {data.get('task_type')} - {data.get('message', '')}")

        elif msg_type == "token":
            content = data.get("content", "")
            if "微信" in content or "成功" in content or "failed" in content or "无法" in content:
                print(f"  💬 {content[:150]}")
                found_success_or_error = True

        elif msg_type == "done":
            print(f"  ✅ Done")
            break

    except json.JSONDecodeError:
        pass

if not found_app_msg and not found_success_or_error:
    print("  (没有看到具体的应用打开结果消息)")

# Test 2: Open notepad (should be found in PATH or via white list)
print("\n\nTest 2: 打开记事本 (Open Notepad)")
print("=" * 50)

SESSION2 = "__notepad_test__"
resp = requests.post(
    f"{BASE}/api/chat/stream",
    json={"message": "帮我打开记事本", "session": SESSION2},
    stream=True,
    timeout=60
)

for line in resp.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data: "):
        continue
    try:
        data = json.loads(line[6:])
        msg_type = data.get("type")

        if msg_type == "classification":
            print(f"  📌 Task: {data.get('task_type')} - {data.get('message', '')}")

        elif msg_type == "token":
            content = data.get("content", "")
            if "记事本" in content or "成功" in content or "已打开" in content:
                print(f"  💬 {content[:150]}")

        elif msg_type == "done":
            print(f"  ✅ Done")
            break

    except json.JSONDecodeError:
        pass

print("\n✅ Test completed")
