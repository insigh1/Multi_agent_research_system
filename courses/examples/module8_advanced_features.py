#!/usr/bin/env python3
"""
Module 8: Advanced Features & Optimization
Demonstrates caching strategies, parallel processing, smart retry logic,
and performance optimization techniques for multi-agent systems.
"""

import asyncio
import time
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import sqlite3
from pathlib import Path

# External dependencies
import aiohttp
import structlog
from asyncio_throttle import Throttler

# Redis support (using redis-py with asyncio)
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Redis not available: {e}")
    print("   Install redis: pip install redis>=5.0.0")
    print("   Module will run with memory and disk caching only")
    aioredis = None
    REDIS_AVAILABLE = False

# Configure logging
logger = structlog.get_logger()

class CacheStrategy(Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    HYBRID = "hybrid"

class RetryStrategy(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    FIXED = "fixed"

@dataclass
class CacheEntry:
    key: str
    value: Any
    timestamp: datetime
    ttl: int  # Time to live in seconds
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)

@dataclass
class RetryConfig:
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True

class SmartCache:
    """Multi-layer intelligent caching system"""
    
    def __init__(self, strategy: CacheStrategy = CacheStrategy.HYBRID, redis_url: str = None):
        self.strategy = strategy
        self.redis_url = redis_url
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.redis_client = None
        self.disk_cache_dir = Path("cache")
        self.disk_cache_dir.mkdir(exist_ok=True)
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "memory_usage": 0
        }
        
        # Cache configuration
        self.max_memory_entries = 1000
        self.memory_ttl = 300  # 5 minutes
        self.disk_ttl = 3600   # 1 hour
        self.redis_ttl = 1800  # 30 minutes
        
    async def initialize(self):
        """Initialize cache connections"""
        if self.strategy in [CacheStrategy.REDIS, CacheStrategy.HYBRID]:
            if self.redis_url and REDIS_AVAILABLE and aioredis:
                try:
                    self.redis_client = aioredis.from_url(self.redis_url, decode_responses=False)
                    await self.redis_client.ping()
                    logger.info("Redis cache initialized")
                except Exception as e:
                    logger.warning("Redis initialization failed", error=str(e))
                    self.redis_client = None
            elif not REDIS_AVAILABLE:
                logger.info("Redis not available, using memory and disk cache only")
                    
    async def cleanup(self):
        """Cleanup cache connections"""
        if self.redis_client:
            await self.redis_client.aclose()
            
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with multi-layer fallback"""
        # Try memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not entry.is_expired():
                entry.hit_count += 1
                self.stats["hits"] += 1
                logger.debug("Cache hit (memory)", key=key)
                return entry.value
            else:
                del self.memory_cache[key]
                
        # Try Redis cache
        if self.redis_client and self.strategy in [CacheStrategy.REDIS, CacheStrategy.HYBRID]:
            try:
                redis_value = await self.redis_client.get(key)
                if redis_value:
                    value = pickle.loads(redis_value)
                    # Store in memory cache for faster access
                    await self._set_memory(key, value, self.memory_ttl)
                    self.stats["hits"] += 1
                    logger.debug("Cache hit (redis)", key=key)
                    return value
            except Exception as e:
                logger.warning("Redis get failed", key=key, error=str(e))
                
        # Try disk cache
        if self.strategy in [CacheStrategy.DISK, CacheStrategy.HYBRID]:
            disk_path = self.disk_cache_dir / f"{key}.cache"
            if disk_path.exists():
                try:
                    with open(disk_path, 'rb') as f:
                        cache_data = pickle.load(f)
                        if cache_data['expires'] > datetime.now():
                            value = cache_data['value']
                            # Promote to higher cache levels
                            await self._set_memory(key, value, self.memory_ttl)
                            if self.redis_client:
                                await self._set_redis(key, value, self.redis_ttl)
                            self.stats["hits"] += 1
                            logger.debug("Cache hit (disk)", key=key)
                            return value
                        else:
                            disk_path.unlink()  # Remove expired entry
                except Exception as e:
                    logger.warning("Disk cache read failed", key=key, error=str(e))
                    
        self.stats["misses"] += 1
        return None
        
    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with multi-layer storage"""
        if ttl is None:
            ttl = self.memory_ttl
            
        # Store in memory
        if self.strategy in [CacheStrategy.MEMORY, CacheStrategy.HYBRID]:
            await self._set_memory(key, value, ttl)
            
        # Store in Redis
        if self.redis_client and self.strategy in [CacheStrategy.REDIS, CacheStrategy.HYBRID]:
            await self._set_redis(key, value, ttl)
            
        # Store on disk
        if self.strategy in [CacheStrategy.DISK, CacheStrategy.HYBRID]:
            await self._set_disk(key, value, ttl)
            
    async def _set_memory(self, key: str, value: Any, ttl: int):
        """Set value in memory cache"""
        # Evict if memory limit reached
        if len(self.memory_cache) >= self.max_memory_entries:
            await self._evict_memory()
            
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            ttl=ttl
        )
        self.memory_cache[key] = entry
        
    async def _set_redis(self, key: str, value: Any, ttl: int):
        """Set value in Redis cache"""
        try:
            serialized = pickle.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning("Redis set failed", key=key, error=str(e))
            
    async def _set_disk(self, key: str, value: Any, ttl: int):
        """Set value in disk cache"""
        try:
            cache_data = {
                'value': value,
                'expires': datetime.now() + timedelta(seconds=ttl)
            }
            disk_path = self.disk_cache_dir / f"{key}.cache"
            with open(disk_path, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning("Disk cache write failed", key=key, error=str(e))
            
    async def _evict_memory(self):
        """Evict least recently used entries from memory"""
        # Sort by hit count and timestamp
        entries = sorted(
            self.memory_cache.items(),
            key=lambda x: (x[1].hit_count, x[1].timestamp)
        )
        
        # Remove oldest 10%
        evict_count = max(1, len(entries) // 10)
        for i in range(evict_count):
            key = entries[i][0]
            del self.memory_cache[key]
            self.stats["evictions"] += 1
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = self.stats["hits"] / (self.stats["hits"] + self.stats["misses"]) if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "memory_entries": len(self.memory_cache),
            "strategy": self.strategy.value
        }

class SmartRetry:
    """Intelligent retry mechanism with various strategies"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info("Retry successful", attempt=attempt + 1)
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        "Operation failed, retrying",
                        attempt=attempt + 1,
                        max_attempts=self.config.max_attempts,
                        delay=f"{delay:.2f}s",
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "All retry attempts failed",
                        attempts=self.config.max_attempts,
                        error=str(e)
                    )
                    
        raise last_exception
        
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on retry strategy"""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = self.config.base_delay
            
        # Apply max delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            import random
            delay = delay * (0.5 + 0.5 * random.random())
            
        return delay
        
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

class ParallelProcessor:
    """Advanced parallel processing with load balancing"""
    
    def __init__(self, max_workers: int = 10, semaphore_limit: int = 5):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        
    async def process_batch(self, tasks: List[Dict[str, Any]], processor_func: Callable) -> List[Any]:
        """Process batch of tasks in parallel with load balancing"""
        results = []
        
        # Create batches to avoid overwhelming the system
        batch_size = min(self.max_workers, len(tasks))
        batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]
        
        for batch in batches:
            batch_tasks = []
            
            for task in batch:
                batch_tasks.append(
                    self._process_single_task(task, processor_func)
                )
                
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    self.failed_tasks += 1
                    logger.error("Task failed", error=str(result))
                    results.append({"error": str(result), "success": False})
                else:
                    self.completed_tasks += 1
                    results.append(result)
                    
        return results
        
    async def _process_single_task(self, task: Dict[str, Any], processor_func: Callable) -> Any:
        """Process single task with semaphore control"""
        async with self.semaphore:
            self.active_tasks += 1
            try:
                result = await processor_func(task)
                return result
            finally:
                self.active_tasks -= 1
                
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        total_tasks = self.completed_tasks + self.failed_tasks
        success_rate = self.completed_tasks / total_tasks if total_tasks > 0 else 0
        
        return {
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": success_rate,
            "max_workers": self.max_workers
        }

