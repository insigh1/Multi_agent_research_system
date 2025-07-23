"""
Utility Functions for Multi-Agent Research System
================================================

Common utilities for logging, monitoring, caching, security, and operations.
"""

import json
import hashlib
import secrets
import time
import asyncio
import logging.config
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List, Callable, Union
from pathlib import Path
from contextlib import asynccontextmanager
import os
import hmac
import redis
import sqlite3

import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from cryptography.fernet import Fernet
import redis.asyncio as redis
from cachetools import TTLCache

# Direct imports for compatibility
# Import with fallback handling for different execution contexts
try:
    from backend.config import Settings
    from backend.exceptions import SecurityError, CacheError, ConfigurationError
except (ImportError, ModuleNotFoundError):
    try:
        from config import Settings
        from exceptions import SecurityError, CacheError, ConfigurationError
    except (ImportError, ModuleNotFoundError):
        from .config import Settings
        from .exceptions import SecurityError, CacheError, ConfigurationError


# Metrics - Initialize with error handling for duplicates
try:
    api_calls_total = Counter('api_calls_total', 'Total API calls', ['service', 'status'])
    request_duration = Histogram('request_duration_seconds', 'Request duration', ['service'])
    active_research_sessions = Gauge('active_research_sessions', 'Active research sessions')
    cache_hits = Counter('cache_hits_total', 'Cache hits', ['cache_type'])
    cache_misses = Counter('cache_misses_total', 'Cache misses', ['cache_type'])
    error_count = Counter('errors_total', 'Total errors', ['error_type'])
except ValueError:
    # Metrics already exist, get existing ones from registry
    from prometheus_client import CollectorRegistry, REGISTRY
    
    # Find existing metrics
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name'):
            if collector._name == 'api_calls_total':
                api_calls_total = collector
            elif collector._name == 'request_duration_seconds':
                request_duration = collector
            elif collector._name == 'active_research_sessions':
                active_research_sessions = collector
            elif collector._name == 'cache_hits_total':
                cache_hits = collector
            elif collector._name == 'cache_misses_total':
                cache_misses = collector
            elif collector._name == 'errors_total':
                error_count = collector


def setup_logging(settings: Settings) -> None:
    """Configure structured logging"""
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
            },
        },
        "handlers": {
            "console": {
                "level": settings.log_level,
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
            "file": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": settings.log_file,
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "formatter": "json",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": settings.log_level,
                "propagate": False,
            },
        }
    }
    
    logging.config.dictConfig(log_config)
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Global flag to track if metrics server is already running
_metrics_server_started = False

def start_metrics_server(port: int) -> None:
    """Start Prometheus metrics server (singleton pattern)"""
    global _metrics_server_started
    
    if _metrics_server_started:
        # Metrics server already running, skip
        return
    
    try:
        start_http_server(port)
        _metrics_server_started = True
        logger = structlog.get_logger(__name__)
        logger.info("Metrics server started", port=port)
    except Exception as e:
        logger = structlog.get_logger(__name__)
        # Only log as warning if it's an "address in use" error, as error otherwise
        if "Address already in use" in str(e):
            logger.warning("Metrics server already running on port", port=port, error=str(e))
            _metrics_server_started = True  # Mark as started since it's already running
        else:
            logger.error("Failed to start metrics server", error=str(e))


class SecurityManager:
    """Handles encryption and secure operations"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        if encryption_key:
            try:
                # Validate key format
                key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
                self.cipher = Fernet(key_bytes)
            except Exception as e:
                raise SecurityError("Invalid encryption key format", details={"error": str(e)})
        else:
            # Generate new key
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            logger = structlog.get_logger(__name__)
            logger.warning("Generated new encryption key - save this for persistence", 
                         key=key.decode())
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception as e:
            raise SecurityError("Encryption failed", details={"error": str(e)})
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            raise SecurityError("Decryption failed", details={"error": str(e)})
    
    def generate_session_id(self) -> str:
        """Generate secure session ID"""
        return secrets.token_urlsafe(16)
    
    def hash_data(self, data: str) -> str:
        """Generate secure hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_api_key(self, api_key: str, service: str) -> bool:
        """Validate API key format"""
        if not api_key or len(api_key) < 10:
            return False
        
        # Service-specific validation
        if service == "fireworks":
            return api_key.startswith("fw-") or len(api_key) > 20
        elif service == "brave":
            return len(api_key) > 15
        
        return True


