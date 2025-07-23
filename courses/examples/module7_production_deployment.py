#!/usr/bin/env python3
"""
Module 7: Production Deployment & Scaling
Demonstrates Docker containers, load balancing, auto-scaling, 
health checks, and production-ready configuration.
"""

import asyncio
import time
import json
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging
from pathlib import Path

# External dependencies
import aiohttp
from aiohttp import web, ClientSession
import structlog
import uvloop
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('research_requests_total', 'Total research requests', ['endpoint', 'method', 'status'])
REQUEST_DURATION = Histogram('research_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('research_active_connections', 'Active connections')
AGENT_EXECUTIONS = Counter('agent_executions_total', 'Agent executions', ['agent_type', 'status'])

@dataclass
class HealthStatus:
    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    checks: Dict[str, bool] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.checks = {}
        self.status_cache = {}
        self.cache_ttl = 30  # seconds
        
    def register_check(self, name: str, check_func):
        """Register a health check function"""
        self.checks[name] = check_func
        
    async def run_check(self, name: str) -> bool:
        """Run a specific health check"""
        if name not in self.checks:
            return False
            
        try:
            return await self.checks[name]()
        except Exception as e:
            logger.error("Health check failed", check=name, error=str(e))
            return False
            
    async def get_health_status(self) -> HealthStatus:
        """Get overall health status"""
        now = datetime.now()
        cache_key = "overall"
        
        # Check cache
        if (cache_key in self.status_cache and 
            (now - self.status_cache[cache_key].timestamp).seconds < self.cache_ttl):
            return self.status_cache[cache_key]
            
        # Run all checks
        check_results = {}
        for check_name in self.checks:
            check_results[check_name] = await self.run_check(check_name)
            
        # Determine overall status
        all_healthy = all(check_results.values())
        any_healthy = any(check_results.values())
        
        if all_healthy:
            status = "healthy"
        elif any_healthy:
            status = "degraded"
        else:
            status = "unhealthy"
            
        health_status = HealthStatus(
            service="research-system",
            status=status,
            checks=check_results,
            details={
                "total_checks": len(check_results),
                "passed_checks": sum(check_results.values()),
                "failed_checks": len(check_results) - sum(check_results.values())
            }
        )
        
        # Cache result
        self.status_cache[cache_key] = health_status
        
        return health_status

class LoadBalancer:
    """Simple round-robin load balancer for agent instances"""
    
    def __init__(self, endpoints: List[str]):
        self.endpoints = endpoints
        self.current_index = 0
        self.healthy_endpoints = set(endpoints)
        
    async def get_endpoint(self) -> Optional[str]:
        """Get next healthy endpoint"""
        if not self.healthy_endpoints:
            return None
            
        healthy_list = list(self.healthy_endpoints)
        endpoint = healthy_list[self.current_index % len(healthy_list)]
        self.current_index += 1
        
        return endpoint
        
    async def mark_unhealthy(self, endpoint: str):
        """Mark endpoint as unhealthy"""
        self.healthy_endpoints.discard(endpoint)
        logger.warning("Endpoint marked unhealthy", endpoint=endpoint)
        
    async def mark_healthy(self, endpoint: str):
        """Mark endpoint as healthy"""
        if endpoint in self.endpoints:
            self.healthy_endpoints.add(endpoint)
            logger.info("Endpoint marked healthy", endpoint=endpoint)

class ProductionLLMAgent:
    """Production-ready LLM agent with comprehensive error handling"""
    
    def __init__(self, api_key: str, model: str, instance_id: str = "default"):
        self.api_key = api_key
        self.model = model
        self.instance_id = instance_id
        self.base_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.session: Optional[ClientSession] = None
        self.is_healthy = True
        self.last_error = None
        
        # Circuit breaker pattern
        self.failure_count = 0
        self.failure_threshold = 5
        self.reset_timeout = 60
        self.last_failure_time = None
        
    async def initialize(self):
        """Initialize the agent with proper session management"""
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=10,  # Per-host limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout
            connect=5   # Connection timeout
        )
        
        self.session = ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": f"research-system/{self.instance_id}"
            }
        )
        
        logger.info("Agent initialized", instance_id=self.instance_id, model=self.model)
        
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            
    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        # Check circuit breaker state
        if self._is_circuit_open():
            return False
            
        try:
            # Simple health check request
            if not self.session:
                await self.initialize()
                
            async with self.session.post(
                self.base_url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "health check"}],
                    "max_tokens": 10
                }
            ) as response:
                self.is_healthy = response.status == 200
                if self.is_healthy:
                    self._record_success()
                else:
                    self._record_failure()
                    
                return self.is_healthy
                
        except Exception as e:
            self.is_healthy = False
            self.last_error = str(e)
            self._record_failure()
            logger.error("Health check failed", instance_id=self.instance_id, error=str(e))
            return False
            
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.failure_count < self.failure_threshold:
            return False
            
        if self.last_failure_time is None:
            return False
            
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure < self.reset_timeout
        
    def _record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.last_failure_time = None
        
    def _record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
    async def generate_response(self, prompt: str, operation: str = "generation") -> Dict[str, Any]:
        """Generate response with production-ready error handling"""
        if self._is_circuit_open():
            AGENT_EXECUTIONS.labels(agent_type=self.model, status="circuit_open").inc()
            return {
                "error": "Circuit breaker open",
                "success": False,
                "circuit_open": True
            }
            
        start_time = time.time()
        
        try:
            if not self.session:
                await self.initialize()
                
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            async with self.session.post(self.base_url, json=payload) as response:
                duration = time.time() - start_time
                REQUEST_DURATION.observe(duration)
                
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    self._record_success()
                    AGENT_EXECUTIONS.labels(agent_type=self.model, status="success").inc()
                    
                    return {
                        "content": content,
                        "tokens_used": data["usage"]["total_tokens"],
                        "duration": duration,
                        "success": True,
                        "instance_id": self.instance_id
                    }
                else:
                    error_text = await response.text()
                    self._record_failure()
                    AGENT_EXECUTIONS.labels(agent_type=self.model, status="error").inc()
                    
                    return {
                        "error": error_text,
                        "status_code": response.status,
                        "duration": duration,
                        "success": False,
                        "instance_id": self.instance_id
                    }
                    
        except Exception as e:
            duration = time.time() - start_time
            self._record_failure()
            AGENT_EXECUTIONS.labels(agent_type=self.model, status="exception").inc()
            
            logger.error("Agent execution failed", 
                        instance_id=self.instance_id,
                        error=str(e),
                        operation=operation)
            
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "success": False,
                "instance_id": self.instance_id
            }

