"""
🔐 权限管理系统 (Permission Management System)

功能:
- RBAC (Role-Based Access Control)
- 细粒度文件级权限
- 分享链接管理
- 权限缓存 (Redis)

权限粒度:
├─ view     (查看)
├─ edit     (编辑)  
├─ delete   (删除)
├─ share    (分享)
├─ comment  (评论)
└─ download (下载)
"""

import sqlite3
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class Permission(Enum):
    """权限枚举"""
    VIEW = "view"
    EDIT = "edit"
    DELETE = "delete"
    SHARE = "share"
    COMMENT = "comment"
    DOWNLOAD = "download"
    MANAGE = "manage"  # 管理权限


class Role(Enum):
    """角色枚举"""
    ADMIN = "admin"          # 所有权限
    EDITOR = "editor"        # 编辑/删除/评论
    MEMBER = "member"        # 查看/评论
    VIEWER = "viewer"        # 仅查看
    CUSTOM = "custom"        # 自定义权限


# 默认角色权限映射
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.VIEW,
        Permission.EDIT,
        Permission.DELETE,
        Permission.SHARE,
        Permission.COMMENT,
        Permission.DOWNLOAD,
        Permission.MANAGE
    ],
    Role.EDITOR: [
        Permission.VIEW,
        Permission.EDIT,
        Permission.DELETE,
        Permission.COMMENT,
        Permission.DOWNLOAD
    ],
    Role.MEMBER: [
        Permission.VIEW,
        Permission.COMMENT,
        Permission.DOWNLOAD
    ],
    Role.VIEWER: [
        Permission.VIEW,
        Permission.DOWNLOAD
    ]
}


@dataclass
class FilePermission:
    """文件权限记录"""
    id: str
    file_id: str
    grantee_id: str  # user_id 或 team_id
    grantee_type: str  # user, team, organization
    permissions: List[str]
    granted_by: str
    granted_at: str
    expires_at: Optional[str] = None
    is_inherited: bool = False  # 是否继承自文件夹


@dataclass
class ShareLink:
    """分享链接"""
    id: str
    file_id: str
    token: str
    created_by: str
    permissions: List[str]  # ["view", "download"]
    password_hash: Optional[str]
    access_count: int
    created_at: str
    expires_at: Optional[str]
    is_public: bool = True


