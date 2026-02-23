#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件格式转换助手 - 支持多种文档格式相互转换
支持: Word (DOCX/DOC), PDF, Excel (XLSX/XLS), PowerPoint (PPTX), Markdown, TXT, HTML
"""

import os
import sys
from typing import Dict, Optional, Any
from datetime import datetime


class FileConverter:
    """文件格式转换器"""

    # 支持的格式
    SUPPORTED_FORMATS = {"pdf", "docx", "txt", "md", "html"}

    @staticmethod
    def _get_output_path(source_path: str, target_format: str, output_dir: str, output_name: str = "") -> str:
        """生成输出文件路径"""
        if not output_name:
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            output_name = base_name

        output_name = output_name.replace(".", "_")  # 去除名称中的点
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_name}_{timestamp}.{target_format}"
        return os.path.join(output_dir, filename)

    @staticmethod
    def convert(source_path: str, target_format: str, output_dir: str = ".", output_name: str = "") -> Dict:
        """
        转换文件格式

        Args:
            source_path: 源文件路径
            target_format: 目标格式 (pdf/docx/txt/md/html)
            output_dir: 输出目录
            output_name: 输出文件名（不含扩展名）

        Returns:
            {success: bool, output_path: str, message: str, ...}
        """
        if not os.path.exists(source_path):
            return {"success": False, "error": f"源文件不存在: {source_path}"}

        source_ext = os.path.splitext(source_path)[1].lower().lstrip(".")
        target_format = target_format.lower()

        if target_format not in FileConverter.SUPPORTED_FORMATS:
            return {
                "success": False,
                "error": f"不支持的目标格式: {target_format}。支持: {', '.join(FileConverter.SUPPORTED_FORMATS)}",
            }

        output_path = FileConverter._get_output_path(source_path, target_format, output_dir, output_name)

        # 根据源格式分发处理
        try:
            if source_ext in ["doc", "docx"]:
                return FileConverter._from_word(source_path, target_format, output_path)
            elif source_ext == "pdf":
                return FileConverter._from_pdf(source_path, target_format, output_path)
            elif source_ext in ["xls", "xlsx"]:
                return FileConverter._from_excel(source_path, target_format, output_path)
            elif source_ext in ["ppt", "pptx"]:
                return FileConverter._from_ppt(source_path, target_format, output_path)
            elif source_ext in ["md", "txt", "text"]:
                return FileConverter._from_text(source_path, target_format, output_path)
            elif source_ext == "html":
                return FileConverter._from_html(source_path, target_format, output_path)
            else:
                return {
                    "success": False,
                    "error": f"不支持的源格式: .{source_ext}。支持 Word/PDF/Excel/PowerPoint/Markdown/TXT/HTML",
                }
        except Exception as e:
            import traceback

            traceback.print_exc()
            return {"success": False, "error": f"转换失败: {str(e)}"}

    @staticmethod
    def _from_word(source_path: str, target_format: str, output_path: str) -> Dict:
        """从 Word 转换"""
        from document_reader import DocumentReader
        from document_generator import save_docx, save_pdf

        try:
            # 读取 Word 内容
            doc_data = DocumentReader.read_word(source_path)
            if not doc_data.get("success"):
                return {"success": False, "error": f"读取 Word 失败: {doc_data.get('error', 'Unknown')}"}

            # 构建 Markdown 文本
            md_text = FileConverter._build_markdown_from_doc_data(doc_data)

            # 根据目标格式输出
            if target_format == "docx":
                # 已经是 DOCX，复制
                import shutil

                shutil.copy2(source_path, output_path)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已复制到: {os.path.basename(output_path)}",
                }
            elif target_format == "pdf":
                save_pdf(
                    md_text,
                    title=doc_data.get("file_name", "Document"),
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 PDF: {os.path.basename(output_path)}",
                }
            elif target_format == "txt":
                # 提取纯文本
                text_content = DocumentReader._extract_text_from_doc_data(doc_data)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 TXT: {os.path.basename(output_path)}",
                }
            elif target_format == "md":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md_text)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Markdown: {os.path.basename(output_path)}",
                }
            elif target_format == "html":
                html = FileConverter._md_to_html(md_text)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 HTML: {os.path.basename(output_path)}",
                }

        except ImportError as e:
            return {
                "success": False,
                "error": f"缺少依赖库: {e}。请安装: pip install python-docx reportlab",
            }

    @staticmethod
    def _from_pdf(source_path: str, target_format: str, output_path: str) -> Dict:
        """从 PDF 转换"""
        try:
            from document_generator import save_docx, save_pdf

            # 1. 尝试用 pdf2docx 转换
            if target_format == "docx":
                try:
                    from pdf2docx import convert

                    convert(source_path, output_path)
                    return {
                        "success": True,
                        "output_path": output_path,
                        "message": f"✅ 已转换为 Word: {os.path.basename(output_path)}",
                    }
                except ImportError:
                    return {
                        "success": False,
                        "error": "缺少 pdf2docx 库。请安装: pip install pdf2docx",
                    }

            # 2. 用 PyPDF2 提取文本后转换
            text_content = FileConverter._extract_text_from_pdf(source_path)
            if target_format == "txt":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 TXT: {os.path.basename(output_path)}",
                }
            elif target_format == "md":
                md_text = f"# PDF 导入文档\n\n{text_content}"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md_text)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Markdown: {os.path.basename(output_path)}",
                }
            elif target_format == "docx":
                save_docx(
                    text_content, title="PDF 转 Word", output_dir=os.path.dirname(output_path), filename=os.path.basename(output_path)
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Word: {os.path.basename(output_path)}",
                }
            elif target_format == "html":
                html = FileConverter._md_to_html(text_content)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 HTML: {os.path.basename(output_path)}",
                }
            elif target_format == "pdf":
                import shutil

                shutil.copy2(source_path, output_path)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已复制到: {os.path.basename(output_path)}",
                }

        except Exception as e:
            return {"success": False, "error": f"PDF 转换失败: {str(e)}"}

    @staticmethod
    def _from_excel(source_path: str, target_format: str, output_path: str) -> Dict:
        """从 Excel 转换"""
        try:
            import pandas as pd

            df = pd.read_excel(source_path)
            text_content = f"# Excel 导入数据\n\n```\n{df.to_string()}\n```"

            if target_format == "txt":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 TXT: {os.path.basename(output_path)}",
                }
            elif target_format == "md":
                # 生成 Markdown 表格
                md_text = f"# Excel 导入数据\n\n{df.to_markdown(index=False)}"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md_text)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Markdown: {os.path.basename(output_path)}",
                }
            elif target_format == "docx":
                from document_generator import save_docx

                save_docx(
                    text_content,
                    title="Excel 转 Word",
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Word: {os.path.basename(output_path)}",
                }
            elif target_format == "pdf":
                from document_generator import save_pdf

                save_pdf(
                    text_content,
                    title="Excel 转 PDF",
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 PDF: {os.path.basename(output_path)}",
                }
            elif target_format == "html":
                html = df.to_html()
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"<html><body>{html}</body></html>")
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 HTML: {os.path.basename(output_path)}",
                }

        except ImportError:
            return {"success": False, "error": "缺少 pandas 库。请安装: pip install pandas openpyxl"}

    @staticmethod
    def _from_ppt(source_path: str, target_format: str, output_path: str) -> Dict:
        """从 PowerPoint 转换"""
        try:
            from document_reader import DocumentReader

            ppt_data = DocumentReader.read_ppt(source_path)
            if not ppt_data.get("success"):
                return {"success": False, "error": f"读取 PPT 失败: {ppt_data.get('error', 'Unknown')}"}

            # 构建文本
            text_content = f"# {ppt_data.get('title', 'Presentation')}\n\n"
            for slide in ppt_data.get("slides", []):
                text_content += f"## 幻灯片 {slide['index'] + 1}: {slide.get('title', '无标题')}\n\n"
                for item in slide.get("content", []):
                    text_content += f"- {item}\n"
                if slide.get("notes"):
                    text_content += f"\n*备注: {slide['notes']}*\n"
                text_content += "\n---\n\n"

            if target_format == "txt":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 TXT: {os.path.basename(output_path)}",
                }
            elif target_format == "md":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Markdown: {os.path.basename(output_path)}",
                }
            elif target_format == "docx":
                from document_generator import save_docx

                save_docx(
                    text_content,
                    title=ppt_data.get("title", "Presentation"),
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Word: {os.path.basename(output_path)}",
                }
            elif target_format == "pdf":
                from document_generator import save_pdf

                save_pdf(
                    text_content,
                    title=ppt_data.get("title", "Presentation"),
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 PDF: {os.path.basename(output_path)}",
                }
            elif target_format == "html":
                html = FileConverter._md_to_html(text_content)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 HTML: {os.path.basename(output_path)}",
                }

        except ImportError:
            return {"success": False, "error": "缺少 python-pptx 库。请安装: pip install python-pptx"}

    @staticmethod
    def _from_text(source_path: str, target_format: str, output_path: str) -> Dict:
        """从 TXT / Markdown 转换"""
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            if target_format == "txt" or target_format == "md":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 {target_format.upper()}: {os.path.basename(output_path)}",
                }
            elif target_format == "docx":
                from document_generator import save_docx

                title = os.path.splitext(os.path.basename(source_path))[0]
                save_docx(
                    text_content,
                    title=title,
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Word: {os.path.basename(output_path)}",
                }
            elif target_format == "pdf":
                from document_generator import save_pdf

                title = os.path.splitext(os.path.basename(source_path))[0]
                save_pdf(
                    text_content,
                    title=title,
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 PDF: {os.path.basename(output_path)}",
                }
            elif target_format == "html":
                html = FileConverter._md_to_html(text_content)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 HTML: {os.path.basename(output_path)}",
                }

        except Exception as e:
            return {"success": False, "error": f"文本转换失败: {str(e)}"}

    @staticmethod
    def _from_html(source_path: str, target_format: str, output_path: str) -> Dict:
        """从 HTML 转换"""
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            if target_format == "html":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已复制为 HTML: {os.path.basename(output_path)}",
                }
            elif target_format in ["txt", "md"]:
                # 简单的 HTML 到 Markdown 转换
                text_content = FileConverter._html_to_text(html_content)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 {target_format.upper()}: {os.path.basename(output_path)}",
                }
            elif target_format == "docx":
                from document_generator import save_docx

                text_content = FileConverter._html_to_text(html_content)
                save_docx(
                    text_content,
                    title="HTML 转 Word",
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 Word: {os.path.basename(output_path)}",
                }
            elif target_format == "pdf":
                from document_generator import save_pdf

                text_content = FileConverter._html_to_text(html_content)
                save_pdf(
                    text_content,
                    title="HTML 转 PDF",
                    output_dir=os.path.dirname(output_path),
                    filename=os.path.basename(output_path),
                )
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"✅ 已转换为 PDF: {os.path.basename(output_path)}",
                }

        except Exception as e:
            return {"success": False, "error": f"HTML 转换失败: {str(e)}"}

    # ===== 辅助方法 =====

    @staticmethod
    def _extract_text_from_pdf(pdf_path: str) -> str:
        """从 PDF 提取文本"""
        try:
            from PyPDF2 import PdfReader

            text = ""
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            return "[需要 PyPDF2：pip install PyPDF2]"

    @staticmethod
    def _build_markdown_from_doc_data(doc_data: Dict) -> str:
        """从文档数据结构构建 Markdown"""
        md = f"# {doc_data.get('file_name', 'Document')}\n\n"
        for para_data in doc_data.get("paragraphs", []):
            para = para_data.get("text", "")
            if para_data.get("level") == 1:
                md += f"## {para}\n\n"
            elif para_data.get("level") == 2:
                md += f"### {para}\n\n"
            else:
                md += f"{para}\n\n"

        # 追加表格（简单 Markdown 表格）
        for table in doc_data.get("tables", []):
            if not table:
                continue
            header = table[0]
            md += "| " + " | ".join([str(c) if c is not None else "" for c in header]) + " |\n"
            md += "| " + " | ".join(["---" for _ in header]) + " |\n"
            for row in table[1:]:
                md += "| " + " | ".join([str(c) if c is not None else "" for c in row]) + " |\n"
            md += "\n"
        return md

    @staticmethod
    def _md_to_html(md_text: str) -> str:
        """简单的 Markdown 到 HTML 转换"""
        try:
            import markdown

            return f"<html><head><meta charset='utf-8'></head><body>{markdown.markdown(md_text)}</body></html>"
        except ImportError:
            # 简单降级版本
            html = md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html = html.replace("\n# ", "\n<h1>").replace("</h1>\n", "</h1>\n")
            html = f"<html><body>{html}</body></html>"
            return html

    @staticmethod
    def _html_to_text(html_content: str) -> str:
        """简单的 HTML 到文本转换"""
        try:
            from html.parser import HTMLParser

            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []

                def handle_data(self, data):
                    if data.strip():
                        self.text.append(data.strip())

            extractor = HTMLTextExtractor()
            extractor.feed(html_content)
            return "\n".join(extractor.text)
        except Exception:
            return html_content.replace("<", "").replace(">", "")