class CacheManager:
    """Enhanced caching with Redis and local fallback"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis: Optional[redis.Redis] = None
        self.local_cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl)
        self.logger = structlog.get_logger(__name__)
        self._connection_healthy = False
    
    async def connect(self) -> None:
        """Connect to Redis with health checking"""
        if not self.settings.enable_cache:
            self.logger.info("Caching disabled by configuration")
            return
        
        try:
            self.redis = redis.from_url(
                self.settings.redis_url, 
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis.ping()
            self._connection_healthy = True
            self.logger.info("Connected to Redis cache", url=self.settings.redis_url)
        except Exception as e:
            self.logger.warning("Redis unavailable, using local cache only", error=str(e))
            self.redis = None
            self._connection_healthy = False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            try:
                await self.redis.close()
                self.logger.info("Disconnected from Redis")
            except Exception as e:
                self.logger.warning("Error disconnecting from Redis", error=str(e))
    
    def _cache_key(self, prefix: str, key: str) -> str:
        """Generate cache key with consistent hashing"""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return f"research:{prefix}:{hash_key}"
    
    async def get(self, prefix: str, key: str) -> Optional[Any]:
        """Get cached value with fallback strategy"""
        cache_key = self._cache_key(prefix, key)
        
        # Try Redis first if available
        if self.redis and self._connection_healthy:
            try:
                value = await self.redis.get(cache_key)
                if value:
                    cache_hits.labels(cache_type="redis").inc()
                    return json.loads(value)
            except Exception as e:
                self.logger.warning("Redis get failed", error=str(e))
                self._connection_healthy = False
        
        # Try local cache
        if cache_key in self.local_cache:
            cache_hits.labels(cache_type="local").inc()
            return self.local_cache[cache_key]
        
        cache_misses.labels(cache_type="combined").inc()
        return None
    
    async def set(self, prefix: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with dual storage"""
        cache_key = self._cache_key(prefix, key)
        ttl = ttl or self.settings.cache_ttl
        
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            raise CacheError(f"Failed to serialize cache value: {str(e)}")
        
        # Set in Redis if available
        if self.redis and self._connection_healthy:
            try:
                await self.redis.setex(cache_key, ttl, serialized)
            except Exception as e:
                self.logger.warning("Redis set failed", error=str(e))
                self._connection_healthy = False
        
        # Always set in local cache
        self.local_cache[cache_key] = value
    
    async def delete(self, prefix: str, key: str) -> None:
        """Delete cached value"""
        cache_key = self._cache_key(prefix, key)
        
        # Delete from Redis
        if self.redis and self._connection_healthy:
            try:
                await self.redis.delete(cache_key)
            except Exception as e:
                self.logger.warning("Redis delete failed", error=str(e))
        
        # Delete from local cache
        self.local_cache.pop(cache_key, None)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cache system health"""
        status = {
            "local_cache": {
                "enabled": True,
                "size": len(self.local_cache),
                "max_size": self.local_cache.maxsize,
                "ttl": self.local_cache.ttl
            },
            "redis": {
                "enabled": self.redis is not None,
                "connected": self._connection_healthy,
                "url": self.settings.redis_url if self.redis else None
            }
        }
        
        if self.redis and self._connection_healthy:
            try:
                await self.redis.ping()
                status["redis"]["ping"] = True
            except Exception:
                status["redis"]["ping"] = False
                self._connection_healthy = False
        
        return status


class ProgressTracker:
    """Track and report research progress"""
    
    def __init__(self, total_steps: int, session_id: str):
        self.total_steps = total_steps
        self.session_id = session_id
        self.completed_steps = 0
        self.current_stage = "initializing"
        self.start_time = time.time()
        self.errors: List[str] = []
        self.stage_times: Dict[str, float] = {}
        self.logger = structlog.get_logger(__name__)
    
    def update_stage(self, stage: str) -> None:
        """Update current processing stage"""
        if self.current_stage != "initializing":
            # Record time for previous stage
            self.stage_times[self.current_stage] = time.time() - self.start_time
        
        self.current_stage = stage
        self.logger.info("Progress update", 
                        session_id=self.session_id,
                        stage=stage,
                        progress=f"{self.completed_steps}/{self.total_steps}")
    
    def complete_step(self, step_name: str) -> None:
        """Mark a step as completed"""
        self.completed_steps += 1
        self.logger.info("Step completed",
                        session_id=self.session_id,
                        step=step_name,
                        progress=f"{self.completed_steps}/{self.total_steps}")
    
    def add_error(self, error: str) -> None:
        """Add error to progress tracking"""
        self.errors.append(error)
        error_count.labels(error_type="progress").inc()
        self.logger.error("Progress error", 
                         session_id=self.session_id,
                         error=error)
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress status"""
        elapsed_time = time.time() - self.start_time
        progress_percent = (self.completed_steps / self.total_steps) * 100
        
        # Estimate remaining time
        if self.completed_steps > 0:
            avg_time_per_step = elapsed_time / self.completed_steps
            remaining_steps = self.total_steps - self.completed_steps
            estimated_remaining = avg_time_per_step * remaining_steps
        else:
            estimated_remaining = None
        
        return {
            "session_id": self.session_id,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "progress_percent": round(progress_percent, 1),
            "current_stage": self.current_stage,
            "elapsed_time": round(elapsed_time, 2),
            "estimated_remaining": round(estimated_remaining, 2) if estimated_remaining else None,
            "errors": self.errors,
            "stage_times": self.stage_times
        }


