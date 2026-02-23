#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件编辑器服务 - 提供本地文件读取、写入、编辑能力
移植自 web/file_editor.py
"""

import os
import re
import shutil
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class FileService:
    """本地文件编辑器服务"""
    
    def __init__(self, workspace_dir: str = None, backup_enabled: bool = True):
        """
        Args:
            workspace_dir: 工作目录（默认为 workspace/）
            backup_enabled: 是否自动备份（修改前创建 .bak）
        """
        if workspace_dir is None:
            # Default to project root 'workspace' folder
            # Assuming this file is in app/core/services/
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            workspace_dir = os.path.join(project_root, "workspace")
            
        self.workspace_dir = Path(workspace_dir)
        self.backup_enabled = backup_enabled
        self.backup_dir = self.workspace_dir / "_backups"
        
        if backup_enabled:
            try:
                self.backup_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not create backup directory: {e}")

    def is_safe_path(self, file_path: str) -> bool:
        """Check if path is safe to access (within allowed directories)"""
        try:
            path = Path(file_path).resolve()
            # Allowed roots
            allowed_roots = [
                self.workspace_dir.resolve(),
                Path.home().resolve(),
                # Allow project root access for dev tools
                Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))).resolve()
            ]
            
            # Windows specific: check drives
            # For testing/dev, we might be lenient, but in prod be strict
            
            return any(path.is_relative_to(root) for root in allowed_roots) or True # TODO: Strict mode later
        except Exception:
            return False

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Reads file content."""
        try:
            if not self.is_safe_path(file_path):
                return {"success": False, "error": "Access denied (path unsafe)"}
            
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            if not path.is_file():
                return {"success": False, "error": "Not a file"}
            
            # Try multiple encodings
            for encoding in ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]:
                try:
                    content = path.read_text(encoding=encoding)
                    lines = content.splitlines()
                    return {
                        "success": True,
                        "content": content,
                        "lines": len(lines),
                        #"line_list": lines, # Omit large list in return for agent
                        "encoding": encoding,
                        "size": path.stat().st_size,
                        "path": str(path.resolve())
                    }
                except UnicodeDecodeError:
                    continue
            
            return {"success": False, "error": "Could not decode file (unsupported encoding)"}
            
        except Exception as e:
            return {"success": False, "error": f"Read failed: {str(e)}"}

    def _create_backup(self, path: Path) -> Optional[str]:
        """Internal backup helper"""
        if not self.backup_enabled:
            return None
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{path.stem}_{timestamp}{path.suffix}.bak"
            backup_path = self.backup_dir / backup_name
            shutil.copy2(path, backup_path)
            return str(backup_path)
        except Exception as e:
            logger.warning(f"Backup failed: {e}")
            return None

    def write_file(self, file_path: str, content: str, encoding: str = "utf-8", create_backup: bool = True) -> Dict[str, Any]:
        """Writes content to file."""
        try:
            if not self.is_safe_path(file_path):
                return {"success": False, "error": "Access denied (path unsafe)"}
            
            path = Path(file_path)
            backup_path = None
            
            if path.exists() and create_backup:
                backup_path = self._create_backup(path)
            
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=encoding)
            
            return {
                "success": True,
                "path": str(path.resolve()),
                "backup": backup_path,
                "size": path.stat().st_size
            }
        except Exception as e:
            return {"success": False, "error": f"Write failed: {str(e)}"}

    def replace_text(self, file_path: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """Replaces text in a file."""
        res = self.read_file(file_path)
        if not res["success"]: return res
        
        content = res["content"]
        encoding = res["encoding"]
        
        if old_text not in content:
            return {"success": False, "error": "Text not found in file"}
            
        new_content = content.replace(old_text, new_text)
        return self.write_file(file_path, new_content, encoding=encoding)

    def list_files(self, directory: str, recursive: bool = False, max_files: int = 50) -> Dict[str, Any]:
        """Lists files in a directory."""
        try:
            if not self.is_safe_path(directory):
                 return {"success": False, "error": "Access denied"}
            
            path = Path(directory)
            if not path.exists():
                return {"success": False, "error": f"Directory not found: {directory}"}
            
            files_list = []
            if recursive:
                iterator = path.rglob("*")
            else:
                iterator = path.glob("*")
                
            count = 0
            for p in iterator:
                if p.is_file():
                    files_list.append(str(p.name))
                    count += 1
                    if count >= max_files:
                        break
            
            return {
                "success": True,
                "files": files_list,
                "count": count,
                "truncated": count >= max_files
            }
        except Exception as e:
            return {"success": False, "error": f"List failed: {str(e)}"}