class ProductionResearchSystem:
    """Production-ready research system with scaling capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agents: Dict[str, List[ProductionLLMAgent]] = {}
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.health_checker = HealthChecker()
        self.app = web.Application()
        self.setup_routes()
        self.setup_health_checks()
        
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/health', self.health_endpoint)
        self.app.router.add_get('/metrics', self.metrics_endpoint)
        self.app.router.add_post('/research', self.research_endpoint)
        self.app.router.add_get('/status', self.status_endpoint)
        
        # Add middleware
        self.app.middlewares.append(self.logging_middleware)
        self.app.middlewares.append(self.metrics_middleware)
        
    def setup_health_checks(self):
        """Setup health check functions"""
        self.health_checker.register_check("agents", self.check_agents_health)
        self.health_checker.register_check("memory", self.check_memory_usage)
        self.health_checker.register_check("disk", self.check_disk_usage)
        
    async def initialize_agents(self):
        """Initialize agent instances for scaling"""
        agent_configs = self.config.get("agents", {})
        
        for agent_type, config in agent_configs.items():
            instances = []
            instance_count = config.get("instances", 1)
            
            for i in range(instance_count):
                agent = ProductionLLMAgent(
                    api_key=self.config["api_key"],
                    model=config["model"],
                    instance_id=f"{agent_type}-{i}"
                )
                await agent.initialize()
                instances.append(agent)
                
            self.agents[agent_type] = instances
            
            # Create load balancer
            endpoints = [f"{agent_type}-{i}" for i in range(instance_count)]
            self.load_balancers[agent_type] = LoadBalancer(endpoints)
            
        logger.info("Agents initialized", 
                   agent_types=list(self.agents.keys()),
                   total_instances=sum(len(instances) for instances in self.agents.values()))
                   
    async def get_agent(self, agent_type: str) -> Optional[ProductionLLMAgent]:
        """Get healthy agent instance using load balancer"""
        if agent_type not in self.load_balancers:
            return None
            
        endpoint = await self.load_balancers[agent_type].get_endpoint()
        if not endpoint:
            return None
            
        # Find agent by instance_id
        for agent in self.agents[agent_type]:
            if agent.instance_id == endpoint:
                if agent.is_healthy:
                    return agent
                else:
                    await self.load_balancers[agent_type].mark_unhealthy(endpoint)
                    
        return None
        
    async def check_agents_health(self) -> bool:
        """Check health of all agents"""
        healthy_count = 0
        total_count = 0
        
        for agent_type, agents in self.agents.items():
            for agent in agents:
                total_count += 1
                if await agent.health_check():
                    healthy_count += 1
                    await self.load_balancers[agent_type].mark_healthy(agent.instance_id)
                else:
                    await self.load_balancers[agent_type].mark_unhealthy(agent.instance_id)
                    
        return healthy_count >= total_count * 0.5  # At least 50% healthy
        
    async def check_memory_usage(self) -> bool:
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 90
        except ImportError:
            return True  # Skip check if psutil not available
            
    async def check_disk_usage(self) -> bool:
        """Check disk usage"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) < 0.90
        except ImportError:
            return True  # Skip check if psutil not available
            
    @web.middleware
    async def logging_middleware(self, request, handler):
        """Logging middleware"""
        start_time = time.time()
        
        try:
            response = await handler(request)
            duration = time.time() - start_time
            
            logger.info("Request processed",
                       method=request.method,
                       path=request.path,
                       status=response.status,
                       duration=f"{duration:.3f}s",
                       remote=request.remote)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error("Request failed",
                        method=request.method,
                        path=request.path,
                        error=str(e),
                        duration=f"{duration:.3f}s",
                        remote=request.remote)
            raise
            
    @web.middleware 
    async def metrics_middleware(self, request, handler):
        """Metrics collection middleware"""
        ACTIVE_CONNECTIONS.inc()
        
        try:
            response = await handler(request)
            REQUEST_COUNT.labels(
                endpoint=request.path,
                method=request.method,
                status=response.status
            ).inc()
            return response
            
        except Exception as e:
            REQUEST_COUNT.labels(
                endpoint=request.path,
                method=request.method,
                status="error"
            ).inc()
            raise
            
        finally:
            ACTIVE_CONNECTIONS.dec()
            
    async def health_endpoint(self, request):
        """Health check endpoint"""
        health_status = await self.health_checker.get_health_status()
        
        status_code = 200
        if health_status.status == "degraded":
            status_code = 200  # Still serving traffic
        elif health_status.status == "unhealthy":
            status_code = 503  # Service unavailable
            
        return web.json_response({
            "status": health_status.status,
            "service": health_status.service,
            "checks": health_status.checks,
            "details": health_status.details,
            "timestamp": health_status.timestamp.isoformat()
        }, status=status_code)
        
    async def metrics_endpoint(self, request):
        """Metrics endpoint for Prometheus"""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        
        return web.Response(
            body=generate_latest(),
            content_type=CONTENT_TYPE_LATEST
        )
        
    async def research_endpoint(self, request):
        """Research endpoint"""
        try:
            data = await request.json()
            query = data.get("query", "")
            
            if not query:
                return web.json_response(
                    {"error": "Query is required"},
                    status=400
                )
                
            # Get planner agent
            planner = await self.get_agent("planner")
            if not planner:
                return web.json_response(
                    {"error": "No healthy planner agents available"},
                    status=503
                )
                
            # Execute research (simplified)
            result = await planner.generate_response(
                f"Create a research plan for: {query}",
                "planning"
            )
            
            return web.json_response({
                "query": query,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error("Research endpoint error", error=str(e))
            return web.json_response(
                {"error": "Internal server error"},
                status=500
            )
            
    async def status_endpoint(self, request):
        """System status endpoint"""
        agent_status = {}
        for agent_type, agents in self.agents.items():
            healthy_instances = sum(1 for agent in agents if agent.is_healthy)
            agent_status[agent_type] = {
                "total_instances": len(agents),
                "healthy_instances": healthy_instances,
                "health_percentage": (healthy_instances / len(agents)) * 100 if agents else 0
            }
            
        return web.json_response({
            "service": "research-system",
            "version": "1.0.0",
            "agents": agent_status,
            "timestamp": datetime.now().isoformat()
        })
        
    async def cleanup(self):
        """Cleanup resources"""
        for agents in self.agents.values():
            for agent in agents:
                await agent.cleanup()

def create_docker_compose():
    """Create docker-compose.yml for production deployment"""
    compose_config = {
        "version": "3.8",
        "services": {
            "research-system": {
                "build": ".",
                "ports": ["8080:8080", "9090:9090"],
                "environment": [
                    "FIREWORKS_API_KEY=${FIREWORKS_API_KEY}",
                    "LOG_LEVEL=INFO",
                    "WORKERS=4"
                ],
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                    "start_period": "40s"
                },
                "deploy": {
                    "replicas": 2,
                    "resources": {
                        "limits": {"cpus": "2.0", "memory": "2G"},
                        "reservations": {"cpus": "0.5", "memory": "512M"}
                    }
                }
            },
            "nginx": {
                "image": "nginx:alpine",
                "ports": ["80:80"],
                "volumes": ["./nginx.conf:/etc/nginx/nginx.conf"],
                "depends_on": ["research-system"]
            },
            "prometheus": {
                "image": "prom/prometheus",
                "ports": ["9091:9090"],
                "volumes": ["./prometheus.yml:/etc/prometheus/prometheus.yml"]
            }
        }
    }
    
    with open("docker-compose.yml", "w") as f:
        import yaml
        yaml.dump(compose_config, f, default_flow_style=False)
        
    print("✅ docker-compose.yml created")

def create_dockerfile():
    """Create Dockerfile for containerization"""
    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "module7_production_deployment.py"]