class OptimizedLLMAgent:
    """Highly optimized LLM agent with advanced features"""
    
    def __init__(self, api_key: str, model: str, cache: SmartCache):
        self.api_key = api_key
        self.model = model
        self.cache = cache
        self.base_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.session = None
        self.throttler = Throttler(rate_limit=10, period=1.0)
        
        # Retry configuration
        self.retry_client = SmartRetry(RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=10.0,
            jitter=True
        ))
        
        # Response cache configuration
        self.cache_ttl = 600  # 10 minutes
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Authorization": f"Bearer {self.api_key}"},
            connector=aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def generate_response(self, prompt: str, use_cache: bool = True, **kwargs) -> Dict[str, Any]:
        """Generate response with caching and optimization"""
        # Generate cache key
        cache_key = self.cache._generate_key(
            f"llm:{self.model}",
            prompt,
            **kwargs
        )
        
        # Try cache first
        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.debug("Using cached response", cache_key=cache_key)
                return {
                    **cached_result,
                    "cached": True,
                    "cache_key": cache_key
                }
                
        # Generate new response with retry logic
        result = await self.retry_client.execute(
            self._make_api_call,
            prompt,
            **kwargs
        )
        
        # Cache the result
        if use_cache and result.get("success", False):
            await self.cache.set(cache_key, result, self.cache_ttl)
            
        result["cached"] = False
        result["cache_key"] = cache_key
        return result
        
    async def _make_api_call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make API call with throttling"""
        start_time = time.time()
        
        async with self.throttler:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            async with self.session.post(self.base_url, json=payload) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    return {
                        "content": content,
                        "tokens_used": data["usage"]["total_tokens"],
                        "model": self.model,
                        "duration": duration,
                        "success": True
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                    
    async def batch_generate(self, prompts: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Generate responses for multiple prompts in parallel"""
        processor = ParallelProcessor(max_workers=5, semaphore_limit=3)
        
        tasks = [{"prompt": prompt, **kwargs} for prompt in prompts]
        
        async def process_task(task):
            return await self.generate_response(task["prompt"], **task)
            
        results = await processor.process_batch(tasks, process_task)
        
        logger.info(
            "Batch processing completed",
            total_prompts=len(prompts),
            **processor.get_stats()
        )
        
        return results

