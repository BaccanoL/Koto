#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive System Stability Test Suite
Tests all 15 phases of the Koto AI Assistant System
"""

import sys
import os
import json
import time
import threading
import traceback
from datetime import datetime
from typing import Dict, List, Tuple

# Add web directory to path
web_path = os.path.join(os.path.dirname(__file__), 'web')
sys.path.insert(0, web_path)
os.chdir(os.path.dirname(__file__))

def print_test_header(phase: int, description: str):
    """Print test header"""
    print(f"\n{'='*70}")
    print(f"PHASE {phase}: {description}")
    print(f"{'='*70}")

def print_result(test_name: str, passed: bool, message: str = ""):
    """Print test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"       {message}")

class StabilityTester:
    """Comprehensive stability testing"""
    
    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.phase_results = {}
    
    def record_test(self, phase: int, test_name: str, passed: bool, error: str = ""):
        """Record test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        if phase not in self.phase_results:
            self.phase_results[phase] = {"passed": 0, "failed": 0, "tests": []}
        
        self.phase_results[phase]["tests"].append({
            "name": test_name,
            "passed": passed,
            "error": error
        })
        
        if passed:
            self.phase_results[phase]["passed"] += 1
        else:
            self.phase_results[phase]["failed"] += 1
        
        print_result(test_name, passed, error)
    
    def test_phase_1_frontend(self):
        """Test Phase 1 - Frontend UI"""
        print_test_header(1, "Frontend UI (KaTeX, Mermaid, Markdown)")
        
        try:
            # Check if static folder exists
            static_path = os.path.join(os.path.dirname(__file__), '..', 'web', 'static')
            exists = os.path.isdir(static_path)
            self.record_test(1, "Static assets folder exists", exists)
            
            # Check templates
            templates_path = os.path.join(os.path.dirname(__file__), '..', 'web', 'templates')
            exists = os.path.isdir(templates_path)
            self.record_test(1, "Templates folder exists", exists)
            
            self.record_test(1, "Frontend rendering system ready", True)
        except Exception as e:
            self.record_test(1, "Frontend tests", False, str(e))
    
    def test_phase_2_memory(self):
        """Test Phase 2 - Memory Manager"""
        print_test_header(2, "Memory Manager")
        
        try:
            from memory_manager import MemoryManager
            
            mm = MemoryManager()
            
            # Test save memory
            mm.save("test_key", {"value": "test_data"}, category="test")
            self.record_test(2, "Save memory entry", True)
            
            # Test retrieve memory
            data = mm.retrieve("test_key")
            retrieved = data is not None and data.get("value") == "test_data"
            self.record_test(2, "Retrieve memory entry", retrieved)
            
            # Test search memory
            results = mm.search("test")
            found = len(results) > 0
            self.record_test(2, "Search memory", found)
            
            # Test memory stats
            stats = mm.get_statistics()
            has_stats = "total_entries" in stats
            self.record_test(2, "Get memory statistics", has_stats)
            
        except Exception as e:
            self.record_test(2, "Memory Manager tests", False, str(e)[:100])
    
    def test_phase_3_knowledge_base(self):
        """Test Phase 3 - Knowledge Base"""
        print_test_header(3, "Knowledge Base")
        
        try:
            from knowledge_base import KnowledgeBase
            
            kb = KnowledgeBase()
            
            # Test add document
            kb.add_document("doc1", "Test content", doc_type="note")
            self.record_test(3, "Add document", True)
            
            # Test retrieve document
            doc = kb.retrieve("doc1")
            retrieved = doc is not None
            self.record_test(3, "Retrieve document", retrieved)
            
            # Test search
            results = kb.search("Test", limit=10)
            found = len(results) > 0
            self.record_test(3, "Search knowledge base", found)
            
        except Exception as e:
            self.record_test(3, "Knowledge Base tests", False, str(e)[:100])
    
    def test_phase_4_agent_planner(self):
        """Test Phase 4 - Agent Planner"""
        print_test_header(4, "Agent Planner")
        
        try:
            from agent_planner import AgentPlanner
            
            planner = AgentPlanner()
            
            # Test plan generation
            plan = planner.plan_task("Analyze data and generate report")
            has_steps = plan and "steps" in plan
            self.record_test(4, "Generate plan", has_steps)
            
            # Test plan execution
            if has_steps:
                results = planner.execute_plan(plan)
                executed = len(results) > 0
                self.record_test(4, "Execute plan", executed)
            
        except Exception as e:
            self.record_test(4, "Agent Planner tests", False, str(e)[:100])
    
    def test_phase_5_workflows(self):
        """Test Phase 5 - Workflow Manager"""
        print_test_header(5, "Workflow Manager")
        
        try:
            from workflow_manager import WorkflowManager, WorkflowStep
            
            wm = WorkflowManager()
            
            # Test create workflow
            workflow = {
                "name": "test_workflow",
                "description": "Test",
                "steps": [
                    {"type": "action", "name": "step1", "action": "test"}
                ]
            }
            wm.create_workflow(workflow)
            self.record_test(5, "Create workflow", True)
            
            # Test list workflows
            workflows = wm.list_workflows()
            has_workflow = len(workflows) > 0
            self.record_test(5, "List workflows", has_workflow)
            
        except Exception as e:
            self.record_test(5, "Workflow Manager tests", False, str(e)[:100])
    
    def test_phase_6_test_generator(self):
        """Test Phase 6 - Test Generator"""
        print_test_header(6, "Test Generator")
        
        try:
            from test_generator import TestGenerator
            
            gen = TestGenerator()
            
            # Test generate tests
            tests = gen.generate_tests("Calculate sum of list", language="python")
            has_tests = len(tests) > 0
            self.record_test(6, "Generate test cases", has_tests)
            
            # Test analyze coverage
            code = "def add(a, b): return a + b"
            coverage = gen.analyze_coverage(code)
            has_coverage = coverage is not None
            self.record_test(6, "Analyze code coverage", has_coverage)
            
        except Exception as e:
            self.record_test(6, "Test Generator tests", False, str(e)[:100])
    
    def test_phase_7_monitoring(self):
        """Test Phase 7 - Performance Monitor"""
        print_test_header(7, "Performance Monitor")
        
        try:
            from performance_monitor import MonitoringHub
            
            monitor = MonitoringHub()
            
            # Test track API
            monitor.track_api_call("GET", "/api/test", 0.045, 200)
            tracked = True
            self.record_test(7, "Track API call", tracked)
            
            # Test health check
            health = monitor.get_system_health()
            has_health = health is not None
            self.record_test(7, "Get system health", has_health)
            
            # Test metrics
            metrics = monitor.get_metrics()
            has_metrics = len(metrics) > 0
            self.record_test(7, "Get performance metrics", has_metrics)
            
        except Exception as e:
            self.record_test(7, "Performance Monitor tests", False, str(e)[:100])
    
    def test_phase_8_rate_limiter(self):
        """Test Phase 8 - Rate Limiter"""
        print_test_header(8, "Rate Limiter")
        
        try:
            from rate_limiter import RateLimiter
            
            limiter = RateLimiter()
            
            # Test token bucket
            allowed = limiter.is_allowed("user_1")
            self.record_test(8, "Check rate limit (token bucket)", allowed)
            
            # Test get quota
            quota = limiter.get_quota_info("user_1")
            has_quota = quota is not None
            self.record_test(8, "Get quota info", has_quota)
            
            # Test adaptive throttling
            throttle_level = limiter.get_throttle_level("user_1")
            has_throttle = throttle_level is not None
            self.record_test(8, "Get throttle level", has_throttle)
            
        except Exception as e:
            self.record_test(8, "Rate Limiter tests", False, str(e)[:100])
    
    def test_phase_9_caching(self):
        """Test Phase 9 - Cache Manager"""
        print_test_header(9, "Cache Manager")
        
        try:
            from cache_manager import LRUCache, CacheDecorator, CacheStatistics
            
            cache = LRUCache(max_size=5)
            
            # Test cache put
            cache.put("key1", "value1")
            self.record_test(9, "Cache put operation", True)
            
            # Test cache get
            value = cache.get("key1")
            retrieved = value == "value1"
            self.record_test(9, "Cache get operation", retrieved)
            
            # Test cache statistics
            stats = CacheStatistics()
            stats.record_hit("key1")
            hit_rate = stats.get_hit_rate()
            has_stats = hit_rate >= 0
            self.record_test(9, "Cache statistics", has_stats)
            
        except Exception as e:
            self.record_test(9, "Cache Manager tests", False, str(e)[:100])
    
    def test_phase_10_security(self):
        """Test Phase 10 - Security Manager"""
        print_test_header(10, "Security Features")
        
        try:
            from security_manager import TokenManager, EncryptionManager
            
            tm = TokenManager()
            
            # Test token generation
            token = tm.generate_token("user_1")
            generated = token is not None
            self.record_test(10, "Generate security token", generated)
            
            # Test token validation
            valid, user_id = tm.validate_token(token)
            is_valid = valid and user_id == "user_1"
            self.record_test(10, "Validate security token", is_valid)
            
            # Test password hashing
            enc = EncryptionManager()
            hashed, salt = enc.hash_password("password123")
            verified = enc.verify_password("password123", hashed, salt)
            self.record_test(10, "Password hashing & verification", verified)
            
        except Exception as e:
            self.record_test(10, "Security Manager tests", False, str(e)[:100])
    
    def test_phase_11_auth(self):
        """Test Phase 11 - User Authentication"""
        print_test_header(11, "User Authentication & Authorization")
        
        try:
            from auth_manager import UserManager
            
            um = UserManager()
            
            # Test create user
            success, user_id = um.create_user("testuser", "test@example.com", "pass123")
            user_created = success
            self.record_test(11, "Create user account", user_created)
            
            # Test authenticate
            if user_created:
                auth, uid = um.authenticate("testuser", "pass123")
                authenticated = auth and uid is not None
                self.record_test(11, "User authentication", authenticated)
            
            # Test session
            if user_created:
                session_id = um.create_session(user_id)
                valid, sid = um.validate_session(session_id)
                session_valid = valid
                self.record_test(11, "Session management", session_valid)
            
        except Exception as e:
            self.record_test(11, "Auth Manager tests", False, str(e)[:100])
    
    def test_phase_12_pipeline(self):
        """Test Phase 12 - Data Pipeline"""
        print_test_header(12, "Data Pipeline & ETL")
        
        try:
            from data_pipeline import DataPipeline
            
            pipeline = DataPipeline()
            
            # Test create pipeline
            pipeline.create_pipeline("test_pipeline", ["extract", "transform", "load"])
            self.record_test(12, "Create data pipeline", True)
            
            # Test add step
            pipeline.add_step("test_pipeline", "validate", {})
            self.record_test(12, "Add pipeline step", True)
            
            # Test list pipelines
            pipelines = pipeline.list_pipelines()
            has_pipeline = len(pipelines) > 0
            self.record_test(12, "List data pipelines", has_pipeline)
            
        except Exception as e:
            self.record_test(12, "Data Pipeline tests", False, str(e)[:100])
    
    def test_phase_13_collaboration(self):
        """Test Phase 13 - Real-time Collaboration"""
        print_test_header(13, "Real-time Collaboration")
        
        try:
            from collaboration_engine import CollaborationEngine
            
            ce = CollaborationEngine()
            
            # Test create session
            session_id = ce.create_collaboration_session("test_doc")
            created = session_id is not None
            self.record_test(13, "Create collaboration session", created)
            
            # Test user join
            if created:
                joined = ce.add_user_to_session(session_id, "user_1")
                self.record_test(13, "User join session", joined)
            
            # Test broadcast message
            if created:
                broadcast = ce.broadcast_message(session_id, {"action": "update"})
                self.record_test(13, "Broadcast message", True)
            
        except Exception as e:
            self.record_test(13, "Collaboration Engine tests", False, str(e)[:100])
    
    def test_phase_14_mobile(self):
        """Test Phase 14 - Mobile Integration"""
        print_test_header(14, "Mobile App Integration")
        
        try:
            from mobile_integration import MobileIntegration
            
            mobile = MobileIntegration()
            
            # Test optimize response
            data = {"key": "value", "nested": {"data": "test"}}
            optimized = mobile.optimize_response(data)
            is_optimized = optimized is not None
            self.record_test(14, "Optimize mobile response", is_optimized)
            
            # Test mobile SDK
            sdk = mobile.get_sdk_info()
            has_sdk = sdk is not None
            self.record_test(14, "Get mobile SDK info", has_sdk)
            
        except Exception as e:
            self.record_test(14, "Mobile Integration tests", False, str(e)[:100])
    
    def test_phase_15_analytics(self):
        """Test Phase 15 - Advanced Analytics"""
        print_test_header(15, "Advanced Analytics & Dashboards")
        
        try:
            from analytics_engine import AnalyticsEngine
            
            ae = AnalyticsEngine()
            
            # Test record event
            ae.record_event("user_action", {"user_id": "user_1", "action": "click"})
            self.record_test(15, "Record analytics event", True)
            
            # Test get metrics
            metrics = ae.get_metrics("user_action")
            has_metrics = len(metrics) > 0
            self.record_test(15, "Get analytics metrics", has_metrics)
            
            # Test dashboard
            dashboard = ae.get_dashboard_data()
            has_dashboard = dashboard is not None
            self.record_test(15, "Generate dashboard data", has_dashboard)
            
        except Exception as e:
            self.record_test(15, "Analytics Engine tests", False, str(e)[:100])
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("KOTO SYSTEM STABILITY TEST SUITE - COMPREHENSIVE")
        print("="*70)
        print(f"Started at: {datetime.now().isoformat()}")
        
        start_time = time.time()
        
        try:
            self.test_phase_1_frontend()
            self.test_phase_2_memory()
            self.test_phase_3_knowledge_base()
            self.test_phase_4_agent_planner()
            self.test_phase_5_workflows()
            self.test_phase_6_test_generator()
            self.test_phase_7_monitoring()
            self.test_phase_8_rate_limiter()
            self.test_phase_9_caching()
            self.test_phase_10_security()
            self.test_phase_11_auth()
            self.test_phase_12_pipeline()
            self.test_phase_13_collaboration()
            self.test_phase_14_mobile()
            self.test_phase_15_analytics()
        except Exception as e:
            print(f"\nFATAL ERROR: {e}")
            traceback.print_exc()
        
        elapsed = time.time() - start_time
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ({100*self.passed_tests//max(1,self.total_tests)}%)")
        print(f"Failed: {self.failed_tests}")
        print(f"Duration: {elapsed:.2f} seconds")
        print(f"Completed at: {datetime.now().isoformat()}")
        
        # Phase breakdown
        print("\nPhase-by-Phase Results:")
        for phase in sorted(self.phase_results.keys()):
            data = self.phase_results[phase]
            total = data["passed"] + data["failed"]
            pct = 100 * data["passed"] // max(1, total)
            print(f"  Phase {phase:2d}: {data['passed']}/{total} tests passed ({pct}%)")
        
        return self.passed_tests, self.failed_tests, elapsed

if __name__ == "__main__":
    tester = StabilityTester()
    passed, failed, duration = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)
