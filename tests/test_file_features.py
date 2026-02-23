#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件编辑与搜索功能测试
"""

import os
import sys

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from web.file_editor import FileEditor
from web.file_indexer import FileIndexer


def test_file_editor():
    """测试文件编辑器"""
    print("=" * 60)
    print("📝 文件编辑器测试")
    print("=" * 60)
    
    editor = FileEditor()
    test_file = os.path.join(editor.workspace_dir, "test_edit_demo.txt")
    
    # 1. 创建测试文件
    print("\n1️⃣ 创建测试文件...")
    content = """# 配置文件
version = 1.0
debug = True
timeout = 30
server_url = http://localhost:8080
"""
    editor.write_file(test_file, content, create_backup=False)
    print(f"✅ 已创建: {test_file}")
    print(f"内容:\n{content}")
    
    # 2. 测试替换
    print("\n2️⃣ 测试文本替换: 把 'True' 改成 'False'")
    result = editor.replace_text(test_file, "True", "False")
    print(f"✅ 替换 {result.get('replacements')} 处")
    print(f"预览: {result.get('preview')}")
    
    # 3. 测试插入
    print("\n3️⃣ 测试插入行: 在第 3 行之后插入 'port = 9000'")
    result = editor.insert_line(test_file, 3, "port = 9000", mode="after")
    print(f"✅ {result.get('message')}")
    
    # 4. 测试智能编辑
    print("\n4️⃣ 测试智能编辑: '把 timeout 改成 60'")
    result = editor.smart_edit(test_file, "把 'timeout = 30' 改成 'timeout = 60'")
    if result.get('success'):
        op_result = result.get('result', {})
        print(f"✅ 操作: {result.get('operation')}, 替换 {op_result.get('replacements')} 处")
    else:
        print(f"❌ {result.get('error')}")
    
    # 5. 显示最终内容
    print("\n5️⃣ 最终文件内容:")
    result = editor.read_file(test_file)
    if result['success']:
        print(f"```\n{result['content']}\n```")
    
    # 6. 显示备份文件
    backups = list(editor.backup_dir.glob("*.bak"))
    if backups:
        print(f"\n💾 备份文件数: {len(backups)}")
        for b in backups[:3]:
            print(f"   - {b.name}")
    
    print()


def test_file_indexer():
    """测试文件索引器"""
    print("=" * 60)
    print("🔍 文件搜索测试")
    print("=" * 60)
    
    indexer = FileIndexer()
    
    # 1. 索引 workspace 目录
    print("\n1️⃣ 索引 workspace 目录...")
    result = indexer.index_directory(str(indexer.workspace_dir), recursive=True)
    print(f"✅ 总文件: {result.get('total')}, 已索引: {result.get('indexed')}, 跳过: {result.get('skipped')}")
    
    # 2. 搜索测试
    print("\n2️⃣ 搜索关键词: 'config'")
    results = indexer.search("config", limit=5)
    if results:
        print(f"✅ 找到 {len(results)} 个匹配:")
        for i, r in enumerate(results, 1):
            print(f"   {i}. {r['file_name']}")
            print(f"      路径: {r['file_path']}")
            print(f"      预览: {r['match_snippet'][:80]}...")
            print()
    else:
        print("❌ 未找到匹配文件")
    
    # 3. 内容查找
    print("\n3️⃣ 根据内容查找相似文件...")
    sample = "version = 1.0\ndebug = False"
    results = indexer.find_by_content(sample, min_similarity=0.2)
    if results:
        print(f"✅ 找到 {len(results)} 个相似文件:")
        for i, r in enumerate(results[:3], 1):
            similarity = r.get('similarity', 0)
            print(f"   {i}. {r['file_name']} (相似度: {similarity:.0%})")
    else:
        print("❌ 未找到相似文件")
    
    # 4. 列出索引统计
    print("\n4️⃣ 索引统计:")
    all_files = indexer.list_indexed_files(limit=100)
    print(f"   总索引文件数: {len(all_files)}")
    
    # 按扩展名分组
    from collections import Counter
    ext_counts = Counter(f['file_ext'] for f in all_files)
    print(f"   文件类型分布:")
    for ext, count in ext_counts.most_common(5):
        print(f"      {ext or '无扩展名'}: {count} 个")
    
    print()


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("Koto 文件编辑与搜索功能测试")
    print("🚀" * 30 + "\n")
    
    try:
        # 测试文件编辑
        test_file_editor()
        
        # 测试文件搜索
        test_file_indexer()
        
        print("\n" + "✅" * 30)
        print("所有测试完成！")
        print("✅" * 30 + "\n")
        
        print("💡 使用方法:")
        print("   1. 修改文件: \"修改 文件路径 把'旧文本'改成'新文本'\"")
        print("   2. 搜索文件: \"找包含'关键词'的文件\"")
        print("   3. 内容查找: \"哪个文件里有'一段内容'\"")
        print()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
