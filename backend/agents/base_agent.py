"""
Base Agent Class for Multi-Agent Research System

This module contains the LLMAgent base class that all specialized agents inherit from.
It provides common functionality for API calls, caching, security, and metrics tracking.
"""

import asyncio
import time
import hashlib
from typing import Dict, Any, Optional

import aiohttp
import structlog

# Import with fallback handling for different execution contexts
try:
    from backend.config import Settings
    from backend.exceptions import AuthenticationError
    from backend.utils import CacheManager, SecurityManager
    from backend.core.timeout_manager import with_api_timeout_and_retries, get_api_timeout
    from backend.core.error_handler import StandardErrorHandler, ErrorContext, ErrorSeverity, RecoveryStrategy
    from backend.enhanced_research_system import (
        ModelManager, ResourceManager, metrics_collector
    )
except (ImportError, ModuleNotFoundError):
    try:
        from config import Settings
        from exceptions import AuthenticationError
        from utils import CacheManager, SecurityManager
        from core.timeout_manager import with_api_timeout_and_retries, get_api_timeout
        from core.error_handler import StandardErrorHandler, ErrorContext, ErrorSeverity, RecoveryStrategy
        from enhanced_research_system import (
            ModelManager, ResourceManager, metrics_collector
        )
    except (ImportError, ModuleNotFoundError):
        from ..config import Settings
        from ..exceptions import AuthenticationError
        from ..utils import CacheManager, SecurityManager
        from ..core.timeout_manager import with_api_timeout_and_retries, get_api_timeout
        from ..core.error_handler import StandardErrorHandler, ErrorContext, ErrorSeverity, RecoveryStrategy
        from ..enhanced_research_system import (
            ModelManager, ResourceManager, metrics_collector
        )


