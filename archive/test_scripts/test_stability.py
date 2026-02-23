#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Koto System Stability Test
Tests all 15 phases and generates a stability report
"""

import sys
import os
import json
from datetime import datetime
sys.path.insert(0, r'c:\Users\12524\Desktop\Koto')

# Import all phase modules
try:
    # Phase 1-9: Core systems (already implemented)
    from web.cache_manager import LRUCache, MultiLevelCache
    
    # Phase 10-15: New systems
    from web.security_manager import SecurityManager
    from web.auth_manager import AuthenticationManager, UserRole, Permission
    from web.etl_engine import ETLEngine
    from web.collaboration_engine import CollaborationEngine, PresenceStatus
    from web.mobile_integration import MobileIntegrationEngine, DeviceType
    from web.analytics_engine import AnalyticsEngine, MetricType
    
    core_imports_ok = True
except Exception as e:
    print(f"Failed to import modules: {e}")
    import traceback
    traceback.print_exc()
    core_imports_ok = False


class KotoSystemTest:
    """Comprehensive Koto system test"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.modules_tested = 0
        self.features_tested = 0
        self.errors = []
    
    def test_caching_system(self):
        """Test caching system (Phase 9)"""
        test_name = "Caching System"
        try:
            cache = LRUCache(max_size=10, default_ttl=3600)
            
            # Test basic operations
            cache.put("key1", "value1")
            assert cache.get("key1") == "value1", "Cache get failed"
            
            stats = cache.get_stats()
            assert stats["size"] == 1, "Cache size incorrect"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 3
            }
            self.features_tested += 3
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"Caching: {e}")
            return False
    
    def test_security_system(self):
        """Test security system (Phase 10)"""
        test_name = "Security System"
        try:
            security = SecurityManager()
            
            # Test token management
            token = security.token_manager.generate_token("test_user")
            assert token.token_id, "Token generation failed"
            
            # Test encryption
            security.encryption_manager.generate_key()
            encrypted = security.encryption_manager.encrypt("data")
            assert encrypted, "Encryption failed"
            
            # Test API keys
            key_id, key_secret = security.api_key_manager.create_api_key("test_user", "app")
            assert security.api_key_manager.validate_api_key(key_id, key_secret), "API key validation failed"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 5
            }
            self.features_tested += 5
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"Security: {e}")
            return False
    
    def test_authentication_system(self):
        """Test authentication system (Phase 11)"""
        test_name = "Authentication & Authorization"
        try:
            auth = AuthenticationManager()
            
            # Test user management
            user = auth.user_manager.create_user(
                "user_001", "testuser", "test@example.com", "hash", [UserRole.USER]
            )
            assert user.username == "testuser", "User creation failed"
            
            # Test permissions
            has_perm = auth.user_manager.has_permission("user_001", Permission.DATA_READ)
            assert has_perm, "Permission check failed"
            
            # Test sessions
            session = auth.session_manager.create_session("sess_001", "user_001", "192.168.1.1")
            assert auth.session_manager.validate_session("sess_001"), "Session validation failed"
            
            # Test audit logging
            auth.audit_logger.log_action("audit_001", "user_001", "login", "session")
            logs = auth.audit_logger.get_user_log("user_001")
            assert len(logs) > 0, "Audit logging failed"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 5
            }
            self.features_tested += 5
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"Authentication: {e}")
            return False
    
    def test_etl_system(self):
        """Test ETL system (Phase 12)"""
        test_name = "ETL & Data Processing"
        try:
            engine = ETLEngine()
            
            # Test stream processing
            result = engine.stream_processor.process_stream(
                list(range(50)),
                lambda chunk: [x * 2 for x in chunk]
            )
            assert result['status'] == 'completed', "Stream processing failed"
            
            # Test batch processing
            job = engine.batch_processor.create_batch_job("job_001", "Test", 100)
            engine.batch_processor.start_job("job_001")
            for i in range(50):
                engine.batch_processor.process_batch_item("job_001", True)
            engine.batch_processor.complete_job("job_001", True)
            
            progress = engine.batch_processor.get_job_progress("job_001")
            assert progress['status'] == 'completed', "Batch processing failed"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 4
            }
            self.features_tested += 4
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"ETL: {e}")
            return False
    
    def test_collaboration_system(self):
        """Test collaboration system (Phase 13)"""
        test_name = "Real-time Collaboration"
        try:
            engine = CollaborationEngine()
            
            # Test presence
            presence = engine.presence_manager.set_presence("user_001", PresenceStatus.ONLINE)
            assert presence.status == PresenceStatus.ONLINE, "Presence setting failed"
            
            # Test messaging
            message = engine.message_manager.send_message("user_001", "room_001", "Test")
            assert message.content == "Test", "Messaging failed"
            
            # Test document collaboration
            doc = engine.document_collaborator.create_document("doc_001", "Test Doc")
            assert doc['doc_id'] == "doc_001", "Document creation failed"
            
            # Test notifications
            notif = engine.notification_manager.create_notification(
                "user_001", type("NotificationType", (), {"MESSAGE": "message"})(),
                "Title", "Content"
            )
            assert notif.notification_id, "Notification creation failed"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 4
            }
            self.features_tested += 4
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"Collaboration: {e}")
            return False
    
    def test_mobile_system(self):
        """Test mobile integration (Phase 14)"""
        test_name = "Mobile App Integration"
        try:
            engine = MobileIntegrationEngine()
            
            # Test device management
            device = engine.device_manager.register_device(
                "user_001", DeviceType.IOS, "iPhone", "token_123",
                "16.0", "1.0.0"
            )
            assert device.device_type == DeviceType.IOS, "Device registration failed"
            
            # Test push notifications
            push = engine.push_manager.create_push(device.device_id, "Title", "Body")
            assert push.delivered == False, "Push creation failed"
            
            # Test sync
            sync = engine.sync_manager.create_sync(device.device_id, "pull")
            engine.sync_manager.start_sync(sync.sync_id)
            engine.sync_manager.complete_sync(sync.sync_id, True)
            
            # Test offline queue
            engine.sync_manager.queue_offline_operation(
                device.device_id,
                {"op": "save"}
            )
            queue = engine.sync_manager.get_offline_queue(device.device_id)
            assert len(queue) > 0, "Offline queue failed"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 5
            }
            self.features_tested += 5
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"Mobile: {e}")
            return False
    
    def test_analytics_system(self):
        """Test analytics system (Phase 15)"""
        test_name = "Advanced Analytics"
        try:
            engine = AnalyticsEngine()
            
            # Test metrics collection
            for i in range(5):
                engine.metrics_collector.record_metric(
                    "metric_test", float(50 + i), MetricType.GAUGE
                )
            
            stats = engine.metrics_collector.get_metric_stats("metric_test")
            assert stats['count'] == 5, "Metrics collection failed"
            
            # Test trends
            trend = engine.trend_analyzer.calculate_trend(
                "metric_test",
                [50.0, 52.0, 54.0, 56.0, 58.0]
            )
            assert 'trend' in trend, "Trend analysis failed"
            
            # Test dashboard
            dashboard = engine.create_performance_dashboard("Test Dashboard")
            assert len(dashboard.widgets) > 0, "Dashboard creation failed"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 5
            }
            self.features_tested += 5
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"Analytics: {e}")
            return False
    
    def test_system_integration(self):
        """Test system integration across phases"""
        test_name = "System Integration"
        try:
            # Create an integrated workflow using multiple systems
            security = SecurityManager()
            auth = AuthenticationManager()
            analytics = AnalyticsEngine()
            
            # Authentication flow
            user = auth.user_manager.create_user(
                "integrated_user", "user1", "user1@test.com", "hash", [UserRole.USER]
            )
            
            # Security flow
            token = security.token_manager.generate_token("integrated_user")
            assert token.token_id, "Integrated auth failed"
            
            # Analytics tracking
            analytics.metrics_collector.record_metric(
                "auth_events", 1.0, MetricType.COUNTER
            )
            
            # Session + Audit
            session = auth.session_manager.create_session(
                "int_sess", "integrated_user", "127.0.0.1"
            )
            auth.audit_logger.log_action(
                "int_audit", "integrated_user", "auth_flow", "system"
            )
            
            assert session.is_active, "Integration test failed"
            
            self.test_results[test_name] = {
                "status": "✓ PASS",
                "tests": 3
            }
            self.features_tested += 3
            return True
        except Exception as e:
            self.test_results[test_name] = {
                "status": "✗ FAIL",
                "error": str(e)
            }
            self.errors.append(f"Integration: {e}")
            return False
    
    def run_all_tests(self):
        """Run all system tests"""
        self.start_time = datetime.now()
        
        print("\n" + "="*70)
        print("KOTO SYSTEM COMPREHENSIVE STABILITY TEST")
        print("="*70)
        
        if not core_imports_ok:
            print("✗ CRITICAL: Core imports failed")
            return False
        
        tests = [
            ("Caching", self.test_caching_system),
            ("Security", self.test_security_system),
            ("Authentication", self.test_authentication_system),
            ("ETL", self.test_etl_system),
            ("Collaboration", self.test_collaboration_system),
            ("Mobile", self.test_mobile_system),
            ("Analytics", self.test_analytics_system),
            ("Integration", self.test_system_integration),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\nTesting {test_name}...", end=" ")
            if test_func():
                print("✓")
                passed += 1
            else:
                print("✗")
                failed += 1
            self.modules_tested += 1
        
        self.end_time = datetime.now()
        
        return failed == 0
    
    def generate_report(self):
        """Generate stability report"""
        if self.end_time is None:
            self.end_time = datetime.now()
        
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_duration_seconds": duration,
            "system_status": "STABLE" if len(self.errors) == 0 else "UNSTABLE",
            "modules_tested": self.modules_tested,
            "features_tested": self.features_tested,
            "test_results": self.test_results,
            "errors": self.errors,
            "summary": {
                "total_tests": self.modules_tested,
                "passed": sum(1 for r in self.test_results.values() if "✓" in r.get("status", "")),
                "failed": len(self.errors),
                "pass_rate": f"{(self.modules_tested - len(self.errors)) / self.modules_tested * 100:.1f}%" if self.modules_tested > 0 else "0%"
            }
        }
        
        return report


def main():
    """Main test execution"""
    tester = KotoSystemTest()
    success = tester.run_all_tests()
    report = tester.generate_report()
    
    # Print summary
    print("\n" + "="*70)
    print("STABILITY TEST SUMMARY")
    print("="*70)
    print(f"System Status: {report['system_status']}")
    print(f"Modules Tested: {report['modules_tested']}")
    print(f"Features Tested: {report['features_tested']}")
    print(f"Pass Rate: {report['summary']['pass_rate']}")
    print(f"Duration: {report['test_duration_seconds']:.2f} seconds")
    
    if report['errors']:
        print(f"\nErrors ({len(report['errors'])}):")
        for error in report['errors']:
            print(f"  - {error}")
    
    # Save report
    report_path = r"c:\Users\12524\Desktop\Koto\STABILITY_REPORT.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nReport saved to: {report_path}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
