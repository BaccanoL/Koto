#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文档智能反馈系统 - 完整闭环
1. 读取文档 → 2. AI分析 → 3. 应用修改 或 自动标注
"""

import os
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime


class DocumentFeedbackSystem:
    """文档智能反馈系统"""
    
    def __init__(self, gemini_client=None, default_model_id: str = "gemini-3-pro-preview"):
        """
        Args:
            gemini_client: Gemini API客户端实例
            default_model_id: 默认优先模型
        """
        self.client = gemini_client
        self.default_model_id = default_model_id
        from web.document_reader import DocumentReader
        from web.document_editor import DocumentEditor
        from web.document_annotator import DocumentAnnotator
        
        self.reader = DocumentReader()
        self.editor = DocumentEditor()
        self.annotator = DocumentAnnotator(annotation_mode="comment")  # 默认使用气泡批注
    
        self._model_cache = None
    def analyze_and_suggest(
        self,
        file_path: str,
        user_requirement: str = "",
        model_id: str = "gemini-3-flash-preview"
    ) -> Dict[str, Any]:
        """
        分析文档并给出AI修改建议
        
        Args:
            file_path: 文档路径
            user_requirement: 用户需求（例如："请优化标题，让它更专业"）
            model_id: 使用的模型ID
        
        Returns:
            {
                "success": True,
                "original_content": {...},
                "ai_suggestions": "AI分析文本",
                "modifications": [...],
                "summary": "修改建议摘要"
            }
        """
        # 第1步：读取文档
        print(f"[DocumentFeedback] 📖 读取文档: {os.path.basename(file_path)}")
        doc_data = self.reader.read_document(file_path)
        
        if not doc_data.get("success"):
            return {
                "success": False,
                "error": f"读取文档失败: {doc_data.get('error')}"
            }
        
        # 第2步：格式化给AI
        formatted_content = self.reader.format_for_ai(doc_data)
        
        # 第3步：构建AI提示
        prompt = self._build_analysis_prompt(
            doc_data.get("type"),
            formatted_content,
            user_requirement
        )
        
        # 第4步：调用AI分析
        if not self.client:
            return {
                "success": False,
                "error": "Gemini客户端未初始化"
            }
        
        selected_model, _ = self._select_best_model(model_id)
        print(f"[DocumentFeedback] 🤖 AI分析中...")
        
        try:
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=32000,
                )
            )
            
            ai_response = response.text if response else ""
            if not ai_response and getattr(response, "candidates", None):
                # 尝试从候选中提取文本
                try:
                    parts = response.candidates[0].content.parts
                    ai_response = "".join([getattr(p, "text", "") for p in parts if getattr(p, "text", "")])
                except Exception:
                    ai_response = ""
            
            if not ai_response:
                return {
                    "success": False,
                    "error": "AI分析失败: 模型未返回内容"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"AI分析失败: {str(e)}"
            }
        
        # 第5步：解析AI建议
        print(f"[DocumentFeedback] 📋 解析AI建议...")
        modifications = self.editor.parse_ai_suggestions(ai_response)
        
        # 提取摘要（AI响应中的文字说明部分）
        summary = self._extract_summary(ai_response)
        
        return {
            "success": True,
            "file_path": file_path,
            "doc_type": doc_data.get("type"),
            "original_content": doc_data,
            "ai_suggestions": ai_response,
            "modifications": modifications,
            "modification_count": len(modifications),
            "summary": summary
        }
    
    def apply_suggestions(
        self,
        file_path: str,
        modifications: list
    ) -> Dict[str, Any]:
        """
        应用AI建议，生成新文档
        
        Args:
            file_path: 原文档路径
            modifications: 修改指令列表
        
        Returns:
            {
                "success": True,
                "new_file_path": "...",
                "applied_count": 5
            }
        """
        print(f"[DocumentFeedback] ✏️ 应用修改...")
        
        # 根据文件类型调用对应的编辑器
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.ppt', '.pptx']:
            result = self.editor.edit_ppt(file_path, modifications)
        elif ext in ['.doc', '.docx']:
            result = self.editor.edit_word(file_path, modifications)
        elif ext in ['.xls', '.xlsx']:
            result = self.editor.edit_excel(file_path, modifications)
        else:
            return {
                "success": False,
                "error": f"不支持的文件类型: {ext}"
            }
        
        if result.get("success"):
            print(f"[DocumentFeedback] ✅ 修改完成: {os.path.basename(result['file_path'])}")
        
        return result
    
    def full_feedback_loop(
        self,
        file_path: str,
        user_requirement: str = "",
        auto_apply: bool = True
    ) -> Dict[str, Any]:
        """
        完整反馈闭环：读取 → 分析 → 修改
        
        Args:
            file_path: 文档路径
            user_requirement: 用户需求
            auto_apply: 是否自动应用修改
        
        Returns:
            完整的处理结果
        """
        print("=" * 60)
        print("🔄 启动文档智能反馈系统")
        print("=" * 60)
        
        # 第1步：分析并获取建议
        analysis_result = self.analyze_and_suggest(file_path, user_requirement)
        
        if not analysis_result.get("success"):
            return analysis_result
        
        print(f"\n📊 分析结果:")
        print(f"   修改建议数: {analysis_result['modification_count']}")
        print(f"   摘要: {analysis_result['summary'][:100]}...")
        
        # 第2步：应用修改（如果启用）
        if auto_apply and analysis_result['modification_count'] > 0:
            apply_result = self.apply_suggestions(
                file_path,
                analysis_result['modifications']
            )
            
            return {
                "success": True,
                "analysis": analysis_result,
                "edit_result": apply_result,
                "new_file_path": apply_result.get("file_path"),
                "applied_count": apply_result.get("applied_count", 0)
            }
        else:
            return {
                "success": True,
                "analysis": analysis_result,
                "message": "仅分析，未应用修改"
            }
    
    def _build_analysis_prompt(
        self,
        doc_type: str,
        formatted_content: str,
        user_requirement: str
    ) -> str:
        """构建AI分析提示"""
        
        base_prompt = f"""你是Koto文档智能分析助手。请分析以下{doc_type.upper()}文档，并给出改进建议。

## 文档内容
{formatted_content}

## 用户需求
{user_requirement if user_requirement else "请全面审查文档，提供专业的优化建议"}

## ⚠️ 特别注意
**请特别关注以下内容，不要遗漏：**
1. **格式变化部分**：包含 **粗体**、*斜体*、[颜色标记] 等格式的文本（文档中标记为"[此段落有格式变化]"）
2. **图标和特殊字符**：如●、★、✓、→、•等符号
3. **字体大小变化**：标题、小字注释等不同字号的内容
4. **混合内容**：既有文字又有图标的部分，例如"● 要点一"、"→ 步骤二"
5. **中英文混排**：包含英文术语的中文句子
6. **数字和单位**：如"10px"、"100%"、"3.5倍"等

## 任务要求
1. 仔细阅读文档内容（**包括所有格式标记的部分**）
2. 分析每个部分的质量和准确性（**尤其是有格式变化的段落**）
3. 给出具体的修改建议（**确保覆盖所有内容，不遗漏图标和特殊格式部分**）

## 输出格式
请按以下JSON格式输出修改建议：

```json
{{
  "summary": "整体分析和建议摘要",
  "modifications": [
"""
        
        if doc_type == "ppt":
            base_prompt += """    {
      "slide_index": 0,
      "action": "update_title",
      "target": "title",
      "content": "修改后的标题",
      "reason": "修改原因"
    },
    {
      "slide_index": 1,
      "action": "update_content",
      "target": "content",
      "position": 0,
      "content": "修改后的内容点",
      "reason": "修改原因"
    },
    {
      "slide_index": 2,
      "action": "add_content",
      "target": "content",
      "content": "新增的要点",
      "reason": "添加原因"
    }
  ]
}
```

可用的action类型：
- update_title: 修改标题
- update_content: 修改内容点（需要position）
- add_content: 添加新内容点
- delete_content: 删除内容点（需要position）
"""
        
        elif doc_type == "word":
            base_prompt += """    {
      "paragraph_index": 0,
      "action": "update",
      "content": "修改后的段落内容",
      "reason": "修改原因"
    },
    {
      "paragraph_index": 3,
      "action": "insert",
      "content": "新插入的段落",
      "reason": "插入原因"
    }
  ]
}
```

可用的action类型：
- update: 修改现有段落
- insert: 插入新段落
- delete: 删除段落
"""
        
        elif doc_type == "excel":
            base_prompt += """    {
      "sheet_name": "Sheet1",
      "row": 0,
      "col": 0,
      "action": "update",
      "value": "新值",
      "reason": "修改原因"
    }
  ]
}
```

可用的action类型：
- update: 修改单元格
- insert_row: 插入行
- delete_row: 删除行
"""
        
        base_prompt += """

