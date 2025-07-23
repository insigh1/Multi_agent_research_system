"""
Unified error handling system for the research system.
Standardizes all error handling patterns found throughout the codebase.
"""

import structlog
import time
from typing import Dict, Any, Optional, Union, Callable, Type, List
from dataclasses import dataclass
from enum import Enum
import traceback
from functools import wraps

logger = structlog.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Recoverable, fallback available
    MEDIUM = "medium"     # Impacts functionality, partial recovery
    HIGH = "high"         # Major functionality loss
    CRITICAL = "critical" # System failure


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETURN_FALLBACK = "return_fallback"     # Return predetermined fallback data
    RETRY_WITH_FALLBACK = "retry_fallback"  # Retry operation, fallback if fails again
    PROPAGATE_WITH_CONTEXT = "propagate"    # Re-raise with added context
    LOG_AND_CONTINUE = "log_continue"       # Log error but continue execution
    GRACEFUL_DEGRADATION = "degrade"        # Reduce functionality but continue


@dataclass
class ErrorContext:
    """Comprehensive error context information"""
    operation: str
    agent_name: str
    component: str
    user_query: Optional[str] = None
    processing_step: Optional[str] = None
    sub_question_id: Optional[int] = None
    session_id: Optional[str] = None
    start_time: Optional[float] = None
    additional_context: Dict[str, Any] = None


@dataclass
class RecoveryResult:
    """Result of error recovery attempt"""
    success: bool
    result: Any = None
    fallback_used: bool = False
    error_message: Optional[str] = None
    recovery_time: float = 0.0
    degraded_functionality: bool = False


class StandardErrorHandler:
    """Unified error handler that standardizes all error handling patterns"""
    
    def __init__(self):
        self.logger = structlog.get_logger("ErrorHandler")
        self.error_counts: Dict[str, int] = {}
        self.recovery_stats: Dict[str, List[bool]] = {}
    
    def handle_error(self, 
                    error: Exception,
                    context: ErrorContext,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETURN_FALLBACK,
                    fallback_factory: Optional[Callable] = None,
                    max_retries: int = 0) -> RecoveryResult:
        """
        Central error handling with standardized recovery strategies
        
        Args:
            error: The exception that occurred
            context: Error context information
            severity: Severity level of the error
            recovery_strategy: How to handle the error
            fallback_factory: Function to create fallback data
            max_retries: Number of retries for RETRY_WITH_FALLBACK strategy
            
        Returns:
            RecoveryResult with outcome and any recovered data
        """
        start_time = time.time()
        error_key = f"{context.agent_name}.{context.operation}"
        
        # Track error frequency
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log error with full context
        self._log_error(error, context, severity)
        
        # Apply recovery strategy
        try:
            if recovery_strategy == RecoveryStrategy.RETURN_FALLBACK:
                result = self._handle_fallback_strategy(error, context, fallback_factory)
            
            elif recovery_strategy == RecoveryStrategy.RETRY_WITH_FALLBACK:
                result = self._handle_retry_strategy(error, context, fallback_factory, max_retries)
            
            elif recovery_strategy == RecoveryStrategy.PROPAGATE_WITH_CONTEXT:
                result = self._handle_propagate_strategy(error, context)
            
            elif recovery_strategy == RecoveryStrategy.LOG_AND_CONTINUE:
                result = self._handle_log_continue_strategy(error, context)
            
            elif recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                result = self._handle_degradation_strategy(error, context, fallback_factory)
            
            else:
                # Default fallback
                result = self._handle_fallback_strategy(error, context, fallback_factory)
            
            # Track recovery success
            self._track_recovery_success(error_key, result.success)
            
            result.recovery_time = time.time() - start_time
            return result
            
        except Exception as recovery_error:
            self.logger.error("Error during error recovery",
                            original_error=str(error),
                            recovery_error=str(recovery_error),
                            context=context.__dict__)
            
            # Ultimate fallback
            return RecoveryResult(
                success=False,
                error_message=f"Recovery failed: {str(recovery_error)}",
                recovery_time=time.time() - start_time
            )
    
    def _log_error(self, error: Exception, context: ErrorContext, severity: ErrorSeverity):
        """Standardized error logging with context"""
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity.value,
            "operation": context.operation,
            "agent": context.agent_name,
            "component": context.component,
            "traceback": traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
        
        # Add optional context
        if context.user_query:
            log_data["user_query"] = context.user_query[:100] + "..." if len(context.user_query) > 100 else context.user_query
        if context.processing_step:
            log_data["processing_step"] = context.processing_step
        if context.sub_question_id:
            log_data["sub_question_id"] = context.sub_question_id
        if context.additional_context:
            log_data.update(context.additional_context)
        
        # Log at appropriate level
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical system error", **log_data)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error", **log_data)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error", **log_data)
        else:
            self.logger.info("Low severity error", **log_data)
    
    def _handle_fallback_strategy(self, error: Exception, context: ErrorContext, 
                                fallback_factory: Optional[Callable]) -> RecoveryResult:
        """Handle RETURN_FALLBACK strategy"""
        if fallback_factory:
            try:
                fallback_data = fallback_factory(error, context)
                return RecoveryResult(
                    success=True,
                    result=fallback_data,
                    fallback_used=True
                )
            except Exception as fallback_error:
                return RecoveryResult(
                    success=False,
                    error_message=f"Fallback creation failed: {str(fallback_error)}"
                )
        else:
            return RecoveryResult(
                success=False,
                error_message="No fallback factory provided"
            )
    
    def _handle_retry_strategy(self, error: Exception, context: ErrorContext,
                             fallback_factory: Optional[Callable], max_retries: int) -> RecoveryResult:
        """Handle RETRY_WITH_FALLBACK strategy"""
        # For now, just return fallback (retry logic would need the original operation)
        return self._handle_fallback_strategy(error, context, fallback_factory)
    
    def _handle_propagate_strategy(self, error: Exception, context: ErrorContext) -> RecoveryResult:
        """Handle PROPAGATE_WITH_CONTEXT strategy"""
        # Enhance error with context and re-raise
        enhanced_message = f"{str(error)} (Context: {context.operation} in {context.agent_name})"
        enhanced_error = type(error)(enhanced_message)
        enhanced_error.__cause__ = error
        raise enhanced_error
    
    def _handle_log_continue_strategy(self, error: Exception, context: ErrorContext) -> RecoveryResult:
        """Handle LOG_AND_CONTINUE strategy"""
        return RecoveryResult(
            success=True,
            result=None,
            error_message=str(error)
        )
    
    def _handle_degradation_strategy(self, error: Exception, context: ErrorContext,
                                   fallback_factory: Optional[Callable]) -> RecoveryResult:
        """Handle GRACEFUL_DEGRADATION strategy"""
        result = self._handle_fallback_strategy(error, context, fallback_factory)
        if result.success:
            result.degraded_functionality = True
        return result
    
    def _track_recovery_success(self, error_key: str, success: bool):
        """Track recovery success rates"""
        if error_key not in self.recovery_stats:
            self.recovery_stats[error_key] = []
        self.recovery_stats[error_key].append(success)
        
        # Keep only last 10 recovery attempts
        if len(self.recovery_stats[error_key]) > 10:
            self.recovery_stats[error_key] = self.recovery_stats[error_key][-10:]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        stats = {
            "error_counts": self.error_counts.copy(),
            "recovery_rates": {},
            "total_errors": sum(self.error_counts.values())
        }
        
        for key, recoveries in self.recovery_stats.items():
            if recoveries:
                stats["recovery_rates"][key] = {
                    "success_rate": sum(recoveries) / len(recoveries),
                    "total_attempts": len(recoveries),
                    "recent_successes": sum(recoveries[-5:]) if len(recoveries) >= 5 else sum(recoveries)
                }
        
        return stats