def extract_json_from_response(response: str) -> str:
    """Extract JSON from various response formats - now delegates to ResponseParser"""
    from core.response_parser import ResponseParser
    return ResponseParser.extract_json_from_response(response)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system operations"""
    import re
    
    # Remove dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    # Avoid reserved names on Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL', 
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    if sanitized.upper() in reserved_names:
        sanitized = f"_{sanitized}"
    
    return sanitized or "unnamed"


def calculate_text_metrics(text: str) -> Dict[str, int]:
    """Calculate text quality metrics"""
    words = text.split()
    sentences = text.split('.')
    
    return {
        "word_count": len(words),
        "sentence_count": len([s for s in sentences if s.strip()]),
        "character_count": len(text),
        "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
        "average_sentence_length": len(words) / len(sentences) if sentences else 0
    }


@asynccontextmanager
async def managed_session(session_manager, session_id: str):
    """Context manager for research sessions with cleanup"""
    try:
        active_research_sessions.inc()
        yield session_id
    finally:
        active_research_sessions.dec()


def get_organized_report_path(session_id: str, report_format: str, query: str = None) -> Path:
    """
    Generate organized file path for research reports
    
    Creates directory structure: exports/reports/YYYY/MM/DD/
    With intelligent naming based on session and query
    
    Args:
        session_id: Unique session identifier
        report_format: File format (pdf, html, json)
        query: Optional research query for better naming
    
    Returns:
        Path object for the report file
    """
    # Create base reports directory
    base_dir = Path("exports/reports")
    
    # Create date-based subdirectory (YYYY/MM/DD)
    now = datetime.now()
    date_dir = base_dir / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
    
    # Ensure directory exists
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp and session info
    timestamp = now.strftime("%H%M%S")  # HHMMSS for uniqueness within the day
    session_short = session_id[:8] if len(session_id) > 8 else session_id
    
    # Create a clean query slug if provided
    query_slug = ""
    if query:
        # Clean and truncate query for filename (max 30 chars)
        import re
        clean_query = re.sub(r'[^\w\s-]', '', query.lower())
        clean_query = re.sub(r'[-\s]+', '-', clean_query)
        query_slug = f"_{clean_query[:30].rstrip('-')}" if clean_query else ""
    
    # Construct filename
    filename = f"research_{timestamp}_{session_short}{query_slug}.{report_format}"
    
    return date_dir / filename


def create_report_index_entry(file_path: Path, session_id: str, query: str, 
                            report_format: str, metadata: Dict[str, Any] = None) -> None:
    """
    Create or update an index file for easy report discovery
    
    Args:
        file_path: Path to the generated report file
        session_id: Session identifier
        query: Research query
        report_format: File format
        metadata: Additional metadata (processing_time, quality_score, etc.)
    """
    index_file = Path("exports/reports/index.json")
    
    # Load existing index or create new one
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            index_data = {"reports": [], "last_updated": None}
    else:
        index_data = {"reports": [], "last_updated": None}
    
    # Create new entry
    entry = {
        "session_id": session_id,
        "query": query,
        "format": report_format,
        "file_path": str(file_path) if file_path.is_absolute() else str(file_path.resolve().relative_to(Path.cwd().resolve())),
        "file_size": file_path.stat().st_size if file_path.exists() else 0,
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    
    # Remove any existing entry for this session and format
    index_data["reports"] = [
        r for r in index_data["reports"] 
        if not (r["session_id"] == session_id and r["format"] == report_format)
    ]
    
    # Add new entry
    index_data["reports"].append(entry)
    index_data["last_updated"] = datetime.now().isoformat()
    
    # Sort by creation date (newest first)
    index_data["reports"].sort(key=lambda x: x["created_at"], reverse=True)
    
    # Keep only the last 1000 reports to prevent unlimited growth
    index_data["reports"] = index_data["reports"][:1000]
    
    # Save updated index
    index_file.parent.mkdir(parents=True, exist_ok=True)
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)


def cleanup_old_reports(days_to_keep: int = 30) -> Dict[str, int]:
    """
    Clean up old report files and update index
    
    Args:
        days_to_keep: Number of days to keep reports (default: 30)
    
    Returns:
        Dictionary with cleanup statistics
    """
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    stats = {"files_deleted": 0, "directories_cleaned": 0, "errors": 0}
    
    reports_dir = Path("exports/reports")
    if not reports_dir.exists():
        return stats
    
    # Clean up old files
    for year_dir in reports_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
            
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
                
            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue
                
                try:
                    # Parse directory date
                    dir_date = datetime(
                        int(year_dir.name), 
                        int(month_dir.name), 
                        int(day_dir.name)
                    )
                    
                    if dir_date < cutoff_date:
                        # Delete all files in this directory
                        for file_path in day_dir.iterdir():
                            if file_path.is_file():
                                file_path.unlink()
                                stats["files_deleted"] += 1
                        
                        # Remove empty directory
                        if not any(day_dir.iterdir()):
                            day_dir.rmdir()
                            stats["directories_cleaned"] += 1
                            
                except (ValueError, OSError) as e:
                    stats["errors"] += 1
                    continue
    
    # Update index to remove references to deleted files
    index_file = Path("exports/reports/index.json")
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Filter out entries for files that no longer exist
            original_count = len(index_data["reports"])
            index_data["reports"] = [
                r for r in index_data["reports"]
                if Path(r["file_path"]).exists()
            ]
            
            # Also filter by date
            index_data["reports"] = [
                r for r in index_data["reports"]
                if datetime.fromisoformat(r["created_at"]) >= cutoff_date
            ]
            
            removed_count = original_count - len(index_data["reports"])
            if removed_count > 0:
                index_data["last_updated"] = datetime.now().isoformat()
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, indent=2, ensure_ascii=False)
                
                stats["index_entries_removed"] = removed_count
                
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            stats["errors"] += 1
    
    return stats


def get_report_summary() -> Dict[str, Any]:
    """
    Get summary statistics about stored reports
    
    Returns:
        Dictionary with report statistics
    """
    summary = {
        "total_reports": 0,
        "by_format": {},
        "by_date": {},
        "total_size": 0,
        "oldest_report": None,
        "newest_report": None
    }
    
    index_file = Path("exports/reports/index.json")
    if not index_file.exists():
        return summary
    
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        reports = index_data.get("reports", [])
        summary["total_reports"] = len(reports)
        
        if reports:
            # Count by format
            for report in reports:
                fmt = report.get("format", "unknown")
                summary["by_format"][fmt] = summary["by_format"].get(fmt, 0) + 1
                summary["total_size"] += report.get("file_size", 0)
            
            # Count by date (group by day)
            for report in reports:
                try:
                    date_str = report["created_at"][:10]  # YYYY-MM-DD
                    summary["by_date"][date_str] = summary["by_date"].get(date_str, 0) + 1
                except (KeyError, IndexError):
                    continue
            
            # Find oldest and newest
            dates = [r["created_at"] for r in reports if "created_at" in r]
            if dates:
                summary["oldest_report"] = min(dates)
                summary["newest_report"] = max(dates)
    
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    
    return summary 