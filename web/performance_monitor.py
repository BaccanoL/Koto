#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 7 - Performance Monitoring & Health Check System
Real-time performance tracking, bottleneck detection, and system health monitoring

This module provides:
1. API performance monitoring and profiling
2. System health checks and status tracking
3. Bottleneck detection and analysis
4. Historical performance data collection
5. Alerts and notifications for performance issues
"""

import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from collections import deque
from enum import Enum


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class PerformanceMetric:
    """Single performance metric"""
    timestamp: str
    metric_name: str
    value: float
    unit: str
    threshold: Optional[float] = None
    status: str = "normal"  # normal, warning, critical
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemMetrics:
    """System resource metrics"""
    timestamp: str
    cpu_usage: float  # 0-100%
    memory_usage: float  # 0-100%
    disk_usage: float  # 0-100%
    memory_mb: float  # Total memory in MB
    available_memory_mb: float  # Available memory in MB
    disk_read_mb_s: float  # Disk read speed
    disk_write_mb_s: float  # Disk write speed
    active_threads: int
    io_wait: float  # IO wait percentage
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APICall:
    """API call performance record"""
    call_id: str
    endpoint: str
    method: str
    timestamp: str
    duration_ms: float
    status_code: int
    request_size_bytes: int
    response_size_bytes: int
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HealthCheck:
    """Health check result"""
    check_id: str
    check_name: str
    timestamp: str
    status: HealthStatus
    duration_ms: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        return data


class PerformanceMonitor:
    """Monitor and track API performance"""
    
    def __init__(self, max_history: int = 10000):
        self.api_calls: deque = deque(maxlen=max_history)
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def record_api_call(self,
                        endpoint: str,
                        method: str,
                        duration_ms: float,
                        status_code: int,
                        request_size: int = 0,
                        response_size: int = 0,
                        error: Optional[str] = None) -> APICall:
        """Record API call metrics"""
        call_id = f"api_{int(time.time() * 1000) % 1000000}"
        
        call = APICall(
            call_id=call_id,
            endpoint=endpoint,
            method=method,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration_ms,
            status_code=status_code,
            request_size_bytes=request_size,
            response_size_bytes=response_size,
            error=error
        )
        
        with self.lock:
            self.api_calls.append(call)
        
        return call
    
    def get_performance_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            calls = [c for c in self.api_calls]
        
        if endpoint:
            calls = [c for c in calls if c.endpoint == endpoint]
        
        if not calls:
            return {
                "total_calls": 0,
                "avg_duration_ms": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
                "error_rate": 0.0
            }
        
        durations = [c.duration_ms for c in calls]
        errors = sum(1 for c in calls if c.error or c.status_code >= 400)
        
        return {
            "total_calls": len(calls),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            "p99_duration_ms": sorted(durations)[int(len(durations) * 0.99)] if durations else 0,
            "error_rate": (errors / len(calls)) * 100 if calls else 0.0,
            "errors": errors,
            "successful": len(calls) - errors
        }
    
    def get_hotspots(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Identify slowest endpoints (bottlenecks)"""
        with self.lock:
            calls = [c for c in self.api_calls]
        
        if not calls:
            return []
        
        # Group by endpoint
        endpoint_stats: Dict[str, List[APICall]] = {}
        for call in calls:
            if call.endpoint not in endpoint_stats:
                endpoint_stats[call.endpoint] = []
            endpoint_stats[call.endpoint].append(call)
        
        # Calculate average time per endpoint
        hotspots = []
        for endpoint, endpoint_calls in endpoint_stats.items():
            avg_time = sum(c.duration_ms for c in endpoint_calls) / len(endpoint_calls)
            hotspots.append({
                "endpoint": endpoint,
                "avg_duration_ms": avg_time,
                "call_count": len(endpoint_calls),
                "total_time_ms": sum(c.duration_ms for c in endpoint_calls)
            })
        
        return sorted(hotspots, key=lambda x: x['avg_duration_ms'], reverse=True)[:top_n]


class SystemHealthMonitor:
    """Monitor system health and resources"""
    
    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1000)
        self.lock = threading.Lock()
        self.thresholds = {
            "cpu": 80.0,
            "memory": 85.0,
            "disk": 90.0,
            "io_wait": 50.0
        }
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        process = psutil.Process()
        
        # CPU and memory
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        # Memory in MB
        memory_info = psutil.virtual_memory()
        total_memory_mb = memory_info.total / (1024 ** 2)
        available_memory_mb = memory_info.available / (1024 ** 2)
        
        # Disk IO
        io_counters = psutil.disk_io_counters()
        disk_read = io_counters.read_bytes / (1024 ** 2)  # MB
        disk_write = io_counters.write_bytes / (1024 ** 2)  # MB
        
        # Threads
        active_threads = process.num_threads()
        
        # IO wait (average)
        io_wait = 0  # Simplified for cross-platform compatibility
        
        metrics = SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_usage=cpu_usage,
            memory_usage=memory_percent,
            disk_usage=disk_usage,
            memory_mb=total_memory_mb,
            available_memory_mb=available_memory_mb,
            disk_read_mb_s=disk_read,
            disk_write_mb_s=disk_write,
            active_threads=active_threads,
            io_wait=io_wait
        )
        
        with self.lock:
            self.metrics_history.append(metrics)
        
        return metrics
    
    def get_health_status(self) -> Dict[str, Any]:
        """Determine overall system health"""
        metrics = self.collect_metrics()
        
        status = HealthStatus.HEALTHY
        issues = []
        
        if metrics.cpu_usage > self.thresholds["cpu"]:
            status = HealthStatus.DEGRADED
            issues.append(f"High CPU usage: {metrics.cpu_usage:.1f}%")
        
        if metrics.memory_usage > self.thresholds["memory"]:
            status = HealthStatus.DEGRADED
            issues.append(f"High memory usage: {metrics.memory_usage:.1f}%")
        
        if metrics.disk_usage > self.thresholds["disk"]:
            status = HealthStatus.CRITICAL
            issues.append(f"Disk space critical: {metrics.disk_usage:.1f}%")
        
        if metrics.memory_usage > 95:
            status = HealthStatus.CRITICAL
        
        return {
            "status": status.value,
            "timestamp": metrics.timestamp,
            "metrics": {
                "cpu": metrics.cpu_usage,
                "memory": metrics.memory_usage,
                "disk": metrics.disk_usage,
                "available_memory_mb": metrics.available_memory_mb,
                "active_threads": metrics.active_threads
            },
            "issues": issues,
            "is_healthy": status == HealthStatus.HEALTHY
        }
    
    def get_metrics_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get historical metrics"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            history = [
                m.to_dict() for m in self.metrics_history
                if datetime.fromisoformat(m.timestamp) > cutoff_time
            ]
        
        return history