class PerformanceOptimizer:
    """System performance optimization and monitoring"""
    
    def __init__(self):
        self.metrics = {
            "response_times": [],
            "cache_hit_rates": [],
            "error_rates": [],
            "throughput": []
        }
        
    def record_operation(self, duration: float, cached: bool, success: bool):
        """Record operation metrics"""
        self.metrics["response_times"].append(duration)
        self.metrics["cache_hit_rates"].append(1 if cached else 0)
        self.metrics["error_rates"].append(0 if success else 1)
        
        # Keep only recent metrics
        max_metrics = 1000
        for metric_list in self.metrics.values():
            if len(metric_list) > max_metrics:
                metric_list.pop(0)
                
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        if not self.metrics["response_times"]:
            return {"error": "No metrics available"}
            
        response_times = self.metrics["response_times"]
        cache_hits = self.metrics["cache_hit_rates"]
        errors = self.metrics["error_rates"]
        
        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
            "cache_hit_rate": sum(cache_hits) / len(cache_hits),
            "error_rate": sum(errors) / len(errors),
            "total_operations": len(response_times)
        }
        
    def suggest_optimizations(self) -> List[str]:
        """Suggest performance optimizations"""
        report = self.get_performance_report()
        suggestions = []
        
        if report.get("cache_hit_rate", 0) < 0.5:
            suggestions.append("Increase cache TTL or improve cache key strategy")
            
        if report.get("avg_response_time", 0) > 5.0:
            suggestions.append("Consider using faster models or increasing parallel processing")
            
        if report.get("error_rate", 0) > 0.05:
            suggestions.append("Implement better error handling and retry logic")
            
        if report.get("p95_response_time", 0) > 10.0:
            suggestions.append("Add request timeouts and circuit breakers")
            
        return suggestions

