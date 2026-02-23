"""测试 OrganizeCleanup 清理重复文件夹功能。"""
import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.organize_cleanup import OrganizeCleanup


def test_cleanup_merges_duplicates():
    """模拟真实场景：相同论文因修订后缀产生了多个文件夹。"""
    test_root = tempfile.mkdtemp(prefix="koto_cleanup_test_")
    organize_dir = os.path.join(test_root, "_organize")

    try:
        # 模拟现有混乱结构
        base_name = "电影时间的计算解析"
        variants = [
            base_name,
            base_name + "_revised",
            base_name + "_revised(1)",
            base_name + "_revised(2)",
            base_name + "_revised_20260215",
        ]

        for i, name in enumerate(variants):
            folder = os.path.join(organize_dir, "other", name)
            os.makedirs(folder, exist_ok=True)
            # 写入相同内容（模拟同一篇论文的多个版本）
            with open(os.path.join(folder, f"paper.docx"), "wb") as f:
                f.write(b"SAME CONTENT FOR ALL VERSIONS " + b"x" * 1000)
            # 最新版多一个附件
            if i == len(variants) - 1:
                with open(os.path.join(folder, "appendix.pdf"), "wb") as f:
                    f.write(b"APPENDIX CONTENT " + b"y" * 500)

        # 另一个重复组
        group2 = ["入伙协议-今茂", "入伙协议-朱总", "入伙协议"]
        for name in group2:
            folder = os.path.join(organize_dir, "legal", name)
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "contract.pdf"), "wb") as f:
                f.write(b"CONTRACT CONTENT " + b"z" * 800)

        # 创建 index.json（占位）
        idx_path = os.path.join(organize_dir, "index.json")
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "total_files": 0, "files": [],
                        "created_at": "", "last_updated": ""}, f)

        # 验证初始状态
        cleanup = OrganizeCleanup(organize_root=organize_dir)
        folder_info = cleanup._scan_folders()
        initial_count = len(folder_info)
        initial_with_files = len([k for k, v in folder_info.items() if v["files"]])
        print(f"初始文件夹数: {initial_count} (含文件: {initial_with_files})")
        assert initial_with_files == len(variants) + len(group2), f"Expected {len(variants) + len(group2)} with files, got {initial_with_files}"

        # dry run 先看看
        dry_report = cleanup.run(dry_run=True)
        print(f"相似组数: {dry_report['similarity_groups']}")
        assert dry_report["similarity_groups"] >= 2, f"Expected >= 2 groups, got {dry_report['similarity_groups']}"
        print("✅ Dry run 识别到相似组")

        # 实际执行
        cleanup2 = OrganizeCleanup(organize_root=organize_dir)
        report = cleanup2.run(dry_run=False)
        print(f"合并文件: {report['merged_files']}")
        print(f"去重文件: {report['deduped_files']}")
        print(f"删除文件夹: {report['removed_folders']}")

        # 验证结果
        remaining = cleanup2._scan_folders()
        remaining_with_files = {k: v for k, v in remaining.items() if v["files"]}
        print(f"剩余文件夹: {list(remaining_with_files.keys())}")

        # 应该只剩 2 个文件夹（每组1个）
        assert len(remaining_with_files) <= 3, f"Expected <= 3 remaining, got {len(remaining_with_files)}: {list(remaining_with_files.keys())}"
        print("✅ 重复文件夹已合并")

        # 验证索引已重建
        with open(idx_path, "r", encoding="utf-8") as f:
            new_idx = json.load(f)
        assert new_idx["total_files"] >= 2, f"Expected >= 2 files in index, got {new_idx['total_files']}"
        print(f"✅ 索引已重建: {new_idx['total_files']} 条记录")

        print("\n🎉 清理测试全部通过！")

    finally:
        shutil.rmtree(test_root)


if __name__ == "__main__":
    test_cleanup_merges_duplicates()
