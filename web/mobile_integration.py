#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 14 - Mobile App Integration
Support for mobile clients, push notifications, and offline synchronization

This module provides:
1. Mobile API endpoints
2. Push notification system
3. Offline data synchronization
4. Mobile authentication
5. Device management
6. Mobile analytics
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import uuid


class DeviceType(Enum):
    """Mobile device types"""
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class SyncStatus(Enum):
    """Synchronization status"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


class PushNotificationPriority(Enum):
    """Push notification priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class MobileDevice:
    """Mobile device information"""
    device_id: str
    user_id: str
    device_type: DeviceType
    push_token: str
    device_name: str
    os_version: str
    app_version: str
    last_sync: str
    is_active: bool = True
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PushNotification:
    """Push notification"""
    notification_id: str
    device_id: str
    title: str
    body: str
    priority: PushNotificationPriority
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sent_at: Optional[str] = None
    delivered: bool = False


@dataclass
class SyncOperation:
    """Synchronization operation"""
    sync_id: str
    device_id: str
    operation_type: str  # "pull", "push"
    status: SyncStatus
    items_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class OfflineQueue:
    """Offline operation queue"""
    queue_id: str
    device_id: str
    operations: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    synced: bool = False


class DeviceManager:
    """Manage mobile devices"""
    
    def __init__(self):
        self.devices: Dict[str, MobileDevice] = {}
        self.user_devices: Dict[str, List[str]] = {}  # user_id -> [device_ids]
    
    def register_device(self, user_id: str, device_type: DeviceType,
                       device_name: str, push_token: str,
                       os_version: str, app_version: str) -> MobileDevice:
        """Register mobile device"""
        device_id = str(uuid.uuid4())
        device = MobileDevice(
            device_id=device_id,
            user_id=user_id,
            device_type=device_type,
            push_token=push_token,
            device_name=device_name,
            os_version=os_version,
            app_version=app_version,
            last_sync=datetime.now().isoformat()
        )
        
        self.devices[device_id] = device
        
        if user_id not in self.user_devices:
            self.user_devices[user_id] = []
        self.user_devices[user_id].append(device_id)
        
        return device
    
    def unregister_device(self, device_id: str) -> bool:
        """Unregister device"""
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        device.is_active = False
        
        return True
    
    def update_device_info(self, device_id: str, **kwargs) -> bool:
        """Update device information"""
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        device.last_sync = datetime.now().isoformat()
        return True
    
    def get_user_devices(self, user_id: str) -> List[MobileDevice]:
        """Get all devices for user"""
        if user_id not in self.user_devices:
            return []
        
        return [self.devices[dev_id] for dev_id in self.user_devices[user_id]
                if dev_id in self.devices]
    
    def get_device_stats(self) -> Dict[str, Any]:
        """Get device statistics"""
        active_devices = sum(1 for d in self.devices.values() if d.is_active)
        by_type = {}
        
        for device_type in DeviceType:
            by_type[device_type.value] = sum(
                1 for d in self.devices.values()
                if d.device_type == device_type and d.is_active
            )
        
        return {
            "total_devices": len(self.devices),
            "active_devices": active_devices,
            "devices_by_type": by_type
        }


