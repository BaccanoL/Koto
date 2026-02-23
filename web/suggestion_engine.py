#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能建议引擎 - 基于用户行为的主动建议系统
分析用户操作模式，提供智能化的文件管理建议
"""

import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

from behavior_monitor import BehaviorMonitor
from knowledge_graph import KnowledgeGraph


class SuggestionEngine:
    """智能建议引擎 - 主动分析并生成建议"""
    
    # 建议类型
    SUGGESTION_ORGANIZE = "organize"  # 文件整理建议
    SUGGESTION_BACKUP = "backup"  # 备份建议
    SUGGESTION_CLEANUP = "cleanup"  # 清理建议
    SUGGESTION_RELATED = "related_files"  # 相关文件推荐
    SUGGESTION_OPTIMIZE = "optimize"  # 性能优化建议
    SUGGESTION_WORKFLOW = "workflow"  # 工作流建议
    
    # 建议优先级
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"
    
    def __init__(self, behavior_monitor: BehaviorMonitor = None,
                 knowledge_graph: KnowledgeGraph = None,
                 db_path: str = "config/suggestions.db"):
        """
        初始化建议引擎
        
        Args:
            behavior_monitor: 行为监控器实例
            knowledge_graph: 知识图谱实例
            db_path: 数据库路径
        """
        self.behavior_monitor = behavior_monitor or BehaviorMonitor()
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()
        self.db_path = db_path
        self._ensure_db()
        
        # 注册规则
        self.rules = [
            self._rule_repeated_file_pattern,
            self._rule_unorganized_files,
            self._rule_stale_files,
            self._rule_similar_searches,
            self._rule_related_files,
            self._rule_backup_reminder,
            self._rule_file_consolidation,
            self._rule_workspace_optimization
        ]
    
    def _ensure_db(self):
        """确保数据库和表结构存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 建议表 - 存储生成的建议
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL,
                context TEXT,  -- JSON格式的上下文数据
                action_items TEXT,  -- JSON格式的可执行操作
                created_at TEXT NOT NULL,
                dismissed_at TEXT,
                applied_at TEXT,
                status TEXT DEFAULT 'pending'  -- pending, dismissed, applied
            )
        """)
        
        # 规则执行历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rule_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                triggered BOOLEAN NOT NULL,
                suggestions_generated INTEGER DEFAULT 0,
                execution_time TEXT NOT NULL
            )
        """)
        
        # 用户反馈表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suggestion_feedback (
                suggestion_id INTEGER NOT NULL,
                feedback_type TEXT NOT NULL,  -- helpful, not_helpful, applied
                feedback_text TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(suggestion_id) REFERENCES suggestions(id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_status ON suggestions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_priority ON suggestions(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_created ON suggestions(created_at DESC)")
        
        conn.commit()
        conn.close()
    
    def generate_suggestions(self, force_regenerate: bool = False) -> List[Dict]:
        """
        生成所有建议
        
        Args:
            force_regenerate: 是否强制重新生成（忽略缓存）
            
        Returns:
            建议列表
        """
        suggestions = []
        
        # 如果不是强制重新生成，先检查是否有未处理的建议
        if not force_regenerate:
            existing = self.get_pending_suggestions()
            if existing:
                return existing
        
        # 运行所有规则
        for rule in self.rules:
            try:
                rule_name = rule.__name__
                triggered = False
                rule_suggestions = rule()
                
                if rule_suggestions:
                    triggered = True
                    suggestions.extend(rule_suggestions)
                
                # 记录规则执行历史
                self._log_rule_execution(rule_name, triggered, len(rule_suggestions or []))
                
            except Exception as e:
                print(f"规则执行失败 {rule.__name__}: {str(e)}")
        
        # 保存建议到数据库
        for suggestion in suggestions:
            self._save_suggestion(suggestion)
        
        return suggestions
    
    def _rule_repeated_file_pattern(self) -> List[Dict]:
        """规则: 检测重复文件模式，建议创建模板"""
        suggestions = []
        
        # 获取最近创建的文件
        recent_events = self.behavior_monitor.get_recent_events(
            limit=50,
            event_type=BehaviorMonitor.EVENT_FILE_CREATE
        )
        
        # 统计文件扩展名
        file_types = Counter()
        for event in recent_events:
            if event["file_path"]:
                ext = Path(event["file_path"]).suffix
                if ext:
                    file_types[ext] += 1
        
        # 如果某种类型文件创建超过5次，建议创建模板
        for ext, count in file_types.items():
            if count >= 5:
                suggestions.append({
                    "type": self.SUGGESTION_WORKFLOW,
                    "title": f"发现重复创建 {ext} 文件",
                    "description": f"你最近创建了 {count} 个 {ext} 文件。是否要创建一个模板来简化工作？",
                    "priority": self.PRIORITY_MEDIUM,
                    "context": {
                        "file_type": ext,
                        "count": count
                    },
                    "action_items": [
                        {
                            "label": "创建模板",
                            "action": "create_template",
                            "params": {"file_type": ext}
                        },
                        {
                            "label": "稍后提醒",
                            "action": "remind_later"
                        }
                    ]
                })
        
        return suggestions
    
    def _rule_unorganized_files(self) -> List[Dict]:
        """规则: 检测未整理的文件，建议分类"""
        suggestions = []
        
        # 获取经常使用的文件
        frequent_files = self.behavior_monitor.get_frequently_used_files(limit=20)
        
        # 统计文件所在目录
        directories = Counter()
        for file_data in frequent_files:
            file_path = file_data["file_path"]
            directory = str(Path(file_path).parent)
            directories[directory] += 1
        
        # 如果某个目录有超过5个常用文件，建议创建子文件夹
        for directory, count in directories.items():
            if count >= 5:
                suggestions.append({
                    "type": self.SUGGESTION_ORGANIZE,
                    "title": f"建议整理 {directory}",
                    "description": f"该目录下有 {count} 个常用文件，建议创建子文件夹进行分类整理。",
                    "priority": self.PRIORITY_LOW,
                    "context": {
                        "directory": directory,
                        "file_count": count
                    },
                    "action_items": [
                        {
                            "label": "自动分类",
                            "action": "auto_organize",
                            "params": {"directory": directory}
                        },
                        {
                            "label": "手动整理",
                            "action": "manual_organize"
                        }
                    ]
                })
        
        return suggestions
    
    def _rule_stale_files(self) -> List[Dict]:
        """规则: 检测过时文件，建议归档或删除"""
        suggestions = []
        
        # 这里简化实现，实际应该扫描文件系统
        # 获取很久没用的文件
        frequent_files = self.behavior_monitor.get_frequently_used_files(limit=100)
        
        stale_files = []
        cutoff_date = datetime.now() - timedelta(days=90)
        
        for file_data in frequent_files:
            last_opened = file_data.get("last_opened")
            if last_opened:
                last_opened_dt = datetime.fromisoformat(last_opened)
                if last_opened_dt < cutoff_date:
                    stale_files.append(file_data)
        
        if len(stale_files) >= 10:
            suggestions.append({
                "type": self.SUGGESTION_CLEANUP,
                "title": "发现长期未使用的文件",
                "description": f"有 {len(stale_files)} 个文件超过90天未打开，建议归档或清理。",
                "priority": self.PRIORITY_LOW,
                "context": {
                    "stale_count": len(stale_files),
                    "cutoff_days": 90
                },
                "action_items": [
                    {
                        "label": "查看列表",
                        "action": "show_stale_files"
                    },
                    {
                        "label": "一键归档",
                        "action": "archive_stale_files"
                    }
                ]
            })
        
        return suggestions
    
    def _rule_similar_searches(self) -> List[Dict]:
        """规则: 检测重复搜索，建议保存或优化"""
        suggestions = []
        
        # 获取搜索历史
        search_history = self.behavior_monitor.get_search_history(limit=50)
        
        # 统计搜索查询
        query_counts = Counter()
        for search in search_history:
            query = search["query"].lower().strip()
            if query:
                query_counts[query] += 1
        
        # 找出重复搜索
        for query, count in query_counts.items():
            if count >= 3:
                suggestions.append({
                    "type": self.SUGGESTION_WORKFLOW,
                    "title": f"重复搜索: \"{query}\"",
                    "description": f"你搜索了 \"{query}\" {count} 次。是否要保存为快捷搜索？",
                    "priority": self.PRIORITY_MEDIUM,
                    "context": {
                        "query": query,
                        "count": count
                    },
                    "action_items": [
                        {
                            "label": "保存快捷搜索",
                            "action": "save_search",
                            "params": {"query": query}
                        },
                        {
                            "label": "忽略",
                            "action": "dismiss"
                        }
                    ]
                })
        
        return suggestions
    
    def _rule_related_files(self) -> List[Dict]:
        """规则: 基于知识图谱推荐相关文件"""
        suggestions = []
        
        # 获取最近打开的文件
        recent_events = self.behavior_monitor.get_recent_events(
            limit=5,
            event_type=BehaviorMonitor.EVENT_FILE_OPEN
        )
        
        if not recent_events:
            return suggestions
        
        # 对最近打开的文件，查找相关文件
        current_file = recent_events[0]["file_path"]
        if not current_file:
            return suggestions
        
        try:
            # 使用概念提取器查找相关文件
            related_files = self.knowledge_graph.concept_extractor.find_related_files(
                current_file, 
                limit=3
            )
            
            if related_files:
                file_names = [Path(f["file_path"]).name for f in related_files[:3]]
                
                suggestions.append({
                    "type": self.SUGGESTION_RELATED,
                    "title": "你可能还需要这些文件",
                    "description": f"基于 \"{Path(current_file).name}\" 的内容，推荐相关文件。",
                    "priority": self.PRIORITY_LOW,
                    "context": {
                        "current_file": current_file,
                        "related_files": [f["file_path"] for f in related_files]
                    },
                    "action_items": [
                        {
                            "label": f"打开 {name}",
                            "action": "open_file",
                            "params": {"file_path": related_files[i]["file_path"]}
                        }
                        for i, name in enumerate(file_names)
                    ]
                })
        except Exception as e:
            pass  # 忽略错误
        
        return suggestions
    
    def _rule_backup_reminder(self) -> List[Dict]:
        """规则: 提醒备份重要文件"""
        suggestions = []
        
        # 获取编辑频繁的文件
        frequent_files = self.behavior_monitor.get_frequently_used_files(limit=10)
        
        high_edit_files = [
            f for f in frequent_files 
            if f.get("edit_count", 0) >= 10
        ]
        
        if high_edit_files:
            suggestions.append({
                "type": self.SUGGESTION_BACKUP,
                "title": "建议备份重要文件",
                "description": f"有 {len(high_edit_files)} 个文件编辑频繁，建议创建备份。",
                "priority": self.PRIORITY_MEDIUM,
                "context": {
                    "file_count": len(high_edit_files),
                    "files": [f["file_path"] for f in high_edit_files[:5]]
                },
                "action_items": [
                    {
                        "label": "立即备份",
                        "action": "backup_files",
                        "params": {"files": [f["file_path"] for f in high_edit_files]}
                    },
                    {
                        "label": "设置自动备份",
                        "action": "setup_auto_backup"
                    }
                ]
            })
        
        return suggestions
    
    def _rule_file_consolidation(self) -> List[Dict]:
        """规则: 检测分散的相关文件，建议合并"""
        suggestions = []
        
        # 获取知识图谱统计
        try:
            stats = self.knowledge_graph.get_statistics()
            
            # 如果文件关联度高，但分散在不同目录
            if stats.get("file_relation_edges", 0) > 20:
                suggestions.append({
                    "type": self.SUGGESTION_ORGANIZE,
                    "title": "发现分散的相关文件",
                    "description": "系统检测到多个相关文件分散在不同位置，建议整合到同一目录。",
                    "priority": self.PRIORITY_LOW,
                    "context": {
                        "relation_count": stats["file_relation_edges"]
                    },
                    "action_items": [
                        {
                            "label": "查看关联图",
                            "action": "show_knowledge_graph"
                        },
                        {
                            "label": "智能整合",
                            "action": "consolidate_related_files"
                        }
                    ]
                })
        except Exception as e:
            pass
        
        return suggestions
    
    def _rule_workspace_optimization(self) -> List[Dict]:
        """规则: 工作空间优化建议"""
        suggestions = []
        
        # 获取用户工作模式
        patterns = self.behavior_monitor.get_work_patterns()
        
        # 分析最活跃的时间段
        time_patterns = patterns.get("time_of_day", [])
        if time_patterns:
            most_active = time_patterns[0]
            period = most_active["period"]
            
            period_names = {
                "morning": "早晨",
                "afternoon": "下午",
                "evening": "晚上",
                "night": "深夜"
            }
            
            suggestions.append({
                "type": self.SUGGESTION_OPTIMIZE,
                "title": "工作模式分析",
                "description": f"你通常在{period_names.get(period, period)}最活跃。是否要针对这个时段优化设置？",
                "priority": self.PRIORITY_LOW,
                "context": {
                    "active_period": period,
                    "frequency": most_active["frequency"]
                },
                "action_items": [
                    {
                        "label": "查看详细分析",
                        "action": "show_work_analysis"
                    },
                    {
                        "label": "优化设置",
                        "action": "optimize_for_period",
                        "params": {"period": period}
                    }
                ]
            })
        
        return suggestions
    
    def _save_suggestion(self, suggestion: Dict) -> int:
        """保存建议到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO suggestions 
            (suggestion_type, title, description, priority, context, action_items, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            suggestion["type"],
            suggestion["title"],
            suggestion["description"],
            suggestion["priority"],
            json.dumps(suggestion.get("context", {})),
            json.dumps(suggestion.get("action_items", [])),
            datetime.now().isoformat()
        ))
        
        suggestion_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return suggestion_id
    
    def _log_rule_execution(self, rule_name: str, triggered: bool, suggestions_count: int):
        """记录规则执行历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO rule_history (rule_name, triggered, suggestions_generated, execution_time)
            VALUES (?, ?, ?, ?)
        """, (rule_name, triggered, suggestions_count, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_pending_suggestions(self, limit: int = 10) -> List[Dict]:
        """获取待处理的建议"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, suggestion_type, title, description, priority, context, action_items, created_at
            FROM suggestions
            WHERE status = 'pending'
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                created_at DESC
            LIMIT ?
        """, (limit,))
        
        suggestions = []
        for row in cursor.fetchall():
            suggestions.append({
                "id": row[0],
                "type": row[1],
                "title": row[2],
                "description": row[3],
                "priority": row[4],
                "context": json.loads(row[5]),
                "action_items": json.loads(row[6]),
                "created_at": row[7]
            })
        
        conn.close()
        return suggestions
    
    def dismiss_suggestion(self, suggestion_id: int, feedback: Optional[str] = None):
        """拒绝建议"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE suggestions
            SET status = 'dismissed', dismissed_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), suggestion_id))
        
        if feedback:
            cursor.execute("""
                INSERT INTO suggestion_feedback (suggestion_id, feedback_type, feedback_text, timestamp)
                VALUES (?, 'not_helpful', ?, ?)
            """, (suggestion_id, feedback, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def apply_suggestion(self, suggestion_id: int, feedback: Optional[str] = None):
        """应用建议"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE suggestions
            SET status = 'applied', applied_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), suggestion_id))
        
        if feedback:
            cursor.execute("""
                INSERT INTO suggestion_feedback (suggestion_id, feedback_type, feedback_text, timestamp)
                VALUES (?, 'applied', ?, ?)
            """, (suggestion_id, feedback, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        """获取建议引擎统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM suggestions")
        total_suggestions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM suggestions WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM suggestions WHERE status = 'applied'")
        applied = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM suggestions WHERE status = 'dismissed'")
        dismissed = cursor.fetchone()[0]
        
        # 应用率
        acceptance_rate = (applied / max(applied + dismissed, 1)) * 100
        
        conn.close()
        
        return {
            "total_suggestions": total_suggestions,
            "pending_suggestions": pending,
            "applied_suggestions": applied,
            "dismissed_suggestions": dismissed,
            "acceptance_rate": round(acceptance_rate, 2)
        }


if __name__ == "__main__":
    # 测试代码
    engine = SuggestionEngine()
    
    print("💡 智能建议引擎测试")
    print("=" * 50)
    
    # 生成建议
    suggestions = engine.generate_suggestions(force_regenerate=True)
    
    print(f"\n生成建议: {len(suggestions)} 条")
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"\n{i}. [{suggestion['priority'].upper()}] {suggestion['title']}")
        print(f"   {suggestion['description']}")
    
    # 获取统计信息
    stats = engine.get_statistics()
    print("\n统计信息：")
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    print("\n" + "=" * 50)
    print("✅ 智能建议引擎已就绪")
