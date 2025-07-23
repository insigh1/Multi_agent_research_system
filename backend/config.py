"""
Configuration Management for Multi-Agent Research System
======================================================

Handles settings, validation, and environment configuration.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # API Configuration
    fireworks_api_key: str = Field(..., min_length=10, description="Fireworks AI API key")
    brave_api_key: Optional[str] = Field(None, min_length=10, description="Brave Search API key")
    firecrawl_api_key: Optional[str] = Field(None, min_length=10, description="Firecrawl API key")
    
    # Search Engine Configuration
    preferred_search_engine: str = Field(
        "firecrawl", 
        pattern="^(firecrawl|brave|auto)$",
        description="Preferred search engine: firecrawl=use Firecrawl with full content, brave=use Brave API, auto=try Firecrawl first then fallback to Brave"
    )
    enable_content_extraction: bool = Field(True, description="Enable full content extraction from sources (requires Firecrawl)")
    max_content_length: int = Field(25000, ge=1000, le=50000, description="Maximum content length per source (characters)")
    
    # AI Model Settings - Multi-Model Architecture
    fireworks_model: str = Field(
        "accounts/fireworks/models/llama-v3p1-8b-instruct", 
        description="Default Fireworks AI model (fallback)"
    )

    # Agent-Specific Model Configuration
    agent_models: dict = Field(default_factory=lambda: {
        # Research Planning - Needs strong reasoning and planning
        "research_planner": {
            "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",  # Better reasoning
            "max_tokens": 1200,
            "temperature": 0.2,  # Lower for more consistent planning
            "description": "Research planning and strategy"
        },
        
        # Web Search/Information Gathering - Needs fast, efficient processing
        "web_search": {
            "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",  # Fast and efficient
            "max_tokens": 600,
            "temperature": 0.3,
            "description": "Web search and information extraction"
        },
        
        # Quality Evaluation - Needs strong analytical skills
        "quality_evaluation": {
            "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",  # Better analysis
            "max_tokens": 1500,
            "temperature": 0.1,  # Very low for consistent evaluation
            "description": "Quality assessment and evaluation"
        },
        
        # Summarization - Needs strong text synthesis
        "summarization": {
            "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",  # Good at synthesis
            "max_tokens": 800,
            "temperature": 0.3,
            "description": "Content summarization and synthesis"
        },
        
        # Report Synthesis - Needs excellent writing capabilities
        "report_synthesis": {
            "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",  # Best available writing
            "max_tokens": 2500,  # Increased from 1000 for comprehensive synthesis
            "temperature": 0.4,  # Slightly higher for more natural writing
            "description": "Final report generation and synthesis"
        }
    }, description="Agent-specific model configurations")

    # Model Selection Strategy
    model_selection_strategy: str = Field(
        "adaptive", 
        pattern="^(single|adaptive|cost_optimized|performance_optimized)$",
        description="Model selection strategy: single=use default for all, adaptive=use agent-specific, cost_optimized=prefer cheaper models, performance_optimized=prefer best models"
    )

    # Cost and Performance Budgets
    max_cost_per_query: float = Field(0.50, ge=0.01, le=5.0, description="Maximum cost per research query (USD)")
    performance_vs_cost_weight: float = Field(0.7, ge=0.0, le=1.0, description="Weight for performance vs cost (1.0=max performance, 0.0=min cost)")

    # Legacy settings (for backward compatibility)
    max_tokens: int = Field(800, ge=100, le=4000, description="Default maximum tokens per API call")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="Default AI model temperature")
    
    # Rate Limiting - Enhanced for High-Concurrency Firecrawl
    max_concurrent_requests: int = Field(50, ge=1, le=100, description="Max concurrent API requests (increased for Firecrawl)")
    requests_per_minute: int = Field(300, ge=1, le=500, description="Rate limit per minute")
    
    # Brave API Rate Limiting & Retry Configuration
    brave_max_retries: int = Field(5, ge=1, le=10, description="Max retries for Brave API rate limits")
    brave_base_delay: float = Field(1.0, ge=0.1, le=5.0, description="Base delay for exponential backoff (seconds)")
    brave_max_delay: float = Field(30.0, ge=5.0, le=120.0, description="Maximum delay for exponential backoff (seconds)")
    brave_backoff_multiplier: float = Field(2.0, ge=1.0, le=5.0, description="Exponential backoff multiplier")
    brave_requests_per_minute: int = Field(30, ge=1, le=100, description="Brave API requests per minute limit")
    brave_burst_allowance: int = Field(5, ge=1, le=15, description="Brave API burst request allowance")
    
    # Enhanced Parallel Processing Settings - Optimized for High-Concurrency Firecrawl
    max_parallel_searches: int = Field(25, ge=1, le=25, description="Max parallel search operations (increased for Firecrawl)")
    max_parallel_summaries: int = Field(10, ge=1, le=15, description="Max parallel summary operations (increased for Firecrawl)") 
    batch_size: int = Field(10, ge=1, le=20, description="Questions per processing batch (increased for Firecrawl)")
    base_delay_seconds: float = Field(0.5, ge=0.5, le=5.0, description="Base delay between operations")
    inter_batch_delay_seconds: float = Field(1.0, ge=1.0, le=10.0, description="Delay between batches")
    
    # Advanced Caching Settings
    enable_semantic_cache: bool = Field(True, description="Enable semantic similarity caching")
    similarity_threshold: float = Field(0.8, ge=0.5, le=1.0, description="Similarity threshold for cache hits")
    cache_compression: bool = Field(True, description="Enable cache compression for large results")
    
    # Timeouts
    api_timeout: int = Field(60, ge=10, le=300, description="API request timeout (seconds)")
    brave_timeout: int = Field(30, ge=5, le=120, description="Brave search timeout (seconds)")
    firecrawl_timeout: int = Field(120, ge=30, le=300, description="Firecrawl search and scrape timeout (seconds)")
    
    # Firecrawl Configuration - Enhanced for High-Concurrency Operations
    firecrawl_max_results: int = Field(3, ge=1, le=100, description="Maximum search results from Firecrawl (increased for high-concurrency)")
    firecrawl_scrape_timeout: int = Field(15, ge=5, le=300, description="Timeout for individual page scraping (seconds, increased for complex pages)")
    firecrawl_enable_markdown: bool = Field(True, description="Extract content as markdown format")
    firecrawl_only_main_content: bool = Field(True, description="Extract only main content, filtering out navigation/footer")
    firecrawl_content_limit: int = Field(2500, ge=1000, le=50000, description="Content length limit for Firecrawl extraction (characters, increased for comprehensive extraction)")
    firecrawl_parallel_scraping: bool = Field(True, description="Enable parallel scraping of multiple URLs for faster performance")
    
    # High-Concurrency Firecrawl Settings
    firecrawl_max_concurrent_browsers: int = Field(50, ge=1, le=100, description="Maximum concurrent browser instances for Firecrawl")
    firecrawl_browser_pool_size: int = Field(100, ge=1, le=200, description="Browser pool size for reusing instances")
    firecrawl_enable_browser_caching: bool = Field(True, description="Enable browser instance caching for performance")
    firecrawl_max_retry_attempts: int = Field(3, ge=1, le=10, description="Maximum retry attempts for failed scrapes")
    
    # Caching
    redis_url: str = Field("redis://localhost:6379", description="Redis connection URL")
    cache_ttl: int = Field(3600, ge=300, le=86400, description="Cache TTL in seconds")
    enable_cache: bool = Field(True, description="Enable caching")
    
    # Database
    db_path: str = Field("research_sessions.db", description="SQLite database path")
    
    # Security
    encryption_key: Optional[str] = Field(None, description="Encryption key for secure storage")
    
    # Monitoring
    metrics_port: int = Field(8000, ge=1024, le=65535, description="Prometheus metrics port")
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    
    # Logging
    log_level: str = Field(
        "INFO", 
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level"
    )
    log_file: str = Field("research_system.log", description="Log file path")
    debug_summaries: bool = Field(False, description="Enable detailed logging for summary generation debugging")
    
    # Research Settings - Enhanced for High-Concurrency Operations
    max_sub_questions: int = Field(5, ge=1, le=20, description="Maximum sub-questions per query (increased for complex research)")
    default_search_results: int = Field(10, ge=1, le=100, description="Default search results count (increased for comprehensive research)")
    
    # Report Generation Settings
    executive_summary_style: str = Field(
        "comprehensive", 
        pattern="^(brief|detailed|comprehensive)$",
        description="Executive summary style: brief=2-3 sentences, detailed=4-6 sentences with implications, comprehensive=full paragraph with analysis"
    )
    
    # URL Relevance Scoring Settings
    url_relevance_weight: float = Field(
        0.35, 
        ge=0.0, le=1.0,
        description="Weight given to URL relevance analysis in search result scoring (0.0-1.0). Higher values = more aggressive URL-based filtering"
    )
    url_relevance_threshold: float = Field(
        0.3,
        ge=0.0, le=1.0, 
        description="Minimum URL relevance score threshold. Results below this get penalized (0.0-1.0)"
    )
    
    # Adaptive Filtering Settings
    preferred_filtering_strategy: str = Field(
        "balanced",
        pattern="^(conservative|balanced|aggressive|domain_diversity|percentile_based)$",
        description="Preferred filtering strategy: conservative=strict quality, balanced=moderate, aggressive=high filtering, domain_diversity=favor variety, percentile_based=statistical thresholds"
    )
    
    # Source Quality Filtering - Adaptive & Context-Aware
    enable_source_filtering: bool = Field(True, description="Enable intelligent adaptive source filtering")
    
    # Adaptive Thresholds (will adjust based on available source quality)
    min_authority_score: float = Field(0.4, ge=0.0, le=1.0, description="Minimum authority score (adaptive baseline)")
    min_relevance_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum relevance score (adaptive baseline)")
    min_content_quality: float = Field(0.4, ge=0.0, le=1.0, description="Minimum content quality score (adaptive baseline)")
    min_overall_confidence: float = Field(0.45, ge=0.0, le=1.0, description="Minimum overall confidence (adaptive baseline)")
    
    # Adaptive Filtering Strategy
    adaptive_filtering_mode: str = Field("smart", pattern="^(strict|smart|lenient|off)$", 
                                       description="Filtering strategy: strict=high standards, smart=adaptive, lenient=keep most, off=no filtering")
    min_sources_threshold: int = Field(3, ge=1, le=10, description="Minimum sources required before applying strict filtering")
    quality_percentile_cutoff: float = Field(0.3, ge=0.1, le=0.8, description="Keep sources above this percentile of available quality")
    
    # Safety Limits
    max_filtered_percentage: float = Field(0.8, ge=0.0, le=0.9, description="Maximum percentage of sources that can be filtered (safety limit)")
    min_sources_after_filtering: int = Field(1, ge=1, le=3, description="Minimum sources to keep regardless of quality")
    
    # Context-Aware Adjustments
    niche_topic_detection: bool = Field(True, description="Detect niche/novel topics and adjust filtering accordingly")
    academic_topic_boost: bool = Field(True, description="Boost filtering for academic/technical topics")
    current_events_boost: bool = Field(True, description="Boost filtering for current events/news topics")
    
    # Advanced Filtering Options
    filter_duplicate_domains: bool = Field(True, description="Filter out excessive results from same domain")
    max_results_per_domain: int = Field(3, ge=1, le=10, description="Maximum results allowed per domain")
    filter_low_content_sources: bool = Field(True, description="Filter sources with minimal content")
    min_snippet_length: int = Field(30, ge=10, le=200, description="Minimum snippet length for content filtering (adaptive)")
    
    # Intelligent Blacklist (only truly low-value sources)
    domain_blacklist: list = Field(default_factory=lambda: [
        "pinterest.com", "tiktok.com", "instagram.com/p/", 
        "facebook.com/posts/", "twitter.com/status/", "t.co/",
        "bit.ly", "tinyurl.com", "spam-site-patterns"
    ], description="Domains to filter out (only clear low-quality sources)")
    
    # Flexible Source Type Scoring (used for relative ranking, not hard cutoffs)
    source_type_preferences: dict = Field(default_factory=lambda: {
        "academic": 1.0,      # Highest preference
        "government": 0.95,   # Very high preference
        "news": 0.8,         # High preference  
        "organization": 0.75, # Good preference
        "wiki": 0.6,         # Moderate preference
        "reference": 0.55,   # Moderate preference
        "blog": 0.4,         # Lower preference (but not excluded)
        "forum": 0.35,       # Lower preference
        "social": 0.2,       # Lowest preference (but not excluded for niche topics)
        "unknown": 0.5       # Neutral preference
    }, description="Source type preferences for ranking (not hard cutoffs)")
    
    # Dynamic Domain Authority Configuration
    enable_dynamic_authority: bool = Field(True, description="Enable dynamic heuristic-based domain authority scoring")
    authority_api_endpoint: Optional[str] = Field(None, description="Optional external domain authority API endpoint")
    authority_api_key: Optional[str] = Field(None, description="API key for external authority service")
    authority_cache_hours: int = Field(24, ge=1, le=168, description="Hours to cache authority scores")
    
    # Authority Scoring Weights (for dynamic calculation)
    authority_weights: dict = Field(default_factory=lambda: {
        "domain_type": 0.35,      # Government/academic TLD weight
        "characteristics": 0.25,  # Domain age, HTTPS, structure
        "url_quality": 0.15,      # Clean URLs, professional paths
        "known_boost": 0.25      # Curated high-authority boost
    }, description="Weights for different authority scoring factors")
    
    # Minimum Authority Thresholds (dynamic system will adjust these based on content availability)
    min_authority_for_pass: float = Field(0.4, ge=0.1, le=0.8, description="Minimum authority score for source to pass quality check")
    fallback_to_content_when_low_authority: bool = Field(True, description="Use content quality to compensate for lower domain authority")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = "RESEARCH_"


class QueryRequest(BaseModel):
    """Validated research query request"""
    
    query: str = Field(..., min_length=3, max_length=1000, description="Research query")
    max_sub_questions: int = Field(5, ge=1, le=10, description="Maximum sub-questions")
    include_web_search: bool = Field(True, description="Include web search results")
    save_session: bool = Field(False, description="Save research session")
    session_id: Optional[str] = Field(None, description="Session ID for resuming")
    output_format: str = Field("console", pattern="^(console|json|html|pdf)$", description="Output format")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Validate and sanitize query"""
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Query must be at least 3 characters long')
        
        # Basic content filtering
        forbidden_terms = ['hack', 'exploit', 'illegal', 'malware', 'virus']
        if any(term in v.lower() for term in forbidden_terms):
            raise ValueError('Query contains forbidden terms')
        
        # Remove potentially harmful characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';']
        for char in dangerous_chars:
            v = v.replace(char, ' ')
        
        return v.strip()
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """Validate session ID format"""
        if v and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Session ID must be alphanumeric with optional hyphens/underscores')
        return v


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    
    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Check timestamp")
    services: dict = Field(..., description="Individual service statuses")
    metrics: dict = Field(default_factory=dict, description="System metrics") 