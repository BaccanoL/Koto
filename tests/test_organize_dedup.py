"""测试 FileOrganizer 的智能去重和相似文件夹合并功能。"""
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.file_organizer import FileOrganizer


def test_dedup_and_similarity():
    test_root = tempfile.mkdtemp(prefix="koto_test_")
    organize_dir = os.path.join(test_root, "_organize")

    try:
        organizer = FileOrganizer(organize_root=organize_dir)

        # 创建测试源文件
        src_dir = os.path.join(test_root, "source")
        os.makedirs(src_dir)

        # 文件A: 原始
        fa = os.path.join(src_dir, "test_doc.txt")
        with open(fa, "w") as f:
            f.write("Hello World - this is the original document")

        # 文件B: 相同内容（重复）
        fb = os.path.join(src_dir, "test_doc_revised.txt")
        with open(fb, "w") as f:
            f.write("Hello World - this is the original document")

        # 文件C: 不同内容
        fc = os.path.join(src_dir, "test_doc_v2.txt")
        with open(fc, "w") as f:
            f.write("Hello World - this is version 2 of the document")

        # Test 1: 组织原始文件
        r1 = organizer.organize_file(fa, "research/test_doc")
        assert r1["success"], f"Test 1 failed: {r1}"
        assert r1.get("folder_created"), "Test 1: folder should be created"
        print("✅ Test 1: 原始文件成功组织")

        # Test 2: 相同内容 → 不同文件夹名（相似） → 应检测到重复
        r2 = organizer.organize_file(fb, "research/test_doc_revised")
        assert r2["success"], f"Test 2 failed: {r2}"
        assert r2.get("skipped_duplicate"), f"Test 2: should detect duplicate, got: {r2}"
        print("✅ Test 2: 重复内容被检测到，跳过")

        # Test 3: 不同内容 → 应该成功添加到相同文件夹
        r3 = organizer.organize_file(fc, "research/test_doc")
        assert r3["success"], f"Test 3 failed: {r3}"
        assert r3.get("folder_created"), f"Test 3: should create file, got: {r3}"
        print("✅ Test 3: 不同内容成功添加到已有文件夹")

        # Test 4: 检查索引去重
        idx = organizer.get_index()
        assert idx["total_files"] == 2, f"Test 4: expected 2 entries, got {idx['total_files']}"
        print("✅ Test 4: 索引只有2条记录（无重复）")

        # Test 5: 文件夹结构应该只有1个文件夹
        folders = organizer.list_organized_folders()
        folder_names = list(folders.keys())
        print(f"   文件夹: {folder_names}")
        assert len(folders) == 1, f"Test 5: expected 1 folder, got {len(folders)}: {folder_names}"
        # 应该有2个文件
        the_folder = list(folders.values())[0]
        assert the_folder["file_count"] == 2, f"Test 5: expected 2 files, got {the_folder['file_count']}"
        print("✅ Test 5: 只有1个文件夹，包含2个文件")

        # Test 6: _is_same_file 正确比较两个不同文件
        from pathlib import Path
        assert not organizer._is_same_file(Path(fa), Path(fc)), "Test 6: different files should not match"
        assert organizer._is_same_file(Path(fa), Path(fb)), "Test 6: identical files should match"
        print("✅ Test 6: _is_same_file 正确比对文件hash")

        print("\n🎉 所有测试通过！")

    finally:
        shutil.rmtree(test_root)


if __name__ == "__main__":
    test_dedup_and_similarity()
