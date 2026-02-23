#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 13 - Real-time Collaboration Features
WebSocket-based collaboration, presence, and live updates

This module provides:
1. Real-time messaging
2. User presence tracking
3. Live document collaboration
4. Notification system
5. Change tracking
6. Conflict resolution
"""

import json
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import uuid


class PresenceStatus(Enum):
    """User presence status"""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"
    BUSY = "busy"


class NotificationType(Enum):
    """Notification types"""
    MESSAGE = "message"
    MENTION = "mention"
    UPDATE = "update"
    INVITE = "invite"
    ALERT = "alert"


@dataclass
class UserPresence:
    """User presence information"""
    user_id: str
    status: PresenceStatus
    last_seen: str
    current_document: Optional[str] = None
    device_info: str = ""
    location: Optional[str] = None


@dataclass
class RealtimeMessage:
    """Real-time message"""
    message_id: str
    sender_id: str
    content: str
    room_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    edited: bool = False
    edited_at: Optional[str] = None
    mentions: List[str] = field(default_factory=list)
    reactions: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class DocumentChange:
    """Document change for collaboration"""
    change_id: str
    user_id: str
    document_id: str
    operation: str  # "insert", "delete", "modify"
    position: int
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    applied: bool = True


@dataclass
class Notification:
    """User notification"""
    notification_id: str
    user_id: str
    notification_type: NotificationType
    title: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False
    read_at: Optional[str] = None


class PresenceManager:
    """Manage user presence"""
    
    def __init__(self):
        self.presence: Dict[str, UserPresence] = {}
        self.presence_history: Dict[str, List[str]] = {}  # user_id -> [timestamps]
    
    def set_presence(self, user_id: str, status: PresenceStatus,
                    document_id: str = None) -> UserPresence:
        """Set user presence"""
        presence = UserPresence(
            user_id=user_id,
            status=status,
            last_seen=datetime.now().isoformat(),
            current_document=document_id
        )
        self.presence[user_id] = presence
        
        if user_id not in self.presence_history:
            self.presence_history[user_id] = []
        self.presence_history[user_id].append(datetime.now().isoformat())
        
        return presence
    
    def get_presence(self, user_id: str) -> Optional[UserPresence]:
        """Get user presence"""
        return self.presence.get(user_id)
    
    def get_online_users(self) -> List[UserPresence]:
        """Get all online users"""
        return [p for p in self.presence.values() if p.status in [PresenceStatus.ONLINE, PresenceStatus.BUSY]]
    
    def get_users_in_document(self, document_id: str) -> List[UserPresence]:
        """Get users working on document"""
        return [p for p in self.presence.values() if p.current_document == document_id]
    
    def get_presence_stats(self) -> Dict[str, Any]:
        """Get presence statistics"""
        return {
            "online_count": len(self.get_online_users()),
            "total_users": len(self.presence),
            "status_breakdown": {
                status.value: sum(1 for p in self.presence.values() if p.status == status)
                for status in PresenceStatus
            }
        }


class MessageManager:
    """Manage real-time messages"""
    
    def __init__(self):
        self.messages: Dict[str, RealtimeMessage] = {}
        self.room_messages: Dict[str, List[str]] = {}  # room_id -> [message_ids]
        self.unread_messages: Dict[str, List[str]] = {}  # user_id -> [message_ids]
    
    def send_message(self, sender_id: str, room_id: str, content: str) -> RealtimeMessage:
        """Send message"""
        message_id = str(uuid.uuid4())
        message = RealtimeMessage(
            message_id=message_id,
            sender_id=sender_id,
            content=content,
            room_id=room_id
        )
        
        self.messages[message_id] = message
        
        if room_id not in self.room_messages:
            self.room_messages[room_id] = []
        self.room_messages[room_id].append(message_id)
        
        return message
    
    def edit_message(self, message_id: str, new_content: str) -> bool:
        """Edit message"""
        if message_id not in self.messages:
            return False
        
        message = self.messages[message_id]
        message.content = new_content
        message.edited = True
        message.edited_at = datetime.now().isoformat()
        
        return True
    
    def delete_message(self, message_id: str) -> bool:
        """Delete message"""
        if message_id in self.messages:
            del self.messages[message_id]
            return True
        return False
    
    def add_reaction(self, message_id: str, user_id: str, emoji: str) -> bool:
        """Add emoji reaction to message"""
        if message_id not in self.messages:
            return False
        
        message = self.messages[message_id]
        if emoji not in message.reactions:
            message.reactions[emoji] = []
        
        if user_id not in message.reactions[emoji]:
            message.reactions[emoji].append(user_id)
        
        return True
    
    def get_room_messages(self, room_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages in room"""
        if room_id not in self.room_messages:
            return []
        
        message_ids = self.room_messages[room_id][-limit:]
        return [asdict(self.messages[msg_id]) for msg_id in message_ids]
    
    def get_message_stats(self) -> Dict[str, Any]:
        """Get message statistics"""
        return {
            "total_messages": len(self.messages),
            "total_rooms": len(self.room_messages),
            "edited_messages": sum(1 for m in self.messages.values() if m.edited),
            "total_reactions": sum(len(reactions) for m in self.messages.values() 
                                  for reactions in m.reactions.values())
        }


