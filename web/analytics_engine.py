#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 15 - Advanced Analytics & Dashboards
Data analytics, reporting, visualization, and BI dashboards

This module provides:
1. Advanced data analytics
2. Real-time metrics
3. Report generation
4. Dashboard creation
5. Trend analysis
6. Business intelligence
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from statistics import mean, median, stdev
import uuid


class MetricType(Enum):
    """Metric types"""
    GAUGE = "gauge"  # Current value
    COUNTER = "counter"  # Cumulative count
    HISTOGRAM = "histogram"  # Distribution
    TIMER = "timer"  # Duration


class ReportFormat(Enum):
    """Report formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"


class DashboardType(Enum):
    """Dashboard types"""
    OVERVIEW = "overview"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    CUSTOM = "custom"


@dataclass
class Metric:
    """Single metric"""
    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    unit: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class DataPoint:
    """Time series data point"""
    timestamp: str
    value: float
    metric_name: str


@dataclass
class Report:
    """Generated report"""
    report_id: str
    title: str
    report_format: ReportFormat
    content: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generated_by: str = ""


@dataclass
class Dashboard:
    """Analytics dashboard"""
    dashboard_id: str
    name: str
    dashboard_type: DashboardType
    widgets: List[str] = field(default_factory=list)  # widget_ids
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_public: bool = False


class MetricsCollector:
    """Collect and aggregate metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.metric_history: Dict[str, List[DataPoint]] = {}
    
    def record_metric(self, name: str, value: float, metric_type: MetricType,
                     unit: str = "", tags: Dict = None) -> Metric:
        """Record metric"""
        metric_id = str(uuid.uuid4())
        metric = Metric(
            metric_id=metric_id,
            name=name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        
        self.metrics[metric_id] = metric
        
        # Store in history
        if name not in self.metric_history:
            self.metric_history[name] = []
        
        self.metric_history[name].append(
            DataPoint(
                timestamp=metric.timestamp,
                value=value,
                metric_name=name
            )
        )
        
        return metric
    
    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for metric"""
        if metric_name not in self.metric_history:
            return {}
        
        data_points = self.metric_history[metric_name]
        values = [dp.value for dp in data_points]
        
        if not values:
            return {}
        
        stats = {
            "count": len(values),
            "sum": sum(values),
            "mean": mean(values),
            "median": median(values),
            "min": min(values),
            "max": max(values)
        }
        
        if len(values) > 1:
            stats["stdev"] = stdev(values)
        
        return stats
    
    def get_recent_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metrics from last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        result = []
        for metric in self.metrics.values():
            metric_time = datetime.fromisoformat(metric.timestamp)
            if metric_time > cutoff_time:
                result.append(asdict(metric))
        
        return result


class TrendAnalyzer:
    """Analyze trends in data"""
    
    def __init__(self):
        self.trends: Dict[str, Dict[str, Any]] = {}
    
    def calculate_trend(self, metric_name: str, data_points: List[float]) -> Dict[str, Any]:
        """Calculate trend from data points"""
        if len(data_points) < 2:
            return {"trend": "insufficient_data"}
        
        # Simple linear trend: compare first half to second half
        mid_point = len(data_points) // 2
        first_half = mean(data_points[:mid_point])
        second_half = mean(data_points[mid_point:])
        
        if first_half == 0:
            change_percent = 0
        else:
            change_percent = ((second_half - first_half) / first_half) * 100
        
        trend = "increasing" if change_percent > 2 else ("decreasing" if change_percent < -2 else "stable")
        
        trend_data = {
            "metric_name": metric_name,
            "trend": trend,
            "change_percent": change_percent,
            "first_half_avg": first_half,
            "second_half_avg": second_half
        }
        
        self.trends[metric_name] = trend_data
        return trend_data
    
    def get_trend_analysis(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get trend analysis for metric"""
        return self.trends.get(metric_name)


class ReportGenerator:
    """Generate reports"""
    
    def __init__(self):
        self.reports: Dict[str, Report] = {}
    
    def generate_report(self, title: str, format: ReportFormat,
                       content: str, generated_by: str = "") -> Report:
        """Generate report"""
        report_id = str(uuid.uuid4())
        report = Report(
            report_id=report_id,
            title=title,
            report_format=format,
            content=content,
            generated_by=generated_by
        )
        
        self.reports[report_id] = report
        return report
    
    def create_summary_report(self, metrics: Dict[str, Dict]) -> Report:
        """Create summary report from metrics"""
        summary_content = {
            "summary": "System Metrics Summary",
            "metrics": metrics,
            "generated_at": datetime.now().isoformat()
        }
        
        return self.generate_report(
            "Metrics Summary",
            ReportFormat.JSON,
            json.dumps(summary_content, indent=2)
        )
    
    def get_report_stats(self) -> Dict[str, Any]:
        """Get report generation statistics"""
        by_format = {}
        for report in self.reports.values():
            format_name = report.report_format.value
            by_format[format_name] = by_format.get(format_name, 0) + 1
        
        return {
            "total_reports": len(self.reports),
            "reports_by_format": by_format
        }


class Widget:
    """Dashboard widget"""
    
    def __init__(self, widget_id: str, title: str, widget_type: str,
                 data_source: str = ""):
        self.widget_id = widget_id
        self.title = title
        self.widget_type = widget_type  # "chart", "gauge", "table", "kpi"
        self.data_source = data_source
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "title": self.title,
            "widget_type": self.widget_type,
            "data_source": self.data_source,
            "created_at": self.created_at
        }


