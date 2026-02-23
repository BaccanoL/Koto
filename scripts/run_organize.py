"""执行微信文件归纳 - 使用 AI 增强分析"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web'))

from file_analyzer import FileAnalyzer
from file_organizer import FileOrganizer
from folder_catalog_organizer import FolderCatalogOrganizer
import json

# 初始化组件
organize_root = os.path.join(os.path.dirname(__file__), '..', 'workspace', '_organize')
analyzer = FileAnalyzer()
organizer = FileOrganizer(organize_root)
catalog = FolderCatalogOrganizer(organize_root, analyzer, organizer)

# 微信文件目录
wechat_dir = r'C:\Users\12524\Documents\WeChat Files\wxid_vfk3vjs6qgtn22\FileStorage\File\2026-02'

print(f"开始归纳: {wechat_dir}")
print(f"目标路径: {organize_root}")
print("=" * 60)

result = catalog.organize_folder(wechat_dir)

print("\n" + "=" * 60)
print(f"归纳完成！")
print(f"  总文件数: {result.get('total_files', 0)}")
print(f"  成功归纳: {result.get('organized_count', 0)}")
print(f"  失败数量: {result.get('failed_count', 0)}")

if result.get('report_markdown'):
    print(f"  报告文件: {result['report_markdown']}")

# 显示归纳结果
print("\n📂 归纳清单:")
for entry in result.get('entries', []):
    status = "✅" if entry.get('organized') else "❌"
    print(f"  {status} {entry['file_name'][:45]:45s} → {entry.get('suggested_folder', '?')}")
    if entry.get('error'):
        print(f"     ⚠️ {entry['error']}")
