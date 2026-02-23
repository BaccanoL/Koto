"""测试 AI 增强分析器对微信文件的分类效果 vs 旧规则引擎"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web'))

from file_analyzer import FileAnalyzer
from pathlib import Path

analyzer = FileAnalyzer()
src = Path(r'C:\Users\12524\Documents\WeChat Files\wxid_vfk3vjs6qgtn22\FileStorage\File\2026-02')
files = sorted([f for f in src.rglob('*') if f.is_file()], key=lambda x: x.name)

# 去重：同一文件名的 _revised 版本只分析原始版
seen_stems = {}
unique_files = []
for f in files:
    stem = analyzer._clean_filename_stem(f.stem)
    if stem not in seen_stems:
        seen_stems[stem] = f
        unique_files.append(f)

print(f"\n共 {len(files)} 个文件，{len(unique_files)} 个不重复主题\n")
print(f"{'文件名':<48} | {'AI?':<3} | {'行业':<15} | {'类别':<15} | {'置信度':<6} | {'实体':<22} | 建议路径")
print("-" * 170)

start = time.time()
for f in unique_files:
    r = analyzer.analyze_file(str(f))
    if r.get('success'):
        name = f.name[:46]
        ai_flag = "✦" if r.get('ai_enhanced') else " "
        industry = r['industry']
        category = r['category']
        confidence = f"{r['confidence']:.2f}"
        entity = (r.get('entity') or '')[:20]
        folder = r['suggested_folder']
        print(f"{name:<48} | {ai_flag:<3} | {industry:<15} | {category:<15} | {confidence:<6} | {entity:<22} | {folder}")

elapsed = time.time() - start
print(f"\n分析耗时: {elapsed:.1f}s (平均 {elapsed/len(unique_files):.1f}s/文件)")

# 也显示重复文件的合并情况
dupes = len(files) - len(unique_files)
if dupes > 0:
    print(f"\n📋 {dupes} 个修订/副本版本将合并到同主题文件夹中")
    for stem, f in seen_stems.items():
        versions = [x for x in files if analyzer._clean_filename_stem(x.stem) == stem]
        if len(versions) > 1:
            print(f"  {stem}: {len(versions)} 个版本")
