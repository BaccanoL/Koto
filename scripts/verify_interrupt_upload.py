import os
import sys
import json
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from web.app import app


def main():
    session = f"pause_test_{int(time.time())}"
    file_path = os.path.join(ROOT, "web", "uploads", "Manus.docx")

    with app.test_client() as client:
        with open(file_path, "rb") as file_obj:
            payload = {
                "session": session,
                "message": "把所有不合适的翻译 不符合中文语序逻辑 生硬的地方标注改善",
                "locked_task": "DOC_ANNOTATE",
                "locked_model": "gemini-3-pro-preview",
                "file": (file_obj, "Manus.docx"),
            }
            response = client.post(
                "/api/chat/file",
                data=payload,
                content_type="multipart/form-data",
                buffered=False,
            )

        task_id = None
        got_cancelled = False
        deadline = time.time() + 80

        for raw in response.response:
            if time.time() > deadline:
                print("TIMEOUT")
                break

            line = raw.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data: "):
                continue

            try:
                evt = json.loads(line[6:])
            except Exception:
                continue

            evt_type = evt.get("type")
            if evt_type in {"classification", "progress", "info", "error", "done"}:
                print("EVT", evt_type, evt.get("message"), evt.get("progress"))

            if evt_type == "classification" and evt.get("task_id") and not task_id:
                task_id = evt["task_id"]
                print("TASK_ID", task_id)
                interrupt_result = client.post(
                    "/api/chat/interrupt",
                    json={"session": session, "task_id": task_id},
                )
                print("INTERRUPT", interrupt_result.status_code, interrupt_result.get_json())

            if evt_type == "info" and "任务已取消" in (evt.get("message") or ""):
                got_cancelled = True
                break

            if evt_type == "done" and evt.get("cancelled"):
                got_cancelled = True
                break

        print("RESULT", got_cancelled, task_id)
        return 0 if got_cancelled else 1


if __name__ == "__main__":
    raise SystemExit(main())