"""
    
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)
        
    print("✅ Dockerfile created")

async def main():
    """Production deployment demo"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("FIREWORKS_API_KEY")
    
    if not api_key:
        print("❌ FIREWORKS_API_KEY not found in environment")
        return
        
    print("🚀 Production Deployment & Scaling Demo")
    print("=" * 50)
    print("Setting up production-ready research system...")
    print()
    
    # Configuration for production deployment
    config = {
        "api_key": api_key,
        "agents": {
            "planner": {
                "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "instances": 2  # 2 planner instances
            },
            "retriever": {
                "model": "accounts/fireworks/models/llama-v3p1-8b-instruct", 
                "instances": 3  # 3 retriever instances
            }
        }
    }
    
    # Create production system
    system = ProductionResearchSystem(config)
    
    try:
        # Initialize agents
        await system.initialize_agents()
        
        # Start metrics server
        start_http_server(9090)
        print("📊 Metrics server started on port 9090")
        
        # Test health checks
        print("🔍 Running health checks...")
        health_status = await system.health_checker.get_health_status()
        print(f"System Status: {health_status.status}")
        print(f"Health Checks: {health_status.checks}")
        print()
        
        # Test load balancing
        print("⚖️ Testing load balancing...")
        for i in range(5):
            planner = await system.get_agent("planner")
            if planner:
                result = await planner.generate_response(
                    f"Test query {i+1}",
                    "test"
                )
                print(f"Request {i+1}: Handled by {result.get('instance_id', 'unknown')}")
            else:
                print(f"Request {i+1}: No healthy agents available")
        print()
        
        # Create deployment files
        print("📦 Creating deployment configuration...")
        create_dockerfile()
        create_docker_compose()
        
        # Create nginx configuration
        nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream research_backend {
        server research-system:8080;
    }
    
    server {
        listen 80;
        
        location /health {
            proxy_pass http://research_backend;
            access_log off;
        }
        
        location / {
            proxy_pass http://research_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
"""
        
        with open("nginx.conf", "w") as f:
            f.write(nginx_config)
        print("✅ nginx.conf created")
        
        # Create prometheus configuration
        prometheus_config = """
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'research-system'
    static_configs:
      - targets: ['research-system:9090']
"""
        
        with open("prometheus.yml", "w") as f:
            f.write(prometheus_config)
        print("✅ prometheus.yml created")
        
        print("\n🎉 Production Deployment Demo Complete!")
        print("Key Features Demonstrated:")
        print("• Docker containerization with health checks")
        print("• Load balancing with circuit breakers")
        print("• Comprehensive health monitoring")
        print("• Prometheus metrics integration")
        print("• Production-ready HTTP API")
        print("• Auto-scaling configuration")
        print("• Nginx reverse proxy setup")
        
        print("\n📋 Deployment Commands:")
        print("docker-compose up --build -d    # Start all services")
        print("docker-compose scale research-system=4  # Scale to 4 instances")
        print("curl http://localhost:80/health  # Check health")
        print("curl http://localhost:9091       # View metrics")
        
    finally:
        await system.cleanup()

if __name__ == "__main__":
    # Use uvloop for better performance
    if sys.platform != "win32":
        uvloop.install()
        
    asyncio.run(main()) 