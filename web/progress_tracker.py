#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
进度追踪系统 - 实时监测和报告文件生成及改进过程
支持通过 SSE (Server-Sent Events) 向前端推送进度更新
"""

import json
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class TaskStage(str, Enum):
    """任务阶段"""
    VALIDATING = "validating"  # 验证输入
    EVALUATING = "evaluating"  # 评估内容质量
    IMPROVING = "improving"     # 改进内容
    GENERATING = "generating"   # 生成文件
    COMPLETED = "completed"     # 完成
    ERROR = "error"             # 错误


@dataclass
class ProgressUpdate:
    """进度更新"""
    task_id: str
    stage: str  # TaskStage 值
    progress_percent: int  # 0-100
    message: str
    timestamp: str
    details: Optional[Dict] = None  # 额外详情
    
    def to_json(self) -> str:
        """转换为 SSE JSON 事件"""
        return json.dumps(asdict(self), ensure_ascii=False)


class ProgressTracker:
    """进度追踪器 - 管理单个任务的进度"""
    
    def __init__(self, task_id: str, total_stages: int = 4):
        """
        Args:
            task_id: 任务 ID（通常是文件生成的 session 或 task ID）
            total_stages: 总阶段数（用于计算进度百分比）
        """
        self.task_id = task_id
        self.total_stages = total_stages
        self.current_stage = 0
        self.stage_progress = 0  # 当前阶段的进度（0-100）
        self.history: List[ProgressUpdate] = []
        self._lock = threading.Lock()
    
    def update(
        self,
        stage: str,
        message: str,
        stage_progress: int = 100,
        details: Optional[Dict] = None
    ) -> ProgressUpdate:
        """更新进度
        
        Args:
            stage: 当前阶段（TaskStage 值之一）
            message: 进度消息
            stage_progress: 当前阶段的进度（0-100，默认100表示该阶段完成）
            details: 额外详情
        
        Returns:
            进度更新对象
        """
        with self._lock:
            # 计算总体进度百分比
            stage_map = {
                TaskStage.VALIDATING.value: 0,
                TaskStage.EVALUATING.value: 1,
                TaskStage.IMPROVING.value: 2,
                TaskStage.GENERATING.value: 3,
                TaskStage.COMPLETED.value: 4,
                TaskStage.ERROR.value: -1,
            }
            
            if stage in stage_map and stage_map[stage] >= 0:
                self.current_stage = stage_map[stage]
                self.stage_progress = stage_progress
            
            # 计算总进度
            if stage == TaskStage.COMPLETED.value:
                overall_progress = 100
            elif stage == TaskStage.ERROR.value:
                overall_progress = 0
            else:
                overall_progress = int((self.current_stage / max(1, self.total_stages - 1)) * 100)
                if self.stage_progress < 100 and self.current_stage < self.total_stages - 1:
                    overall_progress = int(
                        (self.current_stage * 100 + self.stage_progress) / max(1, self.total_stages) * 2 / 3
                    )
            
            update = ProgressUpdate(
                task_id=self.task_id,
                stage=stage,
                progress_percent=min(100, max(0, overall_progress)),
                message=message,
                timestamp=datetime.now().isoformat(),
                details=details
            )
            
            self.history.append(update)
            return update
    
    def get_current_progress(self) -> ProgressUpdate:
        """获取当前进度"""
        with self._lock:
            if self.history:
                return self.history[-1]
            return ProgressUpdate(
                task_id=self.task_id,
                stage=TaskStage.VALIDATING.value,
                progress_percent=0,
                message="准备中...",
                timestamp=datetime.now().isoformat()
            )


class ProgressBroadcaster:
    """进度广播器 - 向多个客户端推送进度更新（SSE）"""
    
    def __init__(self):
        self._trackers: Dict[str, ProgressTracker] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def create_tracker(self, task_id: str, total_stages: int = 4) -> ProgressTracker:
        """创建新的进度追踪器"""
        with self._lock:
            if task_id not in self._trackers:
                self._trackers[task_id] = ProgressTracker(task_id, total_stages)
                self._subscribers[task_id] = []
            return self._trackers[task_id]
    
    def get_tracker(self, task_id: str) -> Optional[ProgressTracker]:
        """获取现有追踪器"""
        return self._trackers.get(task_id)
    
    def subscribe(self, task_id: str, listener: Callable):
        """订阅进度更新
        
        Args:
            task_id: 任务 ID
            listener: 回调函数，签名：listener(update: ProgressUpdate)
        """
        with self._lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = []
            self._subscribers[task_id].append(listener)
    
    def broadcast(self, task_id: str, update: ProgressUpdate):
        """广播进度更新给所有订阅者"""
        with self._lock:
            listeners = self._subscribers.get(task_id, [])
        
        for listener in listeners:
            try:
                listener(update)
            except Exception as e:
                print(f"[进度广播] 监听器异常: {e}")
    
    def update_and_broadcast(
        self,
        task_id: str,
        stage: str,
        message: str,
        stage_progress: int = 100,
        details: Optional[Dict] = None
    ) -> ProgressUpdate:
        """更新进度并广播"""
        tracker = self.get_tracker(task_id)
        if not tracker:
            tracker = self.create_tracker(task_id)
        
        update = tracker.update(stage, message, stage_progress, details)
        self.broadcast(task_id, update)
        return update
    
    def cleanup(self, task_id: str):
        """清理任务的进度记录（节省内存）"""
        with self._lock:
            self._trackers.pop(task_id, None)
            self._subscribers.pop(task_id, None)


class GenerationProgressManager:
    """文件生成进度管理器 - 高级接口"""
    
    def __init__(self, broadcaster: ProgressBroadcaster):
        self.broadcaster = broadcaster
    
    def track_document_generation(
        self,
        task_id: str,
        emit_progress: Callable[[str], None],
        enable_quality_check: bool = True,
        enable_improvement: bool = True
    ) -> Dict[str, str]:
        """创建文档生成的进度追踪器
        
        Args:
            task_id: 任务 ID
            emit_progress: SSE 发送函数，签名：emit_progress(json_string)
            enable_quality_check: 是否启用质量检查
            enable_improvement: 是否启用内容改进
        
        Returns:
            进度回调函数的字典
        """
        tracker = self.broadcaster.create_tracker(task_id, total_stages=4)
        
        def emit_update(update: ProgressUpdate):
            try:
                json_str = update.to_json()
                emit_progress(json_str)
            except Exception as e:
                print(f"[生成进度] SSE 发送失败: {e}")
        
        self.broadcaster.subscribe(task_id, emit_update)
        
        # 第1步：验证
        self.broadcaster.update_and_broadcast(
            task_id,
            TaskStage.VALIDATING.value,
            "正在验证输入内容...",
            details={"step": 1, "total_steps": 4}
        )
        
        # 第2步：评估（如果启用）
        quality_check_callback = None
        if enable_quality_check:
            def quality_check_callback(stage: str, message: str):
                progress = 30 if stage == "evaluating" else 60 if stage == "improving" else 90
                self.broadcaster.update_and_broadcast(
                    task_id,
                    TaskStage.EVALUATING.value if stage == "evaluating" else TaskStage.IMPROVING.value,
                    message,
                    stage_progress=progress,
                    details={"stage": stage}
                )
        
        return {
            "task_id": task_id,
            "tracker": tracker,
            "quality_callback": quality_check_callback,
            "emit_update": lambda stage, msg, pct=100, details=None: 
                self.broadcaster.update_and_broadcast(task_id, stage, msg, pct, details)
        }
    
    def mark_generating(self, task_id: str, file_type: str):
        """标记开始生成文件"""
        self.broadcaster.update_and_broadcast(
            task_id,
            TaskStage.GENERATING.value,
            f"正在生成 {file_type.upper()} 文件...",
            stage_progress=80
        )
    
    def mark_completed(self, task_id: str, file_path: str, details: Optional[Dict] = None):
        """标记生成完成"""
        detail_info = {
            "file_path": file_path,
            **(details or {})
        }
        self.broadcaster.update_and_broadcast(
            task_id,
            TaskStage.COMPLETED.value,
            "文件生成完成！",
            stage_progress=100,
            details=detail_info
        )
        # 清理任务数据（5秒后，给客户端时间接收）
        threading.Timer(5.0, lambda: self.broadcaster.cleanup(task_id)).start()
    
    def mark_error(self, task_id: str, error_message: str):
        """标记生成错误"""
        self.broadcaster.update_and_broadcast(
            task_id,
            TaskStage.ERROR.value,
            f"生成失败: {error_message}",
            stage_progress=0,
            details={"error": error_message}
        )
        # 清理任务数据
        threading.Timer(5.0, lambda: self.broadcaster.cleanup(task_id)).start()


# 全局广播器实例
_global_broadcaster = ProgressBroadcaster()
_global_progress_manager = GenerationProgressManager(_global_broadcaster)


def get_progress_broadcaster() -> ProgressBroadcaster:
    """获取全局进度广播器"""
    return _global_broadcaster


def get_progress_manager() -> GenerationProgressManager:
    """获取全局进度管理器"""
    return _global_progress_manager
