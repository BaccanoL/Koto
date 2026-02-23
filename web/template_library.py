#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模板库系统 - 报告、简历、方案、PPT 模板一键生成
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class TemplateLibrary:
    """模板库管理器"""
    
    # 内置模板定义
    TEMPLATES = {
        "business_report": {
            "name": "商业报告",
            "type": "docx",
            "description": "标准商业报告模板，包含：封面、目录、摘要、主体、结论",
            "variables": ["title", "author", "date", "company", "executive_summary", "main_content", "conclusion"]
        },
        "resume_modern": {
            "name": "现代简历",
            "type": "docx",
            "description": "简洁专业的简历模板",
            "variables": ["name", "title", "contact", "email", "phone", "summary", "experience", "education", "skills"]
        },
        "meeting_minutes": {
            "name": "会议纪要",
            "type": "docx",
            "description": "标准会议记录格式",
            "variables": ["meeting_title", "date", "attendees", "topics", "decisions", "action_items"]
        },
        "project_proposal": {
            "name": "项目方案",
            "type": "docx",
            "description": "完整项目提案模板",
            "variables": ["project_name", "client", "date", "background", "objectives", "scope", "timeline", "budget", "team"]
        },
        "weekly_report": {
            "name": "周报",
            "type": "docx",
            "description": "个人/团队周报模板",
            "variables": ["title", "week_range", "owner", "highlights", "progress", "risks", "next_plan"]
        },
        "work_summary": {
            "name": "工作总结",
            "type": "docx",
            "description": "日/周工作总结模板",
            "variables": ["title", "date", "tasks_done", "blockers", "plans", "notes"]
        },
        "product_intro_ppt": {
            "name": "产品介绍PPT",
            "type": "pptx",
            "description": "产品发布会演示模板",
            "variables": ["product_name", "tagline", "features", "benefits", "use_cases", "pricing", "contact"]
        },
        "tech_presentation": {
            "name": "技术演讲PPT",
            "type": "pptx",
            "description": "技术分享演示模板",
            "variables": ["title", "speaker", "date", "topics", "demo", "qa"]
        }
    }
    
    def __init__(self, workspace_dir: str = None):
        if workspace_dir is None:
            workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
        
        self.workspace_dir = workspace_dir
        self.templates_dir = os.path.join(workspace_dir, "templates")
        os.makedirs(self.templates_dir, exist_ok=True)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用模板"""
        templates = []
        for template_id, info in self.TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": info["name"],
                "type": info["type"],
                "description": info["description"],
                "variables": info["variables"]
            })
        return templates
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板详情"""
        return self.TEMPLATES.get(template_id)
    
    def generate_from_template(
        self,
        template_id: str,
        variables: Dict[str, str],
        output_dir: str = None
    ) -> Dict[str, Any]:
        """从模板生成文档"""
        template = self.get_template(template_id)
        if not template:
            return {"success": False, "error": "模板不存在"}
        
        if output_dir is None:
            output_dir = os.path.join(self.workspace_dir, "documents")
        os.makedirs(output_dir, exist_ok=True)
        
        # 检查必需变量
        missing_vars = [v for v in template["variables"] if v not in variables]
        if missing_vars:
            for key in missing_vars:
                variables[key] = ""
        
        # 根据模板类型生成
        if template["type"] == "docx":
            return self._generate_docx_from_template(template_id, template, variables, output_dir)
        elif template["type"] == "pptx":
            return self._generate_pptx_from_template(template_id, template, variables, output_dir)
        else:
            return {"success": False, "error": "不支持的模板类型"}
    
    def _generate_docx_from_template(
        self,
        template_id: str,
        template: Dict,
        variables: Dict[str, str],
        output_dir: str
    ) -> Dict[str, Any]:
        """生成Word文档"""
        # 根据不同模板生成不同内容
        if template_id == "business_report":
            content = self._build_business_report(variables)
        elif template_id == "resume_modern":
            content = self._build_resume(variables)
        elif template_id == "meeting_minutes":
            content = self._build_meeting_minutes(variables)
        elif template_id == "project_proposal":
            content = self._build_project_proposal(variables)
        elif template_id == "weekly_report":
            content = self._build_weekly_report(variables)
        elif template_id == "work_summary":
            content = self._build_work_summary(variables)
        else:
            return {"success": False, "error": "未实现的模板"}
        
        # 保存文档
        from web.document_generator import save_docx
        
        title = variables.get("title") or variables.get("project_name") or variables.get("meeting_title") or "文档"
        filename = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        output_path = save_docx(content, title=title, output_dir=output_dir, filename=filename)
        
        return {
            "success": True,
            "template": template["name"],
            "output_path": output_path,
            "output_file": os.path.basename(output_path)
        }
    
    def _generate_pptx_from_template(
        self,
        template_id: str,
        template: Dict,
        variables: Dict[str, str],
        output_dir: str
    ) -> Dict[str, Any]:
        """生成PPT"""
        from web.ppt_generator import PPTGenerator
        
        if template_id == "product_intro_ppt":
            outline = self._build_product_ppt_outline(variables)
        elif template_id == "tech_presentation":
            outline = self._build_tech_ppt_outline(variables)
        else:
            return {"success": False, "error": "未实现的PPT模板"}
        
        title = variables.get("product_name") or variables.get("title") or "演示文稿"
        filename = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        output_path = os.path.join(output_dir, filename)
        
        ppt = PPTGenerator(theme="business")
        result = ppt.generate_from_outline(
            title=title,
            outline=outline,
            output_path=output_path,
            subtitle=variables.get("tagline", ""),
            author=variables.get("speaker", "Koto")
        )
        
        if result["success"]:
            return {
                "success": True,
                "template": template["name"],
                "output_path": output_path,
                "output_file": filename,
                "slide_count": result.get("slide_count")
            }
        else:
            return result
    
    # === 模板内容构建器 ===
    
    def _build_business_report(self, vars: Dict[str, str]) -> str:
        return f"""# {vars['title']}

**作者**: {vars.get('author', 'Koto')}  
**日期**: {vars.get('date', datetime.now().strftime('%Y年%m月%d日'))}  
**公司**: {vars.get('company', '')}

---

## 执行摘要

{vars.get('executive_summary', '')}

---

## 主要内容

{vars.get('main_content', '')}

---

## 结论与建议

{vars.get('conclusion', '')}

---

*本报告由 Koto 自动生成*
"""
    
    def _build_resume(self, vars: Dict[str, str]) -> str:
        return f"""# {vars['name']}

**{vars.get('title', '求职意向')}**

📧 {vars.get('email', '')} | 📱 {vars.get('phone', '')}  
{vars.get('contact', '')}

---

## 个人简介

{vars.get('summary', '')}

---

## 工作经历

{vars.get('experience', '')}

---

## 教育背景

{vars.get('education', '')}

---

## 技能专长

{vars.get('skills', '')}
"""
    
    def _build_meeting_minutes(self, vars: Dict[str, str]) -> str:
        return f"""# {vars['meeting_title']}

**日期**: {vars.get('date', datetime.now().strftime('%Y年%m月%d日'))}  
**参会人员**: {vars.get('attendees', '')}

---

## 会议议题

{vars.get('topics', '')}

---

## 决策事项

{vars.get('decisions', '')}

---

## 行动计划

{vars.get('action_items', '')}

---

*会议记录由 Koto 生成*
"""

    def _build_weekly_report(self, vars: Dict[str, str]) -> str:
        return f"""# {vars.get('title', '周报')}

**周期**: {vars.get('week_range', '')}  
**负责人**: {vars.get('owner', '')}

---

## 本周亮点

{vars.get('highlights', '')}

---

## 工作进展

{vars.get('progress', '')}

---

## 风险与问题

{vars.get('risks', '')}

---

## 下周计划

{vars.get('next_plan', '')}

---

*本周报由 Koto 自动生成*
"""

    def _build_work_summary(self, vars: Dict[str, str]) -> str:
        return f"""# {vars.get('title', '工作总结')}

**日期**: {vars.get('date', datetime.now().strftime('%Y年%m月%d日'))}

---

## 完成事项

{vars.get('tasks_done', '')}

---

## 遇到阻碍

{vars.get('blockers', '')}

---

## 下步计划

{vars.get('plans', '')}

---

## 备注

{vars.get('notes', '')}

---

*本总结由 Koto 自动生成*
"""
    
    def _build_project_proposal(self, vars: Dict[str, str]) -> str:
        return f"""# {vars['project_name']} - 项目方案

**客户**: {vars.get('client', '')}  
**日期**: {vars.get('date', datetime.now().strftime('%Y年%m月%d日'))}

---

## 项目背景

{vars.get('background', '')}

---

## 项目目标

{vars.get('objectives', '')}

---

## 项目范围

{vars.get('scope', '')}

---

## 时间规划

{vars.get('timeline', '')}

---

## 预算说明

{vars.get('budget', '')}

---

## 项目团队

{vars.get('team', '')}

---

*本方案由 Koto 生成*
"""
    
    def _build_product_ppt_outline(self, vars: Dict[str, str]) -> List[Dict]:
        return [
            {"title": "产品概览", "points": [vars.get("product_name", ""), vars.get("tagline", "")]},
            {"title": "核心功能", "points": vars.get("features", "").split("\n") if vars.get("features") else []},
            {"title": "价值优势", "points": vars.get("benefits", "").split("\n") if vars.get("benefits") else []},
            {"title": "应用场景", "points": vars.get("use_cases", "").split("\n") if vars.get("use_cases") else []},
            {"title": "定价方案", "points": [vars.get("pricing", "")]},
            {"title": "联系我们", "points": [vars.get("contact", "")]}
        ]
    
    def _build_tech_ppt_outline(self, vars: Dict[str, str]) -> List[Dict]:
        topics_list = vars.get("topics", "").split("\n") if vars.get("topics") else []
        return [
            {"title": "议题概览", "points": topics_list},
            {"title": "技术细节", "points": vars.get("demo", "").split("\n") if vars.get("demo") else []},
            {"title": "Q&A", "points": [vars.get("qa", "提问与讨论")]}
        ]


if __name__ == "__main__":
    lib = TemplateLibrary()
    
    print("=" * 60)
    print("模板库测试")
    print("=" * 60)
    
    # 列出所有模板
    print("\n1. 可用模板:")
    templates = lib.list_templates()
    for t in templates:
        print(f"   [{t['id']}] {t['name']} ({t['type']})")
        print(f"      {t['description']}")
    
    # 测试生成商业报告
    print("\n2. 生成商业报告测试...")
    result = lib.generate_from_template(
        "business_report",
        {
            "title": "2026年市场分析报告",
            "author": "Koto",
            "company": "AI Research Lab",
            "executive_summary": "本报告分析了2026年AI技术市场趋势...",
            "main_content": "## 市场规模\n\n全球AI市场规模预计达到...\n\n## 主要趋势\n\n- 大模型普及\n- 多模态融合\n- 边缘计算",
            "conclusion": "AI技术将继续高速发展，企业应积极布局..."
        }
    )
    
    if result["success"]:
        print(f"   ✅ 生成成功: {result['output_file']}")
    else:
        print(f"   ❌ 生成失败: {result.get('error')}")
    
    print("\n✅ 模板库就绪")
