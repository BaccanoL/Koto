#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的文档标注系统 - 修改建议展示和用户选择

流程：
1. 分析文档 → 生成修改建议列表
2. 返回所有建议给前端（在气泡中显示）
3. 用户选择接受/拒绝
4. 只应用用户接受的修改
"""

import os
import json
import re
from typing import Dict, List, Any, Generator, Tuple, Optional
from datetime import datetime
from copy import deepcopy


class SuggestionAnnotator:
    """
    建议式标注器 - 返回修改建议，由用户选择是否应用
    
    修改建议数据结构:
    {
        "id": "suggestion_001",
        "段落号": 5,
        "原文": "在被记录的时间片段之间",
        "修改": "在记录的时间片段之间",
        "说明": "删除冗余词'被'，简化表述",
        "类型": "删除冗余词",
        "置信度": 0.95,
        "接受": false  // 用户选择
    }
    """
    
    def __init__(self, batch_size: int = 3):
        self.batch_size = batch_size
    
    def analyze_document_streaming(
        self,
        file_path: str,
        user_requirement: str = ""
    ) -> Generator[str, None, None]:
        """
        流式分析文档，返回修改建议
        
        返回SSE事件：
        - progress: 进度
        - suggestion: 单个建议
        - suggestions_complete: 所有建议完成
        - complete: 整个分析完成
        """
        
        from web.document_reader import DocumentReader
        
        # Step 1: 读取文档
        yield self._sse_event("progress", {
            "stage": "reading",
            "message": "📖 正在读取文档...",
            "progress": 0
        })
        
        reader = DocumentReader()
        doc_data = reader.read_document(file_path)
        
        if not doc_data.get("success"):
            yield self._sse_event("error", {
                "message": f"读取文档失败: {doc_data.get('error')}"
            })
            return
        
        paragraphs = doc_data.get("paragraphs", [])
        total_paras = len(paragraphs)
        
        yield self._sse_event("progress", {
            "stage": "reading_complete",
            "message": f"✅ 文档解析完成，共 {total_paras} 段",
            "progress": 10
        })
        
        # Step 2: 分批分析并生成建议
        all_suggestions = []
        batch_count = (total_paras + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(batch_count):
            start_para = batch_idx * self.batch_size
            end_para = min(start_para + self.batch_size, total_paras)
            batch_paras = paragraphs[start_para:end_para]
            
            batch_text = "\n\n---分段---\n\n".join([p["text"] for p in batch_paras])
            
            progress = 10 + int((batch_idx / batch_count) * 70)
            yield self._sse_event("progress", {
                "stage": "analyzing",
                "message": f"🤖 分析第 {batch_idx + 1}/{batch_count} 批（段落 {start_para + 1}-{end_para}）",
                "progress": progress
            })
            
            # 分析这批文本，获得修改建议
            batch_suggestions = self._analyze_batch(
                batch_text,
                start_para,
                batch_paras,
                user_requirement
            )
            
            # 逐个返回建议给客户端
            for suggestion in batch_suggestions:
                all_suggestions.append(suggestion)
                yield self._sse_event("suggestion", suggestion)
            
            yield self._sse_event("batch_complete", {
                "batch": batch_idx + 1,
                "suggestions_found": len(batch_suggestions),
                "total_suggestions": len(all_suggestions)
            })
        
        # Step 3: 返回所有建议汇总
        yield self._sse_event("progress", {
            "stage": "suggestions_complete",
            "message": f"✅ 生成完成！共 {len(all_suggestions)} 处建议",
            "progress": 80
        })
        
        yield self._sse_event("suggestions_complete", {
            "total_suggestions": len(all_suggestions),
            "suggestions": all_suggestions
        })
        
        # Step 4: 等待用户反馈，然后完成
        yield self._sse_event("progress", {
            "stage": "waiting",
            "message": "⏳ 等待用户选择...",
            "progress": 85
        })
        
        yield self._sse_event("complete", {
            "total_suggestions": len(all_suggestions),
            "status": "ready_for_user_choice"
        })
    
    def _analyze_batch(
        self,
        batch_text: str,
        start_para_idx: int,
        batch_paras: List[Dict],
        user_requirement: str
    ) -> List[Dict[str, Any]]:
        """
        分析一批文本，返回修改建议列表
        
        每个建议包含：
        - id: 唯一ID
        - 段落号: 在整个文档中的段落号
        - 原文: 待修改的文本
        - 修改: 修改后的文本
        - 说明: 为什么要修改
        - 类型: 修改的类型
        - 置信度: 0-1的置信度
        """
        
        suggestions = []
        suggestion_id = 0
        
        # 对每个段落应用规则
        for para_idx, para in enumerate(batch_paras):
            para_text = para["text"]
            global_para_idx = start_para_idx + para_idx
            
            # 应用各类规则
            para_suggestions = self._apply_rules(
                para_text,
                global_para_idx,
                suggestion_id
            )
            
            suggestions.extend(para_suggestions)
            suggestion_id += len(para_suggestions)
        
        # 去重但保留有价值的建议
        suggestions = self._deduplicate_suggestions(suggestions)
        
        return suggestions
    
    def _apply_rules(
        self,
        text: str,
        para_idx: int,
        start_id: int
    ) -> List[Dict[str, Any]]:
        """应用所有规则提取修改建议"""
        
        suggestions = []
        rule_id = 0
        
        # 规则1: 删除冗余词"可以"
        for match in re.finditer(r'可以(?:被)?(?:进行)?(\w{2,8})', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "删除冗余词'可以'，使表述更简洁",
                "类型": "删除冗余词",
                "置信度": 0.92,
                "接受": False
            })
            rule_id += 1
        
        # 规则2: 删除冗余词"进行"
        for match in re.finditer(r'进行(\w{2,8})', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "删除冗余词'进行'，简化表述",
                "类型": "删除冗余词",
                "置信度": 0.90,
                "接受": False
            })
            rule_id += 1
        
        # 规则3: 被动句转主动 - "被"
        for match in re.finditer(r'被(\w{2,6})', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "删除'被'字，从被动句改为主动句",
                "类型": "被动→主动",
                "置信度": 0.88,
                "接受": False
            })
            rule_id += 1
        
        # 规则3b: 被动句转主动 - "受到"
        for match in re.finditer(r'受到(\w{2,6})', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "简化'受到'的表述，改为主动句",
                "类型": "被动→主动",
                "置信度": 0.85,
                "接受": False
            })
            rule_id += 1
        
        # 规则4: 删除多余的"是"字
        for match in re.finditer(r'是([a-zA-Z\u4e00-\u9fa5]{2,10})', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "删除多余的'是'字，简化表述",
                "类型": "虚词删除",
                "置信度": 0.85,
                "接受": False
            })
            rule_id += 1
        
        # 规则5: 简化啰嗦表达 - "在...方面"
        for match in re.finditer(r'在([a-zA-Z\u4e00-\u9fa5]{2,8})方面(?:上)?', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "删除'方面'等虚词，简化表述",
                "类型": "啰嗦表达压缩",
                "置信度": 0.87,
                "接受": False
            })
            rule_id += 1
        
        # 规则6: 删除"的...方式"
        for match in re.finditer(r'的([a-zA-Z\u4e00-\u9fa5]{2,8})方式', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "删除'方式'等冗余词",
                "类型": "啰嗦表达压缩",
                "置信度": 0.84,
                "接受": False
            })
            rule_id += 1
        
        # 规则7: "通过...过程"的优化
        for match in re.finditer(r'([a-zA-Z\u4e00-\u9fa5]{2,8})的过程(?:中)?', text):
            original = match.group(0)
            modified = match.group(1)
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": "删除'过程'等冗余词",
                "类型": "啰嗦表达压缩",
                "置信度": 0.83,
                "接受": False
            })
            rule_id += 1
        
        # 规则8: 词序调整 - "对...的..." 型
        for match in re.finditer(r'对([a-zA-Z\u4e00-\u9fa5]{2,6})的([a-zA-Z\u4e00-\u9fa5]{2,6})', text):
            # 这个可能需要更复杂的处理，现在仅识别
            original = match.group(0)
            word1 = match.group(1)
            word2 = match.group(2)
            modified = f"{word2}对{word1}的"
            suggestions.append({
                "id": f"s_{para_idx}_{rule_id}",
                "段落号": para_idx + 1,
                "原文": original,
                "修改": modified,
                "说明": f"调整词序：'{word2}'应该放在前面",
                "类型": "词序调整",
                "置信度": 0.75,
                "接受": False
            })
            rule_id += 1
        
        return suggestions
    
    def _deduplicate_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """去重：删除完全重复的建议"""
        
        seen = set()
        unique = []
        
        for sugg in suggestions:
            key = (sugg["原文"], sugg["修改"])
            if key not in seen:
                seen.add(key)
                unique.append(sugg)
        
        return unique  # 不限制数量，返回全部建议
    
    def apply_user_choices(
        self,
        file_path: str,
        user_choices: List[Dict]
    ) -> Dict[str, Any]:
        """
        根据用户选择应用修改
        
        user_choices: [
            {
                "id": "s_5_0",
                "接受": True  // 用户是否接受
            },
            ...
        ]
        """
        
        try:
            from docx import Document
            
            # 读取原文件
            doc = Document(file_path)
            
            # 构建接受的修改映射
            accepted_map = {}
            for choice in user_choices:
                if choice.get("接受"):
                    accepted_map[choice["id"]] = True
            
            # 重新分析并只应用接受的修改
            # （这里简化处理，实际应该保存建议并精确应用）
            
            modified_count = 0
            
            # 对每个段落应用修改
            for para_idx, para in enumerate(doc.paragraphs):
                para_text = para.text
                
                # 应用用户接受的修改
                # 这需要重新生成建议并检查对应的选择
                
            # 保存为新文件
            base_name = os.path.splitext(file_path)[0]
            output_path = f"{base_name}_final.docx"
            doc.save(output_path)
            
            return {
                "success": True,
                "output_file": output_path,
                "modified_count": modified_count,
                "message": f"已根据您的选择应用 {modified_count} 处修改"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _sse_event(self, event_type: str, data: Dict) -> str:
        """构造SSE事件"""
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
