#!/usr/bin/env python3
"""
Module 6: Metrics, Monitoring & Performance
Demonstrates comprehensive system monitoring, performance analytics, 
and metrics collection for multi-agent research systems.
"""

import asyncio
import time
import json
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import statistics
import os
from pathlib import Path

# External dependencies
import aiohttp
import structlog
from asyncio_throttle import Throttler

# Configure logging
logger = structlog.get_logger()

class MetricType(Enum):
    PERFORMANCE = "performance"
    COST = "cost"
    QUALITY = "quality"
    USAGE = "usage"
    ERROR = "error"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Metric:
    name: str
    value: Union[float, int]
    unit: str
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    level: AlertLevel
    message: str
    metric_name: str
    threshold: float
    actual_value: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceAnalysis:
    avg_response_time: float
    p95_response_time: float
    success_rate: float
    error_rate: float
    total_requests: int
    total_cost: float
    cost_per_request: float
    tokens_per_second: float
    
class MetricsCollector:
    """Comprehensive metrics collection and monitoring system"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self.metrics_buffer: List[Metric] = []
        self.alerts: List[Alert] = []
        
        # Alert thresholds
        self.thresholds = {
            "response_time": {"warning": 5.0, "critical": 10.0},  # seconds
            "error_rate": {"warning": 0.05, "critical": 0.10},    # 5%, 10%
            "cost_per_request": {"warning": 0.50, "critical": 1.00},  # dollars
            "success_rate": {"warning": 0.90, "critical": 0.80}   # 90%, 80%
        }
        
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for metrics storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                metadata TEXT
            )
        """)
        
        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                threshold REAL NOT NULL,
                actual_value REAL NOT NULL,
                timestamp DATETIME NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
    def record_metric(self, metric: Metric):
        """Record a single metric"""
        self.metrics_buffer.append(metric)
        
        # Check for alerts
        self._check_alerts(metric)
        
        # Flush buffer if it gets too large
        if len(self.metrics_buffer) >= 100:
            self._flush_metrics()
            
    def record_performance_metric(self, operation: str, duration: float, 
                                success: bool = True, **metadata):
        """Record a performance metric"""
        metric = Metric(
            name=f"performance.{operation}.duration",
            value=duration,
            unit="seconds",
            metric_type=MetricType.PERFORMANCE,
            metadata={**metadata, "success": success}
        )
        self.record_metric(metric)
        
    def record_cost_metric(self, operation: str, cost: float, tokens: int, 
                          model: str, **metadata):
        """Record a cost metric"""
        cost_metric = Metric(
            name=f"cost.{operation}.total",
            value=cost,
            unit="usd",
            metric_type=MetricType.COST,
            metadata={**metadata, "tokens": tokens, "model": model}
        )
        self.record_metric(cost_metric)
        
        # Also record cost per token
        cost_per_token = cost / tokens if tokens > 0 else 0
        token_metric = Metric(
            name=f"cost.{operation}.per_token",
            value=cost_per_token,
            unit="usd_per_token",
            metric_type=MetricType.COST,
            metadata={**metadata, "model": model}
        )
        self.record_metric(token_metric)
        
    def record_quality_metric(self, operation: str, quality_score: float, 
                            confidence: float, **metadata):
        """Record a quality metric"""
        quality_metric = Metric(
            name=f"quality.{operation}.score",
            value=quality_score,
            unit="score",
            metric_type=MetricType.QUALITY,
            metadata={**metadata, "confidence": confidence}
        )
        self.record_metric(quality_metric)
        
    def record_usage_metric(self, resource: str, usage: float, 
                          capacity: float, **metadata):
        """Record a usage metric"""
        usage_metric = Metric(
            name=f"usage.{resource}.current",
            value=usage,
            unit="units",
            metric_type=MetricType.USAGE,
            metadata={**metadata, "capacity": capacity, "utilization": usage/capacity}
        )
        self.record_metric(usage_metric)
        
    def record_error_metric(self, operation: str, error_type: str, **metadata):
        """Record an error metric"""
        error_metric = Metric(
            name=f"error.{operation}.{error_type}",
            value=1,
            unit="count",
            metric_type=MetricType.ERROR,
            metadata=metadata
        )
        self.record_metric(error_metric)
        
    def _check_alerts(self, metric: Metric):
        """Check if metric triggers any alerts"""
        if "response_time" in metric.name:
            self._check_threshold_alert(metric, "response_time")
        elif "cost" in metric.name and "per_request" in metric.name:
            self._check_threshold_alert(metric, "cost_per_request")
        elif "error_rate" in metric.name:
            self._check_threshold_alert(metric, "error_rate")
        elif "success_rate" in metric.name:
            self._check_threshold_alert(metric, "success_rate", reverse=True)
            
    def _check_threshold_alert(self, metric: Metric, threshold_key: str, reverse: bool = False):
        """Check if metric crosses threshold and create alert"""
        thresholds = self.thresholds.get(threshold_key, {})
        
        for level_name, threshold_value in thresholds.items():
            if reverse:
                # For metrics where lower values are bad (like success_rate)
                triggered = metric.value < threshold_value
            else:
                # For metrics where higher values are bad
                triggered = metric.value > threshold_value
                
            if triggered:
                alert = Alert(
                    level=AlertLevel.WARNING if level_name == "warning" else AlertLevel.CRITICAL,
                    message=f"{metric.name} {level_name}: {metric.value} {metric.unit} (threshold: {threshold_value})",
                    metric_name=metric.name,
                    threshold=threshold_value,
                    actual_value=metric.value
                )
                self.alerts.append(alert)
                
                logger.warning(
                    "Alert triggered",
                    level=alert.level.value,
                    message=alert.message,
                    metric_name=metric.name
                )
                break  # Only trigger the first threshold crossed
                
    def _flush_metrics(self):
        """Flush metrics buffer to database"""
        if not self.metrics_buffer:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert metrics
        for metric in self.metrics_buffer:
            cursor.execute("""
                INSERT INTO metrics (name, value, unit, metric_type, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metric.name,
                metric.value,
                metric.unit,
                metric.metric_type.value,
                metric.timestamp.isoformat(),
                json.dumps(metric.metadata)
            ))
            
        # Insert alerts
        for alert in self.alerts:
            cursor.execute("""
                INSERT INTO alerts (level, message, metric_name, threshold, actual_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert.level.value,
                alert.message,
                alert.metric_name,
                alert.threshold,
                alert.actual_value,
                alert.timestamp.isoformat()
            ))
            
        conn.commit()
        conn.close()
        
        logger.info("Metrics flushed", count=len(self.metrics_buffer), alerts=len(self.alerts))
        
        # Clear buffers
        self.metrics_buffer.clear()
        self.alerts.clear()
        
    def get_performance_analysis(self, hours: int = 24) -> PerformanceAnalysis:
        """Get performance analysis for the last N hours"""
        self._flush_metrics()  # Ensure all metrics are in database
        
        since = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get performance metrics
        cursor.execute("""
            SELECT value, metadata FROM metrics 
            WHERE metric_type = 'performance' 
            AND timestamp > ? 
            AND name LIKE '%.duration'
        """, (since.isoformat(),))
        
        performance_data = cursor.fetchall()
        
        # Get cost metrics
        cursor.execute("""
            SELECT value FROM metrics 
            WHERE metric_type = 'cost' 
            AND timestamp > ? 
            AND name LIKE '%.total'
        """, (since.isoformat(),))
        
        cost_data = cursor.fetchall()
        
        conn.close()
        
        if not performance_data:
            return PerformanceAnalysis(
                avg_response_time=0.0,
                p95_response_time=0.0,
                success_rate=0.0,
                error_rate=0.0,
                total_requests=0,
                total_cost=0.0,
                cost_per_request=0.0,
                tokens_per_second=0.0
            )
            
        # Parse performance data
        response_times = []
        successes = 0
        total_requests = len(performance_data)
        
        for value, metadata_json in performance_data:
            response_times.append(value)
            metadata = json.loads(metadata_json) if metadata_json else {}
            if metadata.get("success", True):
                successes += 1
                
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
        success_rate = successes / total_requests if total_requests > 0 else 0
        error_rate = 1 - success_rate
        
        # Calculate cost statistics
        total_cost = sum(row[0] for row in cost_data)
        cost_per_request = total_cost / total_requests if total_requests > 0 else 0
        
        # Estimate tokens per second (simplified)
        total_time = sum(response_times)
        tokens_per_second = (total_requests * 500) / total_time if total_time > 0 else 0  # Assume 500 tokens per request
        
        return PerformanceAnalysis(
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            success_rate=success_rate,
            error_rate=error_rate,
            total_requests=total_requests,
            total_cost=total_cost,
            cost_per_request=cost_per_request,
            tokens_per_second=tokens_per_second
        )
        
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts"""
        self._flush_metrics()
        
        since = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT level, message, metric_name, threshold, actual_value, timestamp 
            FROM alerts 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC
        """, (since.isoformat(),))
        
        alert_data = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in alert_data:
            alert = Alert(
                level=AlertLevel(row[0]),
                message=row[1],
                metric_name=row[2],
                threshold=row[3],
                actual_value=row[4],
                timestamp=datetime.fromisoformat(row[5])
            )
            alerts.append(alert)
            
        return alerts
        
    def cleanup_old_metrics(self, days: int = 30):
        """Clean up metrics older than N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff.isoformat(),))
        cursor.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff.isoformat(),))
        
        conn.commit()
        conn.close()
        
        logger.info("Old metrics cleaned up", cutoff_date=cutoff.isoformat())

class MonitoredLLMAgent:
    """LLM Agent with integrated monitoring"""
    
    def __init__(self, api_key: str, model: str, metrics_collector: MetricsCollector):
        self.api_key = api_key
        self.model = model
        self.metrics = metrics_collector
        self.base_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.session = None
        self.throttler = Throttler(rate_limit=10, period=1.0)
        
        # Model costs (per 1M tokens)
        self.model_costs = {
            "accounts/fireworks/models/llama-v3p3-70b-instruct": 0.0009,
            "accounts/fireworks/models/llama-v3p1-8b-instruct": 0.0002,
            "accounts/fireworks/models/qwen2p5-72b-instruct": 0.0009
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def generate_response(self, prompt: str, operation: str = "generation") -> Dict[str, Any]:
        """Generate response with comprehensive monitoring"""
        start_time = time.time()
        
        try:
            async with self.throttler:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
                
                async with self.session.post(self.base_url, json=payload) as response:
                    duration = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        tokens_used = data["usage"]["total_tokens"]
                        cost = (tokens_used / 1_000_000) * self.model_costs.get(self.model, 0.001)
                        
                        # Record metrics
                        self.metrics.record_performance_metric(
                            operation, duration, success=True,
                            model=self.model, tokens=tokens_used
                        )
                        
                        self.metrics.record_cost_metric(
                            operation, cost, tokens_used, self.model
                        )
                        
                        # Simulate quality scoring
                        quality_score = min(0.9, len(content) / 1000)  # Simple quality metric
                        confidence = 0.85
                        
                        self.metrics.record_quality_metric(
                            operation, quality_score, confidence
                        )
                        
                        return {
                            "content": content,
                            "tokens_used": tokens_used,
                            "cost": cost,
                            "duration": duration,
                            "quality_score": quality_score,
                            "success": True
                        }
                    else:
                        error_text = await response.text()
                        
                        # Record error metrics
                        self.metrics.record_performance_metric(
                            operation, duration, success=False,
                            error=error_text, status_code=response.status
                        )
                        
                        self.metrics.record_error_metric(
                            operation, "api_error", 
                            status_code=response.status, error=error_text
                        )
                        
                        return {
                            "error": error_text,
                            "status_code": response.status,
                            "duration": duration,
                            "success": False
                        }
                        
        except Exception as e:
            duration = time.time() - start_time
            
            # Record exception metrics
            self.metrics.record_performance_metric(
                operation, duration, success=False,
                error=str(e), error_type=type(e).__name__
            )
            
            self.metrics.record_error_metric(
                operation, "exception",
                error=str(e), error_type=type(e).__name__
            )
            
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "success": False
            }

async def simulate_monitoring_demo():
    """Simulate a monitoring demo with multiple agents and operations"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("FIREWORKS_API_KEY")
    
    if not api_key:
        print("❌ FIREWORKS_API_KEY not found in environment")
        return
        
    # Initialize metrics collector
    metrics_collector = MetricsCollector("demo_metrics.db")
    
    # Initialize multiple agents
    agents = {
        "planner": MonitoredLLMAgent(api_key, "accounts/fireworks/models/llama-v3p3-70b-instruct", metrics_collector),
        "retriever": MonitoredLLMAgent(api_key, "accounts/fireworks/models/llama-v3p1-8b-instruct", metrics_collector),
        "summarizer": MonitoredLLMAgent(api_key, "accounts/fireworks/models/qwen2p5-72b-instruct", metrics_collector)
    }
    
    print("🔍 Metrics, Monitoring & Performance Demo")
    print("=" * 50)
    print("Simulating multi-agent operations with monitoring...")
    print()
    
    # Simulate various operations
    operations = [
        ("planner", "planning", "Create a research plan for quantum computing"),
        ("retriever", "search", "Find information about quantum computing applications"),
        ("summarizer", "summarization", "Summarize quantum computing research findings"),
        ("planner", "planning", "Plan research on AI ethics"),
        ("retriever", "search", "Search for AI ethics guidelines"),
        ("summarizer", "summarization", "Summarize AI ethics research")
    ]
    
    results = []
    
    for agent_name, operation, prompt in operations:
        print(f"🤖 {agent_name.title()} Agent - {operation}")
        
        async with agents[agent_name] as agent:
            result = await agent.generate_response(prompt, operation)
            results.append((agent_name, operation, result))
            
            if result["success"]:
                print(f"✅ Success - {result['tokens_used']} tokens, ${result['cost']:.6f}, {result['duration']:.2f}s")
            else:
                print(f"❌ Failed - {result.get('error', 'Unknown error')}")
        print()
        
        # Add some delay to simulate realistic timing
        await asyncio.sleep(0.5)
    
    # Record some additional metrics
    metrics_collector.record_usage_metric("memory", 512, 1024, process="demo")
    metrics_collector.record_usage_metric("cpu", 45, 100, process="demo")
    
    # Generate performance analysis
    print("📊 Performance Analysis")
    print("-" * 30)
    
    analysis = metrics_collector.get_performance_analysis(hours=1)
    
    print(f"Total Requests: {analysis.total_requests}")
    print(f"Success Rate: {analysis.success_rate:.1%}")
    print(f"Error Rate: {analysis.error_rate:.1%}")
    print(f"Avg Response Time: {analysis.avg_response_time:.2f}s")
    print(f"95th Percentile: {analysis.p95_response_time:.2f}s")
    print(f"Total Cost: ${analysis.total_cost:.6f}")
    print(f"Cost per Request: ${analysis.cost_per_request:.6f}")
    print(f"Tokens per Second: {analysis.tokens_per_second:.1f}")
    print()
    
    # Check for alerts
    alerts = metrics_collector.get_recent_alerts(hours=1)
    if alerts:
        print("🚨 Recent Alerts")
        print("-" * 20)
        for alert in alerts:
            emoji = "🟡" if alert.level == AlertLevel.WARNING else "🔴"
            print(f"{emoji} {alert.level.value.upper()}: {alert.message}")
        print()
    else:
        print("✅ No alerts in the last hour")
        print()
    
    # Display detailed results
    print("📋 Detailed Operation Results")
    print("-" * 35)
    
    for agent_name, operation, result in results:
        print(f"🤖 {agent_name.title()} - {operation}")
        if result["success"]:
            print(f"   Response: {result['content'][:100]}...")
            print(f"   Metrics: {result['tokens_used']} tokens, ${result['cost']:.6f}, {result['duration']:.2f}s")
            print(f"   Quality: {result['quality_score']:.2f}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        print()
    
    print("🎉 Monitoring Demo Complete!")
    print("Key Features Demonstrated:")
    print("• Real-time performance monitoring")
    print("• Cost tracking and optimization")
    print("• Quality metrics and scoring")
    print("• Alert system with thresholds")
    print("• Comprehensive performance analysis")
    print("• Multi-agent coordination monitoring")
    
    # Cleanup
    metrics_collector.cleanup_old_metrics(days=1)  # Clean up demo data

if __name__ == "__main__":
    asyncio.run(simulate_monitoring_demo()) 