# Global error handler instance
error_handler = StandardErrorHandler()


def handle_research_error(operation: str, agent_name: str, component: str = "main"):
    """
    Decorator for standardized error handling in research system methods
    
    Usage:
    @handle_research_error("gather_information", "WebSearchRetrieverAgent")
    async def gather_information(self, ...):
        # method implementation
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    operation=operation,
                    agent_name=agent_name,
                    component=component,
                    start_time=time.time()
                )
                
                # Try to extract additional context from args
                if len(args) > 1 and hasattr(args[1], 'question'):
                    context.user_query = getattr(args[1], 'question', None)
                    context.sub_question_id = getattr(args[1], 'id', None)
                
                # Use appropriate fallback for common operations
                if operation == "gather_information":
                    # Import with fallback handling
                    try:
                        from backend.enhanced_research_system import RetrievalFindings
                    except (ImportError, ModuleNotFoundError):
                        try:
                            from enhanced_research_system import RetrievalFindings
                        except (ImportError, ModuleNotFoundError):
                            from ..enhanced_research_system import RetrievalFindings
                    def fallback_factory(error, ctx):
                        return RetrievalFindings(
                            sub_question_id=ctx.sub_question_id or 0,
                            query_used=ctx.user_query or "Unknown query",
                            results=[],
                            key_insights=["Failed to gather information due to technical issues"],
                            extracted_facts=["No facts could be extracted"],
                            confidence_score=0.0,
                            processing_time=0.0,
                            sources_count=0
                        )
                    
                    result = error_handler.handle_error(
                        e, context, ErrorSeverity.MEDIUM,
                        RecoveryStrategy.RETURN_FALLBACK,
                        fallback_factory
                    )
                    return result.result
                
                # Default: log and re-raise
                error_handler.handle_error(
                    e, context, ErrorSeverity.HIGH,
                    RecoveryStrategy.PROPAGATE_WITH_CONTEXT
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    operation=operation,
                    agent_name=agent_name,
                    component=component,
                    start_time=time.time()
                )
                
                error_handler.handle_error(
                    e, context, ErrorSeverity.HIGH,
                    RecoveryStrategy.PROPAGATE_WITH_CONTEXT
                )
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator 