import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "config" / "gemini_config.env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.app import app


DEFAULT_TARGET = ROOT / "web" / "uploads" / "电影时间的计算解析：基于大视觉语言模型的电影连续性研究.docx"
DEFAULT_REQUIREMENT = "把所有不合适的翻译 不符合中文语序逻辑 生硬的地方改善"
DEFAULT_MODEL = "gemini-3-pro-preview"


def count_revision_markers(docx_path: Path) -> dict:
    with zipfile.ZipFile(docx_path, "r") as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        comments_xml = ""
        if "word/comments.xml" in zf.namelist():
            comments_xml = zf.read("word/comments.xml").decode("utf-8", errors="ignore")

    insertion_count = len(re.findall(r"<w:ins\b", document_xml))
    deletion_count = len(re.findall(r"<w:del\b", document_xml))
    comment_ref_count = len(re.findall(r"<w:commentRangeStart\b", document_xml))
    comment_count = len(re.findall(r"<w:comment\b", comments_xml))

    return {
        "ins": insertion_count,
        "del": deletion_count,
        "comment_refs": comment_ref_count,
        "comments": comment_count,
    }


def run_acceptance(
    file_path: Path,
    requirement: str,
    model_id: str,
    min_applied: int,
    min_revision_markers: int,
    report_path: Path,
) -> int:
    report = {
        "success": False,
        "status": "running",
        "file_path": str(file_path),
        "model_id": model_id,
        "min_applied": min_applied,
        "min_markers": min_revision_markers,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if not file_path.exists():
        print(f"FAIL: input file not found: {file_path}")
        report.update({"status": "failed", "reason": "input_not_found"})
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 2

    payload = {
        "file_path": str(file_path),
        "requirement": requirement,
        "model_id": model_id,
    }

    with app.test_client() as client:
        response = client.post("/api/document/annotate", json=payload)

    status_code = response.status_code
    data = response.get_json(silent=True)

    print(f"HTTP_STATUS={status_code}")
    if not isinstance(data, dict):
        print("FAIL: invalid JSON response")
        print(response.get_data(as_text=True)[:1000])
        report.update({"status": "failed", "reason": "invalid_json_response", "http_status": status_code})
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 3

    success = bool(data.get("success"))
    applied = int(data.get("applied", 0) or 0)
    failed = int(data.get("failed", 0) or 0)
    total = int(data.get("total", applied + failed) or 0)
    revised_file = Path(data.get("revised_file", "")) if data.get("revised_file") else None

    print(f"SUCCESS={success}")
    print(f"APPLIED={applied}")
    print(f"FAILED={failed}")
    print(f"TOTAL={total}")
    print(f"REVISED_FILE={revised_file}")

    if status_code != 200 or not success:
        print(f"FAIL: route execution failed, error={data.get('error')}")
        report.update({
            "status": "failed",
            "reason": "route_failed",
            "http_status": status_code,
            "error": data.get("error"),
            "response": data,
        })
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 4

    if not revised_file or not revised_file.exists():
        print("FAIL: revised file not generated")
        report.update({
            "status": "failed",
            "reason": "revised_missing",
            "response": data,
        })
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 5

    if applied < min_applied:
        print(f"FAIL: applied below threshold ({applied} < {min_applied})")
        report.update({
            "status": "failed",
            "reason": "applied_below_threshold",
            "applied": applied,
            "response": data,
        })
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 6

    markers = count_revision_markers(revised_file)
    marker_total = markers["ins"] + markers["del"] + markers["comments"]

    print("MARKERS=" + json.dumps(markers, ensure_ascii=False))
    print(f"MARKER_TOTAL={marker_total}")

    if marker_total < min_revision_markers:
        print(f"FAIL: revision markers below threshold ({marker_total} < {min_revision_markers})")
        report.update({
            "status": "failed",
            "reason": "markers_below_threshold",
            "marker_total": marker_total,
            "markers": markers,
            "response": data,
        })
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 7

    report.update({
        "success": True,
        "status": "passed",
        "http_status": status_code,
        "applied": applied,
        "failed": failed,
        "total": total,
        "revised_file": str(revised_file),
        "markers": markers,
        "marker_total": marker_total,
    })
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("FINAL_OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="DOC_ANNOTATE one-command acceptance check")
    parser.add_argument("--file", default=str(DEFAULT_TARGET), help="Input .docx file path")
    parser.add_argument("--requirement", default=DEFAULT_REQUIREMENT, help="Annotation requirement text")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model id")
    parser.add_argument("--min-applied", type=int, default=20, help="Minimum applied edits threshold")
    parser.add_argument("--min-markers", type=int, default=40, help="Minimum total revision markers threshold")
    parser.add_argument("--report", default=str(ROOT / "logs" / "doc_annotate_acceptance_report.json"), help="Output report json path")
    args = parser.parse_args()

    return run_acceptance(
        file_path=Path(args.file),
        requirement=args.requirement,
        model_id=args.model,
        min_applied=args.min_applied,
        min_revision_markers=args.min_markers,
        report_path=Path(args.report),
    )


if __name__ == "__main__":
    raise SystemExit(main())