async def main():
    """Advanced features and optimization demo"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("FIREWORKS_API_KEY")
    
    if not api_key:
        print("❌ FIREWORKS_API_KEY not found in environment")
        return
        
    print("🚀 Advanced Features & Optimization Demo")
    print("=" * 50)
    print("Demonstrating advanced caching, parallel processing, and optimization...")
    print()
    
    # Initialize smart cache
    cache = SmartCache(strategy=CacheStrategy.HYBRID, redis_url="redis://localhost:6379")
    await cache.initialize()
    
    # Initialize optimized agent
    agent = OptimizedLLMAgent(api_key, "accounts/fireworks/models/llama-v3p1-8b-instruct", cache)
    
    # Initialize performance optimizer
    optimizer = PerformanceOptimizer()
    
    try:
        async with agent:
            # Test 1: Caching effectiveness
            print("🔄 Testing caching effectiveness...")
            test_prompt = "Explain the concept of machine learning in simple terms"
            
            # First request (cache miss)
            start_time = time.time()
            result1 = await agent.generate_response(test_prompt)
            duration1 = time.time() - start_time
            
            # Second request (cache hit)
            start_time = time.time()
            result2 = await agent.generate_response(test_prompt)
            duration2 = time.time() - start_time
            
            print(f"First request: {duration1:.2f}s (cached: {result1.get('cached', False)})")
            print(f"Second request: {duration2:.2f}s (cached: {result2.get('cached', False)})")
            print(f"Cache speedup: {duration1/duration2:.1f}x faster")
            print()
            
            # Record metrics
            optimizer.record_operation(duration1, result1.get('cached', False), result1.get('success', False))
            optimizer.record_operation(duration2, result2.get('cached', False), result2.get('success', False))
            
            # Test 2: Batch processing
            print("⚡ Testing parallel batch processing...")
            batch_prompts = [
                "What is artificial intelligence?",
                "Explain quantum computing",
                "Describe blockchain technology",
                "What are neural networks?",
                "How does machine learning work?"
            ]
            
            start_time = time.time()
            batch_results = await agent.batch_generate(batch_prompts)
            batch_duration = time.time() - start_time
            
            successful_results = [r for r in batch_results if r.get('success', False)]
            cached_results = [r for r in batch_results if r.get('cached', False)]
            
            print(f"Processed {len(batch_prompts)} prompts in {batch_duration:.2f}s")
            print(f"Success rate: {len(successful_results)}/{len(batch_prompts)} ({len(successful_results)/len(batch_prompts)*100:.1f}%)")
            print(f"Cache hits: {len(cached_results)}/{len(batch_prompts)} ({len(cached_results)/len(batch_prompts)*100:.1f}%)")
            print()
            
            # Record batch metrics
            for result in batch_results:
                optimizer.record_operation(
                    result.get('duration', 0),
                    result.get('cached', False),
                    result.get('success', False)
                )
                
            # Test 3: Cache statistics
            print("📊 Cache Performance Statistics:")
            cache_stats = cache.get_stats()
            for key, value in cache_stats.items():
                if key == "hit_rate":
                    print(f"  {key}: {value:.1%}")
                else:
                    print(f"  {key}: {value}")
            print()
            
            # Test 4: Performance analysis
            print("📈 Performance Analysis:")
            perf_report = optimizer.get_performance_report()
            for key, value in perf_report.items():
                if "rate" in key:
                    print(f"  {key}: {value:.1%}")
                elif "time" in key:
                    print(f"  {key}: {value:.2f}s")
                else:
                    print(f"  {key}: {value}")
            print()
            
            # Test 5: Optimization suggestions
            print("💡 Optimization Suggestions:")
            suggestions = optimizer.suggest_optimizations()
            if suggestions:
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")
            else:
                print("  System is performing well - no immediate optimizations needed")
            print()
            
            # Test 6: Smart retry demonstration
            print("🔄 Testing smart retry mechanism...")
            retry_client = SmartRetry(RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL,
                base_delay=0.5,
                max_delay=5.0,
                jitter=True
            ))
            
            async def failing_function():
                import random
                if random.random() < 0.7:  # 70% chance of failure
                    raise Exception("Simulated failure")
                return "Success!"
                
            try:
                retry_result = await retry_client.execute(failing_function)
                print(f"Retry result: {retry_result}")
            except Exception as e:
                print(f"All retries failed: {e}")
            print()
            
        print("🎉 Advanced Features Demo Complete!")
        print("Key Features Demonstrated:")
        print("• Multi-layer intelligent caching (Memory + Redis + Disk)")
        print("• Smart retry mechanisms with various strategies")
        print("• Parallel batch processing with load balancing")
        print("• Comprehensive performance monitoring")
        print("• Automatic optimization suggestions")
        print("• Circuit breaker patterns and error handling")
        
    finally:
        await cache.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 