class HealthCheckManager:
    """Manage health checks"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results_history: deque = deque(maxlen=1000)
        self.lock = threading.Lock()
    
    def register_check(self, check_name: str, check_fn: Callable):
        """Register a health check function"""
        self.checks[check_name] = check_fn
    
    def run_check(self, check_name: str) -> Optional[HealthCheck]:
        """Execute a single health check"""
        if check_name not in self.checks:
            return None
        
        check_fn = self.checks[check_name]
        start_time = time.time()
        
        try:
            details = check_fn()
            duration_ms = (time.time() - start_time) * 1000
            
            # Determine status from check result
            status = HealthStatus.HEALTHY
            if isinstance(details, dict):
                if details.get("error"):
                    status = HealthStatus.CRITICAL
                elif details.get("warning"):
                    status = HealthStatus.DEGRADED
            
            check = HealthCheck(
                check_id=f"check_{int(time.time() * 1000) % 1000000}",
                check_name=check_name,
                timestamp=datetime.now().isoformat(),
                status=status,
                duration_ms=duration_ms,
                details=details if isinstance(details, dict) else {"result": details}
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            check = HealthCheck(
                check_id=f"check_{int(time.time() * 1000) % 1000000}",
                check_name=check_name,
                timestamp=datetime.now().isoformat(),
                status=HealthStatus.CRITICAL,
                duration_ms=duration_ms,
                details={"error": str(e)},
                error_message=str(e)
            )
        
        with self.lock:
            self.results_history.append(check)
        
        return check
    
    def run_all_checks(self) -> List[HealthCheck]:
        """Run all registered checks"""
        results = []
        for check_name in self.checks.keys():
            check = self.run_check(check_name)
            if check:
                results.append(check)
        
        return results
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get overall health status"""
        checks = self.run_all_checks()
        
        statuses = [c.status for c in checks]
        critical = sum(1 for s in statuses if s == HealthStatus.CRITICAL)
        degraded = sum(1 for s in statuses if s == HealthStatus.DEGRADED)
        healthy = sum(1 for s in statuses if s == HealthStatus.HEALTHY)
        
        # Overall status
        if critical > 0:
            overall = HealthStatus.CRITICAL
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        return {
            "overall_status": overall.value,
            "critical_checks": critical,
            "degraded_checks": degraded,
            "healthy_checks": healthy,
            "total_checks": len(checks),
            "checks": [c.to_dict() for c in checks],
            "timestamp": datetime.now().isoformat()
        }


class MonitoringHub:
    """Central monitoring hub combining all monitors"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.health_monitor = SystemHealthMonitor()
        self.health_check_manager = HealthCheckManager()
        
        # Register default health checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.health_check_manager.register_check(
            "memory_check",
            lambda: {"available_mb": psutil.virtual_memory().available / (1024**2)}
        )
        
        self.health_check_manager.register_check(
            "disk_check",
            lambda: {"free_gb": psutil.disk_usage('/').free / (1024**3)}
        )
        
        self.health_check_manager.register_check(
            "process_check",
            lambda: {"active_threads": psutil.Process().num_threads()}
        )
    
    def record_api_call(self, endpoint: str, method: str, duration_ms: float,
                       status_code: int, request_size: int = 0, 
                       response_size: int = 0, error: Optional[str] = None):
        """Record API call"""
        return self.performance_monitor.record_api_call(
            endpoint, method, duration_ms, status_code, request_size, response_size, error
        )
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": self.health_monitor.get_health_status(),
            "health_checks": self.health_check_manager.get_status_summary(),
            "api_performance": self.performance_monitor.get_performance_stats(),
            "bottlenecks": self.performance_monitor.get_hotspots(top_n=3)
        }
    
    def get_full_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        return {
            "generated_at": datetime.now().isoformat(),
            "system_health": self.get_system_health(),
            "metrics_history": self.health_monitor.get_metrics_history(minutes=60),
            "api_hotspots": self.performance_monitor.get_hotspots(top_n=10)
        }


# Example initialization
if __name__ == "__main__":
    hub = MonitoringHub()
    
    # Simulate some API calls
    for i in range(5):
        hub.record_api_call(
            f"/api/endpoint{i % 2}",
            "GET",
            50 + i * 10,
            200
        )
    
    # Get system health
    health = hub.get_system_health()
    print(json.dumps(health, indent=2, ensure_ascii=False))