class LLMAgent:
    """Enhanced base agent with multi-model support and cost tracking"""
    
    def __init__(self, name: str, role: str, settings: Settings, 
                 cache_manager: CacheManager, security_manager: SecurityManager,
                 model_manager: 'ModelManager' = None, agent_type: str = "default"):
        self.name = name
        self.role = role
        self.settings = settings
        self.cache_manager = cache_manager
        self.security_manager = security_manager
        self.model_manager = model_manager or ModelManager(settings)
        self.agent_type = agent_type
        self.logger = structlog.get_logger(f"Agent.{name}")
        
        # Get agent-specific model configuration
        self.model_config = self.model_manager.get_model_config(agent_type)
        
        # Validate and decrypt API key
        if not security_manager.validate_api_key(settings.fireworks_api_key, "fireworks"):
            raise AuthenticationError("fireworks", "Invalid API key format")
        
        try:
            self.api_key = security_manager.decrypt_data(settings.fireworks_api_key)
        except:
            self.api_key = settings.fireworks_api_key  # Fallback for plain text
        
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        
        self.logger.info("Agent initialized with model configuration",
                        agent_type=agent_type,
                        model=self.model_config["model"],
                        max_tokens=self.model_config["max_tokens"],
                        temperature=self.model_config["temperature"])
        
    @with_api_timeout_and_retries()
    async def _call_fireworks_api(self, prompt: str, max_tokens: int = None, 
                                 resource_manager: ResourceManager = None, 
                                 operation: str = "general") -> str:
        """Enhanced API call with comprehensive metrics tracking"""
        max_tokens = max_tokens or self.settings.max_tokens
        # Use hash of full prompt instead of first 100 chars to prevent cache collisions
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        cache_key = f"{prompt_hash}_{max_tokens}_{self.settings.temperature}"
        
        # Check cache first
        cached_result = await self.cache_manager.get("api_responses", cache_key)
        if cached_result:
            # Record cache hit metrics
            metrics_collector.record_api_call(
                agent_name=self.name,
                operation=operation,
                model=self.model_config["model"],
                start_time=time.time(),
                end_time=time.time(),
                usage={"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
                cache_hit=True,
                success=True
            )
            self.logger.info("Using cached API response", 
                           cache_key=cache_key[:50], 
                           agent=self.name, 
                           operation=operation)
            return cached_result
        
        # Make API call if not cached
        start_time = time.time()
        retry_count = 0
        
        if not resource_manager:
            raise ValueError("ResourceManager is required for API calls")
        
        headers = {
            "Authorization": f"Bearer {self.settings.fireworks_api_key}",
            "Content-Type": "application/json"
        }
        
        # Use agent-specific model configuration
        actual_model = self.model_config["model"]
        actual_max_tokens = max_tokens or self.model_config["max_tokens"]
        actual_temperature = self.model_config["temperature"]
        
        data = {
            "model": actual_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": actual_max_tokens,
            "temperature": actual_temperature
        }
        
        try:
            response = await resource_manager.throttled_request(
                "POST", 
                "https://api.fireworks.ai/inference/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=get_api_timeout()
            )
            
            async with response:
                end_time = time.time()
                
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"API call failed with status {response.status}: {error_text}"
                    
                    # Record failed API call metrics
                    metrics_collector.record_api_call(
                        agent_name=self.name,
                        operation=operation,
                        model=actual_model,
                        start_time=start_time,
                        end_time=end_time,
                        usage={"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
                        cache_hit=False,
                        retry_count=retry_count,
                        success=False,
                        error=error_msg
                    )
                    
                    raise aiohttp.ClientError(error_msg)
                
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                
                # Debug logging for usage data
                self.logger.info("API Response Usage Data", 
                               agent=self.name,
                               model=actual_model,
                               operation=operation,
                               usage_raw=usage,
                               prompt_tokens=usage.get("prompt_tokens", 0),
                               completion_tokens=usage.get("completion_tokens", 0),
                               total_tokens=usage.get("total_tokens", 0))
                
                # Calculate response size
                response_size = len(content.encode('utf-8'))
                
                # Calculate cost for this API call
                cost = self.model_manager.calculate_estimated_cost(
                    actual_model, 
                    usage.get("prompt_tokens", 0), 
                    usage.get("completion_tokens", 0)
                )
                
                # Record model usage and cost
                self.model_manager.record_usage(
                    self.agent_type, actual_model, usage, cost
                )
                
                # Record successful API call metrics
                metrics_collector.record_api_call(
                    agent_name=self.name,
                    operation=operation,
                    model=actual_model,
                    start_time=start_time,
                    end_time=end_time,
                    usage=usage,
                    cache_hit=False,
                    retry_count=retry_count,
                    success=True,
                    response_size=response_size
                )
                
                # Cache the result
                await self.cache_manager.set("api_responses", cache_key, content, ttl=1800)
                
                # Enhanced logging with detailed metrics
                self.logger.info("API call successful", 
                               agent=self.name,
                               agent_type=self.agent_type,
                               operation=operation,
                               model=actual_model,
                               duration=end_time - start_time,
                               prompt_tokens=usage.get("prompt_tokens", 0),
                               completion_tokens=usage.get("completion_tokens", 0),
                               total_tokens=usage.get("total_tokens", 0),
                               response_size=response_size,
                               cost_estimate=cost)
                
                return content
                
        except Exception as e:
            end_time = time.time()
            
            # Record failed API call metrics
            metrics_collector.record_api_call(
                agent_name=self.name,
                operation=operation,
                model=actual_model,
                start_time=start_time,
                end_time=end_time,
                usage={"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
                cache_hit=False,
                retry_count=retry_count,
                success=False,
                error=str(e)
            )
            
            # Use unified error handler 
            context = ErrorContext(
                operation="api_call",
                component=self.name,
                metadata={"operation": operation, "model": actual_model, "duration": end_time - start_time}
            )
            handler = StandardErrorHandler()
            handler.handle_error(e, context, ErrorSeverity.HIGH, RecoveryStrategy.RERAISE) 