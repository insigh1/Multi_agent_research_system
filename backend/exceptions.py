"""
Custom Exceptions for Multi-Agent Research System
================================================

Comprehensive error handling with specific exception types.
"""

from typing import Optional, Dict, Any


class ResearchSystemError(Exception):
    """Base exception for all research system errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ValidationError(ResearchSystemError):
    """Input validation errors"""
    pass


class ConfigurationError(ResearchSystemError):
    """Configuration and setup errors"""
    pass


class APIUnavailableError(ResearchSystemError):
    """API service unavailable errors"""
    
    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        super().__init__(f"{service} API unavailable: {message}")
        self.service = service
        self.status_code = status_code
        self.details = {"service": service, "status_code": status_code}


class RateLimitError(ResearchSystemError):
    """Rate limiting errors"""
    
    def __init__(self, service: str, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded for {service}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)
        self.service = service
        self.retry_after = retry_after
        self.details = {"service": service, "retry_after": retry_after}


class AuthenticationError(ResearchSystemError):
    """Authentication and authorization errors"""
    
    def __init__(self, service: str, message: str = "Authentication failed"):
        super().__init__(f"{service}: {message}")
        self.service = service
        self.details = {"service": service}


class CacheError(ResearchSystemError):
    """Caching system errors"""
    pass


class DatabaseError(ResearchSystemError):
    """Database operation errors"""
    pass


class SecurityError(ResearchSystemError):
    """Security-related errors"""
    pass


class ProcessingError(ResearchSystemError):
    """Data processing and analysis errors"""
    
    def __init__(self, stage: str, message: str, partial_results: Optional[Any] = None):
        super().__init__(f"Processing failed at {stage}: {message}")
        self.stage = stage
        self.partial_results = partial_results
        self.details = {"stage": stage, "has_partial_results": partial_results is not None}


class ResourceExhaustionError(ResearchSystemError):
    """Resource exhaustion errors"""
    
    def __init__(self, resource: str, message: str):
        super().__init__(f"Resource exhausted ({resource}): {message}")
        self.resource = resource
        self.details = {"resource": resource}


class TimeoutError(ResearchSystemError):
    """Operation timeout errors"""
    
    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(f"Operation '{operation}' timed out after {timeout_seconds} seconds")
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.details = {"operation": operation, "timeout_seconds": timeout_seconds}


class CircuitBreakerError(ResearchSystemError):
    """Circuit breaker triggered errors"""
    
    def __init__(self, service: str, failure_count: int):
        super().__init__(f"Circuit breaker open for {service} (failures: {failure_count})")
        self.service = service
        self.failure_count = failure_count
        self.details = {"service": service, "failure_count": failure_count} 