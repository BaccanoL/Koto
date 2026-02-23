import os
import sys
import json
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, "config", "gemini_config.env"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from web.app import app


def main() -> int:
    target = os.path.join(ROOT, "web", "uploads", "电影时间的计算解析：基于大视觉语言模型的电影连续性研究.docx")
    if not os.path.exists(target):
        print("ERROR: target file not found")
        print(target)
        return 2

    payload = {
        "file_path": target,
        "requirement": "把所有不合适的翻译 不符合中文语序逻辑 生硬的地方改善",
        "model_id": "gemini-3-pro-preview"
    }

    with app.test_client() as c:
        resp = c.post("/api/document/annotate", json=payload)

    print(f"HTTP_STATUS={resp.status_code}")
    text = resp.get_data(as_text=True)
    try:
        data = resp.get_json(silent=True)
    except Exception:
        data = None

    if not isinstance(data, dict):
        print("ERROR: invalid json response")
        print(text[:1000])
        return 3

    print("SUCCESS_FIELD=", data.get("success"))
    print("APPLIED=", data.get("applied"))
    print("FAILED=", data.get("failed"))
    print("TOTAL=", data.get("total"))
    print("REVISED_FILE=", data.get("revised_file"))

    revised = data.get("revised_file") or ""
    print("REVISED_EXISTS=", bool(revised and os.path.exists(revised)))

    if resp.status_code != 200 or not data.get("success"):
        print("ERROR_FIELD=", data.get("error"))
        return 4

    if not revised or not os.path.exists(revised):
        return 5

    if int(data.get("applied", 0) or 0) <= 0:
        return 6

    print("FINAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