class PushNotificationManager:
    """Manage push notifications"""
    
    def __init__(self):
        self.notifications: Dict[str, PushNotification] = {}
        self.device_notifications: Dict[str, List[str]] = {}  # device_id -> [notification_ids]
    
    def create_push(self, device_id: str, title: str, body: str,
                   priority: PushNotificationPriority = PushNotificationPriority.NORMAL,
                   data: Dict = None) -> PushNotification:
        """Create push notification"""
        notification_id = str(uuid.uuid4())
        notification = PushNotification(
            notification_id=notification_id,
            device_id=device_id,
            title=title,
            body=body,
            priority=priority,
            data=data or {}
        )
        
        self.notifications[notification_id] = notification
        
        if device_id not in self.device_notifications:
            self.device_notifications[device_id] = []
        self.device_notifications[device_id].append(notification_id)
        
        return notification
    
    def mark_delivered(self, notification_id: str) -> bool:
        """Mark notification as delivered"""
        if notification_id not in self.notifications:
            return False
        
        notification = self.notifications[notification_id]
        notification.delivered = True
        notification.sent_at = datetime.now().isoformat()
        
        return True
    
    def send_bulk(self, user_devices: List[str], title: str, body: str) -> List[str]:
        """Send notification to multiple devices"""
        notification_ids = []
        
        for device_id in user_devices:
            notif = self.create_push(device_id, title, body)
            notification_ids.append(notif.notification_id)
        
        return notification_ids
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get push notification statistics"""
        delivered = sum(1 for n in self.notifications.values() if n.delivered)
        
        return {
            "total_notifications": len(self.notifications),
            "delivered_count": delivered,
            "pending_count": len(self.notifications) - delivered
        }


class SyncManager:
    """Manage offline synchronization"""
    
    def __init__(self):
        self.sync_operations: Dict[str, SyncOperation] = {}
        self.offline_queues: Dict[str, OfflineQueue] = {}
        self.device_syncs: Dict[str, List[str]] = {}  # device_id -> [sync_ids]
    
    def create_sync(self, device_id: str, operation_type: str) -> SyncOperation:
        """Create sync operation"""
        sync_id = str(uuid.uuid4())
        sync_op = SyncOperation(
            sync_id=sync_id,
            device_id=device_id,
            operation_type=operation_type,
            status=SyncStatus.PENDING
        )
        
        self.sync_operations[sync_id] = sync_op
        
        if device_id not in self.device_syncs:
            self.device_syncs[device_id] = []
        self.device_syncs[device_id].append(sync_id)
        
        return sync_op
    
    def start_sync(self, sync_id: str) -> bool:
        """Start synchronization"""
        if sync_id not in self.sync_operations:
            return False
        
        sync_op = self.sync_operations[sync_id]
        sync_op.status = SyncStatus.SYNCING
        
        return True
    
    def complete_sync(self, sync_id: str, success: bool = True,
                     items_count: int = 0) -> bool:
        """Complete synchronization"""
        if sync_id not in self.sync_operations:
            return False
        
        sync_op = self.sync_operations[sync_id]
        sync_op.status = SyncStatus.SYNCED if success else SyncStatus.FAILED
        sync_op.completed_at = datetime.now().isoformat()
        sync_op.items_count = items_count
        
        return True
    
    def queue_offline_operation(self, device_id: str, operation: Dict) -> bool:
        """Queue operation for offline sync"""
        if device_id not in self.offline_queues:
            queue_id = str(uuid.uuid4())
            self.offline_queues[device_id] = OfflineQueue(
                queue_id=queue_id,
                device_id=device_id
            )
        
        self.offline_queues[device_id].operations.append(operation)
        return True
    
    def get_offline_queue(self, device_id: str) -> List[Dict]:
        """Get offline operations queue"""
        if device_id not in self.offline_queues:
            return []
        
        return self.offline_queues[device_id].operations
    
    def flush_offline_queue(self, device_id: str) -> bool:
        """Flush offline queue after sync"""
        if device_id in self.offline_queues:
            self.offline_queues[device_id].operations.clear()
            self.offline_queues[device_id].synced = True
            return True
        return False
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        synced = sum(1 for s in self.sync_operations.values() if s.status == SyncStatus.SYNCED)
        failed = sum(1 for s in self.sync_operations.values() if s.status == SyncStatus.FAILED)
        
        return {
            "total_syncs": len(self.sync_operations),
            "successful_syncs": synced,
            "failed_syncs": failed,
            "queued_operations": sum(len(q.operations) for q in self.offline_queues.values())
        }


class MobileAnalytics:
    """Mobile app analytics"""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.user_sessions: Dict[str, List[Dict]] = {}  # user_id -> [sessions]
    
    def track_event(self, user_id: str, device_id: str, event_name: str,
                   event_data: Dict = None):
        """Track mobile event"""
        event = {
            "event_id": str(uuid.uuid4()),
            "user_id": user_id,
            "device_id": device_id,
            "event_name": event_name,
            "event_data": event_data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.events.append(event)
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(event)
    
    def get_analytics_stats(self) -> Dict[str, Any]:
        """Get analytics statistics"""
        return {
            "total_events": len(self.events),
            "tracked_users": len(self.user_sessions),
            "average_events_per_user": (len(self.events) / len(self.user_sessions)
                                       if self.user_sessions else 0)
        }


class MobileIntegrationEngine:
    """Central mobile integration engine"""
    
    def __init__(self):
        self.device_manager = DeviceManager()
        self.push_manager = PushNotificationManager()
        self.sync_manager = SyncManager()
        self.analytics = MobileAnalytics()
    
    def get_mobile_status(self) -> Dict[str, Any]:
        """Get overall mobile integration status"""
        return {
            "devices": self.device_manager.get_device_stats(),
            "push_notifications": self.push_manager.get_notification_stats(),
            "synchronization": self.sync_manager.get_sync_stats(),
            "analytics": self.analytics.get_analytics_stats()
        }


# Example usage
if __name__ == "__main__":
    engine = MobileIntegrationEngine()
    
    # Register device
    device = engine.device_manager.register_device(
        "user_001", DeviceType.IOS, "iPhone 14", "push_token_abc123",
        "16.0", "1.0.0"
    )
    print(f"Device registered: {device.device_id}")
    
    # Send push notification
    push = engine.push_manager.create_push(
        device.device_id, "New message", "You have a new message",
        PushNotificationPriority.HIGH
    )
    print(f"Push notification created: {push.notification_id}")
    
    # Queue offline operation
    engine.sync_manager.queue_offline_operation(
        device.device_id,
        {"operation": "save", "data": {"key": "value"}}
    )
    
    # Track event
    engine.analytics.track_event(
        "user_001", device.device_id, "app_opened",
        {"timestamp": datetime.now().isoformat()}
    )
    
    # Get status
    status = engine.get_mobile_status()
    print(json.dumps(status, indent=2))
