#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强型PPT工作流处理器
多模型协作生成高质量演示文稿
"""

import os
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from web.ppt_generator import EnhancedPPTGenerator
from web.ppt_quality import PPTQualityChecker
from web.settings import settings


class EnhancedPPTWorkflow:
    """增强型PPT生成工作流"""
    
    @staticmethod
    async def execute(user_input: str, multi_step_info: Dict, client, TaskOrchestrator, WORKSPACE_DIR) -> Dict:
        """
        执行增强型PPT生成工作流
        
        返回生成器，用于流式输出
        """
        context = {"original_input": user_input, "user_input": user_input}
        search_results = None
        images = []
        
        try:
            quality_checker = PPTQualityChecker()
            max_refine_rounds = 1
            refine_round = 0
            # 步骤1: 搜索相关资料
            if multi_step_info.get("requires_search"):
                print("[PPT Workflow] 步骤1: 搜索相关资料")
                search_result = await TaskOrchestrator._execute_web_search(user_input, context)
                if search_result.get("success"):
                    search_results = search_result.get("results", [])
                    print(f"[PPT Workflow] 找到 {len(search_results)} 条相关信息")
            
            # 步骤2: 生成配图
            if multi_step_info.get("requires_images"):
                print("[PPT Workflow] 步骤2: 生成配图")
                # 从用户输入中提取主题
                theme = EnhancedPPTWorkflow._extract_theme(user_input)
                
                # 生成2-3张配图
                num_images = min(3, max(2, len(user_input) // 50))  # 根据请求长度决定图片数量
                for i in range(num_images):
                    image_prompt = f"{theme}主题配图{i+1}，高质量专业插图，演示文稿用途"
                    try:
                        painter_result = await TaskOrchestrator._execute_painter(image_prompt, context)
                        if painter_result.get("success") and painter_result.get("image_paths"):
                            images.extend(painter_result["image_paths"])
                            print(f"[PPT Workflow] 生成配图 {i+1}/{num_images}")
                    except Exception as e:
                        print(f"[PPT Workflow] 配图生成失败: {e}")
                        continue
                
                print(f"[PPT Workflow] 共生成 {len(images)} 张配图")
            
            # 步骤3: 综合生成PPT
            print("[PPT Workflow] 步骤3: 综合生成PPT")

            # 提取标题
            title = EnhancedPPTWorkflow._extract_title(user_input)
            filename = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
            output_path = os.path.join(settings.documents_dir, filename)

            # 检测主题
            theme_style = EnhancedPPTWorkflow._detect_theme(user_input)

            # 使用增强型生成器
            ppt_generator = EnhancedPPTGenerator(theme=theme_style)

            quality_report = None
            while True:
                result = await ppt_generator.generate_with_multimodal(
                    title=title,
                    user_request=user_input,
                    output_path=output_path,
                    search_results=search_results,
                    images=images,
                    ai_client=client,
                    quality_feedback=quality_report
                )

                if not result.get("success"):
                    return {
                        "success": False,
                        "error": result.get("error", "未知错误")
                    }

                # 质量评估
                quality_report = quality_checker.evaluate(output_path)
                if not quality_report.get("success"):
                    print("[PPT Workflow] 质量检查失败，跳过优化")
                    break

                score = quality_report.get("score", 0)
                print(f"[PPT Workflow] 质量评分: {score}")

                if score >= 75 or refine_round >= max_refine_rounds:
                    break

                refine_round += 1
                print(f"[PPT Workflow] 触发质量优化，轮次: {refine_round}")

            rel_path = os.path.relpath(output_path, WORKSPACE_DIR).replace("\\", "/")
            file_size = os.path.getsize(output_path) / 1024

            return {
                "success": True,
                "output_path": output_path,
                "rel_path": rel_path,
                "file_size": file_size,
                "slide_count": result.get("slide_count", 0),
                "images": images,
                "search_results_count": len(search_results) if search_results else 0,
                "theme": theme_style,
                "quality": quality_report,
                "refine_rounds": refine_round
            }
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _extract_theme(user_input: str) -> str:
        """从用户输入中提取主题"""
        # 移除"做ppt"等常见词汇
        cleaned = re.sub(r'(做|生成|制作)(一个|个)?(ppt|幻灯片|演示)', '', user_input.lower())
        cleaned = re.sub(r'(关于|有关|介绍|说)', '', cleaned)
        
        # 提取关键词（取前20个字符）
        theme = cleaned.strip()[:20]
        return theme if theme else "主题演示"
    
    @staticmethod
    def _extract_title(user_input: str) -> str:
        """从用户输入中提取标题"""
        # 尝试提取"关于XXX"模式
        if '关于' in user_input:
            match = re.search(r'关于(.{2,20}?)(的|，|。|ppt|幻灯片)', user_input)
            if match:
                return match.group(1).strip()
        
        # 尝试提取"XXX的PPT"模式
        if 'ppt' in user_input.lower() or '幻灯片' in user_input:
            match = re.search(r'(.{2,20}?)(的)?(ppt|幻灯片)', user_input)
            if match:
                return match.group(1).strip()
        
        # 默认标题
        return "专业演示文稿"
    
    @staticmethod
    def _detect_theme(user_input: str) -> str:
        """检测PPT主题风格"""
        text_lower = user_input.lower()
        
        if any(k in text_lower for k in ['creative', '创意', '艺术', '设计']):
            return 'creative'
        elif any(k in text_lower for k in ['tech', '技术', '科技', '工程']):
            return 'tech'
        else:
            return 'business'
    
    @staticmethod
    def format_result_message(result: Dict) -> str:
        """格式化结果消息"""
        if not result.get("success"):
            return f"❌ PPT生成失败: {result.get('error', '未知错误')}"
        
        output_text = f"\n{'='*50}\n"
        output_text += f"✅ 增强型PPT生成完成\n\n"
        output_text += f"📊 幻灯片数: {result.get('slide_count', 0)} 张\n"
        output_text += f"📂 文件大小: {result.get('file_size', 0):.2f} KB\n"
        output_text += f"🎨 配图数量: {len(result.get('images', []))} 张\n"
        output_text += f"📚 参考资料: {result.get('search_results_count', 0)} 条\n"
        output_text += f"🎭 主题风格: {result.get('theme', 'business')}\n"
        output_text += f"📁 保存位置: {result.get('rel_path', '')}\n"
        quality = result.get("quality")
        if quality and quality.get("success"):
            output_text += f"✅ 质量评分: {quality.get('score', 0)} / 100\n"
            output_text += f"🔁 优化轮次: {result.get('refine_rounds', 0)}\n"
        output_text += f"{'='*50}\n"
        
        return output_text
