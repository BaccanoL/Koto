#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PPT多模型系统测试脚本
验证完整的PPT生成流程

用法:
    python test_ppt_system.py

这个脚本将：
1. 初始化所有PPT模块
2. 测试蓝图生成
3. 测试PPT合成
4. 验证质量检查
5. 生成示例PPT文件
"""

import os
import sys
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppt_master import PPTMasterOrchestrator, PPTBlueprint
from ppt_synthesizer import PPTSynthesizer, PPTQualityEnsurance
from ppt_pipeline import PPTGenerationPipeline

# 默认工作目录
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(os.path.join(WORKSPACE_DIR, "documents"), exist_ok=True)


async def test_orchestrator():
    """测试主协调器"""
    print("\n" + "="*60)
    print("🧪 测试1: PPT主协调器")
    print("="*60)
    
    orchestrator = PPTMasterOrchestrator(ai_client=None)
    
    user_request = "做一个关于人工智能发展的PPT，包含历史、现状和未来展望"
    
    print(f"\n📝 用户请求: {user_request[:50]}...")
    
    # 模拟搜索结果
    mock_search_results = [
        {
            "title": "AI发展历史",
            "content": "人工智能从1956年开始发展，经历了多个阶段的发展和突破。"
        },
        {
            "title": "当前AI技术应用",
            "content": "深度学习、神经网络等技术在图像识别、自然语言处理等领域取得突破性进展。"
        },
        {
            "title": "AI未来展望",
            "content": "AI技术将继续向通用人工智能方向发展，同时在各个应用领域深化。"
        }
    ]
    
    # 生成蓝图
    print("\n📋 生成PPT蓝图...")
    blueprint = await orchestrator.orchestrate_ppt_generation(
        user_request=user_request,
        search_results=mock_search_results,
        existing_images=None
    )
    
    print(f"\n✅ 蓝图生成完成！")
    print(f"   • 幻灯片数: {len(blueprint.slides)}")
    print(f"   • 主题: {blueprint.theme}")
    print(f"   • 规划步骤: {len(blueprint.generation_log)}")
    
    # 显示蓝图中的幻灯片
    print(f"\n📊 PPT结构预览:")
    for slide in blueprint.slides[:5]:  # 显示前5张
        layout_info = f" [{slide.layout_config.get('bullet_style', 'standard')}]" if slide.layout_config else ""
        print(f"   {slide.slide_index+1}. [{slide.slide_type.value}] {slide.title}{layout_info}")
    if len(blueprint.slides) > 5:
        print(f"   ... 还有 {len(blueprint.slides)-5} 张幻灯片")
    
    return blueprint


async def test_quality_check(blueprint):
    """测试质量检查"""
    print("\n" + "="*60)
    print("🧪 测试2: PPT质量评估")
    print("="*60)
    
    print(f"\n🔍 检查 {len(blueprint.slides)} 张幻灯片的质量...")
    
    quality_result = await PPTQualityEnsurance.verify_blueprint_quality(blueprint)
    
    print(f"\n✅ 质量评估完成！")
    print(f"   • 评分: {quality_result['quality_score']:.1f}/100")
    
    print(f"\n📋 质量检查项:")
    for check_name, result in quality_result['checks'].items():
        status = "✓" if result else "✗"
        print(f"   {status} {check_name}")
    
    if quality_result['recommendations']:
        print(f"\n💡 改进建议:")
        for rec in quality_result['recommendations']:
            print(f"   • {rec}")
    
    return quality_result


async def test_synthesizer(blueprint):
    """测试PPT合成"""
    print("\n" + "="*60)
    print("🧪 测试3: PPT合成引擎")
    print("="*60)
    
    synthesizer = PPTSynthesizer(theme=blueprint.theme)
    
    output_path = os.path.join(WORKSPACE_DIR, "documents", "test_ppt_demo.pptx")
    
    print(f"\n⚙️ 合成PPT文件...")
    print(f"   输出路径: {output_path}")
    
    result = await synthesizer.synthesize_from_blueprint(
        blueprint=blueprint,
        output_path=output_path,
        apply_beauty_rules=True
    )
    
    if result["success"]:
        print(f"\n✅ PPT合成成功！")
        print(f"   • 幻灯片数: {result['slide_count']}")
        print(f"   • 文件大小: {result['file_size']:.2f} KB")
        print(f"   • 文件位置: {result['output_path']}")
        return output_path
    else:
        print(f"\n❌ PPT合成失败: {result.get('error')}")
        return None


async def test_full_pipeline():
    """测试完整管道"""
    print("\n" + "="*60)
    print("🧪 测试4: 完整PPT生成管道")
    print("="*60)
    
    pipeline = PPTGenerationPipeline(ai_client=None, workspace_dir=WORKSPACE_DIR)
    
    user_request = "制作一个关于Python编程的PPT，涵盖基础、进阶和实战三个部分"
    output_path = os.path.join(WORKSPACE_DIR, "documents", "python_tutorial.pptx")
    
    print(f"\n📝 用户请求: {user_request[:50]}...")
    print(f"📁 输出路径: {output_path}")
    
    result = await pipeline.generate(
        user_request=user_request,
        output_path=output_path
    )
    
    if result["success"]:
        print(f"\n✅ 完整管道执行成功！")
        print(f"   • 幻灯片数: {result['slide_count']}")
        print(f"   • 质量评分: {result['quality']['score']:.1f}/100")
        print(f"   • 文件大小: {result['file_size_kb']:.2f} KB")
        print(f"\n📋 管道日志:")
        for log_line in result['generation_log'][-5:]:  # 显示最后5条日志
            print(f"   {log_line}")
        return output_path
    else:
        print(f"\n❌ 管道执行失败: {result.get('error')}")
        return None


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🚀 启动PPT多模型系统完整测试")
    print("="*70)
    print(f"\n📍 工作目录: {WORKSPACE_DIR}")
    
    try:
        # 测试1: 协调器
        blueprint = await test_orchestrator()
        
        # 测试2: 质量检查
        quality = await test_quality_check(blueprint)
        
        # 测试3: 合成器
        ppt_path = await test_synthesizer(blueprint)
        
        # 测试4: 完整管道
        ppt_path2 = await test_full_pipeline()
        
        # 总结
        print("\n" + "="*70)
        print("✅ 所有测试完成！")
        print("="*70)
        
        if ppt_path:
            print(f"\n📊 生成的PPT文件:")
            if os.path.exists(ppt_path):
                size = os.path.getsize(ppt_path) / 1024
                print(f"   ✓ {os.path.basename(ppt_path)} ({size:.2f} KB)")
        
        if ppt_path2:
            print(f"   ✓ {os.path.basename(ppt_path2)}")
        
        print(f"\n🎉 PPT多模型系统已准备就绪！")
        print(f"\n使用建议:")
        print(f"1. 在Koto中说: '做一个关于...的PPT'")
        print(f"2. 系统会自动搜索资料、生成配图")
        print(f"3. 最后生成高质量的演示文稿")
        print(f"\n更多信息: 查看 PPT多模型系统集成指南.py")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PPT多模型协作系统 - 测试套件")
    print("="*70)
    print("\n本脚本将测试所有PPT生成模块：")
    print("  ✓ PPTMasterOrchestrator  - 主协调器")
    print("  ✓ PPTContentPlanner      - 内容规划")
    print("  ✓ PPTLayoutPlanner       - 排版规划")
    print("  ✓ PPTSynthesizer         - 合成引擎")
    print("  ✓ PPTQualityEnsurance    - 质量验证")
    print("  ✓ PPTGenerationPipeline  - 完整管道")
    
    # 运行测试
    asyncio.run(run_all_tests())
