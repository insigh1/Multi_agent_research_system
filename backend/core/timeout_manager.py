"""
Unified timeout and retry management system for the research system.
Consolidates all timeout/retry patterns found throughout the codebase.
"""

import structlog
import time
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Union, Callable, List
from dataclasses import dataclass
from enum import Enum
import functools
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pybreaker

logger = structlog.get_logger(__name__)


class TimeoutCategory(Enum):
    """Categories of operations with different timeout requirements"""
    API_CALL = "api_call"           # LLM API calls
    WEB_SEARCH = "web_search"       # Search engine APIs  
    WEB_SCRAPE = "web_scrape"       # Content scraping
    DATABASE = "database"           # Database operations
    FILE_IO = "file_io"            # File operations


class RetryStrategy(Enum):
    """Different retry strategies for various scenarios"""
    EXPONENTIAL = "exponential"     # Exponential backoff
    FIXED = "fixed"                # Fixed delay
    NONE = "none"                  # No retries
    CIRCUIT_BREAKER = "circuit_breaker"  # Circuit breaker pattern


@dataclass
class TimeoutConfig:
    """Configuration for timeouts and retries"""
    total_timeout: float           # Total timeout in seconds
    connection_timeout: float      # Connection timeout
    read_timeout: float           # Read timeout
    retry_attempts: int           # Number of retry attempts
    retry_strategy: RetryStrategy # Retry strategy
    backoff_multiplier: float     # Backoff multiplier for exponential strategy
    backoff_min: float           # Minimum backoff time
    backoff_max: float           # Maximum backoff time
    circuit_breaker_threshold: int = 5  # Circuit breaker failure threshold
    circuit_breaker_reset: int = 60     # Circuit breaker reset time


