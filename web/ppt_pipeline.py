#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PPT生成管道 - 集成所有模块的完整工作流
从用户需求到高质量PPT输出
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from web.ppt_master import PPTMasterOrchestrator, PPTBlueprint
from web.ppt_synthesizer import PPTSynthesizer, PPTBeautyOptimizer, PPTQualityEnsurance


class PPTGenerationPipeline:
    """
    PPT生成管道 - 统一的生成接口
    
    流程：
    1. 接收用户请求和资源
    2. 使用MasterOrchestrator规划
    3. 生成蓝图
    4. 质量检查
    5. 使用Synthesizer合成
    6. 返回最终PPT
    """
    
    def __init__(self, ai_client=None, workspace_dir: str = "."):
        self.ai_client = ai_client
        self.workspace_dir = workspace_dir
        self.orchestrator = PPTMasterOrchestrator(ai_client)
        self.synthesizer = PPTSynthesizer()
        self.log = []
    
    async def generate(
        self,
        user_request: str,
        output_path: str,
        search_results: Optional[List[Dict]] = None,
        existing_images: Optional[List[str]] = None,
        progress_callback=None,
        thought_callback=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Args:
            progress_callback: 进度回调 callback(msg: str, progress: int)
            thought_callback: 思考/规划回调 callback(thought_text: str)
        """
        
        def _report(msg, p=None):
            if progress_callback:
                try: progress_callback(msg, p)
                except: pass
            self._log(f"[{p}%] {msg}" if p is not None else msg)

        def _think(text):
            if thought_callback:
                try: thought_callback(text)
                except: pass
            self._log(f"[THOUGHT] {text}")

        _report("🚀 开始PPT生成管道", 5)
        self._log("=" * 70)
        
        try:
            # 阶段1: 规划
            _report("【阶段1】正在进行内容规划与蓝图设计...", 10)
            
            # 1.1 获取初步大纲
            _think(f"正在分析文档内容 ({len(user_request)} chars)... 提取核心论点与关键数据")
            
            blueprint = await self.orchestrator.orchestrate_ppt_generation(
                user_request=user_request,
                search_results=search_results,
                existing_images=existing_images,
                progress_callback=progress_callback,
                **kwargs
            )
            
            # [NEW] 将规划蓝图转化为自然语言反馈给用户
            # Dynamic Thinking: Generate a summary that feels specific
            plan_summary = (
                f"已构思完毕 - 这是一份关于「{blueprint.title}」的 {len(blueprint.slides)} 页演示方案。\n"
                f"我们将采用 {blueprint.theme} 风格，{blueprint.visual_style} 视觉导向。\n\n"
            )
            
            # Identify key sections dynamically
            sections = [s.title for s in blueprint.slides if s.slide_type.value == 'section']
            if sections:
                plan_summary += f"核心章节包括：{'、'.join(sections)}。\n"
            
            # Mention special features
            special_slides = [s for s in blueprint.slides if s.slide_type.value in ['comparison', 'data', 'flow']]
            if special_slides:
                 plan_summary += f"我特别设计了 {len(special_slides)} 页用于展示{'对比分析' if 'comparison' in [s.slide_type.value for s in special_slides] else '关键数据/流程'}。\n"
            
            plan_summary += "\n正在进一步细化每个页面的排版..."
            _think(plan_summary)
            
            _report(f"✅ 蓝图设计锁定 (共 {len(blueprint.slides)} 页)", 40)
            self._log(f"   - 幻灯片数: {len(blueprint.slides)}")
            self._log(f"   - 主题: {blueprint.theme}")
            self._log(f"   - 规划步骤: {len(blueprint.generation_log)}")
            
            # 阶段2: 质量检查
            _report(f"【阶段2】正在检查第 {blueprint.slides[0].slide_index}-{blueprint.slides[-1].slide_index} 页的内容一致性...", 45)
            
            # 使用更详细的提示，模拟"思考"过程
            quality_check = await PPTQualityEnsurance.verify_blueprint_quality(blueprint)
            score = quality_check['quality_score']
            
            check_details = []
            if not quality_check['checks'].get('content_density_ok', True):
                check_details.append("部分幻灯片字数过多，需要精简")
            if not quality_check['checks'].get('has_images', False):
                 check_details.append("视觉元素不足，建议增加配图")
            
            thought_msg = f"质量评分: {score:.0f}/100"
            if check_details:
                thought_msg += " | 发现待改进项：" + "、".join(check_details)
            else:
                thought_msg += " | 结构逻辑清晰，内容分布合理"
                
            if quality_check['recommendations']:
                 rec_str = "\n".join([f"- {r}" for r in quality_check['recommendations'][:2]])
                 thought_msg += f"\n\n正在执行优化策略：\n{rec_str}"
            
            _think(thought_msg)

            self._log("\n【阶段2】蓝图质量检查")
            self._log("-" * 70)
            
            self._log(f"✅ 质量评分: {quality_check['quality_score']:.1f}/100")
            
            for check_name, result in quality_check['checks'].items():
                status = "✓" if result else "✗"
                self._log(f"   {status} {check_name}")
            
            if quality_check['recommendations']:
                self._log("\n📋 改进建议:")
                for rec in quality_check['recommendations']:
                    self._log(f"   - {rec}")
            

            # 阶段3: 模型资源准备 (增加自动配图)
            self._log("\n【阶段3】资源准备与视觉增强")
            self._log("-" * 70)
            
            _think("正在分配图像资源与视觉主题...")

            enable_auto_images = kwargs.get("enable_auto_images", True)
            
            if enable_auto_images:
                _think("视觉策略：根据主题自动生成或搜索配图...")
                # 自动获取图像 (生成或搜索)
                self._acquire_images_for_blueprint(blueprint)
                
                # Report after loading
                images_found = sum(len(s.image_paths) for s in blueprint.slides)
                if images_found > 0:
                     _think(f"已获取 {images_found} 张相关配图，正在整合布局...")
                else:
                     _think("未找到合适配图，将采用纯色/极简布局策略...")
            else:
                self._log("ℹ️ 已跳过自动配图（enable_auto_images=False）")
            
            image_map = self._prepare_image_map(blueprint, existing_images)
            
            self._log(f"✅ 图像映射完成: {len(image_map)} 张幻灯片有图像")
            
            # 阶段4: PPT合成
            self._log("\n【阶段4】PPT合成与美化")
            self._log("-" * 70)
            
            _think(f"正在进行最终渲染，应用 {blueprint.theme} 配色方案...")
                    
            def _synth_reporter(msg, p=None):
                if progress_callback: progress_callback(msg, p)

            synthesis_result = await self.synthesizer.synthesize_from_blueprint(
                blueprint=blueprint,
                output_path=output_path,
                apply_beauty_rules=True,
                image_paths=image_map,
                progress_callback=_synth_reporter
            )
            
            _think(f"✅ 文件已生成。幻灯片总数：{synthesis_result.get('slide_count')}。")

            if not synthesis_result.get("success"):
                self._log(f"❌ PPT合成失败: {synthesis_result.get('error')}")
                return {
                    "success": False,
                    "error": synthesis_result.get('error'),
                    "stage": "synthesis"
                }
            
            self._log(f"✅ PPT合成完成")
            self._log(f"   - 文件大小: {synthesis_result['file_size']:.2f} KB")
            self._log(f"   - 幻灯片总数: {synthesis_result['slide_count']}")
            
            # 阶段5: 最终验证
            self._log("\n【阶段5】最终验证与输出")
            self._log("-" * 70)
            
            final_result = self._finalize_result(
                synthesis_result,
                blueprint,
                quality_check,
                output_path
            )
            
            self._log(f"✅ PPT生成完成！")
            self._log(f"📁 保存路径: {output_path}")
            self._log("=" * 70)
            
            return final_result
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            self._log(f"\n❌ 错误: {error_msg}")
            self._log(f"堆栈: {traceback.format_exc()}")
            
            return {
                "success": False,
                "error": error_msg,
                "traceback": traceback.format_exc(),
                "logs": self.log
            }
    

    def _prepare_image_map(
        self,
        blueprint: PPTBlueprint,
        existing_images: Optional[List[str]] = None
    ) -> Dict[int, List[str]]:
        """
        为蓝图中的幻灯片映射图像
        优先使用 blueprint 中自动获取的 image_paths
        其次使用 existing_images 补充
        """
        
        image_map = {}
        
        # 1. 首先映射 blueprint 中自动获取/生成的图像
        for slide in blueprint.slides:
            if slide.image_paths:
                image_map[slide.slide_index] = slide.image_paths
                
        # 2. 如果还有空缺，尝试使用 existing_images 填充
        if existing_images:
            img_index = 0
            for slide in blueprint.slides:
                # 如果该页还没有图像，且需要图像
                if slide.slide_index not in image_map:
                    if (slide.image_prompts or 
                        slide.slide_type.value in ["content_image", "image_full"]):
                        if img_index < len(existing_images):
                            image_map[slide.slide_index] = [existing_images[img_index]]
                            img_index += 1
        
        return image_map

    def _acquire_images_for_blueprint(self, blueprint: PPTBlueprint):
        """
        为蓝图自动获取图像 (生成或搜索)
        """
        try:
            # 报告状态
            if self.orchestrator and hasattr(self.orchestrator, '_report') and hasattr(self.orchestrator, '_think'):
                 # Need a way to call _think/ _report from here?
                 # Since this is a method of pipeline, we can use self._log for now.
                 pass

            from web.image_manager import ImageManager
            # 尝试获取 client，如果没有则无法生成
            client = self.ai_client if self.ai_client else None
            
            # 尝试懒加载 client 如果 self.ai_client 为空 (从 app 获取)
            if not client:
                try:
                    from web.app import get_client
                    client = get_client()
                    print("[PPT_Pipeline] 已懒加载 AI Client")
                except ImportError:
                     # 尝试从 web.app 的 LazyModule 获取
                    try:
                        import google.genai as genai
                        if os.environ.get("GEMINI_API_KEY"):
                             client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
                    except:
                        pass

            if not client:
                self._log("⚠️ 无法初始化 ImageManager (无 AI Client)，跳过自动配图")
                return

            img_mgr = ImageManager(client=client, workspace_dir=self.workspace_dir)
            
            count = 0
            for slide in blueprint.slides:
                # 限制：不要每页都配图，避免太慢和太乱，仅针对明确需要图的页面
                if slide.image_prompts and not slide.image_paths:
                    # 取第一个提示词
                    prompt = slide.image_prompts[0]
                    self._log(f"   🎨 正在为第 {slide.slide_index} 页配图: {prompt[:20]}...")
                    
                    # 尝试获取图像
                    img_path = img_mgr.get_image(prompt, method="auto")
                    
                    if img_path:
                        slide.image_paths.append(img_path)
                        count += 1
                        self._log(f"      ✅ 获取成功")
                    else:
                        self._log(f"      ⚠️ 获取失败")
                        
            self._log(f"✅ 自动配图完成: 新增 {count} 张图像")
            
        except Exception as e:
            self._log(f"❌ 自动配图过程出错: {str(e)}")

    
    def _finalize_result(
        self,
        synthesis_result: Dict,
        blueprint: PPTBlueprint,
        quality_check: Dict,
        output_path: str
    ) -> Dict[str, Any]:
        """
        最终化结果 - 整合所有信息
        """
        
        return {
            "success": True,
            "output_path": output_path,
            "file_size_kb": synthesis_result.get('file_size', 0),
            "slide_count": synthesis_result.get('slide_count', 0),
            "title": blueprint.title,
            "subtitle": blueprint.subtitle,
            "theme": blueprint.theme,
            "quality": {
                "score": quality_check.get('quality_score', 0),
                "checks": quality_check.get('checks', {}),
                "recommendations": quality_check.get('recommendations', [])
            },
            "blueprint_info": {
                "total_content_points": sum(len(s.content) for s in blueprint.slides),
                "image_heavy_slides": len([
                    s for s in blueprint.slides
                    if s.slide_type.value in ["content_image", "image_full"]
                ]),
                "layout_types": list(set(
                    s.slide_type.value for s in blueprint.slides
                )),
            },
            "resource_summary": self.orchestrator.resource_manager.get_summary_for_blueprint(),
            "generation_log": self.log,
            "timestamp": datetime.now().isoformat()
        }
    
    def _log(self, message: str):
        """记录日志"""
        self.log.append(message)
        print(message)
    
    def get_logs(self) -> List[str]:
        """获取所有日志"""
        return self.log


class PPTGenerationTaskHandler:
    """
    PPT生成任务处理器 - 在chat_stream中使用
    处理用户请求并调用生成管道
    """
    
    def __init__(self, ai_client=None, workspace_dir: str = "."):
        self.pipeline = PPTGenerationPipeline(ai_client, workspace_dir)
    
    async def handle_ppt_generation_task(
        self,
        user_request: str,
        documents_dir: str,
        search_executor=None,
        image_generator=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理PPT生成任务
        
        包括：
        1. 调用搜索获取信息
        2. 调用图像生成获取配图
        3. 执行PPT生成
        4. 返回结果
        """
        
        search_results = None
        images = []
        
        # 步骤1: 搜索（如果有搜索执行器）
        if search_executor:
            try:
                print("[TaskHandler] 正在搜索相关信息...")
                search_result = await search_executor(user_request, {})
                if search_result.get("success"):
                    search_results = search_result.get("results", [])
                    print(f"[TaskHandler] 找到 {len(search_results)} 条相关信息")
            except Exception as e:
                print(f"[TaskHandler] 搜索失败: {e}")
        
        # 步骤2: 生成图像（如果有图像生成器）
        if image_generator:
            try:
                print("[TaskHandler] 正在生成配图...")
                # 提取主题
                import re
                theme_match = re.search(r'关于(.{2,20}?)(的|，|。)', user_request)
                theme = theme_match.group(1) if theme_match else "主题"
                
                # 生成2-3张图
                for i in range(2):
                    prompt = f"{theme}主题相关的专业插图{i+1}，高质量，演示文稿用途"
                    try:
                        img_result = await image_generator(prompt, {})
                        if img_result.get("success") and img_result.get("image_paths"):
                            images.extend(img_result["image_paths"])
                    except Exception as e:
                        print(f"[TaskHandler] 图像生成失败: {e}")
            except Exception as e:
                print(f"[TaskHandler] 图像处理失败: {e}")
        
        # 步骤3: 执行PPT生成
        print("[TaskHandler] 正在生成PPT...")
        
        # 生成输出路径
        import re
        title_match = re.search(r'关于(.{2,20}?)(的|，|。)', user_request)
        title = title_match.group(1) if title_match else "演示"
        
        filename = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        output_path = os.path.join(documents_dir, filename)
        
        # 执行生成
        result = await self.pipeline.generate(
            user_request=user_request,
            output_path=output_path,
            search_results=search_results,
            existing_images=images if images else None,
            **kwargs
        )
        
        return result
    
    def get_pipeline_logs(self) -> List[str]:
        """获取管道日志"""
        return self.pipeline.get_logs()


def format_ppt_generation_result(result: Dict[str, Any]) -> str:
    """
    格式化PPT生成结果为人类可读的消息
    """
    
    if not result.get("success"):
        return f"❌ PPT生成失败: {result.get('error', '未知错误')}\n\n详情: {result.get('error_detail', '')}"
    
    output = "\n" + "=" * 60 + "\n"
    output += "✅ 高质量PPT生成完成！\n\n"
    
    output += f"📊 PPT信息:\n"
    output += f"  • 标题: {result.get('title', '无')}\n"
    output += f"  • 幻灯片数: {result.get('slide_count', 0)} 张\n"
    output += f"  • 文件大小: {result.get('file_size_kb', 0):.2f} KB\n"
    output += f"  • 主题风格: {result.get('theme', 'business')}\n"
    output += f"  • 保存位置: {result.get('output_path', '无')}\n\n"
    
    # 质量信息
    quality = result.get('quality', {})
    if quality:
        output += f"🎯 质量评价:\n"
        output += f"  • 质量评分: {quality.get('score', 0):.1f}/100\n"
        
        checks = quality.get('checks', {})
        if checks:
            output += f"  • 质量检查:\n"
            for check_name, passed in checks.items():
                icon = "✓" if passed else "✗"
                output += f"    {icon} {check_name}\n"
        
        recommendations = quality.get('recommendations', [])
        if recommendations:
            output += f"\n  • 改进建议:\n"
            for rec in recommendations:
                output += f"    • {rec}\n"
    
    # 蓝图信息
    blueprint_info = result.get('blueprint_info', {})
    if blueprint_info:
        output += f"\n📋 内容结构:\n"
        output += f"  • 总要点数: {blueprint_info.get('total_content_points', 0)}\n"
        output += f"  • 含图幻灯片: {blueprint_info.get('image_heavy_slides', 0)} 张\n"
        output += f"  • 布局类型: {', '.join(blueprint_info.get('layout_types', []))}\n"
    
    # 资源信息
    resources = result.get('resource_summary', {})
    if resources:
        output += f"\n📚 资源统计:\n"
        output += f"  • 搜索关键词: {resources.get('search_keywords_count', 0)}\n"
        output += f"  • 参考资料: {resources.get('references_count', 0)} 条\n"
        output += f"  • 配图数量: {resources.get('generated_images_count', 0)} 张\n"
    
    output += "\n" + "=" * 60 + "\n"
    
    return output