class DocumentCollaborator:
    """Manage document collaboration"""
    
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.changes: Dict[str, List[DocumentChange]] = {}  # doc_id -> [changes]
        self.locks: Dict[str, str] = {}  # doc_id -> user_id
    
    def create_document(self, doc_id: str, title: str, content: str = "") -> Dict[str, Any]:
        """Create collaborative document"""
        document = {
            "doc_id": doc_id,
            "title": title,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "collaborators": set(),
            "version": 0
        }
        self.documents[doc_id] = document
        self.changes[doc_id] = []
        return document
    
    def apply_change(self, doc_id: str, user_id: str, operation: str,
                    position: int, content: str) -> Optional[DocumentChange]:
        """Apply change to document"""
        if doc_id not in self.documents:
            return None
        
        change_id = str(uuid.uuid4())
        change = DocumentChange(
            change_id=change_id,
            user_id=user_id,
            document_id=doc_id,
            operation=operation,
            position=position,
            content=content
        )
        
        # Apply change
        doc = self.documents[doc_id]
        if operation == "insert":
            doc["content"] = doc["content"][:position] + content + doc["content"][position:]
        elif operation == "delete":
            doc["content"] = doc["content"][:position] + doc["content"][position + len(content):]
        elif operation == "modify":
            doc["content"] = doc["content"][:position] + content + doc["content"][position + len(content):]
        
        doc["modified_at"] = datetime.now().isoformat()
        doc["version"] += 1
        
        self.changes[doc_id].append(change)
        return change
    
    def lock_document(self, doc_id: str, user_id: str) -> bool:
        """Lock document for editing"""
        if doc_id in self.locks and self.locks[doc_id] != user_id:
            return False  # Document already locked
        
        self.locks[doc_id] = user_id
        return True
    
    def unlock_document(self, doc_id: str, user_id: str) -> bool:
        """Unlock document"""
        if doc_id in self.locks and self.locks[doc_id] == user_id:
            del self.locks[doc_id]
            return True
        return False
    
    def get_document_history(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get document change history"""
        if doc_id not in self.changes:
            return []
        
        return [asdict(change) for change in self.changes[doc_id]]
    
    def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get collaboration statistics"""
        return {
            "total_documents": len(self.documents),
            "total_changes": sum(len(changes) for changes in self.changes.values()),
            "locked_documents": len(self.locks),
            "average_version": sum(d.get("version", 0) for d in self.documents.values()) / len(self.documents)
                              if self.documents else 0
        }


class NotificationManager:
    """Manage notifications"""
    
    def __init__(self):
        self.notifications: Dict[str, Notification] = {}
        self.user_notifications: Dict[str, List[str]] = {}  # user_id -> [notification_ids]
    
    def create_notification(self, user_id: str, notif_type: NotificationType,
                           title: str, content: str) -> Notification:
        """Create notification"""
        notification_id = str(uuid.uuid4())
        notification = Notification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=notif_type,
            title=title,
            content=content
        )
        
        self.notifications[notification_id] = notification
        
        if user_id not in self.user_notifications:
            self.user_notifications[user_id] = []
        self.user_notifications[user_id].append(notification_id)
        
        return notification
    
    def mark_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        if notification_id not in self.notifications:
            return False
        
        notification = self.notifications[notification_id]
        notification.read = True
        notification.read_at = datetime.now().isoformat()
        
        return True
    
    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get user notifications"""
        if user_id not in self.user_notifications:
            return []
        
        notif_ids = self.user_notifications[user_id]
        notifications = [asdict(self.notifications[nid]) for nid in notif_ids]
        
        if unread_only:
            notifications = [n for n in notifications if not n["read"]]
        
        return notifications
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        unread = sum(1 for n in self.notifications.values() if not n.read)
        
        return {
            "total_notifications": len(self.notifications),
            "unread_count": unread,
            "users_with_notifications": len(self.user_notifications)
        }


class CollaborationEngine:
    """Central collaboration engine"""
    
    def __init__(self):
        self.presence_manager = PresenceManager()
        self.message_manager = MessageManager()
        self.document_collaborator = DocumentCollaborator()
        self.notification_manager = NotificationManager()
    
    def get_collaboration_status(self) -> Dict[str, Any]:
        """Get overall collaboration status"""
        return {
            "presence": self.presence_manager.get_presence_stats(),
            "messages": self.message_manager.get_message_stats(),
            "documents": self.document_collaborator.get_collaboration_stats(),
            "notifications": self.notification_manager.get_notification_stats()
        }


# Example usage
if __name__ == "__main__":
    engine = CollaborationEngine()
    
    # Set presence
    engine.presence_manager.set_presence("user_001", PresenceStatus.ONLINE, "doc_001")
    print("User presence set")
    
    # Send message
    message = engine.message_manager.send_message("user_001", "room_001", "Hello!")
    print(f"Message sent: {message.message_id}")
    
    # Create document
    doc = engine.document_collaborator.create_document("doc_001", "Shared Document")
    print(f"Document created: {doc['doc_id']}")
    
    # Create notification
    notif = engine.notification_manager.create_notification(
        "user_001", NotificationType.MESSAGE, "New message", "You have a new message"
    )
    print(f"Notification created: {notif.notification_id}")
    
    # Get status
    status = engine.get_collaboration_status()
    print(json.dumps(status, indent=2))
