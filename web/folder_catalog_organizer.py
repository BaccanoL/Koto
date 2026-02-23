"""
指定路径文件夹自动归纳 + 归纳清单生成（含发送者/来源人线索）
"""
from __future__ import annotations

import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class FolderCatalogOrganizer:
    """对指定文件夹执行批量归纳，并输出带发送者线索的清单。"""

    def __init__(self, organize_root: str, analyzer: Any, organizer: Any):
        self.organize_root = Path(organize_root)
        self.analyzer = analyzer
        self.organizer = organizer

    def organize_folder(self, source_dir: str, recursive: bool = True) -> Dict[str, Any]:
        source_path = Path(source_dir)
        if not source_path.exists() or not source_path.is_dir():
            return {
                "success": False,
                "error": f"目录不存在: {source_dir}",
            }

        files = list(source_path.rglob("*")) if recursive else list(source_path.glob("*"))
        files = [f for f in files if f.is_file()]

        if not files:
            return {
                "success": False,
                "error": "目录中没有可处理文件",
                "source_dir": str(source_path),
            }

        entries: List[Dict[str, Any]] = []
        organized_count = 0
        failed_count = 0

        for file_path in files:
            try:
                analysis = self.analyzer.analyze_file(str(file_path))
                suggested_folder = analysis.get("suggested_folder") or "other/uncategorized"

                sender_info = self._extract_sender_info(file_path)
                metadata = {
                    "sender": sender_info.get("sender"),
                    "sender_source": sender_info.get("sender_source"),
                    "office_creator": sender_info.get("office_creator"),
                    "office_last_modified_by": sender_info.get("office_last_modified_by"),
                }

                result = self.organizer.organize_file(
                    str(file_path),
                    suggested_folder,
                    auto_confirm=True,
                    metadata=metadata,
                )

                if result.get("success"):
                    organized_count += 1
                else:
                    failed_count += 1

                entries.append({
                    "file_name": file_path.name,
                    "source_path": str(file_path),
                    "suggested_folder": suggested_folder,
                    "sender": sender_info.get("sender") or "未知",
                    "sender_source": sender_info.get("sender_source") or "unknown",
                    "organized": bool(result.get("success")),
                    "organized_path": result.get("dest_file") or "",
                    "error": result.get("error") or "",
                })
            except Exception as e:
                failed_count += 1
                entries.append({
                    "file_name": file_path.name,
                    "source_path": str(file_path),
                    "suggested_folder": "other/uncategorized",
                    "sender": "未知",
                    "sender_source": "unknown",
                    "organized": False,
                    "organized_path": "",
                    "error": str(e),
                })

        report_paths = self._write_reports(str(source_path), entries)

        return {
            "success": organized_count > 0,
            "source_dir": str(source_path),
            "total_files": len(files),
            "organized_count": organized_count,
            "failed_count": failed_count,
            "report_markdown": report_paths.get("markdown"),
            "report_json": report_paths.get("json"),
            "entries": entries,
        }

    def _extract_sender_info(self, file_path: Path) -> Dict[str, Optional[str]]:
        ext = file_path.suffix.lower()

        # 1) 文件名前缀推断（例如：朱总-500万-收款凭证.pdf）
        by_name = self._sender_from_filename(file_path.stem)
        if by_name:
            return {
                "sender": by_name,
                "sender_source": "filename_prefix",
                "office_creator": None,
                "office_last_modified_by": None,
            }

        # 2) Office 元数据（docx/pptx/xlsx/pptm）
        if ext in {".docx", ".pptx", ".xlsx", ".pptm", ".docm", ".xlsm"}:
            creator, last_modified_by = self._extract_office_author(file_path)
            sender = creator or last_modified_by
            if sender:
                return {
                    "sender": sender,
                    "sender_source": "office_metadata",
                    "office_creator": creator,
                    "office_last_modified_by": last_modified_by,
                }

        # 3) PDF Author
        if ext == ".pdf":
            pdf_author = self._extract_pdf_author(file_path)
            if pdf_author:
                return {
                    "sender": pdf_author,
                    "sender_source": "pdf_metadata",
                    "office_creator": None,
                    "office_last_modified_by": None,
                }

        return {
            "sender": None,
            "sender_source": "unknown",
            "office_creator": None,
            "office_last_modified_by": None,
        }

    def _sender_from_filename(self, stem: str) -> Optional[str]:
        m = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9·\-]{1,24})[\-—_].+", stem)
        if m:
            value = m.group(1).strip()
            if value and len(value) >= 2:
                return value
        return None

    def _extract_office_author(self, file_path: Path) -> tuple[Optional[str], Optional[str]]:
        creator = None
        last_modified_by = None
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                if "docProps/core.xml" not in zf.namelist():
                    return None, None
                xml = zf.read("docProps/core.xml").decode("utf-8", errors="ignore")
                m_creator = re.search(r"<dc:creator>(.*?)</dc:creator>", xml)
                m_modified = re.search(r"<cp:lastModifiedBy>(.*?)</cp:lastModifiedBy>", xml)
                creator = (m_creator.group(1).strip() if m_creator else None) or None
                last_modified_by = (m_modified.group(1).strip() if m_modified else None) or None
        except Exception:
            return None, None
        return creator, last_modified_by

    def _extract_pdf_author(self, file_path: Path) -> Optional[str]:
        try:
            with open(file_path, "rb") as f:
                head = f.read(65536)
            m = re.search(rb"/Author\s*\(([^)]*)\)", head)
            if m:
                value = m.group(1).decode("utf-8", errors="ignore").strip()
                return value or None
        except Exception:
            return None
        return None

    def _write_reports(self, source_dir: str, entries: List[Dict[str, Any]]) -> Dict[str, str]:
        report_dir = self.organize_root / "_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"folder_catalog_{ts}"
        json_path = report_dir / f"{base_name}.json"
        md_path = report_dir / f"{base_name}.md"

        payload = {
            "generated_at": datetime.now().isoformat(),
            "source_dir": source_dir,
            "total": len(entries),
            "success": sum(1 for e in entries if e.get("organized")),
            "failed": sum(1 for e in entries if not e.get("organized")),
            "entries": entries,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        lines = [
            "# 文件夹自动归纳清单",
            "",
            f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 来源目录: {source_dir}",
            f"- 总文件数: {len(entries)}",
            f"- 成功: {sum(1 for e in entries if e.get('organized'))}",
            f"- 失败: {sum(1 for e in entries if not e.get('organized'))}",
            "",
            "| 文件名 | 发送者/来源人 | 识别来源 | 归纳目录 | 结果 |",
            "|---|---|---|---|---|",
        ]

        for item in entries:
            file_name = self._md_escape(item.get("file_name", ""))
            sender = self._md_escape(item.get("sender", "未知"))
            sender_source = self._md_escape(item.get("sender_source", "unknown"))
            folder = self._md_escape(item.get("suggested_folder", ""))
            status = "✅" if item.get("organized") else f"❌ {self._md_escape(item.get('error', ''))}"
            lines.append(f"| {file_name} | {sender} | {sender_source} | {folder} | {status} |")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return {
            "json": str(json_path),
            "markdown": str(md_path),
        }

    def _md_escape(self, text: str) -> str:
        if text is None:
            return ""
        return str(text).replace("|", "\\|").replace("\n", " ")
