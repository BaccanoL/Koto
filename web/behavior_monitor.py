#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
行为监控模块 - 追踪用户文件操作行为
为智能建议和洞察报告提供数据基础
"""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict


class BehaviorMonitor:
    """用户行为监控器 - 追踪并分析用户操作"""
    
    # 定义事件类型
    EVENT_FILE_OPEN = "file_open"
    EVENT_FILE_EDIT = "file_edit"
    EVENT_FILE_CREATE = "file_create"
    EVENT_FILE_DELETE = "file_delete"
    EVENT_FILE_SEARCH = "file_search"
    EVENT_FILE_ORGANIZE = "file_organize"
    EVENT_ANNOTATION = "annotation"
    EVENT_EXPORT = "export"
    EVENT_VOICE_INPUT = "voice_input"
    EVENT_IMAGE_GEN = "image_generation"
    
    def __init__(self, db_path: str = "config/user_behavior.db"):
        """
        初始化行为监控器
        
        Args:
            db_path: SQLite数据库路径
        """
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """确保数据库和表结构存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 事件日志表 - 存储所有用户操作事件
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                file_path TEXT,
                session_id TEXT,
                event_data TEXT,  -- JSON格式的额外数据
                timestamp TEXT NOT NULL,
                duration_ms INTEGER  -- 操作持续时间（毫秒）
            )
        """)
        
        # 文件使用统计表 - 聚合的文件使用数据
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_usage_stats (
                file_path TEXT PRIMARY KEY,
                open_count INTEGER DEFAULT 0,
                edit_count INTEGER DEFAULT 0,
                last_opened TEXT,
                last_edited TEXT,
                total_time_spent_ms INTEGER DEFAULT 0,
                favorite BOOLEAN DEFAULT 0
            )
        """)
        
        # 搜索历史表 - 存储用户搜索记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                result_count INTEGER,
                clicked_result TEXT,  -- 用户点击的结果
                timestamp TEXT NOT NULL
            )
        """)
        
        # 用户会话表 - 记录用户使用会话
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                event_count INTEGER DEFAULT 0,
                files_touched INTEGER DEFAULT 0
            )
        """)
        
        # 工作模式表 - 分析用户工作模式
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,  -- 'time_of_day', 'file_type', 'operation_type'
                pattern_value TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_observed TEXT NOT NULL,
                UNIQUE(pattern_type, pattern_value)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON event_log(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_timestamp ON event_log(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_file ON event_log(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_query ON search_history(query)")
        
        conn.commit()
        conn.close()
    
    def log_event(self, event_type: str, file_path: Optional[str] = None,
                  session_id: Optional[str] = None, event_data: Optional[Dict] = None,
                  duration_ms: Optional[int] = None) -> int:
        """
        记录用户操作事件
        
        Args:
            event_type: 事件类型
            file_path: 相关文件路径（可选）
            session_id: 会话ID（可选）
            event_data: 额外的事件数据（可选）
            duration_ms: 操作持续时间（毫秒）
            
        Returns:
            事件ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        event_data_json = json.dumps(event_data or {})
        
        cursor.execute("""
            INSERT INTO event_log (event_type, file_path, session_id, event_data, timestamp, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_type, file_path, session_id, event_data_json, timestamp, duration_ms))
        
        event_id = cursor.lastrowid
        
        # 更新文件使用统计
        if file_path:
            self._update_file_stats(cursor, event_type, file_path, timestamp, duration_ms or 0)
        
        # 更新工作模式
        self._update_work_pattern(cursor, event_type, timestamp)
        
        conn.commit()
        conn.close()
        
        return event_id
    
    def _update_file_stats(self, cursor, event_type: str, file_path: str, 
                           timestamp: str, duration_ms: int):
        """更新文件使用统计"""
        # 获取当前统计
        cursor.execute("SELECT * FROM file_usage_stats WHERE file_path = ?", (file_path,))
        stats = cursor.fetchone()
        
        if stats is None:
            # 创建新记录
            cursor.execute("""
                INSERT INTO file_usage_stats 
                (file_path, open_count, edit_count, last_opened, last_edited, total_time_spent_ms)
                VALUES (?, 0, 0, NULL, NULL, 0)
            """, (file_path,))
        
        # 更新统计
        if event_type == self.EVENT_FILE_OPEN:
            cursor.execute("""
                UPDATE file_usage_stats
                SET open_count = open_count + 1,
                    last_opened = ?,
                    total_time_spent_ms = total_time_spent_ms + ?
                WHERE file_path = ?
            """, (timestamp, duration_ms, file_path))
        
        elif event_type == self.EVENT_FILE_EDIT:
            cursor.execute("""
                UPDATE file_usage_stats
                SET edit_count = edit_count + 1,
                    last_edited = ?,
                    total_time_spent_ms = total_time_spent_ms + ?
                WHERE file_path = ?
            """, (timestamp, duration_ms, file_path))
    
    def _update_work_pattern(self, cursor, event_type: str, timestamp: str):
        """更新工作模式统计"""
        dt = datetime.fromisoformat(timestamp)
        
        # 记录时间模式（早晨/下午/晚上）
        hour = dt.hour
        if 6 <= hour < 12:
            time_pattern = "morning"
        elif 12 <= hour < 18:
            time_pattern = "afternoon"
        elif 18 <= hour < 24:
            time_pattern = "evening"
        else:
            time_pattern = "night"
        
        cursor.execute("""
            INSERT INTO work_patterns (pattern_type, pattern_value, frequency, last_observed)
            VALUES ('time_of_day', ?, 1, ?)
            ON CONFLICT(pattern_type, pattern_value) DO UPDATE SET
                frequency = frequency + 1,
                last_observed = ?
        """, (time_pattern, timestamp, timestamp))
        
        # 记录操作类型模式
        cursor.execute("""
            INSERT INTO work_patterns (pattern_type, pattern_value, frequency, last_observed)
            VALUES ('operation_type', ?, 1, ?)
            ON CONFLICT(pattern_type, pattern_value) DO UPDATE SET
                frequency = frequency + 1,
                last_observed = ?
        """, (event_type, timestamp, timestamp))
    
    def log_search(self, query: str, result_count: int, clicked_result: Optional[str] = None) -> int:
        """
        记录搜索事件
        
        Args:
            query: 搜索查询
            result_count: 结果数量
            clicked_result: 用户点击的结果
            
        Returns:
            搜索记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO search_history (query, result_count, clicked_result, timestamp)
            VALUES (?, ?, ?, ?)
        """, (query, result_count, clicked_result, timestamp))
        
        search_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return search_id
    
    def get_recent_events(self, limit: int = 50, event_type: Optional[str] = None) -> List[Dict]:
        """
        获取最近的事件
        
        Args:
            limit: 返回数量限制
            event_type: 过滤特定事件类型（可选）
            
        Returns:
            事件列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if event_type:
            cursor.execute("""
                SELECT event_type, file_path, event_data, timestamp, duration_ms
                FROM event_log
                WHERE event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (event_type, limit))
        else:
            cursor.execute("""
                SELECT event_type, file_path, event_data, timestamp, duration_ms
                FROM event_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        events = []
        for row in cursor.fetchall():
            event_type, file_path, event_data_str, timestamp, duration_ms = row
            
            try:
                event_data = json.loads(event_data_str)
            except:
                event_data = {}
            
            events.append({
                "event_type": event_type,
                "file_path": file_path,
                "event_data": event_data,
                "timestamp": timestamp,
                "duration_ms": duration_ms
            })
        
        conn.close()
        return events
    
    def get_frequently_used_files(self, limit: int = 10) -> List[Dict]:
        """
        获取最常用的文件
        
        Args:
            limit: 返回数量限制
            
        Returns:
            文件列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, open_count, edit_count, last_opened, total_time_spent_ms
            FROM file_usage_stats
            ORDER BY (open_count + edit_count * 2) DESC
            LIMIT ?
        """, (limit,))
        
        files = []
        for row in cursor.fetchall():
            file_path, open_count, edit_count, last_opened, total_time = row
            
            files.append({
                "file_path": file_path,
                "open_count": open_count,
                "edit_count": edit_count,
                "last_opened": last_opened,
                "total_time_spent_ms": total_time,
                "usage_score": open_count + edit_count * 2
            })
        
        conn.close()
        return files
    
    def get_search_history(self, limit: int = 20) -> List[Dict]:
        """
        获取搜索历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            搜索历史列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT query, result_count, clicked_result, timestamp
            FROM search_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        history = []
        for row in cursor.fetchall():
            query, result_count, clicked_result, timestamp = row
            
            history.append({
                "query": query,
                "result_count": result_count,
                "clicked_result": clicked_result,
                "timestamp": timestamp
            })
        
        conn.close()
        return history
    
    def get_work_patterns(self) -> Dict:
        """
        获取用户工作模式分析
        
        Returns:
            工作模式字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        patterns = {}
        
        # 获取时间模式
        cursor.execute("""
            SELECT pattern_value, frequency
            FROM work_patterns
            WHERE pattern_type = 'time_of_day'
            ORDER BY frequency DESC
        """)
        
        patterns["time_of_day"] = [
            {"period": row[0], "frequency": row[1]}
            for row in cursor.fetchall()
        ]
        
        # 获取操作类型模式
        cursor.execute("""
            SELECT pattern_value, frequency
            FROM work_patterns
            WHERE pattern_type = 'operation_type'
            ORDER BY frequency DESC
        """)
        
        patterns["operation_types"] = [
            {"operation": row[0], "frequency": row[1]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return patterns
    
    def get_daily_activity(self, days: int = 7) -> List[Dict]:
        """
        获取每日活动统计
        
        Args:
            days: 统计天数
            
        Returns:
            每日统计列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM event_log
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (start_date,))
        
        activity = []
        for row in cursor.fetchall():
            date, count = row
            activity.append({
                "date": date,
                "event_count": count
            })
        
        conn.close()
        return activity
    
    def get_statistics(self) -> Dict:
        """获取总体统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总事件数
        cursor.execute("SELECT COUNT(*) FROM event_log")
        total_events = cursor.fetchone()[0]
        
        # 总文件数
        cursor.execute("SELECT COUNT(*) FROM file_usage_stats")
        total_files = cursor.fetchone()[0]
        
        # 总搜索数
        cursor.execute("SELECT COUNT(*) FROM search_history")
        total_searches = cursor.fetchone()[0]
        
        # 最活跃的操作类型
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM event_log
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        most_common_operation = result[0] if result else None
        
        # 最近7天活动
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM event_log WHERE timestamp >= ?
        """, (seven_days_ago,))
        recent_activity = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_events": total_events,
            "total_files_tracked": total_files,
            "total_searches": total_searches,
            "most_common_operation": most_common_operation,
            "last_7_days_events": recent_activity
        }
    
    def detect_anomalies(self) -> List[Dict]:
        """
        检测异常行为模式
        
        Returns:
            异常列表
        """
        anomalies = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检测1: 最近24小时内操作突然增多
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM event_log WHERE timestamp >= ?
        """, (yesterday,))
        recent_count = cursor.fetchone()[0]
        
        # 获取平均每日操作数
        cursor.execute("""
            SELECT COUNT(*) / MAX(1, (JULIANDAY('now') - JULIANDAY(MIN(timestamp))))
            FROM event_log
        """)
        avg_daily = cursor.fetchone()[0] or 0
        
        if recent_count > avg_daily * 3:  # 超过平均3倍
            anomalies.append({
                "type": "high_activity",
                "message": f"最近24小时操作异常频繁 ({recent_count} 次)",
                "severity": "info"
            })
        
        # 检测2: 多次搜索相同内容但没有点击结果
        cursor.execute("""
            SELECT query, COUNT(*) as count
            FROM search_history
            WHERE clicked_result IS NULL
            GROUP BY query
            HAVING count >= 3
            ORDER BY count DESC
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            query, count = row
            anomalies.append({
                "type": "unsuccessful_search",
                "message": f"搜索 '{query}' {count} 次但未点击结果",
                "severity": "warning",
                "suggestion": "可能需要改进搜索功能或内容索引"
            })
        
        conn.close()
        
        return anomalies


if __name__ == "__main__":
    # 测试代码
    monitor = BehaviorMonitor()
    
    print("📊 行为监控测试")
    print("=" * 50)
    
    # 记录一些测试事件
    monitor.log_event(
        BehaviorMonitor.EVENT_FILE_OPEN,
        file_path="test_document.txt",
        duration_ms=5000
    )
    
    monitor.log_event(
        BehaviorMonitor.EVENT_FILE_EDIT,
        file_path="test_document.txt",
        event_data={"lines_changed": 10},
        duration_ms=120000
    )
    
    monitor.log_search("机器学习", result_count=5, clicked_result="ml_guide.pdf")
    
    # 获取统计信息
    stats = monitor.get_statistics()
    print("\n统计信息：")
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    # 获取最近事件
    recent = monitor.get_recent_events(limit=5)
    print(f"\n最近事件: {len(recent)} 条")
    
    print("\n" + "=" * 50)
    print("✅ 行为监控模块已就绪")