class DashboardBuilder:
    """Build and manage dashboards"""
    
    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}
        self.widgets: Dict[str, Widget] = {}
    
    def create_dashboard(self, name: str, dashboard_type: DashboardType) -> Dashboard:
        """Create dashboard"""
        dashboard_id = str(uuid.uuid4())
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name=name,
            dashboard_type=dashboard_type
        )
        
        self.dashboards[dashboard_id] = dashboard
        return dashboard
    
    def add_widget(self, dashboard_id: str, title: str, widget_type: str,
                  data_source: str = "") -> Optional[str]:
        """Add widget to dashboard"""
        if dashboard_id not in self.dashboards:
            return None
        
        widget_id = str(uuid.uuid4())
        widget = Widget(widget_id, title, widget_type, data_source)
        
        self.widgets[widget_id] = widget
        self.dashboards[dashboard_id].widgets.append(widget_id)
        self.dashboards[dashboard_id].updated_at = datetime.now().isoformat()
        
        return widget_id
    
    def get_dashboard_content(self, dashboard_id: str) -> Dict[str, Any]:
        """Get complete dashboard content"""
        if dashboard_id not in self.dashboards:
            return {}
        
        dashboard = self.dashboards[dashboard_id]
        widgets = [self.widgets[wid].to_dict() for wid in dashboard.widgets
                  if wid in self.widgets]
        
        return {
            "dashboard_id": dashboard.dashboard_id,
            "name": dashboard.name,
            "type": dashboard.dashboard_type.value,
            "widgets": widgets,
            "updated_at": dashboard.updated_at
        }
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        return {
            "total_dashboards": len(self.dashboards),
            "total_widgets": len(self.widgets),
            "average_widgets_per_dashboard": (
                sum(len(d.widgets) for d in self.dashboards.values()) / len(self.dashboards)
                if self.dashboards else 0
            )
        }


class AnalyticsEngine:
    """Central analytics engine"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.trend_analyzer = TrendAnalyzer()
        self.report_generator = ReportGenerator()
        self.dashboard_builder = DashboardBuilder()
    
    def get_analytics_status(self) -> Dict[str, Any]:
        """Get overall analytics status"""
        recent_metrics = self.metrics_collector.get_recent_metrics()
        
        return {
            "metrics": {
                "total_recorded": len(self.metrics_collector.metrics),
                "recent_count": len(recent_metrics)
            },
            "trends": len(self.trend_analyzer.trends),
            "reports": self.report_generator.get_report_stats(),
            "dashboards": self.dashboard_builder.get_dashboard_stats()
        }
    
    def create_performance_dashboard(self, name: str) -> Dashboard:
        """Create performance monitoring dashboard"""
        dashboard = self.dashboard_builder.create_dashboard(name, DashboardType.PERFORMANCE)
        
        # Add standard widgets
        self.dashboard_builder.add_widget(dashboard.dashboard_id, "System Health", "gauge")
        self.dashboard_builder.add_widget(dashboard.dashboard_id, "Response Times", "chart")
        self.dashboard_builder.add_widget(dashboard.dashboard_id, "Error Rate", "chart")
        self.dashboard_builder.add_widget(dashboard.dashboard_id, "Active Users", "kpi")
        
        return dashboard


# Example usage
if __name__ == "__main__":
    engine = AnalyticsEngine()
    
    # Record metrics
    for i in range(10):
        engine.metrics_collector.record_metric(
            "response_time_ms", 50 + i * 5, MetricType.TIMER, "ms"
        )
    
    # Calculate trend
    trend_data = engine.trend_analyzer.calculate_trend(
        "response_time_ms",
        [50, 52, 54, 56, 58, 60, 62, 64, 66, 68]
    )
    print(f"Trend: {trend_data['trend']}")
    
    # Create dashboard
    dashboard = engine.create_performance_dashboard("System Performance")
    print(f"Dashboard created: {dashboard.name} with {len(dashboard.widgets)} widgets")
    
    # Generate report
    metrics_stats = {}
    for name in ["response_time_ms"]:
        metrics_stats[name] = engine.metrics_collector.get_metric_stats(name)
    
    report = engine.report_generator.create_summary_report(metrics_stats)
    print(f"Report generated: {report.report_id}")
    
    # Get status
    status = engine.get_analytics_status()
    print(json.dumps(status, indent=2))
