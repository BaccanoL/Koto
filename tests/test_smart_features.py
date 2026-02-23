#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能功能综合测试脚本
测试概念提取、知识图谱、行为监控、智能建议和洞察报告
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from web.concept_extractor import ConceptExtractor
from web.knowledge_graph import KnowledgeGraph
from web.behavior_monitor import BehaviorMonitor
from web.suggestion_engine import SuggestionEngine
from web.insight_reporter import InsightReporter


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def test_concept_extraction():
    """测试概念提取"""
    print_section("📝 1. 概念提取测试")
    
    extractor = ConceptExtractor()
    
    # 创建测试文件
    test_files = {
        'test_ai.txt': """
        人工智能和机器学习正在改变世界。深度学习模型可以识别图像、理解语言。
        神经网络是深度学习的基础。TensorFlow和PyTorch是流行的深度学习框架。
        自然语言处理技术让计算机能够理解人类语言。
        """,
        'test_python.txt': """
        Python是一种强大的编程语言。它广泛应用于数据科学和机器学习领域。
        NumPy和Pandas是Python数据分析的核心库。
        Flask和Django是流行的Python Web框架。
        """,
        'test_web.txt': """
        前端开发使用HTML、CSS和JavaScript。
        React、Vue和Angular是流行的前端框架。
        Node.js让JavaScript可以运行在服务器端。
        RESTful API是Web服务的常用设计模式。
        """
    }
    
    print("创建测试文件...")
    workspace_dir = Path("workspace")
    workspace_dir.mkdir(exist_ok=True)
    
    file_paths = []
    for filename, content in test_files.items():
        filepath = workspace_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        file_paths.append(str(filepath))
        print(f"  ✓ {filename}")
    
    print("\n提取概念...")
    for filepath in file_paths:
        print(f"\n📄 {Path(filepath).name}:")
        result = extractor.analyze_file(filepath)
        
        if "error" not in result:
            for concept_data in result["concepts"][:5]:
                print(f"  • {concept_data['concept']}: {concept_data['score']:.4f}")
    
    # 查找相关文件
    print("\n\n查找相关文件...")
    related = extractor.find_related_files(file_paths[0], limit=2)
    if related:
        print(f"与 {Path(file_paths[0]).name} 相关的文件:")
        for item in related:
            print(f"  • {Path(item['file_path']).name}")
            print(f"    相似度: {item['similarity']:.2%}")
            print(f"    共享概念: {', '.join(item['shared_concepts'][:3])}")
    
    # 统计信息
    stats = extractor.get_statistics()
    print("\n📊 概念提取统计:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    return file_paths


def test_knowledge_graph(file_paths):
    """测试知识图谱"""
    print_section("🕸️ 2. 知识图谱测试")
    
    kg = KnowledgeGraph()
    
    print("构建知识图谱...")
    kg.build_file_graph(file_paths, force_rebuild=True)
    
    # 获取图数据
    print("\n获取图谱数据...")
    graph_data = kg.get_graph_data(max_nodes=50)
    print(f"  • 节点数: {len(graph_data['nodes'])}")
    print(f"  • 边数: {len(graph_data['edges'])}")
    
    # 获取文件邻居
    print(f"\n获取 {Path(file_paths[0]).name} 的邻居节点...")
    neighbors = kg.get_file_neighbors(file_paths[0], depth=1)
    if "error" not in neighbors:
        print(f"  • 邻居节点: {len(neighbors['nodes'])}")
        print(f"  • 连接边: {len(neighbors['edges'])}")
    
    # 概念聚类
    print("\n测试概念聚类...")
    concepts = kg.concept_extractor.get_top_concepts(limit=1)
    if concepts:
        concept = concepts[0]['concept']
        cluster = kg.get_concept_cluster(concept, limit=5)
        print(f"概念 '{concept}' 相关的文件:")
        for file_data in cluster['files']:
            print(f"  • {Path(file_data['file_path']).name}")
            print(f"    相关度: {file_data['relevance']:.4f}")
    
    # 统计信息
    stats = kg.get_statistics()
    print("\n📊 知识图谱统计:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")


def test_behavior_monitoring():
    """测试行为监控"""
    print_section("👁️ 3. 行为监控测试")
    
    monitor = BehaviorMonitor()
    
    print("模拟用户行为...")
    
    # 模拟一些操作
    events = [
        (BehaviorMonitor.EVENT_FILE_OPEN, "workspace/test_ai.txt", 5000),
        (BehaviorMonitor.EVENT_FILE_EDIT, "workspace/test_ai.txt", 120000),
        (BehaviorMonitor.EVENT_FILE_OPEN, "workspace/test_python.txt", 3000),
        (BehaviorMonitor.EVENT_FILE_EDIT, "workspace/test_python.txt", 60000),
        (BehaviorMonitor.EVENT_FILE_SEARCH, None, 1000),
        (BehaviorMonitor.EVENT_FILE_OPEN, "workspace/test_ai.txt", 2000),
    ]
    
    for event_type, file_path, duration in events:
        monitor.log_event(
            event_type=event_type,
            file_path=file_path,
            duration_ms=duration
        )
        print(f"  ✓ {event_type}")
        time.sleep(0.1)  # 模拟时间间隔
    
    # 记录搜索
    monitor.log_search("机器学习", result_count=5, clicked_result="test_ai.txt")
    monitor.log_search("Python", result_count=3, clicked_result="test_python.txt")
    print("  ✓ 记录搜索历史")
    
    # 获取最常用文件
    print("\n📊 最常用文件:")
    frequent_files = monitor.get_frequently_used_files(limit=3)
    for file_data in frequent_files:
        print(f"  • {Path(file_data['file_path']).name}")
        print(f"    打开: {file_data['open_count']}次, 编辑: {file_data['edit_count']}次")
        print(f"    使用评分: {file_data['usage_score']}")
    
    # 工作模式
    print("\n⏰ 工作模式:")
    patterns = monitor.get_work_patterns()
    if patterns.get('time_of_day'):
        for pattern in patterns['time_of_day']:
            print(f"  • {pattern['period']}: {pattern['frequency']}次")
    
    # 统计信息
    stats = monitor.get_statistics()
    print("\n📊 行为监控统计:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")


def test_suggestions():
    """测试智能建议"""
    print_section("💡 4. 智能建议测试")
    
    engine = SuggestionEngine()
    
    print("生成智能建议...")
    suggestions = engine.generate_suggestions(force_regenerate=True)
    
    if suggestions:
        print(f"\n生成了 {len(suggestions)} 条建议:\n")
        for i, suggestion in enumerate(suggestions[:5], 1):
            priority_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(suggestion['priority'], "⚪")
            
            print(f"{i}. {priority_emoji} [{suggestion['type']}] {suggestion['title']}")
            print(f"   {suggestion['description']}")
            print()
    else:
        print("暂无建议")
    
    # 获取待处理建议
    pending = engine.get_pending_suggestions(limit=3)
    print(f"待处理建议: {len(pending)} 条")
    
    # 统计信息
    stats = engine.get_statistics()
    print("\n📊 建议引擎统计:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")


def test_insights():
    """测试洞察报告"""
    print_section("📈 5. 洞察报告测试")
    
    reporter = InsightReporter()
    
    print("生成周报...")
    report = reporter.generate_weekly_report()
    
    print("\n📊 报告摘要:")
    print(f"  报告类型: {report['type']}")
    print(f"  周期: {report['period']['days']}天")
    
    # 显示部分报告内容
    sections = report['sections']
    
    if 'activity_overview' in sections:
        activity = sections['activity_overview']
        print(f"\n活动概览:")
        print(f"  • 总操作数: {activity['total_events']}")
        print(f"  • 日均活跃: {activity['daily_average']}次")
        print(f"  • 活跃天数: {activity['active_days']}")
    
    if 'productivity' in sections:
        prod = sections['productivity']
        print(f"\n生产力分析:")
        print(f"  • 编辑文件: {prod['total_files_edited']}个")
        print(f"  • 总编辑次数: {prod['total_edits']}")
        print(f"  • 生产力评分: {prod['productivity_score']}%")
        print(f"  • 评价: {prod['interpretation']}")
    
    # 显示Markdown摘要的前500字符
    print("\n📝 Markdown报告摘要:")
    print(report.get('summary_markdown', '')[:500] + "...\n")
    
    # 导出报告
    output_path = "workspace/weekly_report.md"
    reporter.export_report_markdown(report, output_path)
    print(f"✅ 报告已导出到: {output_path}")


def main():
    """主测试流程"""
    print("\n" + "🧠" * 30)
    print("    Koto 智能文件大脑 - 综合功能测试")
    print("🧠" * 30)
    
    try:
        # 1. 概念提取
        file_paths = test_concept_extraction()
        
        # 2. 知识图谱
        test_knowledge_graph(file_paths)
        
        # 3. 行为监控
        test_behavior_monitoring()
        
        # 4. 智能建议
        test_suggestions()
        
        # 5. 洞察报告
        test_insights()
        
        print_section("✅ 所有测试完成")
        
        print("\n🎉 功能演示:")
        print("  1. 概念提取: 自动识别文件中的关键词和主题")
        print("  2. 知识图谱: 构建文件关系网络，发现关联")
        print("  3. 行为监控: 追踪用户操作，分析使用模式")
        print("  4. 智能建议: 基于行为主动提供建议")
        print("  5. 洞察报告: 生成周报/月报，展示工作洞察")
        
        print("\n🌐 启动Web界面:")
        print("  1. 运行: python web/app.py")
        print("  2. 访问: http://localhost:5000/knowledge-graph")
        print("  3. 体验可视化知识图谱和智能建议\n")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