注意：
- 只输出JSON，不要其他解释
- modifications数组中每个修改都要有明确的理由
- 索引从0开始
- 保持专业和准确
"""
        
        return base_prompt
    
    def _extract_summary(self, ai_response: str) -> str:
        """从AI响应中提取摘要"""
        import json
        import re
        
        try:
            # 尝试提取JSON中的summary字段
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("summary", "AI建议已生成")
            
            # 提取非JSON部分作为摘要
            summary = re.sub(r'```json.*?```', '', ai_response, flags=re.DOTALL).strip()
            return summary[:200] if summary else "AI建议已生成"
        
        except Exception:
            return "AI建议已生成"

    def _list_available_models(self) -> List[Dict[str, str]]:
        """列出当前 API 可用模型（仅包含支持 generateContent 的模型）"""
        if self._model_cache is not None:
            return self._model_cache
        if not self.client:
            self._model_cache = []
            return self._model_cache
        try:
            models = []
            for m in self.client.models.list():
                supported = getattr(m, "supported_generation_methods", []) or []
                if "generateContent" not in supported:
                    continue
                name = getattr(m, "name", "")
                display_name = getattr(m, "display_name", "")
                base_name = name.split("/")[-1] if name else ""
                if base_name:
                    models.append({
                        "name": base_name,
                        "display_name": display_name or base_name
                    })
            self._model_cache = models
            return models
        except Exception:
            self._model_cache = []
            return self._model_cache

    def _select_best_model(self, preferred: str) -> (str, List[Dict[str, str]]):
        """根据可用模型选择最高质量模型（优先使用 preferred）"""
        models = self._list_available_models()
        available = {m["name"] for m in models}

        if not models:
            fallback = "gemini-2.5-pro" if preferred != "gemini-2.5-pro" else preferred
            return fallback, models

        priority = [
            preferred,
            "gemini-3-flash-preview",
            "gemini-3-pro-preview",
            "gemini-3-flash",
            "gemini-3-pro",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-001",
        ]

        for name in priority:
            if name in available:
                return name, models

        # 若无法获取列表，或列表为空，则回退为用户指定模型
        return preferred, models

    def _format_model_table(self, models: List[Dict[str, str]]) -> str:
        """生成可用模型表格（Markdown）"""
        if not models:
            return "（暂时无法获取可用模型列表）"

        rows = ["| 模型ID | 显示名称 |", "| --- | --- |"]
        for m in models:
            rows.append(f"| {m['name']} | {m['display_name']} |")
        return "\n".join(rows)
    
    # ==================== 文档自动标注功能 ====================
    
    def _analyze_chunk_for_annotations(
        self,
        chunk: str,
        doc_type: str,
        user_requirement: str,
        model_id: str,
        chunk_index: int,
        total_chunks: int,
        full_doc_context: str = "",
        max_retries: int = 3
    ) -> Optional[List[Dict[str, str]]]:
        """
        分析单个分段并返回标注列表（严格顺序执行，上一段完成后再处理下一段）
        """
        base_context = user_requirement + f"\n(注：这是文档的第{chunk_index}部分，共{total_chunks}部分)"
        def _call_model(contents: str):
            from google.genai import types
            return self.client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=12000,
                )
            )

        def _call_with_timeout(contents: str, timeout_seconds: int = 120):
            import threading
            result_holder = {"response": None, "error": None}

            def _runner():
                try:
                    print(f"[DocumentFeedback] 🌐 调用AI API (超时: {timeout_seconds}s)...")
                    result_holder["response"] = _call_model(contents)
                    print(f"[DocumentFeedback] ✅ AI响应成功")
                except Exception as e:
                    print(f"[DocumentFeedback] ❌ AI调用异常: {e}")
                    result_holder["error"] = e

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join(timeout_seconds)
            if t.is_alive():
                print(f"[DocumentFeedback] ⏱️ AI调用超时 ({timeout_seconds}s)")
                return None, TimeoutError(f"Chunk timeout after {timeout_seconds}s")
            if result_holder["error"]:
                return None, result_holder["error"]
            return result_holder["response"], None

        all_annotations: List[Dict[str, str]] = []
        seen_texts = set()
        # 质量优先：确保多轮审阅，避免“只跑一轮”导致遗漏
        if len(chunk) <= 1800:
            max_rounds = 2
        else:
            max_rounds = 3
        
        min_new_per_round = 3

        for round_idx in range(1, max_rounds + 1):
            print(f"[DocumentFeedback] 🔁 第{chunk_index}段进入第{round_idx}/{max_rounds}轮审阅")
            # 第一轮注重全面扫描，如果只有一轮，则直接要求全面
            current_focus_prompt = ""
            if round_idx == 1:
                target_count = max(5, len(chunk) // 200) # 动态计算目标数量，每200字1个
                current_focus_prompt = f"\n\n本轮重点：全面扫描，找出所有明显的语病、翻译腔和拗口表达。目标约{target_count}处修改。"
            else:
                current_focus_prompt = "\n\n本轮重点：查漏补缺，关注上一轮可能忽略的逻辑连接词、标点符号和深层润色。目标约5-10处补充修改。"

            prompt = self._build_annotation_prompt(
                doc_type,
                chunk,
                base_context + f"\n\n这是第{round_idx}/{max_rounds}轮审阅。请找出真正需要修改的问题，本轮目标约{target_count if round_idx == 1 else 10}处修改。" + current_focus_prompt,
                full_doc_context=full_doc_context
            )
            strict_prompt = self._build_annotation_prompt(
                doc_type,
                chunk,
                base_context + f"\n\n请务必仅输出JSON数组，本轮最多15条；若确实没有问题再返回空数组。"
            )

            for retry in range(max_retries):
                try:
                    response, err = _call_with_timeout(prompt)  # 使用默认180秒超时
                    if err:
                        raise err
                    if response and response.text:
                        annotations = self._parse_annotation_response(response.text)
                        if annotations:
                            # 二次快速检测：仅过滤掉"原文在文档中完全找不到"的幻觉项
                            try:
                                from web.document_validator import DocumentValidator
                                validation = DocumentValidator.validate_modifications(chunk, annotations)
                                if validation.get('risk_level') == 'HIGH':
                                    # 只过滤真正找不到原文的项（幻觉），不过滤其他 warning
                                    rejected_indices = set()
                                    for issue in validation.get('issues', []):
                                        import re
                                        m = re.match(r"#(\d+):\s*原文未找到", issue)
                                        if m:
                                            rejected_indices.add(int(m.group(1)) - 1)
                                    
                                    if rejected_indices:
                                        before = len(annotations)
                                        annotations = [a for i, a in enumerate(annotations) if i not in rejected_indices]
                                        print(f"[DocumentFeedback] 🛡️ 二次检测: 过滤 {before - len(annotations)} 条幻觉项，保留 {len(annotations)} 条")
                            except Exception as e:
                                print(f"[DocumentFeedback] ⚠️ 二次检测跳过: {e}")
                            
                            new_items = []
                            for item in annotations:
                                text = (item.get("原文片段") or "").strip()
                                if text and text not in seen_texts:
                                    seen_texts.add(text)
                                    new_items.append(item)
                            all_annotations.extend(new_items)
                            if len(new_items) < min_new_per_round:
                                if round_idx < max_rounds:
                                    print(f"[DocumentFeedback] ℹ️ 第{chunk_index}段第{round_idx}轮新增较少({len(new_items)}条)，继续下一轮查漏")
                                    break
                                return all_annotations
                            break
                        if retry < max_retries - 1:
                            prompt = strict_prompt
                            continue
                        return all_annotations
                    if retry < max_retries - 1:
                        prompt = strict_prompt
                        continue
                except Exception as e:
                    error_msg = str(e)[:100]
                    if retry < max_retries - 1:
                        print(f"[DocumentFeedback] ⚠️ 第{chunk_index}段第{round_idx}轮失败，准备重试: {error_msg}")
                        continue
                    print(f"[DocumentFeedback] ❌ 第{chunk_index}段第{round_idx}轮失败（已重试{max_retries}次）: {error_msg}")
                    return self._fallback_annotations_from_chunk(chunk)

        return all_annotations

    @staticmethod
    def _fallback_annotations_from_chunk(chunk: str) -> List[Dict[str, str]]:
        """AI失败时的本地兜底标注 - 优化版（更具体的建议+均匀分布）"""
        import re
        annotations = []
        
        # ==================== Helper: 生成具体的修改建议 ====================
        def suggest_remove_bei(match_obj, original_text):
            """去掉被动语态：被X的 → X的"""
            verb = match_obj.group(1) if match_obj.lastindex >= 1 else ""
            # 提取完整片段
            full_match = match_obj.group(0)
            new_text = full_match.replace("被", "", 1)
            return {
                "原文片段": full_match,
                "修改建议": f"去除被动语态",
                "修改后文本": new_text,
                "理由": "去除被动语态，使表意更直接"
            }
        
        def suggest_remove_jinxing(match_obj, original_text):
            """去掉名词化：对X进行Y → YX"""
            obj = match_obj.group(1) if match_obj.lastindex >= 1 else ""
            action = match_obj.group(2) if match_obj.lastindex >= 2 else "处理"
            new_text = f"{action}{obj}"
            return {
                "原文片段": match_obj.group(0),
                "修改建议": "简化名词化表达",
                "修改后文本": new_text,
                "理由": "避免名词化表达，更符合中文习惯"
            }
        
        def suggest_simplify_tongguo(match_obj, original_text):
            """简化通过：通过X来Y → 用X或XY"""
            method = match_obj.group(1) if match_obj.lastindex >= 1 else ""
            if method:
                new_text = f"用{method}"
                return {
                    "原文片段": match_obj.group(0),
                    "修改建议": "简化连接词",
                    "修改后文本": new_text,
                    "理由": "删除冗余的连接词，表意更简洁"
                }
            return {
                "原文片段": match_obj.group(0),
                "修改建议": "删除冗余连接词",
                "修改后文本": "直接表达",
                "理由": "删除'通过...来'，直接表达"
            }
        
        def suggest_remove_suo(match_obj, original_text):
            """去掉所字结构：所X的Y → X的Y"""
            verb = match_obj.group(1) if match_obj.lastindex >= 1 else ""
            full_match = match_obj.group(0)
            new_text = full_match.replace("所", "", 1)
            return {
                "原文片段": full_match,
                "修改建议": "去除冗余的'所'字结构",
                "修改后文本": new_text,
                "理由": "去除冗余的'所'字结构，简化表达"
            }
        
        # ==================== 优化策略1：被动句问题 ====================
        # 被+动词 → 去掉"被"
        passive_patterns = [
            (r'被(\w{2,6})(?:的|了|着)', suggest_remove_bei),
            (r'被(\w{2,4})呈现', suggest_remove_bei),
            (r'被(\w{2,4})记录', suggest_remove_bei),
            (r'被(\w{2,4})感知', suggest_remove_bei),
            (r'被(用)为', suggest_remove_bei),  # 新增：被用为
            (r'被(称)为', suggest_remove_bei),  # 新增：被称为
            (r'被(视)为', suggest_remove_bei),  # 新增：被视为
            (r'被(认)为', suggest_remove_bei),  # 新增：被认为
        ]
        for pattern, suggest_func in passive_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 3 <= len(text) <= 15:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略2：名词化问题 ====================
        # 对X进行Y → YX
        nominalization_patterns = [
            (r'对(\w{2,4})进行(\w{2,4})', suggest_remove_jinxing),
            (r'进行(\w{2,4})(?:的)', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化名词化",
                "修改后文本": f"{m.group(1)}的",
                "理由": "避免'进行'的冗余表达"
            }),
            (r'进行了(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化名词化",
                "修改后文本": m.group(1),
                "理由": "去掉'进行了'，直接用动词"
            }),
        ]
        for pattern, suggest_func in nominalization_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 4 <= len(text) <= 12:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略3：冗余转移词 ====================
        # 通过X来Y → 用X或XY
        connector_patterns = [
            (r'通过(\w{2,6})(?:得以|来|以)', suggest_simplify_tongguo),
            (r'从而(\w{2,4})(?:得以|使|让)', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化逻辑连接",
                "修改后文本": f"使{m.group(1)}",
                "理由": "用'使'简化'从而'的表达"
            }),
            (r'由于(\w{2,4})(?:，|，)从而', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化逻辑表达",
                "修改后文本": f"由于{m.group(1)}，因此",
                "理由": "用'因此'或'所以'简化"
            }),
            (r'以便(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "改用更自然的表达",
                "修改后文本": f"为了{m.group(1)}",
                "理由": "'为了'比'以便'更自然"
            }),
        ]
        for pattern, suggest_func in connector_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 4 <= len(text) <= 15:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略4：学术虚词 ====================
        # 影响/作用等 → 具体动词
        abstract_terms = [
            (r'\b影响\b(?!力)', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "替换为具体动词",
                "修改后文本": "（决定/制约/改变/驱动）",
                "理由": "避免使用空泛的学术虚词"
            }),
            (r'\b作用\b(?!域)', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "替换为具体动词",
                "修改后文本": "（驱动/促进/抑制/推动）",
                "理由": "避免使用空泛的学术虚词"
            }),
            (r'\b关系\b', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "具体化表达",
                "修改后文本": "（因果关系/相关性/对应关系）",
                "理由": "用具体的关系类型替代泛指"
            }),
            (r'\b机制\b', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "具体化表达",
                "修改后文本": "（原理/过程/方法/规律）",
                "理由": "用具体概念替代空泛的'机制'"
            }),
            (r'\b因素\b', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "具体化表达",
                "修改后文本": "（条件/参数/变量/要素）",
                "理由": "用具体概念替代空泛的'因素'"
            }),
        ]
        for pattern, suggest_func in abstract_terms:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 2 <= len(text) <= 6:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略5：所字结构 ====================
        # 所+动词+的 → 去掉"所"
        suo_patterns = [
            (r'所(\w{2,4})的', suggest_remove_suo),
            (r'所谓(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "删除冗余修饰",
                "修改后文本": m.group(1),
                "理由": "直接表达，删除'所谓'的冗余修饰"
            }),
        ]
        for pattern, suggest_func in suo_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 3 <= len(text) <= 10:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略6：模糊限定词 ====================
        # 非常/极其等 → 删除或换更强动词
        hedge_patterns = [
            (r'(?:非常|极其|十分|特别)(\w{2,6})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "删除模糊限定词",
                "修改后文本": m.group(1),
                "理由": "直接使用形容词，删除模糊修饰"
            }),
            (r'(?:似乎|好像|仿佛)(\w{2,6})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "改为更确定的表述",
                "修改后文本": f"可能是{m.group(1)}/表明{m.group(1)}",
                "理由": "避免模糊的推测表达"
            }),
        ]
        for pattern, suggest_func in hedge_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)[:12]
                if 3 <= len(text) <= 12:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略7：冗长表达 ====================
        # X之间的Y → X的Y
        redundant_patterns = [
            (r'(\w{2,6})之间(?:的)?', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "去掉冗余的'之间'",
                "修改后文本": f"{m.group(1)}的",
                "理由": "简化冗余的'之间'表达"
            }),
            (r'(\w{2,4})(?:形式|方式|过程)的(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "去除冗余名词",
                "修改后文本": f"{m.group(1)}{m.group(2)}",
                "理由": "删除'形式/方式/过程'等冗余名词"
            }),
        ]
        for pattern, suggest_func in redundant_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 4 <= len(text) <= 15:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略8：消极表述 ====================
        negative_patterns = [
            (r'(?:不|无|没有)(?:能|法|办法)(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "改为正面表述",
                "修改后文本": f"难以{m.group(1)}/尚未{m.group(1)}",
                "理由": "用正面表述替代否定形式"
            }),
            (r'难以(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "改为更自然的表述",
                "修改后文本": f"很难{m.group(1)}",
                "理由": "'很难X'比'难以X'更自然"
            }),
        ]
        for pattern, suggest_func in negative_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)[:10]
                if 3 <= len(text) <= 10:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略9：高频虚词提取 ====================
        freq_words = [
            ('能够', {
                "修改建议": "删除冗余虚词",
                "修改后文本": "（直接用具体动词）",
                "理由": "删除虚词，直接表达动作"
            }),
            ('可以', {
                "修改建议": "根据语境优化",
                "修改后文本": "（删除或换具体动词）",
                "理由": "'可以'往往可以省略或用更具体的动词替代"
            }),
            ('进一步', {
                "修改建议": "改用更自然的表达",
                "修改后文本": "进而/接着/随后",
                "理由": "'进一步'的替代表达更自然"
            }),
        ]
        for word, anno_template in freq_words:
            for match in re.finditer(re.escape(word), chunk):
                # 提取上下文
                start = max(0, match.start() - 3)
                end = min(len(chunk), match.end() + 5)
                context = chunk[start:end].replace('\n', '').strip()
                if len(context) > len(word) and len(context) <= 20:
                    annotations.append({
                        "原文片段": context[:15],
                        "修改建议": anno_template["修改建议"],
                        "修改后文本": anno_template["修改后文本"],
                        "理由": anno_template["理由"]
                    })
                    break  # 每个词最多提取一次上下文
        
        # ==================== 优化策略10：表达冗余检测 ====================
        redundancy_patterns = [
            (r'进行(\w{1,4})(处理|分析|研究|操作|观察|测试|验证)', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "去掉冗余的'进行'",
                "修改后文本": f"{m.group(2)}{m.group(1)}",
                "理由": "'进行'与后面的动词构成冗余"
            }),
            (r'对(\w{1,4})的(分析|研究|处理|观察|理解|认识)', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化冗余结构",
                "修改后文本": f"{m.group(2)}{m.group(1)}",
                "理由": "去除'对...的'冗余结构"
            }),
        ]
        for pattern, suggest_func in redundancy_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 4 <= len(text) <= 12:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 优化策略11：学术翻译常见问题 ====================
        academic_patterns = [
            # "呈现出" → "呈现"
            (r'呈现出(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "去掉冗余的'出'",
                "修改后文本": f"呈现{m.group(1)}",
                "理由": "'呈现出'中的'出'是冗余的"
            }),
            # "显示出" → "显示"
            (r'显示出(\w{2,4})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "去掉冗余的'出'",
                "修改后文本": f"显示{m.group(1)}",
                "理由": "'显示出'中的'出'是冗余的"
            }),
            # "具有...性" → "有...性" 或直接用形容词
            (r'具有(\w{2,4})性', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化表达",
                "修改后文本": f"有{m.group(1)}性",
                "理由": "'具有'可简化为'有'"
            }),
            # "具有...的特征" → "有...特征"
            (r'具有(\w{2,4})的特征', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化表达",
                "修改后文本": f"有{m.group(1)}特征",
                "理由": "简化冗余表达"
            }),
            # "在...方面" 可能是冗余的
            (r'在(\w{2,4})方面', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "考虑删除",
                "修改后文本": f"在{m.group(1)}上",
                "理由": "'在...方面'可能冗余，考虑简化"
            }),
            # "获得了...的" → "获得..."
            (r'获得了(\w{2,4})的', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化表达",
                "修改后文本": f"获得{m.group(1)}",
                "理由": "去掉冗余的'了...的'"
            }),
            # "产生了...的" → "产生..."
            (r'产生了(\w{2,4})的', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "简化表达",
                "修改后文本": f"产生{m.group(1)}",
                "理由": "去掉冗余的'了...的'"
            }),
        ]
        for pattern, suggest_func in academic_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 3 <= len(text) <= 15:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 新增：优化策略12：图标和特殊符号优化 ====================
        # 识别图标和特殊字符，提供优化建议
        icon_patterns = [
            # ●、• 等圆点符号
            (r'[●○◆◇■□▪▫•][\s]*([^\n]{1,30})', lambda m, t: {
                "原文片段": m.group(0)[:20],
                "修改建议": "统一列表符号",
                "修改后文本": f"• {m.group(1)}",
                "理由": "建议使用统一的列表符号'•'，提升文档一致性"
            }),
            # → ← ↑ ↓ 等箭头符号
            (r'[→←↑↓⇒⇐⇑⇓➔➜][\s]*([^\n]{1,30})', lambda m, t: {
                "原文片段": m.group(0)[:20],
                "修改建议": "优化箭头表达",
                "修改后文本": f"→ {m.group(1)}" if m.group(0)[0] in '→⇒➔➜' else f"← {m.group(1)}",
                "理由": "统一箭头符号样式，建议使用'→'或用文字表达"
            }),
            # ★ ☆ 等星号符号
            (r'[★☆✓✔✕✖✗✘][\s]*([^\n]{1,30})', lambda m, t: {
                "原文片段": m.group(0)[:20],
                "修改建议": "规范特殊标记",
                "修改后文本": f"✓ {m.group(1)}" if m.group(0)[0] in '★☆✓✔' else f"✗ {m.group(1)}",
                "理由": "使用标准符号，提升可读性"
            }),
            # 数字序号后跟内容，但格式不规范
            (r'(\d+)[\\.、。\s]{0,2}([^\n]{5,30})', lambda m, t: {
                "原文片段": m.group(0)[:20],
                "修改建议": "规范序号格式",
                "修改后文本": f"{m.group(1)}. {m.group(2).strip()}",
                "理由": "统一使用'数字.'的序号格式"
            }),
        ]
        for pattern, suggest_func in icon_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)[:20]
                if 2 <= len(text) <= 20:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 新增：优化策略13：中英文混排优化 ====================
        # 识别中英文混排，检查空格和格式
        mixed_patterns = [
            # 中文+英文无空格
            (r'([\u4e00-\u9fa5])([A-Za-z]{2,})', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "中英文间加空格",
                "修改后文本": f"{m.group(1)} {m.group(2)}",
                "理由": "中英文混排时建议加空格，提升可读性"
            }),
            # 英文+中文无空格
            (r'([A-Za-z]{2,})([\u4e00-\u9fa5])', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "中英文间加空格",
                "修改后文本": f"{m.group(1)} {m.group(2)}",
                "理由": "中英文混排时建议加空格，提升可读性"
            }),
            # 中文+数字无空格（某些情况）
            (r'([\u4e00-\u9fa5])(\d{2,}[A-Za-z%]+)', lambda m, t: {
                "原文片段": m.group(0),
                "修改建议": "数字单位前加空格",
                "修改后文本": f"{m.group(1)} {m.group(2)}",
                "理由": "中文与带单位数字间建议加空格"
            }),
        ]
        for pattern, suggest_func in mixed_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(0)
                if 2 <= len(text) <= 15:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 新增：优化策略14：格式变化检测 ====================
        # 检测HTML标记（从增强的提取中来的）
        format_patterns = [
            # <b>xxx</b> 粗体标记
            (r'<b>([^<]{2,20})</b>', lambda m, t: {
                "原文片段": m.group(1),
                "修改建议": "检查粗体使用",
                "修改后文本": m.group(1),
                "理由": "此处使用了粗体强调，请确认是否必要"
            }),
            # <i>xxx</i> 斜体标记
            (r'<i>([^<]{2,20})</i>', lambda m, t: {
                "原文片段": m.group(1),
                "修改建议": "检查斜体使用",
                "修改后文本": m.group(1),
                "理由": "此处使用了斜体，确认是否符合文档规范"
            }),
        ]
        for pattern, suggest_func in format_patterns:
            for m in re.finditer(pattern, chunk):
                text = m.group(1) if m.lastindex >= 1 else m.group(0)
                if 2 <= len(text) <= 20:
                    anno = suggest_func(m, text)
                    if isinstance(anno, dict):
                        annotations.append(anno)
        
        # ==================== 去重+均匀分布 ====================
        # 按策略分组统计，确保各类都有代表
        unique_annos = {}  # {原文片段: 完整标注}
        for anno in annotations:
            text = anno.get("原文片段", "").strip()
            # 放宽长度限制：2-25字符（之前是2-20）
            if text and 2 <= len(text) <= 25:
                if text not in unique_annos:
                    unique_annos[text] = anno  # 保留完整的标注对象
        
        # 转换为列表并按长度分布排序（实现均匀分布）
        unique_list = list(unique_annos.values())
        unique_list.sort(key=lambda x: len(x.get("原文片段", "")))
        
        # 大幅提升每个chunk的标注数量：50 → 80
        return unique_list[:80]

    @staticmethod
    def _split_into_chunks_by_paragraphs(formatted_content: str, max_chars: int) -> List[str]:
        """按段落切分，保证每段不超过max_chars"""
        paragraphs = [p for p in formatted_content.split("\n\n") if p.strip()]
        chunks = []
        current = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para) + 2  # 预留分隔符长度
            if current_len + para_len > max_chars and current:
                chunks.append("\n\n".join(current))
                current = [para]
                current_len = para_len
            else:
                current.append(para)
                current_len += para_len

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def analyze_for_annotation_chunked(
        self,
        file_path: str,
        user_requirement: str = "",
        model_id: Optional[str] = None,
        chunk_size: int = 5000,  # 增大分块大小，减少API调用次数 (原: 3000)
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        分段处理大文档标注（适用于超大文档）
        
        Args:
            file_path: Word文档路径
            user_requirement: 用户需求
            model_id: LLM模型ID
            chunk_size: 每段最大字符数
            progress_callback: 进度回调函数 callback(current, total, message)
            
        Returns:
            合并后的标注结果
        """
        effective_model_id = model_id or self.default_model_id
        print(f"[DocumentFeedback] 📖 读取大文档: {os.path.basename(file_path)}")
        
        # 读取文档
        doc_data = self.reader.read_document(file_path)
        if not doc_data.get("success"):
            return {"success": False, "error": f"读取文档失败: {doc_data.get('error')}"}
        
        formatted_content = self.reader.format_for_ai(doc_data)
        total_length = len(formatted_content)
        
        # 如果文档不大，直接使用标准方法
        if total_length <= chunk_size:
            print(f"[DocumentFeedback] 📄 文档较小({total_length}字符)，使用标准处理")
            return self.analyze_for_annotation(file_path, user_requirement, effective_model_id)

        # 分段处理（按段落切分，保证不打断句子）
        print(f"[DocumentFeedback] 📚 文档较大({total_length}字符)，分段处理")
        chunks = self._split_into_chunks_by_paragraphs(formatted_content, chunk_size)
        
        # AI禁用时，对每个chunk应用本地兜底
        if os.getenv("KOTO_DISABLE_AI") == "1":
            print(f"[DocumentFeedback] ⚠️ KOTO_DISABLE_AI=1，使用本地兜底标注（{len(chunks)}段）")
            
            # 第一轮：收集所有候选标注，同时统计每段的信息密度
            all_candidates = []  # [(原文片段, 修改建议, chunk_index, 优先级)]
            chunk_densities = []  # 记录每段的词汇密度
            
            print(f"\n[DocumentFeedback] 📋 第一阶段：收集标注候选...\n")
            for i, chunk in enumerate(chunks):
                chunk_fallback = self._fallback_annotations_from_chunk(chunk)
                density = len(chunk_fallback) / max(1, len(chunk) / 1000)  # 每1000字的标注密度
                chunk_densities.append(density)
                
                for anno in chunk_fallback:
                    all_candidates.append({
                        "原文片段": anno.get("原文片段", ""),
                        "修改建议": anno.get("修改建议", ""),
                        "修改后文本": anno.get("修改后文本", ""),
                        "理由": anno.get("理由", ""),
                        "chunk_idx": i,
                        "density": density
                    })
                
                progress = ((i + 1) / len(chunks)) * 100
                bar_filled = int(10 * (i + 1) / len(chunks))
                bar = '█' * bar_filled + '░' * (10 - bar_filled)
                print(f"\r[DocumentFeedback] 🔍 [{bar}] {i+1}/{len(chunks)} | 密度: {density:.1f}/千字", end="")
            
            print()  # 换行
            
            # 计算平均密度和目标标注数
            avg_density = sum(chunk_densities) / len(chunk_densities) if chunk_densities else 0
            target_count = len(formatted_content) // 1000 * 10
            
            # 第二轮：按密度均衡选择标注
            print(f"\n[DocumentFeedback] ⚖️ 第二阶段：均衡分布（目标{target_count}条）...\n")
            
            # 分chunk选择，确保每段都有适当数量
            target_per_chunk = max(1, target_count // len(chunks))
            selected_annotations = []
            seen_texts = set()
            
            for chunk_idx in range(len(chunks)):
                chunk_candidates = [c for c in all_candidates if c["chunk_idx"] == chunk_idx]
                
                # 去重（放宽长度限制）
                unique_candidates = {}
                for c in chunk_candidates:
                    text = c["原文片段"].strip()
                    if text and 2 <= len(text) <= 20:  # 放宽上限
                        if text not in unique_candidates:
                            unique_candidates[text] = c
                
                # 按密度调整该段应取的数量
                if chunk_idx < 2:
                    # 前两段词汇密集，多取
                    take_count = min(len(unique_candidates), target_per_chunk + 12)
                elif chunk_idx == 2:
                    # 第3段相对稀疏
                    take_count = min(len(unique_candidates), target_per_chunk + 8)
                elif chunk_idx == 3:
                    # 第4段密集
                    take_count = min(len(unique_candidates), target_per_chunk + 12)
                else:
                    # 第5段最后的都取
                    take_count = len(unique_candidates)
                
                # 选择该段的标注
                chunk_selection = list(unique_candidates.values())[:take_count]
                
                for anno in chunk_selection:
                    text = anno["原文片段"].strip()
                    if text not in seen_texts:
                        seen_texts.add(text)
                        selected_annotations.append({
                            "原文片段": anno["原文片段"],
                            "修改建议": anno["修改建议"],
                            "修改后文本": anno.get("修改后文本", ""),
                            "理由": anno.get("理由", "")
                        })
                
                progress = ((chunk_idx + 1) / len(chunks)) * 100
                bar_filled = int(20 * (chunk_idx + 1) / len(chunks))
                bar = '█' * bar_filled + '░' * (20 - bar_filled)
                print(f"\r[DocumentFeedback] 📊 [{bar}] {chunk_idx+1}/{len(chunks)} ({progress:.0f}%) | " +
                      f"本段{len(chunk_selection)}条 | 累计{len(selected_annotations)}条", end="")
            
            print()  # 换行
            
            # 如果标注数不足目标，补充
            if len(selected_annotations) < target_count:
                shortage = target_count - len(selected_annotations)
                for c in all_candidates:
                    if shortage <= 0:
                        break
                    text = c["原文片段"].strip()
                    if text not in seen_texts and 2 <= len(text) <= 25:  # 放宽限制
                        seen_texts.add(text)
                        selected_annotations.append({
                            "原文片段": text,
                            "修改建议": c["修改建议"],
                            "修改后文本": c.get("修改后文本", ""),
                            "理由": c.get("理由", "")
                        })
                        shortage -= 1
            
            return {
                "success": True,
                "file_path": file_path,
                "annotations": selected_annotations[:target_count],
                "summary": f"本地兜底分{len(chunks)}段生成{len(selected_annotations)}条标注（目标：{target_count}条）",
                "annotation_count": len(selected_annotations),
                "chunks_processed": len(chunks),
                "chunk_densities": chunk_densities
            }

        selected_model, available_models = self._select_best_model(effective_model_id)
        model_note = f"模型: {selected_model}"
        if selected_model != effective_model_id:
            model_note += f"（首选: {effective_model_id}，已自动降级）"
        model_table = self._format_model_table(available_models)

        print(f"[DocumentFeedback] � 文档较大({total_length}字符)，分{len(chunks)}段处理")
        print(f"[DocumentFeedback] 🎯 目标标注数: 约{total_length//1000*10}条（每1000字10条）\n")

        # 处理每一段（严格顺序执行，失败自动拆分重试）
        from collections import deque
        all_annotations = []
        seen_texts = set()
        processed = 0
        min_chunk_size = 800
        start_time = time.time()
        queue = deque(chunks)
        total_chunks_initial = len(chunks)

        while queue:
            chunk = queue.popleft()
            processed += 1
            current_total = processed + len(queue)

            elapsed = time.time() - start_time
            progress_pct = (processed / max(1, current_total)) * 100
            bar_length = 20
            bar_filled = int(bar_length * processed / max(1, current_total))
            progress_bar = '█' * bar_filled + '░' * (bar_length - bar_filled)

            print(f"\n[DocumentFeedback] 📊 [{progress_bar}] {processed}/{current_total} ({progress_pct:.0f}%)")
            print(f"[DocumentFeedback] ⏱️ 已用时: {elapsed:.1f}s | 累计{len(all_annotations)}条标注 | 剩余{len(queue)}段")

            annotations = self._analyze_chunk_for_annotations(
                chunk=chunk,
                doc_type=doc_data.get("type"),
                user_requirement=user_requirement,
                model_id=selected_model,
                chunk_index=processed,
                total_chunks=current_total,
                full_doc_context=formatted_content,
                max_retries=2
            )

            if annotations is None:
                if len(chunk) <= min_chunk_size:
                    return {
                        "success": False,
                        "error": f"分段内容过小仍失败（{len(chunk)}字符），请检查网络或API配置后重试",
                        "file_path": file_path
                    }
                sub_chunks = self._split_into_chunks_by_paragraphs(chunk, max(min_chunk_size, len(chunk) // 2))
                if len(sub_chunks) <= 1:
                    return {
                        "success": False,
                        "error": f"分段拆分失败，无法继续处理（{len(chunk)}字符）",
                        "file_path": file_path
                    }
                for sc in reversed(sub_chunks):
                    queue.appendleft(sc)
                print(f"[DocumentFeedback] 🔁 分段失败，已拆分为{len(sub_chunks)}段重试")
                continue

            new_count = 0
            for item in annotations:
                text = (item.get("原文片段") or "").strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    all_annotations.append(item)
                    new_count += 1

            msg = f"已完成 {processed}/{current_total} 段 (本段+{new_count}条，累计{len(all_annotations)}条)"
            print(f"[DocumentFeedback] ✅ 第 {processed} 段完成: 新增 {new_count} 条标注")
            if progress_callback:
                progress_callback(processed, current_total, msg)

        elapsed_total = time.time() - start_time

        print(f"\n[DocumentFeedback] 🎉 分段处理完成")
        print(f"[DocumentFeedback] ⏱️ 总耗时: {elapsed_total:.1f}s")
        print(f"[DocumentFeedback] 📊 共生成{len(all_annotations)}条标注（目标: 约{total_length//1000*10}条）\n")
        
        return {
            "success": True,
            "file_path": file_path,
            "annotations": all_annotations,
            "summary": (
                f"分段顺序处理（初始{total_chunks_initial}段），共生成{len(all_annotations)}条标注（耗时{elapsed_total:.1f}s）。"
                f"{model_note}\n\n可用模型：\n{model_table}"
            ),
            "annotation_count": len(all_annotations),
            "chunks_processed": processed,
            "target_count": total_length // 1000 * 10
        }
    
    def analyze_for_annotation(
        self,
        file_path: str,
        user_requirement: str = "",
        model_id: str = "gemini-3-flash-preview"
    ) -> Dict[str, Any]:
        """
        分析文档，生成标注格式的建议
        改进版：逐段标注，确保覆盖全文
        """
        print(f"[DocumentFeedback] 📖 读取文档: {os.path.basename(file_path)}")
        
        # 第1步：读取文档
        doc_data = self.reader.read_document(file_path)
        if not doc_data.get("success"):
            return {
                "success": False,
                "error": f"读取文档失败: {doc_data.get('error')}"
            }
        
        # 第2步：格式化内容
        formatted_content = self.reader.format_for_ai(doc_data)
        
        # 第3步：按段落切分
        paragraphs = [p.strip() for p in formatted_content.split("\n\n") if p.strip()]
        print(f"[DocumentFeedback] 📝 文档共 {len(paragraphs)} 段，将逐段分析...")
        
        # 如果段落太多（超过20段），建议使用本地兜底（更快）
        if len(paragraphs) > 20:
            print(f"[DocumentFeedback] ⚠️ 文档段落较多（{len(paragraphs)}段），使用本地快速标注模式")
            print(f"[DocumentFeedback] 💡 提示：如需更详细的 AI 分析，请使用较小的文档或分段上传")
            
            all_annotations: List[Dict[str, str]] = []
            seen_texts = set()
            
            # 使用本地兜底处理所有段落
            for idx, para in enumerate(paragraphs):
                if para and len(para) > 20:
                    annotations = self._fallback_annotations_from_chunk(para)
                    for ann in annotations[:5]:  # 每段最多取5条
                        text = (ann.get("原文片段") or "").strip()
                        if text and text not in seen_texts:
                            seen_texts.add(text)
                            all_annotations.append(ann)
                
                # 显示进度
                if (idx + 1) % 10 == 0 or idx == len(paragraphs) - 1:
                    print(f"[DocumentFeedback] 📊 已处理 {idx + 1}/{len(paragraphs)} 段，已收集 {len(all_annotations)} 条标注")
            
            return {
                "success": True,
                "annotations": all_annotations[:150],  # 限制到150条
                "summary": f"使用本地规则快速生成 {len(all_annotations[:150])} 条标注建议（共{len(paragraphs)}段）"
            }
        
        # 第4步：收集所有标注
        all_annotations: List[Dict[str, str]] = []
        seen_texts = set()
        
        # 如果没有AI客户端，直接用本地标注
        if not self.client:
            print(f"[DocumentFeedback] ⚠️ 未配置AI客户端，使用本地兜底标注")
            for idx, para in enumerate(paragraphs):
                if para:
                    annotations = self._fallback_annotations_from_chunk(para)
                    for ann in annotations:
                        text = (ann.get("原文片段") or "").strip()
                        if text and text not in seen_texts:
                            seen_texts.add(text)
                            all_annotations.append(ann)
            return {
                "success": True,
                "annotations": all_annotations[:100],  # 限制到100条
                "summary": f"使用本地规则生成{len(all_annotations)}条标注建议"
            }
        
        # 第5步：逐段用AI标注
        selected_model, available_models = self._select_best_model(model_id)
        
        for para_idx, paragraph in enumerate(paragraphs):
            if not paragraph or len(paragraph) < 20:
                continue  # 跳过太短的段落
            
            print(f"[DocumentFeedback] 🔄 分析第 {para_idx + 1}/{len(paragraphs)} 段...")
            
            # 为每段构建Prompt
            para_prompt = self._build_annotation_prompt(
                doc_data.get("type"),
                paragraph,
                user_requirement + "\n\n请为这一段输出3-8条改进建议。"
            )
            
            try:
                from google.genai import types
                
                response = self.client.models.generate_content(
                    model=selected_model,
                    contents=para_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=2000,
                    )
                )
                
                # 解析标注
                annotations = self._parse_annotation_response(response.text)
                for ann in annotations:
                    text = (ann.get("原文片段") or "").strip()
                    if text and text not in seen_texts and len(text) <= 30:
                        seen_texts.add(text)
                        all_annotations.append(ann)
                
                # 如果这段没有标注到问题，用本地兜底
                if not annotations:
                    fallback = self._fallback_annotations_from_chunk(paragraph)
                    for ann in fallback[:3]:  # 每段最多补充3条本地标注
                        text = (ann.get("原文片段") or "").strip()
                        if text and text not in seen_texts:
                            seen_texts.add(text)
                            all_annotations.append(ann)
                
            except Exception as e:
                print(f"[DocumentFeedback] ⚠️ 第 {para_idx + 1} 段分析失败，使用本地标注: {str(e)[:50]}")
                fallback = self._fallback_annotations_from_chunk(paragraph)
                for ann in fallback[:5]:  # 本地标注最多加5条
                    text = (ann.get("原文片段") or "").strip()
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        all_annotations.append(ann)
        
        # 第6步：返回结果
        summary = f"共标注 {len(all_annotations)} 处需要改进"
        print(f"[DocumentFeedback] ✅ 分析完成，{summary}")
        
        return {
            "success": True,
            "annotations": all_annotations[:150],  # 限制到150条
            "summary": summary
        }
    
    def annotate_document(
        self,
        file_path: str,
        annotations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        应用标注到文档副本
        
        Args:
            file_path: 原Word文档路径
            annotations: 标注列表
                [
                    {"原文片段": "需要修改的文本", "修改建议": "建议修改为..."},
                    ...
                ]
        
        Returns:
            {
                "success": True,
                "original_file": "原文件路径",
                "revised_file": "标注后的文件路径",
                "applied": 成功应用数,
                "failed": 失败数
            }
        """
        print(f"[DocumentFeedback] ✏️ 应用标注...")
        
        result = self.annotator.annotate_document(file_path, annotations)
        
        if result.get("success"):
            print(f"[DocumentFeedback] ✅ 标注完成: {os.path.basename(result.get('revised_file', ''))}")
        
        return result
    
    def full_annotation_loop_streaming(
        self,
        file_path: str,
        user_requirement: str = "",
        task_id: str = None,
        model_id: Optional[str] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ):
        """
        完整标注闭环（流式版本，支持进度反馈和任务取消）
        
        Args:
            file_path: Word文档路径
            user_requirement: 用户需求
            task_id: 任务ID（用于检查是否被取消）
        
        Yields:
            {'stage': 'xxx', 'progress': 0-100, 'message': '...'}
        """
        from datetime import datetime
        import shutil
        from web.task_scheduler import check_task_cancelled
        effective_model_id = model_id or self.default_model_id

        def _is_cancelled() -> bool:
            try:
                if cancel_check and cancel_check():
                    return True
            except Exception:
                pass
            return bool(task_id and check_task_cancelled(task_id))
        
        print("=" * 60)
        print("🔄 启动文档自动标注系统（完整闭环-流式）")
        print("=" * 60)
        
        # ===== Stage 1: 读取文档 =====
        if _is_cancelled():
            yield {
                'stage': 'cancelled',
                'progress': 0,
                'message': '⏸️ 任务已被取消',
                'detail': ''
            }
            return
        
        yield {
            'stage': 'reading',
            'progress': 5,
            'message': f'📖 正在读取文档: {os.path.basename(file_path)}',
            'detail': '解析Word文件结构'
        }
        
        try:
            doc_data = self.reader.read_document(file_path)
            if not doc_data.get("success"):
                yield {
                    'stage': 'error',
                    'progress': 0,
                    'message': f'❌ 读取失败: {doc_data.get("error")}',
                    'detail': ''
                }
                return
            
            total_paras = len(doc_data.get("paragraphs", []))
            total_chars = sum(len(p.get("text", "")) for p in doc_data.get("paragraphs", []))
            
            yield {
                'stage': 'reading_complete',
                'progress': 10,
                'message': '✅ 文档读取完成',
                'detail': f'{total_paras} 段，{total_chars} 字'
            }
        except Exception as e:
            yield {
                'stage': 'error',
                'progress': 0,
                'message': f'❌ 读取错误: {str(e)[:100]}',
                'detail': ''
            }
            return
        
        # ===== Stage 2: 分析生成标注建议 =====
        if _is_cancelled():
            yield {
                'stage': 'cancelled',
                'progress': 0,
                'message': '⏸️ 任务已被取消',
                'detail': '分析前中断'
            }
            return
        
        yield {
            'stage': 'analyzing',
            'progress': 15,
            'message': f'🤖 正在分析文档...',
            'detail': f'使用 AI({effective_model_id}) 检查 {total_paras} 段文本'
        }
        
        chunk_size = 4000 if (self.client and os.getenv("KOTO_DISABLE_AI") != "1") else 10000
        
        # ===== 使用线程 + Queue 实现真正实时进度推送 =====
        import queue as queue_module
        import threading
        
        progress_q = queue_module.Queue()
        result_holder = {"result": None, "error": None}
        last_yield_time = [time.time()]
        
        _SENTINEL = object()  # 线程完成的标记
        
        def on_analysis_progress(current, total, message):
            """进度回调 — 在分析线程中调用，通过 Queue 发送到主线程"""
            progress = 15 + int((current / total) * 35)
            current_time = time.time()
            if current_time - last_yield_time[0] >= 0.3:
                last_yield_time[0] = current_time
                # 将详细进度拼接到 message 中，确保前端看到
                detail_msg = message
                if "已完成" in message:
                     # 简化一下以免过长
                     detail_msg = message.split('(')[0].strip() + "..."
                
                progress_q.put({
                    'stage': 'analyzing',
                    'progress': progress,
                    'message': f'🤖 {message}',  # 直接显示具体进度
                    'detail': message
                })
        
        def run_analysis():
            """在后台线程中运行分析"""
            try:
                result_holder["result"] = self.analyze_for_annotation_chunked(
                    file_path,
                    user_requirement,
                    model_id=effective_model_id,
                    chunk_size=chunk_size,
                    progress_callback=on_analysis_progress
                )
            except Exception as e:
                result_holder["error"] = e
            finally:
                progress_q.put(_SENTINEL)
        
        analysis_thread = threading.Thread(target=run_analysis, daemon=True)
        analysis_thread.start()
        
        # 主线程：实时从 Queue 取出进度事件并 yield（SSE 推送给浏览器）
        heartbeat_interval = 3.0  # 每3秒发一次心跳防止 SSE 超时
        last_heartbeat = time.time()
        current_progress = [15]  # 跟踪当前进度，防止心跳数字回退
        
        try:
            while True:
                if _is_cancelled():
                    yield {
                        'stage': 'cancelled',
                        'progress': 0,
                        'message': '⏸️ 任务已被取消',
                        'detail': '分析过程中中断'
                    }
                    return
                try:
                    evt = progress_q.get(timeout=1.0)
                    if evt is _SENTINEL:
                        break
                    current_progress[0] = max(current_progress[0], evt.get('progress', 15))
                    yield evt
                    last_heartbeat = time.time()
                except queue_module.Empty:
                    if not analysis_thread.is_alive():
                        break
                    # 发送心跳防止浏览器 SSE 超时断连
                    now = time.time()
                    if now - last_heartbeat >= heartbeat_interval:
                        last_heartbeat = now
                        yield {
                            'stage': 'analyzing',
                            'progress': current_progress[0],
                            'message': '🤖 正在分析文档...',
                            'detail': '等待 AI 响应中...'
                        }
            
            analysis_thread.join(timeout=10)
            
            # 检查线程执行结果
            if result_holder["error"]:
                raise result_holder["error"]
            
            analysis_result = result_holder["result"]
            
            if not analysis_result or not analysis_result.get("success"):
                error_msg = (analysis_result or {}).get("error", "未知错误")
                yield {
                    'stage': 'error',
                    'progress': 0,
                    'message': f'❌ 分析失败: {error_msg}',
                    'detail': ''
                }
                return
            
            annotations = analysis_result.get("annotations", [])
            
            yield {
                'stage': 'analysis_complete',
                'progress': 50,
                'message': f'✅ 分析完成',
                'detail': f'找到 {len(annotations)} 处修改'
            }
            
        except Exception as e:
            yield {
                'stage': 'error',
                'progress': 0,
                'message': f'❌ 分析错误: {str(e)[:100]}',
                'detail': ''
            }
            return
        
        if len(annotations) == 0:
            yield {
                'stage': 'complete',
                'progress': 100,
                'message': '✅ 分析完成，未找到需要修改的地方',
                'detail': '',
                'result': {
                    'success': True,
                    'message': '未找到修改点',
                    'original_file': file_path,
                    'applied': 0
                }
            }
            return
        
        # ===== Stage 3: 应用标注到文档 =====
        if _is_cancelled():
            yield {
                'stage': 'cancelled',
                'progress': 0,
                'message': '⏸️ 任务已被取消',
                'detail': '应用修改前中断'
            }
            return
        
        yield {
            'stage': 'applying',
            'progress': 55,
            'message': '📝 正在应用修改到文档...',
            'detail': f'将使用 Track Changes 标注 {len(annotations)} 处'
        }
        
        try:
            from web.track_changes_editor import TrackChangesEditor
            
            editor = TrackChangesEditor(author="Koto AI")
            
            # 创建副本
            base_name = os.path.splitext(file_path)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            simple_revised = f"{base_name}_revised.docx"
            
            # 检查文件是否被占用
            try:
                if os.path.exists(simple_revised):
                    with open(simple_revised, 'a'):
                        pass
                    revised_file = simple_revised
                else:
                    revised_file = simple_revised
            except (PermissionError, IOError):
                revised_file = f"{base_name}_revised_{timestamp}.docx"
                print(f"[DocumentFeedback] ⚠️ 原修改版被占用，创建新版本: {os.path.basename(revised_file)}")
            
            # 复制文件
            shutil.copy2(file_path, revised_file)
            
            # 再次检查取消
            if _is_cancelled():
                yield {
                    'stage': 'cancelled',
                    'progress': 0,
                    'message': '⏸️ 任务已被取消',
                    'detail': '应用修改过程中中断'
                }
                return
            
            yield {
                'stage': 'applying',
                'progress': 60,
                'message': '📝 正在应用混合标注...',
                'detail': f'精确修改+方向建议 共{len(annotations)}项'
            }
            
            # 应用混合标注 — 自动区分精确修改和方向建议
            # ✏️ 短文本（<=30字）且有替换文本 → Track Changes（修订标记）
            # 💬 长文本（>30字）或只有建议 → Comment（批注气泡）
            apply_q = queue_module.Queue()
            apply_result_holder = {"result": None, "error": None}
            
            def on_apply_progress(current, total, status, detail):
                pct = 60 + int((current / total) * 25) if total > 0 else 60
                apply_q.put({
                    'stage': 'applying',
                    'progress': pct,
                    'message': f'📝 {status}...',
                    'detail': detail
                })
            
            def run_apply():
                try:
                    apply_result_holder["result"] = editor.apply_hybrid_changes(
                        revised_file,
                        annotations,
                        progress_callback=on_apply_progress
                    )
                except Exception as e:
                    apply_result_holder["error"] = e
                finally:
                    apply_q.put(_SENTINEL)
            
            apply_thread = threading.Thread(target=run_apply, daemon=True)
            apply_thread.start()
            
            while True:
                if _is_cancelled():
                    yield {
                        'stage': 'cancelled',
                        'progress': 0,
                        'message': '⏸️ 任务已被取消',
                        'detail': '应用修改过程中中断'
                    }
                    return
                try:
                    evt = apply_q.get(timeout=1.0)
                    if evt is _SENTINEL:
                        break
                    yield evt
                except queue_module.Empty:
                    if not apply_thread.is_alive():
                        break
            
            apply_thread.join(timeout=10)
            
            if apply_result_holder["error"]:
                raise apply_result_holder["error"]
            
            edit_result = apply_result_holder["result"]
            
            applied = edit_result.get("applied", 0)
            failed = edit_result.get("failed", 0)
            
            yield {
                'stage': 'applying_complete',
                'progress': 85,
                'message': f'✅ 修改应用完成',
                'detail': f'成功: {applied}, 失败: {failed}'
            }
            
        except Exception as e:
            import traceback
            yield {
                'stage': 'error',
                'progress': 0,
                'message': f'❌ 应用错误: {str(e)[:100]}',
                'detail': traceback.format_exc()[:200]
            }
            return
        
        # ===== Stage 4: 完成 =====
        
        # 添加到文件网络索引
        try:
            from web.processed_file_network import get_file_network
            file_network = get_file_network()
            file_network.record_processing(
                file_path=file_path,
                operation="annotate",
                changes_count=applied,
                output_file=revised_file,
                status="success" if applied > 0 else "partial",
                details={
                    "requirement": user_requirement,
                    "total_annotations": len(annotations),
                    "applied": applied,
                    "failed": failed
                }
            )
        except Exception as e:
            print(f"[DocumentFeedback] 文件网络索引记录失败: {e}")
        
        yield {
            'stage': 'complete',
            'progress': 100,
            'message': '✅ 文档修改完成！',
            'detail': f'修改位置: {applied}，定位失败: {failed}',
            'result': {
                'success': edit_result.get("success", False),
                'original_file': file_path,
                'revised_file': revised_file,
                'applied': applied,
                'failed': failed,
                'total': len(annotations),
                'analysis_summary': analysis_result.get("summary")
            }
        }

    def full_annotation_loop(
        self,
        file_path: str,
        user_requirement: str = "",
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        完整标注闭环：读取 -> 分析 -> 定位 -> 注入
        
        Args:
            file_path: Word文档路径
            user_requirement: 用户需求
        
        Returns:
            {
                "success": True,
                "original_file": "...",
                "revised_file": "...",
                "applied": 5,
                "failed": 1
            }
        """
        print("=" * 60)
        print("🔄 启动文档自动标注系统（完整闭环）")
        print("=" * 60)
        
        effective_model_id = model_id or self.default_model_id

        # 第1步：分析生成标注建议（使用分段方法处理大文档）
        chunk_size = 4000 if (self.client and os.getenv("KOTO_DISABLE_AI") != "1") else 10000
        analysis_result = self.analyze_for_annotation_chunked(
            file_path,
            user_requirement,
            model_id=effective_model_id,
            chunk_size=chunk_size
        )
        
        if not analysis_result.get("success"):
            return analysis_result
        
        annotations = analysis_result.get("annotations", [])
        print(f"\n📊 分析结果: 生成 {len(annotations)} 个标注建议")
        
        if len(annotations) == 0:
            return {
                "success": True,
                "message": "AI分析完成，但未找到需要修改的地方",
                "original_file": file_path
            }
        
        # 第2步：应用标注到文档（使用Track Changes修订模式）
        print(f"\n[DocumentFeedback] � 以右侧批注气泡添加修改建议...")
        
        # 使用批注方式 — 原文不变，修改建议以右侧气泡显示
        from web.track_changes_editor import TrackChangesEditor
        import shutil
        from datetime import datetime
        
        editor = TrackChangesEditor(author="Koto AI")
        
        # 创建副本（带时间戳避免冲突）
        base_name = os.path.splitext(file_path)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        simple_revised = f"{base_name}_revised.docx"
        
        # 检查文件是否被占用
        try:
            if os.path.exists(simple_revised):
                # 尝试打开检测是否被占用
                with open(simple_revised, 'a'):
                    pass
                revised_file = simple_revised
            else:
                revised_file = simple_revised
        except (PermissionError, IOError):
            # 文件被占用，使用时间戳版本
            revised_file = f"{base_name}_revised_{timestamp}.docx"
            print(f"[DocumentFeedback] ⚠️ 原修改版被占用，创建新版本: {os.path.basename(revised_file)}")
        
        # 复制文件
        shutil.copy2(file_path, revised_file)
        
        # 应用混合标注（精确修改+方向建议）
        edit_result = editor.apply_hybrid_changes(revised_file, annotations)
        
        # 添加到文件网络索引
        try:
            from web.processed_file_network import get_file_network
            file_network = get_file_network()
            file_network.record_processing(
                file_path=file_path,
                operation="annotate",
                changes_count=edit_result.get("applied", 0),
                output_file=revised_file,
                status="success" if edit_result.get("applied", 0) > 0 else "partial",
                details={
                    "requirement": user_requirement,
                    "total_annotations": len(annotations),
                    "applied": edit_result.get("applied"),
                    "failed": edit_result.get("failed")
                }
            )
        except Exception as e:
            print(f"[DocumentFeedback] 文件网络索引记录失败: {e}")
        
        return {
            "success": edit_result.get("success", False),
            "original_file": file_path,
            "revised_file": revised_file,
            "applied": edit_result.get("applied"),
            "failed": edit_result.get("failed"),
            "total": edit_result.get("total"),
            "analysis_summary": analysis_result.get("summary")
        }
    
    def _build_annotation_prompt(
        self,
        doc_type: str,
        formatted_content: str,
        user_requirement: str,
        full_doc_context: str = ""
    ) -> str:
        """构建用于标注的AI Prompt - 精准修改版，生成可直接替换的文本修订"""
        
        # 统计段落数，用于指导 AI 均匀分布
        paragraphs = [p.strip() for p in formatted_content.split("\n\n") if p.strip()]
        para_count = len(paragraphs)
        
        # 如果提供了全文背景，限制长度以免超限(保留开头结尾和目录大纲信息)
        global_ctx_prompt = ""
        if full_doc_context and len(full_doc_context) > len(formatted_content) * 1.5:
            # 只有当背景明显长于当前片段时才包含背景，避免第一段自我重复干扰
            ctx_len = len(full_doc_context)
            if ctx_len > 30000:
                # 截取开头3000字和结尾2000字作为背景
                global_ctx_prompt = f"""
## 全文背景参考（节选）
...（前文忽略）
{full_doc_context[:3000]}
...
{full_doc_context[-2000:]}
"""
            else:
                global_ctx_prompt = f"""
## 全文完整背景（供连贯性分析参考）
{full_doc_context}
"""

        base_prompt = f"""你是一名资深学术编辑。请逐段审阅此{doc_type.upper()}文档片段（共{para_count}段），基于全文背景进行**直接修改**。

{global_ctx_prompt}

## 当前待审阅文档片段（共{para_count}段）
{formatted_content}

## 任务要求
{user_requirement if user_requirement else "对文档进行学术润色，提升表达的专业性、准确性和连贯性"}

## 🚫 重要指令：
1. **少废话，多干活**：不要给出"建议修改..."的空洞批注，而是**直接提供修改后的文本**。
2. **精准定位**：原文片段必须与文档中的文本完全一致，不要省略或修改原文。
3. **适度修改**：只修改真正有语病、翻译腔、逻辑不通顺或生硬的地方。不要为了修改而修改。保持原意不变。

## ⚠️ 去AI味 — 必须严格遵守的语言风格：
你改写后的文本**绝对不能有AI味**。以下是具体禁令：
- **禁用破折号**（——）来做解释或插入语，改用逗号、括号或拆成两句。
- **禁用引号强调**：不要用"XXX"来强调概念，直接写出来。
- **禁用排比堆砌**：不要把三个以上并列短语排在一起，像"提升了效率、优化了流程、增强了体验"这种要砍掉。
- **禁用以下AI高频套话**：值得注意的是、需要指出的是、总而言之、综上所述、不仅...而且...、一方面...另一方面...、从...角度来看、在...背景下、具有重要意义、发挥着关键作用、提供了有力支撑。
- **少用"进行""实现""开展"等万能动词**，换成具体的动作。
- **语言要朴实自然**，像一个有经验的人写的，不像AI生成的。读起来应该像正常人说的话，而不是机器拼出来的。
- **句子要短**，一句话说一件事。不要把多个信息塞进一个长从句里。

### 示例（错误 vs 正确）：
- ❌ "该方法在提升效率、优化流程、增强体验等方面具有重要意义"
- ✅ "该方法能有效提升工作效率"
- ❌ "值得注意的是，这一发现为后续研究提供了有力支撑"
- ✅ "这一发现对后续研究有参考价值"
- ❌ "通过对数据的深入分析——包括统计检验和回归建模——我们发现..."
- ✅ "统计检验和回归建模的分析结果表明..."

## 标注类型

### 类型A：术语与用词修正（直接替换）
纠正不地道的表达、口语化词汇、翻译腔。
*   原文="被广泛地进行使用" -> 改为="已广泛使用"
*   原文="在这个图像中" -> 改为="该图像"

### 类型B：句子重写与润色（直接替换）
遇到长难句、逻辑不通顺的句子，**直接重写**整句。用短句，少用从句。
*   原文="[选中拗口的整句]" -> 改为="[重写后的简洁句子]"
*   ⚠️ **注意**：选中文本不要超过一段，最好以句为单位。

### 类型C：结构性批注（仅限必要时）
只有当确实通过修改无法解决（如完全跑题、段落缺失）时，才使用建议。
*   改为="建议：..."

## 输出格式
只返回JSON数组，禁止其他文字：
[
  {{"原文": "被广泛地进行使用", "改为": "已广泛使用", "原因": "精简"}},
  {{"原文": "在当前数字艺术发展的主流实践中，研究者们主要聚焦于...（原长句）", "改为": "目前数字艺术研究主要集中在...（重写后）", "原因": "去冗余"}},
  {{"原文": "这为后续研究提供了有力支撑", "改为": "这对后续研究有参考价值", "原因": "去套话"}}
]
"""
        return base_prompt
    
    def _parse_annotation_response(self, ai_response: str) -> List[Dict[str, str]]:
        """解析AI响应为标注格式"""
        import re
        import json
        
        try:
            # 尝试提取JSON数组
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接找数组
                json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = ai_response
            
            data = json.loads(json_str)
            
            # 验证格式
            if isinstance(data, list):
                valid_annotations = []
                for item in data:
                    if isinstance(item, dict):
                        # 提取原文
                        original = item.get("原文片段") or item.get("原文") or item.get("original")
                        # 提取修改建议
                        modified = item.get("修改建议") or item.get("改为") or item.get("修改后文本") or item.get("modified")
                        # 提取原因
                        reason = item.get("修改原因") or item.get("原因") or item.get("reason")
                        
                        if original and modified:
                            entry = {
                                "原文片段": str(original).strip(),
                                "修改建议": str(modified).strip()
                            }
                            if reason:
                                entry["修改原因"] = str(reason).strip()
                            valid_annotations.append(entry)
                return valid_annotations
            
            # 如果是对象包裹格式，尝试提取 annotations/modifications/suggestions
            if isinstance(data, dict):
                for key in ["annotations", "modifications", "suggestions"]:
                    if key in data and isinstance(data[key], list):
                        valid_annotations = []
                        for item in data[key]:
                            if isinstance(item, dict):
                                # 同样支持多种格式
                                original = item.get("原文片段") or item.get("原文") or item.get("original")
                                modified = item.get("修改建议") or item.get("改为") or item.get("修改后文本") or item.get("modified")
                                reason = item.get("修改原因") or item.get("原因") or item.get("reason")
                                
                                if original and modified:
                                    entry = {
                                        "原文片段": str(original).strip(),
                                        "修改建议": str(modified).strip()
                                    }
                                    if reason:
                                        entry["修改原因"] = str(reason).strip()
                                    valid_annotations.append(entry)
                        if valid_annotations:
                            return valid_annotations
            
            return []
        
        except Exception as e:
            print(f"[DocumentFeedback] 解析标注失败: {e}")
            return []


if __name__ == "__main__":
    print("文档智能反馈系统准备就绪")
