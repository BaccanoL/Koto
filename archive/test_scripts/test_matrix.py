# -*- coding: utf-8 -*-
"""Koto end-to-end task matrix test (routing + output sanity)."""
import json
import os
import time
import requests

BASE = "http://127.0.0.1:5000"


def stream_request(message, session, max_wait=120, locked_task=None, locked_model=None):
    import threading
    import queue
    payload = {
        "message": message,
        "session": session,
    }
    if locked_task:
        payload["locked_task"] = locked_task
    if locked_model:
        payload["locked_model"] = locked_model

    result = {
        "classification": None,
        "tokens": [],
        "done": None,
        "errors": [],
        "elapsed": None,
    }

    done_q = queue.Queue()

    def _worker():
        try:
            start = time.time()
            resp = requests.post(
                f"{BASE}/api/chat/stream",
                json=payload,
                stream=True,
                timeout=(10, max_wait + 10),
            )

            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")
                if msg_type == "classification":
                    result["classification"] = data
                elif msg_type == "token":
                    content = data.get("content", "")
                    if content:
                        result["tokens"].append(content)
                elif msg_type == "error":
                    result["errors"].append(data.get("message", ""))
                elif msg_type == "done":
                    result["done"] = data
                    break

                if time.time() - start > max_wait:
                    result["errors"].append(f"timeout after {max_wait}s")
                    break

            result["elapsed"] = round(time.time() - start, 2)
        except Exception as e:
            result["errors"].append(str(e))
        finally:
            done_q.put(True)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    t.join(timeout=max_wait + 5)
    if t.is_alive():
        result["errors"].append(f"timeout after {max_wait}s")
        result["elapsed"] = round(max_wait, 2)
    return result


def check_file(path):
    if not path:
        return None
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    if os.path.exists(path):
        return {
            "exists": True,
            "size": os.path.getsize(path),
            "path": path,
        }
    return {"exists": False, "path": path}


def main():
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(os.getcwd(), "logs", f"matrix_test_{ts}.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")

    def log(msg):
        print(msg, flush=True)
        log_file.write(msg + "\n")
        log_file.flush()

    # Health check
    r = requests.get(f"{BASE}/api/health", timeout=5)
    if r.status_code != 200:
        log("Server not healthy")
        log_file.close()
        return

    tests = [
        {
            "name": "CHAT",
            "message": "你好",
            "expect": "CHAT",
            "max_wait": 30,
        },
        {
            "name": "SYSTEM_OPEN_APP",
            "message": "打开记事本",
            "expect": "SYSTEM",
            "max_wait": 30,
        },
        {
            "name": "AGENT_TOOL",
            "message": "列出提醒",
            "expect": "AGENT",
            "max_wait": 40,
            "locked_model": "gemini-2.5-flash",
        },
        {
            "name": "WEB_SEARCH",
            "message": "今天北京天气",
            "expect": "WEB_SEARCH",
            "max_wait": 90,
            "locked_model": "gemini-2.5-flash",
        },
        {
            "name": "CODER",
            "message": "写一个快速排序函数（Python）",
            "expect": "CODER",
            "max_wait": 60,
        },
        {
            "name": "RESEARCH",
            "message": "简要概述量子计算的核心原理",
            "expect": "RESEARCH",
            "max_wait": 90,
        },
        {
            "name": "PAINTER",
            "message": "画一只极简风格黑白猫图标",
            "expect": "PAINTER",
            "max_wait": 120,
        },
        {
            "name": "FILE_GEN_WORD",
            "message": "帮我做一个关于AI的简短word报告，300字即可",
            "expect": "FILE_GEN",
            "max_wait": 180,
        },
        {
            "name": "FILE_GEN_PPT",
            "message": "帮我做一个3页PPT，主题是AI发展趋势",
            "expect": "FILE_GEN",
            "max_wait": 240,
        },
    ]

    summaries = []
    for t in tests:
        session = f"__matrix__{t['name']}"
        log(f"\n=== {t['name']} ===")
        try:
            res = stream_request(
                t["message"],
                session,
                max_wait=t["max_wait"],
                locked_task=t.get("locked_task"),
                locked_model=t.get("locked_model"),
            )
        except Exception as e:
            log(f"error: {t['name']} exception: {e}")
            summaries.append({
                "name": t["name"],
                "expected": t["expect"],
                "got": None,
                "ok_route": False,
                "elapsed": None,
                "errors": [str(e)],
                "saved_files": [],
                "file_checks": [],
                "sample_output": "",
            })
            continue

        task_type = None
        if res["classification"]:
            task_type = res["classification"].get("task_type")
        ok_route = (task_type == t["expect"])

        saved_files = []
        if res["done"]:
            saved_files = res["done"].get("saved_files", []) or []

        file_checks = []
        for f in saved_files:
            file_checks.append(check_file(f))

        summaries.append({
            "name": t["name"],
            "expected": t["expect"],
            "got": task_type,
            "ok_route": ok_route,
            "elapsed": res["elapsed"],
            "errors": res["errors"],
            "saved_files": saved_files,
            "file_checks": file_checks,
            "sample_output": res["tokens"][0][:200] if res["tokens"] else "",
        })

        log(f"route: {task_type} (expected {t['expect']})")
        log(f"elapsed: {res['elapsed']}s")
        if res["errors"]:
            log(f"errors: {res['errors']}")
        if saved_files:
            log(f"saved_files: {saved_files}")

    log("\n=== SUMMARY ===")
    for s in summaries:
        log(
            f"{s['name']}: route_ok={s['ok_route']} got={s['got']} elapsed={s['elapsed']}s "
            f"files={len(s['saved_files'])} errors={len(s['errors'])}"
        )

    log_file.close()


if __name__ == "__main__":
    main()
