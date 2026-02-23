"""
智能文件归纳器 - 自动创建文件夹和组织文件

包含智能去重、相似文件夹合并、内容hash比对等机制。
"""
import os
import json
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
from difflib import SequenceMatcher


class FileOrganizer:
    """文件归纳管理器"""
    
    def __init__(self, organize_root: str = "workspace/_organize"):
        """
        初始化归纳系统
        
        Args:
            organize_root: 归纳文件夹的根目录
        """
        self.organize_root = Path(organize_root)
        self.organize_root.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.organize_root / "index.json"
        self.metadata_template = {
            "created_at": datetime.now().isoformat(),
            "files_count": 0,
            "last_updated": datetime.now().isoformat()
        }
        
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """确保索引文件存在"""
        if not self.index_file.exists():
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "total_files": 0,
                    "last_updated": datetime.now().isoformat(),
                    "files": []
                }, f, ensure_ascii=False, indent=2)
    
    def organize_file(self, source_file: str, suggested_folder: str, auto_confirm: bool = False, metadata: Optional[Dict] = None) -> Dict:
        """
        组织单个文件到归纳文件夹
        
        包含智能去重:
        1. 检查现有文件夹是否已有相似名称 → 合并到现有文件夹
        2. 检查目标文件夹内是否已有相同内容文件 → 跳过复制
        
        Args:
            source_file: 源文件路径
            suggested_folder: 建议的相对路径（如 "finance/华芯长昇"）
            auto_confirm: 是否自动应用建议
            metadata: 元数据（发送者、实体等）
        """
        source_path = Path(source_file)
        
        if not source_path.exists():
            return {
                "success": False,
                "error": f"源文件不存在: {source_file}"
            }
        
        # 清理建议路径（移除不安全字符）
        safe_folder = self._sanitize_path(suggested_folder)
        
        # ★ 智能文件夹匹配：检查是否已存在相似文件夹，避免重复创建
        matched_folder = self._find_similar_existing_folder(safe_folder)
        if matched_folder:
            safe_folder = matched_folder
        
        # 创建完整目标路径
        dest_dir = self.organize_root / safe_folder
        dest_path = dest_dir / source_path.name
        
        # ★ 检查目标文件夹里是否已有内容相同的文件
        source_hash = self._compute_file_hash(source_path)
        existing_dup = self._find_content_duplicate(dest_dir, source_hash)
        if existing_dup:
            return {
                "success": True,
                "source_file": source_file,
                "dest_file": str(existing_dup),
                "relative_path": str(existing_dup.relative_to(self.organize_root)),
                "folder_created": False,
                "message": f"文件已存在（内容相同）: {existing_dup.name}",
                "skipped_duplicate": True
            }
        
        # 处理重复文件名
        dest_path = self._get_unique_path(dest_path, source_path)
        
        try:
            # 创建目标目录
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制文件（保留原文件）
            shutil.copy2(source_path, dest_path)
            
            # 更新索引
            self._update_index(source_file, str(dest_path), safe_folder, metadata)
            
            # 创建文件夹元数据
            self._update_folder_metadata(dest_dir)
            
            return {
                "success": True,
                "source_file": source_file,
                "dest_file": str(dest_path),
                "relative_path": str(dest_path.relative_to(self.organize_root)),
                "folder_created": True,
                "message": f"文件已成功组织到: {safe_folder}"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"文件组织失败: {str(e)}"
            }
    
    def _sanitize_path(self, path: str) -> str:
        """清理路径中的不安全字符"""
        # 移除特殊字符，但保留 / 作为路径分隔符
        replacements = {
            '\\': '/',
            ':': '_',
            '*': '_',
            '?': '_',
            '"': '_',
            '<': '_',
            '>': '_',
            '|': '_'
        }
        
        for char, replacement in replacements.items():
            path = path.replace(char, replacement)
        
        # 移除连续的空格
        while '  ' in path:
            path = path.replace('  ', ' ')
        
        return path.strip()
    
    def _get_unique_path(self, path: Path, source_path: Path = None) -> Path:
        """获取唯一的文件路径（避免覆盖）"""
        if not path.exists():
            return path
        
        # 如果源文件跟目标文件内容相同，直接返回原路径（跳过）
        if source_path and self._is_same_file(source_path, path):
            return path
        
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            # 检查新路径的文件内容是否与源文件相同
            if source_path and self._is_same_file(source_path, new_path):
                return new_path
            counter += 1

    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for matching."""
        if not name:
            return ""
        normalized = re.sub(r"\s+", " ", name.strip())
        return normalized.lower()
    
    @staticmethod
    def _compute_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
        """计算文件的 SHA-256 hash"""
        h = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
        except Exception:
            return ""
        return h.hexdigest()
    
    def _is_same_file(self, file_a: Path, file_b: Path) -> bool:
        """比较两个文件内容是否相同（先比大小，再比hash）"""
        try:
            if file_a.stat().st_size != file_b.stat().st_size:
                return False
            return self._compute_file_hash(file_a) == self._compute_file_hash(file_b)
        except Exception:
            return False

    def _find_content_duplicate(self, dest_dir: Path, source_hash: str) -> Optional[Path]:
        """检查目标文件夹内是否已有内容相同的文件"""
        if not dest_dir.exists() or not source_hash:
            return None
        for existing_file in dest_dir.iterdir():
            if existing_file.is_file() and not existing_file.name.startswith('_'):
                if self._compute_file_hash(existing_file) == source_hash:
                    return existing_file
        return None

    # 修订后缀模式（用于文件夹名清理，与 FileAnalyzer 保持一致）
    _REVISION_PATTERNS = [
        re.compile(r'_revised\(\d+\)$', re.IGNORECASE),
        re.compile(r'_revised_\d{8,14}$', re.IGNORECASE),
        re.compile(r'_revised$', re.IGNORECASE),
        re.compile(r'\(\d+\)$'),
        re.compile(r'_\d{8,14}$'),
        re.compile(r'_copy\d*$', re.IGNORECASE),
        re.compile(r'_副本\d*$'),
    ]

    def _clean_name_for_matching(self, name: str) -> str:
        """清理名称用于匹配：去掉修订后缀、空格等。"""
        for pat in self._REVISION_PATTERNS:
            name = pat.sub('', name)
        return name.strip().lower()

    def _find_similar_existing_folder(self, suggested_folder: str) -> Optional[str]:
        """检查 _organize 根目录下是否已有相似名称的文件夹。
        
        例如 suggested_folder = "other/电影时间的计算解析"，
        而已存在 "other/电影时间的计算解析：基于大视觉语言模型的电影连续性研究"，
        应该归入后者。
        
        匹配策略: 
        1. 精确匹配（完全相同）
        2. 清理修订后缀后再匹配
        3. 前缀匹配（A 是 B 的前缀，或反之）
        4. 模糊匹配（相似度 > 0.6）
        """
        parts = suggested_folder.replace('\\', '/').split('/')
        
        if len(parts) >= 2:
            parent_name = parts[0]  # industry
            entity_name = '/'.join(parts[1:])  # entity part
            parent_dir = self.organize_root / parent_name
        else:
            parent_dir = self.organize_root
            entity_name = parts[0]
        
        # 搜集所有现有文件夹
        existing_folders = []
        search_dirs = set()
        if parent_dir.exists():
            search_dirs.add(parent_dir)
        search_dirs.add(self.organize_root)
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for item in search_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    try:
                        rel = str(item.relative_to(self.organize_root)).replace('\\', '/')
                        existing_folders.append(rel)
                    except ValueError:
                        pass
                    # 也检查二级目录
                    for sub_item in item.iterdir():
                        if sub_item.is_dir() and not sub_item.name.startswith('_'):
                            try:
                                rel = str(sub_item.relative_to(self.organize_root)).replace('\\', '/')
                                existing_folders.append(rel)
                            except ValueError:
                                pass
        
        if not existing_folders:
            return None
        
        # 清理建议名称的修订后缀
        entity_clean = self._clean_name_for_matching(entity_name)
        
        best_match = None
        best_score = 0.0
        
        for existing in existing_folders:
            existing_lower = existing.lower().replace('\\', '/')
            existing_leaf = existing_lower.split('/')[-1] if '/' in existing_lower else existing_lower
            existing_clean = self._clean_name_for_matching(existing_leaf)
            
            # 1. 精确匹配
            if existing_lower == suggested_folder.lower().replace('\\', '/'):
                return existing  # 完全相同
            
            # 2. 清理后精确匹配（如 test_doc_revised → test_doc）
            if entity_clean == existing_clean:
                return existing
            
            # 3. 前缀匹配（某个是另一个的前缀）
            if existing_clean.startswith(entity_clean) or entity_clean.startswith(existing_clean):
                shorter = min(len(entity_clean), len(existing_clean))
                longer = max(len(entity_clean), len(existing_clean), 1)
                score = shorter / longer
                if score > best_score:
                    best_score = score
                    best_match = existing
            
            # 4. 模糊匹配
            similarity = SequenceMatcher(None, entity_clean, existing_clean).ratio()
            if similarity > 0.6 and similarity > best_score:
                best_score = similarity
                best_match = existing
        
        if best_match and best_score >= 0.4:
            return best_match
        
        return None
    
    def _update_index(self, source_file: str, dest_file: str, folder: str, metadata: Optional[Dict] = None):
        """更新全局索引（含去重）"""
        with open(self.index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        file_size = Path(source_file).stat().st_size if Path(source_file).exists() else 0
        
        # ★ 去重：检查是否已有相同源文件和目标文件的记录
        for existing in index.get("files", []):
            if existing.get("organized_path") == dest_file:
                # 已存在相同记录，更新时间戳即可
                existing["organized_at"] = datetime.now().isoformat()
                index["last_updated"] = datetime.now().isoformat()
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, ensure_ascii=False, indent=2)
                return
        
        # 添加新条目
        entry = {
            "source_path": source_file,
            "organized_path": dest_file,
            "folder": folder,
            "file_name": Path(source_file).name,
            "file_size": file_size,
            "organized_at": datetime.now().isoformat()
        }

        if metadata:
            entry["metadata"] = metadata
            entity = metadata.get("entity")
            entity_type = metadata.get("entity_type")
            if entity:
                entry["entity"] = entity
            if entity_type:
                entry["entity_type"] = entity_type

        index["files"].append(entry)
        
        index["total_files"] = len(index["files"])
        index["last_updated"] = datetime.now().isoformat()
        
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def find_entity_folder(self, entity_name: str) -> Optional[str]:
        """Find an existing folder for the given entity name.
        Only returns the top-level entity folder (no deep subpaths).
        """
        if not entity_name:
            return None
        target = self._normalize_entity_name(entity_name)
        index = self.get_index()
        for entry in index.get("files", []):
            existing = entry.get("entity")
            if existing and self._normalize_entity_name(existing) == target:
                old_folder = entry.get("folder", "")
                # 只取第一级目录（实体名），不复用旧的深层路径
                top_level = old_folder.split("/")[0].split("\\")[0]
                if top_level:
                    return top_level
        return None
    
    def _update_folder_metadata(self, folder_path: Path):
        """更新文件夹的元数据"""
        metadata_file = folder_path / "_metadata.json"
        
        # 统计该文件夹下的文件
        file_count = len(list(folder_path.glob("*"))) - 1  # 减去metadata文件本身
        
        metadata = {
            "folder": str(folder_path.relative_to(self.organize_root)),
            "file_count": max(0, file_count),
            "last_updated": datetime.now().isoformat(),
            "files": [
                f.name for f in folder_path.glob("*") 
                if f.is_file() and not f.name.startswith("_")
            ]
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def get_index(self) -> Dict:
        """获取完整索引"""
        with open(self.index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def search_files(self, keyword: str) -> List[Dict]:
        """搜索已组织的文件"""
        index = self.get_index()
        results = []
        
        keyword_lower = keyword.lower()
        for entry in index.get("files", []):
            if (keyword_lower in entry.get("file_name", "").lower() or 
                keyword_lower in entry.get("folder", "").lower()):
                results.append(entry)
        
        return results
    
    def get_categories_stats(self) -> Dict:
        """获取分类统计信息"""
        index = self.get_index()
        stats = {}
        
        for entry in index.get("files", []):
            folder = entry.get("folder", "other")
            industry = folder.split("/")[0]
            
            if industry not in stats:
                stats[industry] = {
                    "count": 0,
                    "size": 0,
                    "files": []
                }
            
            stats[industry]["count"] += 1
            stats[industry]["size"] += entry.get("file_size", 0)
            stats[industry]["files"].append(entry.get("file_name"))
        
        return stats
    
    def list_organized_folders(self) -> Dict:
        """列出所有已创建的文件夹"""
        folders = {}
        
        for root, dirs, files in os.walk(self.organize_root):
            root_path = Path(root)
            
            # 跳过根目录和元数据文件
            if root_path == self.organize_root:
                continue
            
            relative = root_path.relative_to(self.organize_root)
            non_metadata_files = [f for f in files if not f.startswith("_")]
            
            if non_metadata_files:  # 只显示有文件的文件夹
                folders[str(relative)] = {
                    "file_count": len(non_metadata_files),
                    "files": non_metadata_files,
                    "full_path": str(root_path)
                }
        
        return folders
    
    def organize_batch(self, files_with_suggestions: List[Dict]) -> List[Dict]:
        """
        批量组织文件
        
        Args:
            files_with_suggestions: [
                {"file": "path", "folder": "suggested_folder"},
                ...
            ]
        
        Returns:
            List of organization results
        """
        results = []
        for item in files_with_suggestions:
            result = self.organize_file(
                item["file"],
                item["folder"],
                item.get("auto_confirm", False)
            )
            results.append(result)
        
        return results


# 快速测试
if __name__ == "__main__":
    organizer = FileOrganizer()
    
    # 测试统计
    print("\n📊 分类统计:")
    stats = organizer.get_categories_stats()
    for industry, info in stats.items():
        print(f"  {industry}: {info['count']} 文件")
    
    print("\n📁 已创建的文件夹:")
    folders = organizer.list_organized_folders()
    for folder, info in folders.items():
        print(f"  {folder}: {info['file_count']} 文件")
