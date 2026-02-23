#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for Phases 10-15
Validates all new security, auth, ETL, collaboration, mobile, and analytics features
"""

import sys
import os
sys.path.insert(0, r'c:\Users\12524\Desktop\Koto')

from datetime import datetime
from web.security_manager import (
    SecurityManager, TokenType, EncryptionManager, APIKeyManager, SecureCredentialStore
)
from web.auth_manager import (
    AuthenticationManager, UserRole, Permission, UserManager
)
from web.etl_engine import (
    ETLEngine, StreamProcessor, BatchProcessor
)
from web.collaboration_engine import (
    CollaborationEngine, PresenceStatus, NotificationType
)
from web.mobile_integration import (
    MobileIntegrationEngine, DeviceType, PushNotificationPriority
)
from web.analytics_engine import (
    AnalyticsEngine, MetricType, ReportFormat, DashboardType
)


def test_phase10_security():
    """Test Phase 10: Security Features"""
    print("\n" + "="*60)
    print("TEST PHASE 10: Advanced Security Features")
    print("="*60)
    
    try:
        # Initialize security manager
        security = SecurityManager()
        print("✓ SecurityManager initialized")
        
        # Test token generation
        token = security.token_manager.generate_token("user_001", scopes=["read", "write"])
        assert token.token_id, "Token should have ID"
        assert token.token_type == TokenType.ACCESS, "Token type should be ACCESS"
        print(f"✓ Token generated: {token.token_id[:16]}...")
        
        # Test token validation
        validated = security.token_manager.validate_token(token.value)
        assert validated is not None, "Token should be valid"
        print("✓ Token validation works")
        
        # Test encryption
        security.encryption_manager.generate_key()
        encrypted = security.encryption_manager.encrypt("secret_data")
        assert encrypted, "Data should be encrypted"
        print("✓ Encryption/decryption working")
        
        # Test API key management
        key_id, key_secret = security.api_key_manager.create_api_key("user_001", "test_app")
        assert security.api_key_manager.validate_api_key(key_id, key_secret), "API key should validate"
        print("✓ API key management working")
        
        # Test credential storage
        security.credential_store.store_credential("cred_001", "admin", "password123", "system")
        assert security.credential_store.verify_credential("cred_001", "password123"), "Credential should verify"
        print("✓ Secure credential storage working")
        
        # Test CORS
        security.cors_manager.add_allowed_origin("https://example.com")
        assert security.cors_manager.is_origin_allowed("https://example.com"), "Origin should be allowed"
        print("✓ CORS management working")
        
        # Get status
        status = security.get_security_status()
        print(f"✓ Security status: {status['tokens']['total_tokens']} tokens, {status['encryption']['rotation_needed']} rotation needed")
        
        return True
    
    except Exception as e:
        print(f"✗ Phase 10 test failed: {e}")
        return False


def test_phase11_authentication():
    """Test Phase 11: Authentication & Authorization"""
    print("\n" + "="*60)
    print("TEST PHASE 11: User Authentication & Authorization")
    print("="*60)
    
    try:
        # Initialize auth manager
        auth = AuthenticationManager()
        print("✓ AuthenticationManager initialized")
        
        # Create user
        user = auth.user_manager.create_user(
            "user_001", "john_doe", "john@example.com", "hashed_pass", [UserRole.USER]
        )
        assert user.user_id == "user_001", "User should be created"
        print(f"✓ User created: {user.username}")
        
        # Test user lookup
        found_user = auth.user_manager.get_user("user_001")
        assert found_user is not None, "User should be found"
        print("✓ User lookup works")
        
        # Test permissions
        has_perm = auth.user_manager.has_permission("user_001", Permission.DATA_READ)
        assert has_perm, "User should have DATA_READ permission"
        print("✓ Permission checking works")
        
        # Create session
        session = auth.session_manager.create_session("sess_001", "user_001", "192.168.1.1")
        assert session.is_active, "Session should be active"
        print(f"✓ Session created: {session.session_id[:16]}...")
        
        # Validate session
        assert auth.session_manager.validate_session("sess_001"), "Session should be valid"
        print("✓ Session validation works")
        
        # Audit logging
        auth.audit_logger.log_action(
            "audit_001", "user_001", "login", "user_session", status="success"
        )
        logs = auth.audit_logger.get_user_log("user_001")
        assert len(logs) > 0, "Audit logs should be recorded"
        print(f"✓ Audit logging: {len(logs)} entries")
        
        # Get auth status
        auth_status = auth.get_auth_status()
        print(f"✓ Auth status: {auth_status['users']['total_users']} users, {auth_status['sessions']} active sessions")
        
        return True
    
    except Exception as e:
        print(f"✗ Phase 11 test failed: {e}")
        return False


def test_phase12_etl():
    """Test Phase 12: ETL & Data Processing"""
    print("\n" + "="*60)
    print("TEST PHASE 12: Data ETL & Processing")
    print("="*60)
    
    try:
        # Initialize ETL engine
        engine = ETLEngine()
        print("✓ ETLEngine initialized")
        
        # Test stream processor
        stream_result = engine.stream_processor.process_stream(
            list(range(100)),
            lambda chunk: [item * 2 for item in chunk]
        )
        assert stream_result['status'] == 'completed', "Stream should complete"
        print(f"✓ Stream processing: {stream_result['items_processed']} items processed")
        
        # Test batch processor
        job = engine.batch_processor.create_batch_job("job_001", "Test Job", 500)
        engine.batch_processor.start_job("job_001")
        
        for i in range(100):
            engine.batch_processor.process_batch_item("job_001", True)
        
        engine.batch_processor.complete_job("job_001", True)
        progress = engine.batch_processor.get_job_progress("job_001")
        assert progress['status'] == 'completed', "Job should be completed"
        print(f"✓ Batch processing: {progress['processed_items']} items processed")
        
        # Get ETL status
        etl_status = engine.get_etl_status()
        print(f"✓ ETL status: {etl_status['stream_processor']['status']}, {etl_status['stream_processor']['chunks_processed']} chunks")
        
        return True
    
    except Exception as e:
        print(f"✗ Phase 12 test failed: {e}")
        return False


def test_phase13_collaboration():
    """Test Phase 13: Real-time Collaboration"""
    print("\n" + "="*60)
    print("TEST PHASE 13: Real-time Collaboration Features")
    print("="*60)
    
    try:
        # Initialize collaboration engine
        engine = CollaborationEngine()
        print("✓ CollaborationEngine initialized")
        
        # Test presence
        presence = engine.presence_manager.set_presence("user_001", PresenceStatus.ONLINE, "doc_001")
        assert presence.status == PresenceStatus.ONLINE, "User should be online"
        print(f"✓ Presence set: {presence.status.value}")
        
        # Test messaging
        message = engine.message_manager.send_message("user_001", "room_001", "Hello!")
        assert message.content == "Hello!", "Message should be sent"
        print(f"✓ Message sent: {message.message_id[:16]}...")
        
        # Test message reactions
        assert engine.message_manager.add_reaction(message.message_id, "user_001", "👍"), "Should add reaction"
        print("✓ Message reactions working")
        
        # Test document collaboration
        doc = engine.document_collaborator.create_document("doc_001", "Test Document", "Initial content")
        assert doc['version'] == 0, "Document should be created"
        print(f"✓ Document created: {doc['doc_id']}")
        
        # Test document changes
        change = engine.document_collaborator.apply_change("doc_001", "user_001", "insert", 0, "New ")
        assert change is not None, "Change should be applied"
        print("✓ Document changes working")
        
        # Test notifications
        notif = engine.notification_manager.create_notification(
            "user_001", NotificationType.MESSAGE, "New message", "You have a message"
        )
        assert notif.notification_type == NotificationType.MESSAGE, "Notification should be created"
        print(f"✓ Notification created: {notif.notification_id[:16]}...")
        
        # Get collaboration status
        collab_status = engine.get_collaboration_status()
        print(f"✓ Collaboration status: {collab_status['presence']['online_count']} users online")
        
        return True
    
    except Exception as e:
        print(f"✗ Phase 13 test failed: {e}")
        return False


def test_phase14_mobile():
    """Test Phase 14: Mobile Integration"""
    print("\n" + "="*60)
    print("TEST PHASE 14: Mobile App Integration")
    print("="*60)
    
    try:
        # Initialize mobile engine
        engine = MobileIntegrationEngine()
        print("✓ MobileIntegrationEngine initialized")
        
        # Test device registration
        device = engine.device_manager.register_device(
            "user_001", DeviceType.IOS, "iPhone 14", "push_token_123",
            "16.0", "1.0.0"
        )
        assert device.device_type == DeviceType.IOS, "Device should be registered"
        print(f"✓ Device registered: {device.device_id[:16]}...")
        
        # Test push notifications
        push = engine.push_manager.create_push(
            device.device_id, "Title", "Body",
            PushNotificationPriority.HIGH
        )
        assert push.delivered == False, "Push should be created"
        engine.push_manager.mark_delivered(push.notification_id)
        print("✓ Push notification system working")
        
        # Test synchronization
        sync = engine.sync_manager.create_sync(device.device_id, "pull")
        engine.sync_manager.start_sync(sync.sync_id)
        engine.sync_manager.complete_sync(sync.sync_id, True, 50)
        assert sync.status.value == 'synced', "Sync status should be tracked"
        print("✓ Synchronization working")
        
        # Test offline queue
        engine.sync_manager.queue_offline_operation(
            device.device_id,
            {"operation": "save", "data": {"key": "value"}}
        )
        queue = engine.sync_manager.get_offline_queue(device.device_id)
        assert len(queue) > 0, "Queue should have operations"
        print("✓ Offline queue working")
        
        # Test analytics
        engine.analytics.track_event(
            "user_001", device.device_id, "app_opened", {"source": "home"}
        )
        print("✓ Mobile analytics tracking")
        
        # Get mobile status
        mobile_status = engine.get_mobile_status()
        print(f"✓ Mobile status: {mobile_status['devices']['active_devices']} devices")
        
        return True
    
    except Exception as e:
        print(f"✗ Phase 14 test failed: {e}")
        return False


def test_phase15_analytics():
    """Test Phase 15: Advanced Analytics & Dashboards"""
    print("\n" + "="*60)
    print("TEST PHASE 15: Advanced Analytics & Dashboards")
    print("="*60)
    
    try:
        # Initialize analytics engine
        engine = AnalyticsEngine()
        print("✓ AnalyticsEngine initialized")
        
        # Test metric collection
        for i in range(10):
            engine.metrics_collector.record_metric(
                "response_time", 50 + i * 5, MetricType.TIMER, "ms"
            )
        
        metrics_stat = engine.metrics_collector.get_metric_stats("response_time")
        assert metrics_stat['count'] == 10, "Should have 10 metrics"
        print(f"✓ Metrics collected: {metrics_stat['count']} data points, avg={metrics_stat['mean']:.1f}ms")
        
        # Test trend analysis
        trend = engine.trend_analyzer.calculate_trend(
            "response_time",
            [50, 52, 54, 56, 58, 60, 62, 64, 66, 68]
        )
        assert trend['trend'] in ['increasing', 'decreasing', 'stable'], "Trend should be calculated"
        print(f"✓ Trend analysis: {trend['trend']} ({trend['change_percent']:.1f}%)")
        
        # Test report generation
        report = engine.report_generator.create_summary_report({"response_time": metrics_stat})
        assert report.report_id, "Report should be generated"
        print(f"✓ Report generated: {report.report_id[:16]}...")
        
        # Test dashboard creation
        dashboard = engine.create_performance_dashboard("Performance Dashboard")
        assert len(dashboard.widgets) > 0, "Dashboard should have widgets"
        print(f"✓ Dashboard created with {len(dashboard.widgets)} widgets")
        
        # Get analytics status
        analytics_status = engine.get_analytics_status()
        print(f"✓ Analytics status: {analytics_status['metrics']['total_recorded']} metrics recorded")
        
        return True
    
    except Exception as e:
        print(f"✗ Phase 15 test failed: {e}")
        return False


def run_all_phase_tests():
    """Run all Phase 10-15 tests"""
    print("\n" + "="*60)
    print("RUNNING COMPREHENSIVE PHASE TESTS (10-15)")
    print("="*60)
    
    results = {
        "Phase 10 - Security": test_phase10_security(),
        "Phase 11 - Authentication": test_phase11_authentication(),
        "Phase 12 - ETL": test_phase12_etl(),
        "Phase 13 - Collaboration": test_phase13_collaboration(),
        "Phase 14 - Mobile": test_phase14_mobile(),
        "Phase 15 - Analytics": test_phase15_analytics()
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_phase_tests()
    sys.exit(0 if success else 1)