class UnifiedTimeoutManager:
    """Unified timeout and retry management system"""
    
    def __init__(self, settings=None):
        self.settings = settings
        self.logger = structlog.get_logger(__name__)
        
        # Default timeout configurations for different operation types
        self.default_configs = {
            TimeoutCategory.API_CALL: TimeoutConfig(
                total_timeout=60.0,
                connection_timeout=15.0,
                read_timeout=45.0,
                retry_attempts=3,
                retry_strategy=RetryStrategy.EXPONENTIAL,
                backoff_multiplier=1.0,
                backoff_min=4.0,
                backoff_max=10.0,
                circuit_breaker_threshold=5,
                circuit_breaker_reset=60
            ),
            TimeoutCategory.WEB_SEARCH: TimeoutConfig(
                total_timeout=30.0,
                connection_timeout=10.0,
                read_timeout=20.0,
                retry_attempts=2,
                retry_strategy=RetryStrategy.EXPONENTIAL,
                backoff_multiplier=1.0,
                backoff_min=2.0,
                backoff_max=5.0,
                circuit_breaker_threshold=3,
                circuit_breaker_reset=30
            ),
            TimeoutCategory.WEB_SCRAPE: TimeoutConfig(
                total_timeout=120.0,
                connection_timeout=10.0,
                read_timeout=100.0,
                retry_attempts=1,
                retry_strategy=RetryStrategy.FIXED,
                backoff_multiplier=1.0,
                backoff_min=2.0,
                backoff_max=2.0,
                circuit_breaker_threshold=5,
                circuit_breaker_reset=30
            ),
            TimeoutCategory.DATABASE: TimeoutConfig(
                total_timeout=10.0,
                connection_timeout=5.0,
                read_timeout=8.0,
                retry_attempts=2,
                retry_strategy=RetryStrategy.EXPONENTIAL,
                backoff_multiplier=0.5,
                backoff_min=1.0,
                backoff_max=3.0,
                circuit_breaker_threshold=3,
                circuit_breaker_reset=20
            ),
            TimeoutCategory.FILE_IO: TimeoutConfig(
                total_timeout=5.0,
                connection_timeout=2.0,
                read_timeout=3.0,
                retry_attempts=1,
                retry_strategy=RetryStrategy.FIXED,
                backoff_multiplier=1.0,
                backoff_min=1.0,
                backoff_max=1.0,
                circuit_breaker_threshold=2,
                circuit_breaker_reset=10
            )
        }
        
        # Initialize circuit breakers
        self.circuit_breakers = {}
        self._init_circuit_breakers()
        
        # Apply settings overrides if provided
        if settings:
            self._apply_settings_overrides()
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for each category"""
        for category, config in self.default_configs.items():
            self.circuit_breakers[category] = pybreaker.CircuitBreaker(
                fail_max=config.circuit_breaker_threshold,
                reset_timeout=config.circuit_breaker_reset,
                name=f"{category.value}_breaker"
            )
    
    def _apply_settings_overrides(self):
        """Apply settings overrides to default configurations"""
        if hasattr(self.settings, 'api_timeout'):
            self.default_configs[TimeoutCategory.API_CALL].total_timeout = self.settings.api_timeout
        
        if hasattr(self.settings, 'firecrawl_timeout'):
            self.default_configs[TimeoutCategory.WEB_SEARCH].total_timeout = self.settings.firecrawl_timeout
            self.default_configs[TimeoutCategory.WEB_SCRAPE].total_timeout = self.settings.firecrawl_timeout
            self.default_configs[TimeoutCategory.WEB_SCRAPE].read_timeout = max(self.settings.firecrawl_timeout - 20.0, 60.0)
        
        if hasattr(self.settings, 'firecrawl_scrape_timeout'):
            self.default_configs[TimeoutCategory.WEB_SCRAPE].total_timeout = self.settings.firecrawl_scrape_timeout
    
    def get_config(self, category: TimeoutCategory, custom_overrides: Optional[Dict[str, Any]] = None) -> TimeoutConfig:
        """Get timeout configuration for a specific category"""
        config = self.default_configs[category]
        
        if custom_overrides:
            # Apply custom overrides
            for key, value in custom_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        return config
    
    def get_aiohttp_timeout(self, category: TimeoutCategory, custom_overrides: Optional[Dict[str, Any]] = None) -> aiohttp.ClientTimeout:
        """Get aiohttp ClientTimeout for a specific category"""
        config = self.get_config(category, custom_overrides)
        
        return aiohttp.ClientTimeout(
            total=config.total_timeout,
            connect=config.connection_timeout,
            sock_read=config.read_timeout
        )
    
    def with_retries(self, category: TimeoutCategory, custom_overrides: Optional[Dict[str, Any]] = None):
        """Decorator to add retries to a function"""
        config = self.get_config(category, custom_overrides)
        
        def decorator(func):
            if config.retry_strategy == RetryStrategy.EXPONENTIAL:
                return retry(
                    stop=stop_after_attempt(config.retry_attempts),
                    wait=wait_exponential(
                        multiplier=config.backoff_multiplier,
                        min=config.backoff_min,
                        max=config.backoff_max
                    ),
                    retry=retry_if_exception_type((
                        aiohttp.ClientError, 
                        asyncio.TimeoutError,
                        ConnectionError,
                        OSError
                    ))
                )(func)
            
            elif config.retry_strategy == RetryStrategy.FIXED:
                return retry(
                    stop=stop_after_attempt(config.retry_attempts),
                    wait=wait_exponential(multiplier=0, min=config.backoff_min, max=config.backoff_min),
                    retry=retry_if_exception_type((
                        aiohttp.ClientError, 
                        asyncio.TimeoutError,
                        ConnectionError,
                        OSError
                    ))
                )(func)
            
            elif config.retry_strategy == RetryStrategy.NONE:
                return func
            
            elif config.retry_strategy == RetryStrategy.CIRCUIT_BREAKER:
                return self.circuit_breakers[category](func)
            
            return func
        
        return decorator
    
    def with_circuit_breaker(self, category: TimeoutCategory):
        """Decorator to add circuit breaker to a function"""
        return self.circuit_breakers[category]
    
    def with_timeout_and_retries(self, category: TimeoutCategory, custom_overrides: Optional[Dict[str, Any]] = None):
        """Combined decorator for timeout and retries"""
        def decorator(func):
            # Apply retries first, then circuit breaker
            func_with_retries = self.with_retries(category, custom_overrides)(func)
            func_with_circuit_breaker = self.with_circuit_breaker(category)(func_with_retries)
            return func_with_circuit_breaker
        
        return decorator
    
    async def execute_with_timeout(self, 
                                 category: TimeoutCategory, 
                                 operation: Callable,
                                 *args,
                                 custom_overrides: Optional[Dict[str, Any]] = None,
                                 **kwargs) -> Any:
        """Execute an operation with unified timeout and retry handling"""
        config = self.get_config(category, custom_overrides)
        
        @self.with_timeout_and_retries(category, custom_overrides)
        async def _execute():
            try:
                return await asyncio.wait_for(
                    operation(*args, **kwargs),
                    timeout=config.total_timeout
                )
            except asyncio.TimeoutError as e:
                self.logger.warning(
                    "Operation timed out",
                    category=category.value,
                    timeout=config.total_timeout,
                    operation=operation.__name__ if hasattr(operation, '__name__') else str(operation)
                )
                raise
        
        return await _execute()
    
    def get_request_timeout(self, category: TimeoutCategory, format_type: str = "seconds") -> Union[float, int, aiohttp.ClientTimeout]:
        """Get timeout value in different formats for various libraries"""
        config = self.get_config(category)
        
        if format_type == "seconds":
            return config.total_timeout
        elif format_type == "milliseconds":
            return int(config.total_timeout * 1000)
        elif format_type == "aiohttp":
            return self.get_aiohttp_timeout(category)
        elif format_type == "requests":
            return (config.connection_timeout, config.read_timeout)
        else:
            return config.total_timeout
    
    def get_circuit_breaker_status(self, category: TimeoutCategory) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring"""
        breaker = self.circuit_breakers[category]
        return {
            "category": category.value,
            "state": breaker.current_state,
            "failure_count": breaker.fail_counter,
            "failure_threshold": breaker.fail_max,
            "reset_timeout": breaker.reset_timeout,
            "last_failure": getattr(breaker, 'last_failure_time', None)
        }
    
    def get_all_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            category.value: self.get_circuit_breaker_status(category)
            for category in TimeoutCategory
        }
    
    def reset_circuit_breaker(self, category: TimeoutCategory):
        """Manually reset a circuit breaker"""
        self.circuit_breakers[category].reset()
        self.logger.info("Circuit breaker reset", category=category.value)
    
    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers"""
        for category in TimeoutCategory:
            self.reset_circuit_breaker(category)


# Global timeout manager instance
timeout_manager = UnifiedTimeoutManager()


# Convenience decorators for common use cases
def with_api_timeout_and_retries(custom_overrides: Optional[Dict[str, Any]] = None):
    """Decorator for API calls with appropriate timeout and retry handling"""
    return timeout_manager.with_timeout_and_retries(TimeoutCategory.API_CALL, custom_overrides)


def with_search_timeout_and_retries(custom_overrides: Optional[Dict[str, Any]] = None):
    """Decorator for search operations with appropriate timeout and retry handling"""
    return timeout_manager.with_timeout_and_retries(TimeoutCategory.WEB_SEARCH, custom_overrides)


def with_scrape_timeout_and_retries(custom_overrides: Optional[Dict[str, Any]] = None):
    """Decorator for scraping operations with appropriate timeout and retry handling"""
    return timeout_manager.with_timeout_and_retries(TimeoutCategory.WEB_SCRAPE, custom_overrides)


def with_db_timeout_and_retries(custom_overrides: Optional[Dict[str, Any]] = None):
    """Decorator for database operations with appropriate timeout and retry handling"""
    return timeout_manager.with_timeout_and_retries(TimeoutCategory.DATABASE, custom_overrides)


# Utility functions for common timeout patterns
def get_api_timeout() -> aiohttp.ClientTimeout:
    """Get standardized API timeout"""
    return timeout_manager.get_aiohttp_timeout(TimeoutCategory.API_CALL)


def get_search_timeout() -> aiohttp.ClientTimeout:
    """Get standardized search timeout"""
    return timeout_manager.get_aiohttp_timeout(TimeoutCategory.WEB_SEARCH)


def get_search_timeout_seconds() -> float:
    """Get standardized search timeout in seconds"""
    return timeout_manager.get_request_timeout(TimeoutCategory.WEB_SEARCH, "seconds")


def get_scrape_timeout_seconds() -> float:
    """Get standardized scrape timeout in seconds"""
    return timeout_manager.get_request_timeout(TimeoutCategory.WEB_SCRAPE, "seconds")


def get_scrape_timeout_ms() -> int:
    """Get standardized scrape timeout in milliseconds"""
    return timeout_manager.get_request_timeout(TimeoutCategory.WEB_SCRAPE, "milliseconds") 