class PermissionManager:
    """权限管理系统"""
    
    def __init__(self, db_path: str = ".koto_permissions.db"):
        self.db_path = db_path
        self._init_database()
        self.permission_cache = {}  # 简单内存缓存
    
    def _init_database(self):
        """初始化权限数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                password_hash TEXT,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # 组织表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                created_at TIMESTAMP,
                FOREIGN KEY(owner_id) REFERENCES users(id)
            )
        """)
        
        # 角色定义表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                name TEXT NOT NULL,
                permissions TEXT,
                is_custom BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP,
                FOREIGN KEY(organization_id) REFERENCES organizations(id)
            )
        """)
        
        # 用户-组织关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_organizations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                role_id TEXT,
                joined_at TIMESTAMP,
                UNIQUE(user_id, organization_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(organization_id) REFERENCES organizations(id),
                FOREIGN KEY(role_id) REFERENCES roles(id)
            )
        """)
        
        # 文件权限表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_permissions (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                grantee_id TEXT NOT NULL,
                grantee_type TEXT,
                permissions TEXT,
                granted_by TEXT,
                granted_at TIMESTAMP,
                expires_at TIMESTAMP,
                is_inherited BOOLEAN DEFAULT FALSE,
                organization_id TEXT,
                UNIQUE(file_id, grantee_id),
                INDEX idx_file (file_id),
                INDEX idx_grantee (grantee_id)
            )
        """)
        
        # 分享链接表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS share_links (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_by TEXT NOT NULL,
                permissions TEXT,
                password_hash TEXT,
                access_count INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                is_public BOOLEAN DEFAULT TRUE,
                organization_id TEXT,
                INDEX idx_token (token),
                INDEX idx_file (file_id)
            )
        """)
        
        # 权限变更历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permission_history (
                id TEXT PRIMARY KEY,
                file_id TEXT,
                resource_id TEXT,
                action TEXT,
                old_permissions TEXT,
                new_permissions TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP,
                organization_id TEXT,
                INDEX idx_file (file_id),
                INDEX idx_changed_at (changed_at)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== 权限检查 ====================
    
    def check_permission(
        self,
        user_id: str,
        file_id: str,
        action: str,
        organization_id: str = "default"
    ) -> bool:
        """
        检查用户是否有权限执行操作
        
        Args:
            user_id: 用户ID
            file_id: 文件ID
            action: 动作 (view, edit, delete等)
            organization_id: 组织ID
            
        Returns:
            True/False
        """
        # 检查缓存
        cache_key = f"{user_id}:{file_id}:{action}"
        if cache_key in self.permission_cache:
            cached_result, cached_time = self.permission_cache[cache_key]
            if time.time() - cached_time < 300:  # 5分钟缓存
                return cached_result
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否是组织admin
            cursor.execute("""
                SELECT uo.role_id FROM user_organizations uo
                WHERE uo.user_id = ? AND uo.organization_id = ?
            """, (user_id, organization_id))
            
            row = cursor.fetchone()
            if row:
                role_id = row[0]
                # 获取角色权限
                cursor.execute("""
                    SELECT permissions FROM roles WHERE id = ?
                """, (role_id,))
                
                role_row = cursor.fetchone()
                if role_row:
                    permissions = json.loads(role_row[0] or '[]')
                    if action in permissions:
                        self.permission_cache[cache_key] = (True, time.time())
                        return True
            
            # 检查文件级权限
            cursor.execute("""
                SELECT permissions, expires_at FROM file_permissions
                WHERE file_id = ? AND grantee_id = ?
                AND (expires_at IS NULL OR expires_at > ?)
            """, (file_id, user_id, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                permissions = json.loads(row[0] or '[]')
                has_permission = action in permissions
                self.permission_cache[cache_key] = (has_permission, time.time())
                return has_permission
            
            # 检查分享链接权限 (简化)
            result = False
            self.permission_cache[cache_key] = (result, time.time())
            return result
            
        finally:
            conn.close()
    
    # ==================== 权限授予 ====================
    
    def grant_permission(
        self,
        file_id: str,
        grantee_id: str,
        grantee_type: str,
        permissions: List[str],
        granted_by: str,
        organization_id: str = "default",
        expires_in_days: Optional[int] = None
    ) -> bool:
        """授予权限"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            expires_at = None
            if expires_in_days:
                expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
            
            permission_id = self._generate_id("perm")
            
            cursor.execute("""
                INSERT OR REPLACE INTO file_permissions (
                    id, file_id, grantee_id, grantee_type, permissions,
                    granted_by, granted_at, expires_at, organization_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                permission_id,
                file_id,
                grantee_id,
                grantee_type,
                json.dumps(permissions),
                granted_by,
                datetime.now().isoformat(),
                expires_at,
                organization_id
            ))
            
            # 记录变更历史
            self._record_permission_change(
                cursor,
                file_id,
                grantee_id,
                "grant",
                None,
                permissions,
                granted_by,
                organization_id
            )
            
            conn.commit()
            self._clear_cache(file_id)
            return True
            
        except Exception as e:
            print(f"Error granting permission: {e}")
            return False
        finally:
            conn.close()
    
    # ==================== 权限撤销 ====================
    
    def revoke_permission(
        self,
        file_id: str,
        grantee_id: str,
        revoked_by: str,
        organization_id: str = "default"
    ) -> bool:
        """撤销权限"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取原有权限
            cursor.execute("""
                SELECT permissions FROM file_permissions
                WHERE file_id = ? AND grantee_id = ?
            """, (file_id, grantee_id))
            
            row = cursor.fetchone()
            old_permissions = json.loads(row[0]) if row else []
            
            # 删除权限
            cursor.execute("""
                DELETE FROM file_permissions
                WHERE file_id = ? AND grantee_id = ?
            """, (file_id, grantee_id))
            
            # 记录变更
            self._record_permission_change(
                cursor,
                file_id,
                grantee_id,
                "revoke",
                old_permissions,
                [],
                revoked_by,
                organization_id
            )
            
            conn.commit()
            self._clear_cache(file_id)
            return True
            
        except Exception as e:
            print(f"Error revoking permission: {e}")
            return False
        finally:
            conn.close()
    
    # ==================== 分享链接 ====================
    
    def create_share_link(
        self,
        file_id: str,
        created_by: str,
        permissions: List[str] = None,
        password: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        organization_id: str = "default"
    ) -> Optional[str]:
        """
        创建分享链接
        
        Args:
            file_id: 文件ID
            created_by: 创建者ID
            permissions: 权限 (默认仅查看)
            password: 可选密码保护
            expires_in_days: 过期天数
            
        Returns:
            分享链接Token, 或None
        """
        if permissions is None:
            permissions = ["view", "download"]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            link_id = self._generate_id("link")
            token = secrets.token_urlsafe(16)
            
            password_hash = None
            if password:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            expires_at = None
            if expires_in_days:
                expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
            
            cursor.execute("""
                INSERT INTO share_links (
                    id, file_id, token, created_by, permissions,
                    password_hash, created_at, expires_at, organization_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                link_id,
                file_id,
                token,
                created_by,
                json.dumps(permissions),
                password_hash,
                datetime.now().isoformat(),
                expires_at,
                organization_id
            ))
            
            conn.commit()
            return token
            
        finally:
            conn.close()
    
    def access_share_link(
        self,
        token: str,
        password: Optional[str] = None
    ) -> Optional[Dict]:
        """
        访问分享链接
        
        Returns:
            {
                "file_id": "...",
                "permissions": ["view", "download"],
                "expired": False
            }
            或 None (无效/过期)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT file_id, permissions, password_hash, expires_at
                FROM share_links
                WHERE token = ? AND is_public = TRUE
            """, (token,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            file_id, perms, pwd_hash, expires_at = row
            
            # 检查过期
            if expires_at:
                if datetime.fromisoformat(expires_at) < datetime.now():
                    return None
            
            # 检查密码
            if pwd_hash:
                if not password:
                    return None
                if hashlib.sha256(password.encode()).hexdigest() != pwd_hash:
                    return None
            
            # 增加访问计数
            cursor.execute("""
                UPDATE share_links SET access_count = access_count + 1
                WHERE token = ?
            """, (token,))
            conn.commit()
            
            return {
                "file_id": file_id,
                "permissions": json.loads(perms),
                "expired": False
            }
            
        finally:
            conn.close()
    
    # ==================== 权限查询 ====================
    
    def get_file_permissions(self, file_id: str) -> List[Dict]:
        """获取文件的所有权限"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, grantee_id, grantee_type, permissions, granted_by, granted_at
                FROM file_permissions
                WHERE file_id = ?
            """, (file_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "grantee_id": row[1],
                    "grantee_type": row[2],
                    "permissions": json.loads(row[3]),
                    "granted_by": row[4],
                    "granted_at": row[5]
                })
            
            return results
            
        finally:
            conn.close()
    
    def get_user_files(self, user_id: str, organization_id: str = "default") -> List[Dict]:
        """获取用户有权访问的所有文件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DISTINCT file_id, permissions FROM file_permissions
                WHERE grantee_id = ? AND organization_id = ?
                AND (expires_at IS NULL OR expires_at > ?)
            """, (user_id, organization_id, datetime.now().isoformat()))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "file_id": row[0],
                    "permissions": json.loads(row[1])
                })
            
            return results
            
        finally:
            conn.close()
    
    # ==================== 权限历史 ====================
    
    def get_permission_history(
        self,
        file_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """获取权限变更历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, action, old_permissions, new_permissions, changed_by, changed_at
                FROM permission_history
                WHERE file_id = ?
                ORDER BY changed_at DESC
                LIMIT ?
            """, (file_id, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "action": row[1],
                    "old_permissions": json.loads(row[2] or '[]'),
                    "new_permissions": json.loads(row[3] or '[]'),
                    "changed_by": row[4],
                    "changed_at": row[5]
                })
            
            return results
            
        finally:
            conn.close()
    
    # ==================== 辅助方法 ====================
    
    def _record_permission_change(
        self,
        cursor,
        file_id: str,
        resource_id: str,
        action: str,
        old_perms,
        new_perms,
        changed_by: str,
        organization_id: str
    ):
        """记录权限变更"""
        history_id = self._generate_id("hist")
        cursor.execute("""
            INSERT INTO permission_history (
                id, file_id, resource_id, action, old_permissions, new_permissions,
                changed_by, changed_at, organization_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id,
            file_id,
            resource_id,
            action,
            json.dumps(old_perms) if old_perms else None,
            json.dumps(new_perms) if new_perms else None,
            changed_by,
            datetime.now().isoformat(),
            organization_id
        ))
    
    def _clear_cache(self, file_id: str):
        """清除特定文件的缓存"""
        keys_to_delete = [k for k in self.permission_cache.keys() if file_id in k]
        for key in keys_to_delete:
            del self.permission_cache[key]
    
    @staticmethod
    def _generate_id(prefix: str) -> str:
        """生成ID"""
        return f"{prefix}_{secrets.token_hex(8)}"


# 全局实例
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """获取全局权限管理器实例"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
