#!/usr/bin/env python3
"""
Multi-Agent Research System
Copyright (c) 2025 David Lee (@insigh1) - Fireworks AI
MIT License - see LICENSE file for details

Enhanced Multi-Agent Research System
====================================

Multi-agent research system with enhanced planning, intelligent caching, 
adaptive filtering, and parallel processing capabilities.
"""

import time
import asyncio
import aiohttp
import structlog
import json

import sqlite3
import pickle
import hashlib
import statistics
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from urllib.parse import urlparse
from collections import defaultdict

# Import Firecrawl API for direct integration (not MCP-dependent)
try:
    import requests
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    requests = None

# Import local dependencies with fallback handling
try:
    from backend.config import Settings, QueryRequest
    from backend.utils import (
        CacheManager, SecurityManager, ProgressTracker, 
        setup_logging
    )
    from backend.exceptions import (
        ResearchSystemError, ConfigurationError, ValidationError, 
        RateLimitError, TimeoutError
    )
except (ImportError, ModuleNotFoundError):
    try:
        from config import Settings, QueryRequest
        from utils import (
            CacheManager, SecurityManager, ProgressTracker, 
            setup_logging
        )
        from exceptions import (
            ResearchSystemError, ConfigurationError, ValidationError, 
            RateLimitError, TimeoutError
        )
    except (ImportError, ModuleNotFoundError):
        from .config import Settings, QueryRequest
        from .utils import (
            CacheManager, SecurityManager, ProgressTracker, 
            setup_logging
        )
        from .exceptions import (
            ResearchSystemError, ConfigurationError, ValidationError, 
            RateLimitError, TimeoutError
        )

# Setup structured logging
logger = structlog.get_logger(__name__)

# Initialize console for output
console = Console()

# Unified timeout and retry management with fallback handling
try:
    from backend.core.timeout_manager import (
        with_api_timeout_and_retries,
        with_search_timeout_and_retries,
        get_api_timeout,
        get_search_timeout
    )
except (ImportError, ModuleNotFoundError):
    try:
        from core.timeout_manager import (
            with_api_timeout_and_retries,
            with_search_timeout_and_retries,
            get_api_timeout,
            get_search_timeout
        )
    except (ImportError, ModuleNotFoundError):
        from .core.timeout_manager import (
            with_api_timeout_and_retries,
            with_search_timeout_and_retries,
            get_api_timeout,
            get_search_timeout
        )


class Throttler:
    """Simple rate limiter for API requests"""
    
    def __init__(self, rate_limit: int, period: int = 60):
        self.rate_limit = rate_limit
        self.period = period
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self._lock:
            now = time.time()
            # Remove requests older than the period
            self.requests = [req_time for req_time in self.requests if now - req_time < self.period]
            
            # If we're at the rate limit, wait
            if len(self.requests) >= self.rate_limit:
                sleep_time = self.period - (now - self.requests[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    self.requests = self.requests[1:]  # Remove the oldest request
            
            # Record this request
            self.requests.append(now)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Enhanced data structures and metrics tracking

@dataclass
class SearchResult:
    """Enhanced search result with quality metrics"""
    url: str
    title: str
    snippet: str
    relevance_score: float
    source_type: str
    content: str = ""  # Full content or longer description
    date_published: Optional[str] = None
    authority_score: float = 0.5
    content_quality: float = 0.5
    language: str = "en"

@dataclass
class SubQuestion:
    """Enhanced sub-question with metadata"""
    id: int
    question: str
    priority: int
    search_terms: List[str]
    estimated_complexity: float = 1.0
    category: str = "general"

@dataclass
class ResearchPlan:
    """Enhanced research plan"""
    main_query: str
    sub_questions: List[SubQuestion]
    research_strategy: str
    estimated_complexity: int
    estimated_duration: float = 0.0
    categories: List[str] = field(default_factory=list)

@dataclass 
class RetrievalFindings:
    """Enhanced findings with metrics"""
    sub_question_id: int
    query_used: str
    results: List[SearchResult]
    key_insights: List[str]
    extracted_facts: List[str]
    confidence_score: float = 0.0
    processing_time: float = 0.0
    sources_count: int = 0

@dataclass
class Summary:
    """Enhanced summary with metadata"""
    sub_question_id: int
    question: str
    answer: str
    key_points: List[str]
    sources: List[str]
    confidence_level: float
    word_count: int = 0
    processing_time: float = 0.0

@dataclass
class FinalReport:
    """Comprehensive final report"""
    original_query: str
    executive_summary: str
    detailed_findings: List[Summary]
    methodology: str
    limitations: List[str]
    recommendations: List[str]
    sources_cited: List[str]
    completion_timestamp: str
    quality_score: float
    processing_time: float = 0.0
    total_sources: int = 0
    total_words: int = 0
    research_categories: List[str] = field(default_factory=list)

@dataclass
class QualityAssessment:
    """Comprehensive quality assessment from LLM evaluation"""
    overall_confidence: float
    relevance_score: float
    authority_score: float
    completeness_score: float
    recency_score: float
    consistency_score: float
    quality_feedback: List[str]
    improvement_suggestions: List[str]
    assessment_reasoning: str

@dataclass
class FilteringDecision:
    """Result of adaptive source filtering analysis"""
    filtered_results: List[SearchResult]
    original_count: int
    filtered_count: int
    kept_count: int
    filtering_strategy: str
    quality_distribution: Dict[str, float]
    reasoning: List[str]
    topic_classification: str
    confidence_boost: float = 0.0

# Enhanced metrics tracking structures
@dataclass
class APIMetrics:
    """Detailed metrics for individual API calls"""
    call_id: str
    agent_name: str
    operation: str
    model_used: str
    start_time: float
    end_time: float
    duration: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0
    cache_hit: bool = False
    retry_count: int = 0
    success: bool = True
    error_message: Optional[str] = None
    response_size: int = 0
    rate_limited: bool = False

@dataclass
class StepMetrics:
    """Metrics for individual pipeline steps"""
    step_name: str
    agent_name: str
    start_time: float
    end_time: float
    duration: float
    api_calls: List[APIMetrics] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    cache_hits: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True

@dataclass
class PipelineMetrics:
    """Comprehensive metrics for the entire research pipeline"""
    session_id: str
    query: str
    start_time: float
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    steps: List[StepMetrics] = field(default_factory=list)
    total_api_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_cache_hits: int = 0
    errors: List[str] = field(default_factory=list)
    model_usage: Dict[str, int] = field(default_factory=dict)
    agent_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    success: bool = True

class MetricsCollector:
    """Centralized metrics collection and analysis"""
    
    def __init__(self):
        self.current_pipeline: Optional[PipelineMetrics] = None
        self.current_step: Optional[StepMetrics] = None
        self.api_call_counter = 0
        self.current_sources: List[Dict[str, Any]] = []  # Store current sources for web UI
        self.quality_evaluations: List[Dict[str, Any]] = []  # Store quality evaluations for web UI
        self.source_filtering_data: Optional[Dict[str, Any]] = None  # Store source filtering data for web UI
        self.summaries: List[Dict[str, Any]] = []  # Store summaries for web UI
        self.final_report: Optional[Dict[str, Any]] = None  # Store final report for web UI
    
    def start_pipeline(self, session_id: str, query: str) -> PipelineMetrics:
        """Start tracking a new research pipeline"""
        self.current_pipeline = PipelineMetrics(
            session_id=session_id,
            query=query,
            start_time=time.time()
        )
        # Clear previous data when starting a new pipeline
        self.current_sources = []
        self.quality_evaluations = []
        self.source_filtering_data = None
        self.summaries = []
        self.final_report = None
        return self.current_pipeline
    
    def start_step(self, step_name: str, agent_name: str) -> StepMetrics:
        """Start tracking a pipeline step"""
        self.current_step = StepMetrics(
            step_name=step_name,
            agent_name=agent_name,
            start_time=time.time(),
            end_time=0,
            duration=0
        )
        return self.current_step
    
    def end_step(self, success: bool = True, error: Optional[str] = None) -> Optional[StepMetrics]:
        """End the current step and add to pipeline"""
        if not self.current_step or not self.current_pipeline:
            return None
            
        self.current_step.end_time = time.time()
        self.current_step.duration = self.current_step.end_time - self.current_step.start_time
        self.current_step.success = success
        
        if error:
            self.current_step.errors.append(error)
            self.current_pipeline.errors.append(f"{self.current_step.step_name}: {error}")
        
        # Calculate step totals
        self.current_step.total_tokens = sum(call.total_tokens for call in self.current_step.api_calls)
        self.current_step.total_cost = sum(call.cost_estimate for call in self.current_step.api_calls)
        self.current_step.cache_hits = sum(1 for call in self.current_step.api_calls if call.cache_hit)
        
        # Add to pipeline
        self.current_pipeline.steps.append(self.current_step)
        completed_step = self.current_step
        self.current_step = None
        
        return completed_step
    
    def record_api_call(self, agent_name: str, operation: str, model: str, 
                       start_time: float, end_time: float, usage: Dict[str, Any],
                       cache_hit: bool = False, retry_count: int = 0, 
                       success: bool = True, error: Optional[str] = None,
                       response_size: int = 0) -> APIMetrics:
        """Record detailed API call metrics"""
        self.api_call_counter += 1
        
        # Debug logging
        print(f"🔧 DEBUG record_api_call: Agent={agent_name}, Operation={operation}")
        print(f"   Pipeline exists: {self.current_pipeline is not None}")
        if self.current_pipeline:
            print(f"   API calls before increment: {self.current_pipeline.total_api_calls}")
        else:
            print("   WARNING: No current pipeline to record API call!")
        
        # Calculate cost estimate (rough estimates for Fireworks)
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
        
        # Get pricing from centralized module with fallback handling
        try:
            from backend.pricing import get_model_cost
        except (ImportError, ModuleNotFoundError):
            try:
                from pricing import get_model_cost
            except (ImportError, ModuleNotFoundError):
                from .pricing import get_model_cost
        costs = get_model_cost(model)
        
        cost_estimate = (
            (prompt_tokens * costs["input"] / 1_000_000) +
            (completion_tokens * costs["output"] / 1_000_000)
        )
        
        metrics = APIMetrics(
            call_id=f"api_{self.api_call_counter}_{int(time.time())}",
            agent_name=agent_name,
            operation=operation,
            model_used=model,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_estimate=cost_estimate,
            cache_hit=cache_hit,
            retry_count=retry_count,
            success=success,
            error_message=error,
            response_size=response_size
        )
        
        # Add to current step if active
        if self.current_step:
            self.current_step.api_calls.append(metrics)
        
        # Update pipeline totals
        if self.current_pipeline:
            self.current_pipeline.total_api_calls += 1
            self.current_pipeline.total_tokens += total_tokens
            self.current_pipeline.total_cost += cost_estimate
            if cache_hit:
                self.current_pipeline.total_cache_hits += 1
            
            # Debug logging after increment
            print(f"   API calls after increment: {self.current_pipeline.total_api_calls}")
            print(f"   Total tokens: {self.current_pipeline.total_tokens}")
            print(f"   Total cost: {self.current_pipeline.total_cost}")
            
            # Track model usage
            if model not in self.current_pipeline.model_usage:
                self.current_pipeline.model_usage[model] = 0
            self.current_pipeline.model_usage[model] += 1
            
            # Track agent performance
            if agent_name not in self.current_pipeline.agent_performance:
                self.current_pipeline.agent_performance[agent_name] = {
                    "total_calls": 0, "total_tokens": 0, "total_duration": 0.0, "avg_duration": 0.0
                }
            
            agent_perf = self.current_pipeline.agent_performance[agent_name]
            agent_perf["total_calls"] += 1
            agent_perf["total_tokens"] += total_tokens
            agent_perf["total_duration"] += metrics.duration
            agent_perf["avg_duration"] = agent_perf["total_duration"] / agent_perf["total_calls"]
        
        return metrics
    
    def end_pipeline(self, success: bool = True) -> Optional[PipelineMetrics]:
        """End the current pipeline and calculate final metrics"""
        if not self.current_pipeline:
            return None
            
        self.current_pipeline.end_time = time.time()
        self.current_pipeline.total_duration = (
            self.current_pipeline.end_time - self.current_pipeline.start_time
        )
        self.current_pipeline.success = success
        
        completed_pipeline = self.current_pipeline
        self.current_pipeline = None
        self.current_step = None
        
        return completed_pipeline
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current pipeline metrics"""
        if not self.current_pipeline:
            return {}
        
        return {
            "session_id": self.current_pipeline.session_id,
            "query": self.current_pipeline.query,
            "elapsed_time": time.time() - self.current_pipeline.start_time,
            "total_api_calls": self.current_pipeline.total_api_calls,
            "total_tokens": self.current_pipeline.total_tokens,
            "estimated_cost": self.current_pipeline.total_cost,
            "cache_hits": self.current_pipeline.total_cache_hits,
            "steps_completed": len(self.current_pipeline.steps),
            "current_step": self.current_step.step_name if self.current_step else None,
            "model_usage": self.current_pipeline.model_usage,
            "agent_performance": self.current_pipeline.agent_performance,
            "current_sources": self.current_sources
        }
    
    def update_sources(self, sources: List[SearchResult]):
        """Update the current sources for web UI display (accumulates sources from all sub-questions)"""
        # Create new source data
        new_sources = [
            {
                "url": source.url,
                "title": source.title,
                "snippet": source.snippet,
                "content": source.content,  # Include the full content field
                "source_type": source.source_type,
                "authority_score": source.authority_score,
                "relevance_score": source.relevance_score,
                "date_published": source.date_published
            }
            for source in sources
        ]
        
        # Accumulate sources (avoiding duplicates by URL)
        existing_urls = {source["url"] for source in self.current_sources}
        
        for source in new_sources:
            if source["url"] not in existing_urls:
                self.current_sources.append(source)
                existing_urls.add(source["url"])
    
    def update_source_filtering(self, filtering_decision: 'FilteringDecision', original_sources: List[SearchResult]):
        """Update source filtering data for web UI display (accumulates data from all sub-questions)"""
        # Convert accepted sources
        accepted_sources = []
        for source in filtering_decision.filtered_results:
            source_data = {
                "title": source.title,
                "url": source.url,
                "snippet": source.snippet,
                "content": source.content,
                "relevance_score": source.relevance_score,
                "authority_score": source.authority_score,
                "content_quality": source.content_quality,
                "source_type": source.source_type,
                "date_published": source.date_published,
                "language": source.language
            }
            accepted_sources.append(source_data)
        
        # Calculate rejected sources
        accepted_urls = {source.url for source in filtering_decision.filtered_results}
        rejected_sources = []
        for source in original_sources:
            if source.url not in accepted_urls:
                # Add rejection information
                source_data = {
                    "title": source.title,
                    "url": source.url,
                    "snippet": source.snippet,
                    "content": source.content,
                    "relevance_score": source.relevance_score,
                    "authority_score": source.authority_score,
                    "content_quality": source.content_quality,
                    "source_type": source.source_type,
                    "date_published": source.date_published,
                    "language": source.language,
                    "rejection_reasons": self._determine_rejection_reasons(source, filtering_decision),
                    "rejection_explanation": self._generate_rejection_explanation(source, filtering_decision)
                }
                rejected_sources.append(source_data)
        
        # Initialize source_filtering_data if not already present
        if self.source_filtering_data is None:
            self.source_filtering_data = {
                "accepted_sources": [],
                "rejected_sources": [],
                "filtering_summary": {
                    "original_count": 0,
                    "kept_count": 0,
                    "filtered_count": 0,
                    "strategy": filtering_decision.filtering_strategy,
                    "topic_classification": filtering_decision.topic_classification,
                    "confidence_boost": 0.0,
                    "reasoning": [],
                    "quality_distribution": {}
                }
            }
        
        # Accumulate accepted and rejected sources (avoiding duplicates by URL)
        existing_accepted_urls = {source["url"] for source in self.source_filtering_data["accepted_sources"]}
        existing_rejected_urls = {source["url"] for source in self.source_filtering_data["rejected_sources"]}
        
        for source in accepted_sources:
            if source["url"] not in existing_accepted_urls:
                self.source_filtering_data["accepted_sources"].append(source)
                existing_accepted_urls.add(source["url"])
        
        for source in rejected_sources:
            if source["url"] not in existing_rejected_urls:
                self.source_filtering_data["rejected_sources"].append(source)
                existing_rejected_urls.add(source["url"])
        
        # Accumulate filtering summary stats
        summary = self.source_filtering_data["filtering_summary"]
        summary["original_count"] += filtering_decision.original_count
        summary["kept_count"] += filtering_decision.kept_count
        summary["filtered_count"] += filtering_decision.filtered_count
        
        # Update strategy and topic classification (use the most recent)
        summary["strategy"] = filtering_decision.filtering_strategy
        summary["topic_classification"] = filtering_decision.topic_classification
        
        # Average the confidence boost
        if summary["confidence_boost"] == 0.0:
            summary["confidence_boost"] = filtering_decision.confidence_boost
        else:
            summary["confidence_boost"] = (summary["confidence_boost"] + filtering_decision.confidence_boost) / 2
        
        # Accumulate reasoning (limit to prevent overwhelming the UI)
        for reason in filtering_decision.reasoning:
            if reason not in summary["reasoning"] and len(summary["reasoning"]) < 10:
                summary["reasoning"].append(reason)
        
        # Merge quality distribution (use average where applicable)
        for key, value in filtering_decision.quality_distribution.items():
            if key in summary["quality_distribution"]:
                # Average numerical values
                if isinstance(value, (int, float)) and isinstance(summary["quality_distribution"][key], (int, float)):
                    summary["quality_distribution"][key] = (summary["quality_distribution"][key] + value) / 2
                else:
                    summary["quality_distribution"][key] = value
            else:
                summary["quality_distribution"][key] = value
    
    def _determine_rejection_reasons(self, source: SearchResult, filtering_decision: 'FilteringDecision') -> List[str]:
        """Determine why a source was rejected based on filtering criteria"""
        reasons = []
        
        # Use the actual thresholds from the filtering decision
        thresholds = filtering_decision.quality_distribution.get('thresholds', {
            'authority': 0.3, 'relevance': 0.3, 'content_quality': 0.2
        })
        
        if source.authority_score and source.authority_score < thresholds.get('authority', 0.3):
            reasons.append("low_authority")
        if source.relevance_score and source.relevance_score < thresholds.get('relevance', 0.3):
            reasons.append("low_relevance")
        if source.content_quality and source.content_quality < thresholds.get('content_quality', 0.2):
            reasons.append("low_quality")
        
        # Overall quality check
        if source.authority_score and source.relevance_score and source.content_quality:
            overall = (source.authority_score + source.relevance_score + source.content_quality) / 3
            if overall < 0.35:
                reasons.append("overall_quality")
        
        return reasons if reasons else ["filtering_criteria"]
    
    def _generate_rejection_explanation(self, source: SearchResult, filtering_decision: 'FilteringDecision') -> str:
        """Generate human-readable explanation for why source was rejected"""
        strategy = filtering_decision.filtering_strategy
        
        authority = source.authority_score or 0.5
        relevance = source.relevance_score or 0.5
        quality = source.content_quality or 0.5
        
        if authority < 0.3:
            return f"Source authority score ({authority:.1%}) below {strategy} filtering threshold. Domain may lack credibility indicators."
        elif relevance < 0.3:
            return f"Content relevance score ({relevance:.1%}) too low for query. Source may not contain pertinent information."
        elif quality < 0.2:
            return f"Content quality score ({quality:.1%}) insufficient. May lack depth or contain low-value content."
        else:
            overall = (authority + relevance + quality) / 3
            return f"Overall quality score ({overall:.1%}) below {strategy} filtering standards. Combined metrics indicate limited value for research."
    

    
    def update_quality_evaluations(self, quality_evaluations: List[QualityAssessment], sub_questions: List[SubQuestion], findings: List[RetrievalFindings]):
        """Update quality evaluations for web UI display"""
        self.quality_evaluations = []
        
        for i, quality_eval in enumerate(quality_evaluations):
            if quality_eval is not None and i < len(sub_questions) and i < len(findings):
                sub_question = sub_questions[i]
                finding = findings[i]
                
                # Create detailed quality evaluation data for UI
                eval_data = {
                    "sub_question_id": sub_question.id,
                    "sub_question": sub_question.question,
                    "overall_confidence": quality_eval.overall_confidence,
                    "relevance_score": quality_eval.relevance_score,
                    "authority_score": quality_eval.authority_score,
                    "completeness_score": quality_eval.completeness_score,
                    "recency_score": quality_eval.recency_score,
                    "consistency_score": quality_eval.consistency_score,
                    "quality_feedback": quality_eval.quality_feedback,
                    "improvement_suggestions": quality_eval.improvement_suggestions,
                    "assessment_reasoning": quality_eval.assessment_reasoning,
                    "sources_evaluated": len(finding.results) if hasattr(finding, 'results') else 0,
                    "insights_found": len(finding.key_insights) if hasattr(finding, 'key_insights') else 0,
                    "facts_extracted": len(finding.extracted_facts) if hasattr(finding, 'extracted_facts') else 0,
                    "pass_fail_status": "PASS" if quality_eval.overall_confidence >= 0.6 else "FAIL",
                    "quality_grade": self._get_quality_grade(quality_eval.overall_confidence),
                    "source_breakdown": [
                        {
                            "url": result.url,
                            "title": result.title,
                            "authority_score": result.authority_score,
                            "relevance_score": result.relevance_score,
                            "source_type": result.source_type,
                            "date_published": result.date_published,
                            "passed_quality": self._simple_quality_check(result)
                        }
                        for result in finding.results[:10]  # Limit to top 10 sources for UI
                    ] if hasattr(finding, 'results') else []
                }
                
                self.quality_evaluations.append(eval_data)
    
    def _get_quality_grade(self, confidence: float) -> str:
        """Convert confidence score to letter grade"""
        if confidence >= 0.9:
            return "A+"
        elif confidence >= 0.8:
            return "A"
        elif confidence >= 0.7:
            return "B+"
        elif confidence >= 0.6:
            return "B"
        elif confidence >= 0.5:
            return "C+"
        elif confidence >= 0.4:
            return "C"
        elif confidence >= 0.3:
            return "D"
        else:
            return "F"
    
    def _simple_quality_check(self, result: SearchResult) -> bool:
        """Simple quality evaluation for metrics collection using unified assessor"""
        try:
            from core.quality_assessor import UnifiedQualityAssessor, AssessmentRequest, AssessmentMode
            
            # Create a temporary quality assessor instance
            assessor = UnifiedQualityAssessor()
            
            # Create assessment request
            request = AssessmentRequest(
                results=[result],
                sub_question=None,
                mode=AssessmentMode.ALGORITHMIC_FAST
            )
            
            # Get quality metrics
            quality_metrics = assessor._algorithmic_fast_assessment(request)
            
            # Use composite score similar to original logic
            composite_score = (quality_metrics.authority_score * 0.4 + 
                             quality_metrics.relevance_score * 0.4 + 
                             quality_metrics.content_quality * 0.2)
            
            # Pass if composite score is decent (55%) OR if high authority with some relevance
            return (composite_score >= 0.55 or 
                    (quality_metrics.authority_score >= 0.8 and quality_metrics.relevance_score >= 0.2) or
                    (quality_metrics.relevance_score >= 0.7 and quality_metrics.authority_score >= 0.3))
            
        except Exception:
            # Fallback to original simple logic
            authority_score = result.authority_score or 0.5
            relevance_score = result.relevance_score or 0.5
            content_quality = result.content_quality or 0.5
            
            composite_score = authority_score * 0.4 + relevance_score * 0.4 + content_quality * 0.2
            
            return (composite_score >= 0.55 or 
                    (authority_score >= 0.8 and relevance_score >= 0.2) or
                    (relevance_score >= 0.7 and authority_score >= 0.3))
    
    def update_summaries(self, summaries: List['Summary']):
        """Update summaries for web UI display (accumulates summaries from all sub-questions)"""
        # Get existing summary IDs to avoid duplicates
        existing_summary_ids = {summary["sub_question_id"] for summary in self.summaries}
        
        for summary in summaries:
            # Only add if we don't already have a summary for this sub-question
            if summary.sub_question_id not in existing_summary_ids:
                summary_data = {
                    "sub_question_id": summary.sub_question_id,
                    "question": summary.question,
                    "answer": summary.answer,
                    "key_points": summary.key_points,
                    "sources": summary.sources,
                    "confidence_level": summary.confidence_level,
                    "word_count": summary.word_count,
                    "processing_time": summary.processing_time,
                    "confidence_grade": self._get_quality_grade(summary.confidence_level)
                }
                self.summaries.append(summary_data)
                existing_summary_ids.add(summary.sub_question_id)
    
    def update_final_report(self, final_report: 'FinalReport'):
        """Update final report for web UI display"""
        from dataclasses import asdict
        self.final_report = asdict(final_report)

# Create a global metrics_collector instance for backward compatibility
metrics_collector = MetricsCollector()

class MetricsFormatter:
    """Format metrics for display in CLI and web UI"""
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
    
    @staticmethod
    def format_cost(cost: float) -> str:
        """Format cost in USD"""
        return f"${cost:.4f}"
    
    @staticmethod
    def format_tokens(tokens: int) -> str:
        """Format token count with K/M suffixes"""
        if tokens < 1000:
            return str(tokens)
        elif tokens < 1000000:
            return f"{tokens/1000:.1f}K"
        else:
            return f"{tokens/1000000:.1f}M"
    
    @staticmethod
    def get_step_summary(step: StepMetrics) -> Dict[str, Any]:
        """Get a summary of step metrics"""
        # Determine the model used in this step from API calls
        model_used = "N/A"
        if step.api_calls:
            # Get the most commonly used model in this step (in case multiple models are used)
            model_usage = {}
            for call in step.api_calls:
                model_name = call.model_used.split('/')[-1] if '/' in call.model_used else call.model_used
                model_usage[model_name] = model_usage.get(model_name, 0) + 1
            
            # Use the most frequently used model
            if model_usage:
                model_used = max(model_usage.items(), key=lambda x: x[1])[0]
        
        return {
            "step_name": step.step_name,
            "agent": step.agent_name,
            "model_used": model_used,  # Include the model used for this step
            "duration": MetricsFormatter.format_duration(step.duration),
            "duration_raw": step.duration,
            "api_calls": len(step.api_calls),
            "total_tokens": MetricsFormatter.format_tokens(step.total_tokens),
            "total_tokens_raw": step.total_tokens,
            "cost": MetricsFormatter.format_cost(step.total_cost),
            "cost_raw": step.total_cost,
            "cache_hits": step.cache_hits,
            "success": step.success,
            "errors": step.errors
        }
    
    @staticmethod
    def get_api_call_summary(call: APIMetrics) -> Dict[str, Any]:
        """Get a summary of API call metrics"""
        return {
            "call_id": call.call_id,
            "agent": call.agent_name,
            "operation": call.operation,
            "model": call.model_used.split('/')[-1] if '/' in call.model_used else call.model_used,
            "duration": MetricsFormatter.format_duration(call.duration),
            "duration_raw": call.duration,
            "prompt_tokens": call.prompt_tokens,
            "completion_tokens": call.completion_tokens,
            "total_tokens": MetricsFormatter.format_tokens(call.total_tokens),
            "total_tokens_raw": call.total_tokens,
            "cost": MetricsFormatter.format_cost(call.cost_estimate),
            "cost_raw": call.cost_estimate,
            "cache_hit": call.cache_hit,
            "retry_count": call.retry_count,
            "success": call.success,
            "error": call.error_message,
            "response_size": f"{call.response_size} bytes" if call.response_size else "N/A"
        }
    
    @staticmethod
    def get_pipeline_summary(pipeline: PipelineMetrics) -> Dict[str, Any]:
        """Get a comprehensive pipeline summary"""
        return {
            "session_id": pipeline.session_id,
            "query": pipeline.query,
            "total_duration": MetricsFormatter.format_duration(pipeline.total_duration or 0),
            "total_duration_raw": pipeline.total_duration or 0,
            "steps_completed": len(pipeline.steps),
            "total_api_calls": pipeline.total_api_calls,
            "total_tokens": MetricsFormatter.format_tokens(pipeline.total_tokens),
            "total_tokens_raw": pipeline.total_tokens,
            "total_cost": MetricsFormatter.format_cost(pipeline.total_cost),
            "total_cost_raw": pipeline.total_cost,
            "cache_hits": pipeline.total_cache_hits,
            "cache_hit_rate": f"{(pipeline.total_cache_hits / max(pipeline.total_api_calls, 1)) * 100:.1f}%",
            "success": pipeline.success,
            "errors": pipeline.errors,
            "model_usage": pipeline.model_usage,
            "agent_performance": pipeline.agent_performance,
            "steps": [MetricsFormatter.get_step_summary(step) for step in pipeline.steps]
        }
    
    @staticmethod
    def format_cli_summary(pipeline: PipelineMetrics) -> str:
        """Format metrics for CLI display"""
        summary = MetricsFormatter.get_pipeline_summary(pipeline)
        
        output = []
        output.append("=" * 80)
        output.append("RESEARCH PIPELINE METRICS")
        output.append("=" * 80)
        output.append(f"Query: {summary['query']}")
        output.append(f"Session ID: {summary['session_id']}")
        output.append(f"Total Duration: {summary['total_duration']}")
        output.append(f"Success: {'Yes' if summary['success'] else 'No'}")
        output.append("")
        
        # Overall stats
        output.append("OVERALL STATISTICS")
        output.append("-" * 40)
        output.append(f"Steps Completed: {summary['steps_completed']}")
        output.append(f"Total API Calls: {summary['total_api_calls']}")
        output.append(f"Total Tokens: {summary['total_tokens']}")
        output.append(f"Total Cost: {summary['total_cost']}")
        output.append(f"Cache Hits: {summary['cache_hits']} ({summary['cache_hit_rate']})")
        output.append("")
        
        # Model usage
        if summary['model_usage']:
            output.append("🤖 MODEL USAGE")
            output.append("-" * 40)
            for model, count in summary['model_usage'].items():
                model_name = model.split('/')[-1] if '/' in model else model
                output.append(f"{model_name}: {count} calls")
            output.append("")
        
        # Agent performance
        if summary['agent_performance']:
            output.append("👥 AGENT PERFORMANCE")
            output.append("-" * 40)
            for agent, perf in summary['agent_performance'].items():
                output.append(f"{agent}:")
                output.append(f"  Calls: {perf['total_calls']}")
                output.append(f"  Tokens: {MetricsFormatter.format_tokens(perf['total_tokens'])}")
                output.append(f"  Avg Duration: {MetricsFormatter.format_duration(perf['avg_duration'])}")
            output.append("")
        
        # Step breakdown
        output.append("⏱️ STEP BREAKDOWN")
        output.append("-" * 80)
        output.append(f"{'Step':<25} {'Agent':<20} {'Duration':<12} {'Tokens':<10} {'Cost':<10} {'Calls':<6}")
        output.append("-" * 80)
        
        for step_summary in summary['steps']:
            output.append(f"{step_summary['step_name']:<25} "
                         f"{step_summary['agent']:<20} "
                         f"{step_summary['duration']:<12} "
                         f"{step_summary['total_tokens']:<10} "
                         f"{step_summary['cost']:<10} "
                         f"{step_summary['api_calls']:<6}")
        
        output.append("=" * 80)
        
        return "\n".join(output)
    
    @staticmethod
    def format_web_summary(pipeline: PipelineMetrics) -> Dict[str, Any]:
        """Format metrics for web UI display"""
        summary = MetricsFormatter.get_pipeline_summary(pipeline)
        
        # Add detailed step information with token breakdown
        detailed_steps = []
        for step in pipeline.steps:
            # Calculate step-level token breakdown from API calls
            step_prompt_tokens = sum(call.prompt_tokens for call in step.api_calls)
            step_completion_tokens = sum(call.completion_tokens for call in step.api_calls)
            
            step_summary = MetricsFormatter.get_step_summary(step)
            step_summary.update({
                "prompt_tokens": step_prompt_tokens,
                "completion_tokens": step_completion_tokens,
                "tokens_per_second": round(step.total_tokens / max(step.duration, 0.1), 1) if step.duration > 0 else 0
            })
            detailed_steps.append(step_summary)
        
        summary["steps"] = detailed_steps
        
        # Add detailed API call information
        all_api_calls = []
        for step in pipeline.steps:
            for call in step.api_calls:
                call_summary = MetricsFormatter.get_api_call_summary(call)
                call_summary["step_name"] = step.step_name
                all_api_calls.append(call_summary)
        
        summary["api_calls_detail"] = all_api_calls
        
        # Add performance insights
        if pipeline.steps:
            slowest_step = max(pipeline.steps, key=lambda s: s.duration)
            most_expensive_step = max(pipeline.steps, key=lambda s: s.total_cost)
            
            summary["insights"] = {
                "slowest_step": {
                    "name": slowest_step.step_name,
                    "duration": MetricsFormatter.format_duration(slowest_step.duration),
                    "agent": slowest_step.agent_name
                },
                "most_expensive_step": {
                    "name": most_expensive_step.step_name,
                    "cost": MetricsFormatter.format_cost(most_expensive_step.total_cost),
                    "agent": most_expensive_step.agent_name
                },
                "efficiency_score": min(100, max(0, 100 - (pipeline.total_duration or 0) * 2)),
                "cost_efficiency": "high" if pipeline.total_cost < 0.01 else "medium" if pipeline.total_cost < 0.05 else "low"
            }
        
        return summary




# Circuit breakers are defined above near imports


class ResourceManager:
    """Enhanced HTTP resource management"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
        self.throttler = Throttler(rate_limit=settings.requests_per_minute, period=60)
        self.logger = structlog.get_logger(__name__)
    
    async def __aenter__(self):
        timeout = get_api_timeout()
        connector = aiohttp.TCPConnector(
            limit=self.settings.max_concurrent_requests,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "ResearchSystem/2.0"}
        )
        self.logger.info("Resource manager initialized")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.logger.info("Resource manager closed")
    
    async def throttled_request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make throttled HTTP request with error handling"""
        async with self.throttler:
            if not self.session:
                raise RuntimeError("ResourceManager not initialized")
            
            try:
                response = await self.session.request(method, url, **kwargs)
                return response
            except aiohttp.ClientError as e:
                self.logger.error("HTTP request failed", method=method, url=url, error=str(e))
                raise


class ModelManager:
    """Manages model selection, cost tracking, and performance optimization"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger("ModelManager")
        
        # Cost tracking
        self.current_query_cost = 0.0
        self.agent_costs = {}
        
        # Import centralized pricing with fallback handling
        try:
            from backend.pricing import MODEL_COSTS
        except (ImportError, ModuleNotFoundError):
            try:
                from pricing import MODEL_COSTS
            except (ImportError, ModuleNotFoundError):
                from .pricing import MODEL_COSTS
        self.model_costs = MODEL_COSTS
        
        # Cost-optimized alternatives
        self.cost_alternatives = {
            "llama-v3p1-405b-instruct": "llama-v3p3-70b-instruct",
            "llama-v3p3-70b-instruct": "llama-v3p1-8b-instruct",
            "deepseek-r1-0528": "deepseek-v3",
            "deepseek-r1": "deepseek-v3"
        }
    
    def get_model_config(self, agent_type: str) -> dict:
        """Get model configuration for a specific agent type"""
        
        # Get base config from settings
        base_config = self.settings.agent_models.get(agent_type, {
            "model": self.settings.fireworks_model,
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "description": f"Default config for {agent_type}"
        })
        
        # Apply model selection strategy
        if self.settings.model_selection_strategy == "single":
            # Use default model for all agents
            return {
                "model": self.settings.fireworks_model,
                "max_tokens": self.settings.max_tokens,
                "temperature": self.settings.temperature,
                "description": "Single model strategy"
            }
        
        elif self.settings.model_selection_strategy == "cost_optimized":
            # Use cheaper alternatives if available
            original_model = base_config["model"]
            model_key = original_model.split('/')[-1] if '/' in original_model else original_model
            
            if model_key in self.cost_alternatives:
                alternative = self.cost_alternatives[model_key]
                base_config["model"] = f"accounts/fireworks/models/{alternative}"
                self.logger.info("Using cost-optimized model", 
                               original=model_key, 
                               alternative=alternative,
                               agent_type=agent_type)
        
        elif self.settings.model_selection_strategy == "performance_optimized":
            # Use the best available models
            performance_upgrades = {
                "web_search": "llama-v3p3-70b-instruct",
                "research_planner": "llama-v3p1-405b-instruct",
                "quality_evaluation": "llama-v3p1-405b-instruct",
                "summarization": "llama-v3p1-405b-instruct",
                "report_synthesis": "llama-v3p1-405b-instruct"
            }
            
            if agent_type in performance_upgrades:
                base_config["model"] = f"accounts/fireworks/models/{performance_upgrades[agent_type]}"
                self.logger.info("Using performance-optimized model", 
                               model=performance_upgrades[agent_type],
                               agent_type=agent_type)
        
        # Check cost budget before finalizing
        if self._would_exceed_budget(base_config["model"], base_config["max_tokens"]):
            fallback_model = "accounts/fireworks/models/llama-v3p1-8b-instruct"
            self.logger.warning("Model would exceed budget, using fallback", 
                              original=base_config["model"],
                              fallback=fallback_model,
                              current_cost=self.current_query_cost,
                              max_cost=self.settings.max_cost_per_query)
            base_config["model"] = fallback_model
            base_config["max_tokens"] = min(base_config["max_tokens"], 600)
        
        return base_config
    
    def calculate_estimated_cost(self, model: str, prompt_tokens: int, max_tokens: int) -> float:
        """Calculate estimated cost for a model call"""
        model_key = model.split('/')[-1] if '/' in model else model
        costs = self.model_costs.get(model_key, {"input": 0.5, "output": 0.5})
        
        # Estimate completion tokens (typically 20-50% of max_tokens)
        estimated_completion_tokens = min(max_tokens * 0.3, max_tokens)
        
        cost = (
            (prompt_tokens * costs["input"] / 1_000_000) +
            (estimated_completion_tokens * costs["output"] / 1_000_000)
        )
        
        return cost
    
    def _would_exceed_budget(self, model: str, max_tokens: int) -> bool:
        """Check if using this model would exceed the query budget"""
        estimated_cost = self.calculate_estimated_cost(model, 1000, max_tokens)  # Assume 1k prompt tokens
        return (self.current_query_cost + estimated_cost) > self.settings.max_cost_per_query
    
    def record_usage(self, agent_type: str, model: str, usage: dict, cost: float):
        """Record model usage and cost for tracking"""
        self.current_query_cost += cost
        
        if agent_type not in self.agent_costs:
            self.agent_costs[agent_type] = {
                "total_cost": 0.0,
                "total_tokens": 0,
                "call_count": 0,
                "models_used": set()
            }
        
        self.agent_costs[agent_type]["total_cost"] += cost
        self.agent_costs[agent_type]["total_tokens"] += usage.get("total_tokens", 0)
        self.agent_costs[agent_type]["call_count"] += 1
        self.agent_costs[agent_type]["models_used"].add(model.split('/')[-1])
    
    def get_cost_summary(self) -> dict:
        """Get cost summary for the current query"""
        return {
            "total_cost": self.current_query_cost,
            "total_tokens": sum(agent["total_tokens"] for agent in self.agent_costs.values()),
            "agent_costs": {
                agent: {
                    "model": list(data["models_used"])[0] if data["models_used"] else "unknown",
                    "total_cost": data["total_cost"],
                    "total_tokens": data["total_tokens"],
                    "call_count": data["call_count"]
                }
                for agent, data in self.agent_costs.items()
            }
        }
    
    def reset_query_tracking(self):
        """Reset tracking for a new query"""
        self.current_query_cost = 0.0
        self.agent_costs = {}


class DatabaseManager:
    """Enhanced database management with session persistence"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(__name__)
    
    def initialize(self):
        """Initialize database with enhanced schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_sessions (
                    session_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data BLOB,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    step_name TEXT,
                    result_data BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES research_sessions (session_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON research_sessions(status);
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_session ON research_results(session_id);
            """)
            
            conn.commit()
            self.logger.info("Database initialized", db_path=str(self.db_path))
    
    def save_session(self, session_id: str, query: str, status: str, 
                    data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Save research session with metadata"""
        serialized_data = pickle.dumps(data)
        metadata_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO research_sessions 
                (session_id, query, status, updated_at, data, metadata)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """, (session_id, query, status, serialized_data, metadata_json))
            conn.commit()
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load research session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT data, metadata FROM research_sessions 
                WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            if row:
                data = pickle.loads(row[0])
                metadata = json.loads(row[1] or '{}')
                return {"data": data, "metadata": metadata}
        return None
    
    def save_result(self, session_id: str, step_name: str, result_data: Any):
        """Save intermediate research result"""
        serialized_data = pickle.dumps(result_data)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO research_results 
                (session_id, step_name, result_data)
                VALUES (?, ?, ?)
            """, (session_id, step_name, serialized_data))
            conn.commit()
            
        self.logger.debug("Saved research result", 
                         session_id=session_id, 
                         step=step_name)


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
            from core.error_handler import StandardErrorHandler, ErrorContext, ErrorSeverity, RecoveryStrategy
            context = ErrorContext(
                operation="api_call",
                component=self.name,
                metadata={"operation": operation, "model": actual_model, "duration": end_time - start_time}
            )
            handler = StandardErrorHandler()
            handler.handle_error(e, context, ErrorSeverity.HIGH, RecoveryStrategy.RERAISE)


class AdaptiveSourceFilter:
    """Intelligent source filtering that adapts to research context and available quality"""
    
    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
    
    def filter_sources(self, results: List[SearchResult], sub_question: SubQuestion, 
                      quality_assessment: Optional[QualityAssessment] = None) -> FilteringDecision:
        """
        Intelligently filter sources based on research context and quality
        
        Returns detailed information about what was filtered and why
        """
        
        if not self.settings.enable_source_filtering:
            return self._create_empty_decision("Source filtering disabled in settings")
        
        if not results:
            return self._create_empty_decision("No sources to filter")
        
        original_count = len(results)
        
        # Step 1: Analyze topic context
        topic_analysis = self._analyze_topic_context(sub_question)
        
        # Step 2: Analyze source quality distribution
        quality_analysis = self._analyze_source_quality_distribution(results)
        
        # Step 3: Determine filtering strategy
        strategy = self._determine_filtering_strategy(
            topic_analysis, quality_analysis, original_count, quality_assessment
        )
        
        # Step 4: Calculate adaptive thresholds
        thresholds = self._calculate_adaptive_thresholds(
            quality_analysis, strategy, topic_analysis
        )
        
        # Step 5: Apply filtering with detailed logging
        self.logger.info("Starting adaptive source filtering",
                       original_sources=original_count,
                       topic_classification=topic_analysis["classification"],
                       strategy=strategy,
                       question=sub_question.question[:50] + "..." if len(sub_question.question) > 50 else sub_question.question)
        
        # Log quality distribution before filtering
        self.logger.info("Source quality distribution (before filtering)",
                       avg_authority=f"{quality_analysis['mean_authority']:.3f}",
                       avg_relevance=f"{quality_analysis['mean_relevance']:.3f}",
                       avg_content_quality=f"{quality_analysis['mean_quality']:.3f}",
                       quality_range=f"{quality_analysis.get('p25_authority', 0.0):.3f}-{quality_analysis.get('p75_authority', 1.0):.3f}")
        
        filtered_results = self._apply_adaptive_filtering(results, thresholds, strategy, topic_analysis)
        
        # Apply safety limits to prevent over-filtering
        final_results = self._apply_safety_limits(results, filtered_results, original_count)
        
        # Calculate confidence boost
        confidence_boost = self._calculate_confidence_boost(results, final_results, strategy)
        
        # Generate reasoning
        reasoning = self._generate_filtering_reasoning(
            topic_analysis, quality_analysis, strategy, thresholds, 
            original_count, len(final_results)
        )
        
        # Create decision object
        decision = FilteringDecision(
            filtered_results=final_results,
            original_count=original_count,
            filtered_count=original_count - len(final_results),
            kept_count=len(final_results),
            filtering_strategy=strategy,
            quality_distribution=quality_analysis,
            reasoning=reasoning,
            topic_classification=topic_analysis["classification"],
            confidence_boost=confidence_boost
        )
        
        # Log final filtering summary
        filtering_rate = (decision.filtered_count / original_count * 100) if original_count > 0 else 0
        self.logger.info("Adaptive filtering completed",
                       original_count=original_count,
                       kept_count=decision.kept_count,
                       filtered_count=decision.filtered_count,
                       filtering_rate=f"{filtering_rate:.1f}%",
                       strategy=strategy,
                       confidence_boost=f"+{confidence_boost:.3f}",
                       topic=topic_analysis["classification"])
        
        # Log the top reasons for filtering decisions
        if reasoning:
            self.logger.info("🎯 Key filtering decisions",
                           primary_reason=reasoning[0] if reasoning else "No specific reason",
                           secondary_reason=reasoning[1] if len(reasoning) > 1 else "N/A")
        
        return decision
    
    def _analyze_topic_context(self, sub_question: SubQuestion) -> Dict[str, Any]:
        """Analyze the research topic to determine filtering approach"""
        question_lower = sub_question.question.lower()
        search_terms = [term.lower() for term in sub_question.search_terms]
        all_text = question_lower + " " + " ".join(search_terms)
        
        # Detect topic characteristics
        characteristics = {
            "is_academic": any(term in all_text for term in [
                "research", "study", "analysis", "methodology", "theory", "hypothesis",
                "peer review", "journal", "publication", "academic", "university"
            ]),
            "is_technical": any(term in all_text for term in [
                "algorithm", "technical", "engineering", "software", "hardware", 
                "programming", "code", "development", "architecture", "protocol"
            ]),
            "is_current_events": any(term in all_text for term in [
                "2024", "2023", "recent", "latest", "current", "today", "now",
                "breaking", "update", "news", "announcement"
            ]),
            "is_niche": len(search_terms) > 3 and any(len(term) > 8 for term in search_terms),
            "is_broad": any(term in all_text for term in [
                "overview", "introduction", "basics", "general", "common", "popular"
            ]),
            "is_comparative": any(term in all_text for term in [
                "vs", "versus", "compare", "comparison", "difference", "better", "best"
            ])
        }
        
        # Classify topic type
        if characteristics["is_academic"]:
            classification = "academic"
        elif characteristics["is_technical"]:
            classification = "technical"
        elif characteristics["is_current_events"]:
            classification = "current_events"
        elif characteristics["is_niche"]:
            classification = "niche"
        elif characteristics["is_broad"]:
            classification = "broad"
        else:
            classification = "general"
        
        return {
            "classification": classification,
            "characteristics": characteristics,
            "complexity_score": len([k for k, v in characteristics.items() if v]) / len(characteristics)
        }
    
    def _analyze_source_quality_distribution(self, results: List[SearchResult]) -> Dict[str, float]:
        """Analyze the quality distribution of available sources"""
        if not results:
            return {"mean_authority": 0.0, "mean_relevance": 0.0, "mean_quality": 0.0}
        
        # Filter out None values to prevent arithmetic errors
        authority_scores = [r.authority_score for r in results if r.authority_score is not None]
        relevance_scores = [r.relevance_score for r in results if r.relevance_score is not None]
        content_scores = [r.content_quality for r in results if r.content_quality is not None]
        
        # Provide defaults if all values are None
        if not authority_scores:
            authority_scores = [0.5]
        if not relevance_scores:
            relevance_scores = [0.5]
        if not content_scores:
            content_scores = [0.5]
        
        # Calculate percentiles for adaptive thresholding
        import statistics
        
        def safe_percentile(data, percentile):
            if not data:
                return 0.0
            try:
                return statistics.quantiles(sorted(data), n=100)[percentile-1] if len(data) > 1 else data[0]
            except:
                return statistics.median(data) if data else 0.0
        
        return {
            "mean_authority": statistics.mean(authority_scores),
            "mean_relevance": statistics.mean(relevance_scores),
            "mean_quality": statistics.mean(content_scores),
            "median_authority": statistics.median(authority_scores),
            "median_relevance": statistics.median(relevance_scores),
            "median_quality": statistics.median(content_scores),
            "p25_authority": safe_percentile(authority_scores, 25),
            "p75_authority": safe_percentile(authority_scores, 75),
            "p25_relevance": safe_percentile(relevance_scores, 25),
            "p75_relevance": safe_percentile(relevance_scores, 75),
            "quality_variance": statistics.variance(authority_scores) if len(authority_scores) > 1 else 0.0,
            "source_type_diversity": len(set(r.source_type for r in results)) / max(len(results), 1)
        }
    
    def _determine_filtering_strategy(self, topic_analysis: Dict, quality_analysis: Dict, 
                                    source_count: int, quality_assessment: Optional[QualityAssessment]) -> str:
        """Determine the appropriate filtering strategy based on context"""
        
        # Check explicit mode setting
        if self.settings.adaptive_filtering_mode in ["strict", "lenient"]:
            return self.settings.adaptive_filtering_mode
        
        # Adaptive decision logic
        classification = topic_analysis["classification"]
        mean_authority = quality_analysis.get("mean_authority", 0.5)
        source_diversity = quality_analysis.get("source_type_diversity", 0.5)
        
        # Factors that suggest lenient filtering
        lenient_factors = [
            classification in ["niche", "technical"],  # Specialized topics
            source_count < self.settings.min_sources_threshold,  # Few sources available
            mean_authority < 0.4,  # Generally low authority sources
            source_diversity < 0.3,  # Low source diversity
            bool(quality_assessment and quality_assessment.overall_confidence < 0.5)  # Low overall confidence
        ]
        
        # Factors that suggest strict filtering
        strict_factors = [
            classification in ["broad", "general"],  # Common topics with many sources
            source_count > 15,  # Many sources available
            mean_authority > 0.7,  # High quality sources available
            source_diversity > 0.6,  # High source diversity
            bool(quality_assessment and quality_assessment.overall_confidence > 0.8)  # High confidence
        ]
        
        lenient_score = sum(lenient_factors)
        strict_score = sum(strict_factors)
        
        if lenient_score > strict_score:
            return "lenient"
        elif strict_score > lenient_score + 1:  # Bias toward lenient
            return "strict"
        else:
            return "smart"  # Balanced approach
    
    def _calculate_adaptive_thresholds(self, quality_analysis: Dict, strategy: str, 
                                     topic_analysis: Dict) -> Dict[str, float]:
        """Calculate adaptive filtering thresholds based on available quality"""
        
        base_thresholds = {
            "authority": self.settings.min_authority_score,
            "relevance": self.settings.min_relevance_score,
            "content_quality": self.settings.min_content_quality,
            "overall": self.settings.min_overall_confidence
        }
        
        # Adjust based on strategy
        if strategy == "strict":
            multipliers = {"authority": 1.3, "relevance": 1.2, "content_quality": 1.2, "overall": 1.2}
        elif strategy == "lenient":
            multipliers = {"authority": 0.7, "relevance": 0.8, "content_quality": 0.8, "overall": 0.8}
        else:  # smart
            multipliers = {"authority": 1.0, "relevance": 1.0, "content_quality": 1.0, "overall": 1.0}
        
        # Calculate thresholds based on strategy (not available quality - that was the bug!)
        adaptive_thresholds = {}
        for metric in base_thresholds:
            threshold = base_thresholds[metric] * multipliers[metric]
            
            # Apply topic-specific adjustments to the calculated threshold
            if topic_analysis["classification"] == "niche":
                # Be slightly more lenient with niche topics
                threshold *= 0.95
            elif topic_analysis["classification"] == "academic":
                # Maintain higher standards for academic topics
                threshold *= 1.05
                
            # Set reasonable bounds but don't make them too lenient
            min_bounds = {
                "authority": 0.25,     # Never go below 0.25 for authority
                "relevance": 0.35,     # Never go below 0.35 for relevance  
                "content_quality": 0.25, # Never go below 0.25 for content quality
                "overall": 0.35        # Never go below 0.35 for overall
            }
            
            adaptive_thresholds[metric] = max(min_bounds[metric], min(0.85, threshold))
        
        return adaptive_thresholds
    
    def _apply_adaptive_filtering(self, results: List[SearchResult], thresholds: Dict[str, float],
                                strategy: str, topic_analysis: Dict) -> List[SearchResult]:
        """Apply adaptive filtering with simplified logic"""
        
        if not results:
            return results
        
        filtered_results = []
        
        for result in results:
            # Filter out sources with insufficient content
            content_length = len(result.content.strip()) if result.content else 0
            if content_length < 200:
                continue
            
            # Check quality thresholds
            authority_score = result.authority_score or 0.5
            relevance_score = result.relevance_score or 0.5
            content_quality = result.content_quality or 0.5
            overall_quality = (authority_score + relevance_score + content_quality) / 3
            
            # Apply thresholds
            if (authority_score >= thresholds["authority"] and
                relevance_score >= thresholds["relevance"] and
                content_quality >= thresholds["content_quality"] and
                overall_quality >= thresholds["overall"]):
                filtered_results.append(result)
        
        self.logger.info("Adaptive filtering completed", 
                        strategy=strategy,
                        original=len(results), 
                        kept=len(filtered_results))
        
        return filtered_results
    
    def _apply_domain_diversity_filtering(self, results: List[SearchResult]) -> List[SearchResult]:
        """Limit results per domain while preserving quality"""
        from urllib.parse import urlparse
        from collections import defaultdict
        
        domain_results = defaultdict(list)
        
        # Group by domain
        for result in results:
            try:
                domain = urlparse(result.url).netloc.lower()
                domain_results[domain].append(result)
            except:
                domain_results["unknown"].append(result)
        
        # Keep best results from each domain
        filtered = []
        for domain, domain_list in domain_results.items():
            # Sort by combined quality score
            domain_list.sort(
                key=lambda r: ((r.authority_score or 0.5) + (r.relevance_score or 0.5) + (r.content_quality or 0.5)) / 3,
                reverse=True
            )
            # Keep up to max_results_per_domain
            filtered.extend(domain_list[:self.settings.max_results_per_domain])
        
        return filtered
    
    def _apply_percentile_filtering(self, results: List[SearchResult]) -> List[SearchResult]:
        """Keep only sources above a quality percentile - simplified version"""
        if len(results) <= 5:
            return results
        
        # Simple quality-based filtering
        quality_scores = []
        for result in results:
            # Calculate simple composite score
            authority = result.authority_score or 0.5
            relevance = result.relevance_score or 0.5
            quality = result.content_quality or 0.5
            
            composite_score = (authority + relevance + quality) / 3
            quality_scores.append((composite_score, result))
        
        # Sort by quality and keep top results
        quality_scores.sort(reverse=True)
        cutoff_index = max(3, int(len(quality_scores) * 0.7))  # Keep top 70%
        
        return [result for _, result in quality_scores[:cutoff_index]]
    
    def _apply_safety_limits(self, original_results: List[SearchResult], 
                           filtered_results: List[SearchResult], original_count: int) -> List[SearchResult]:
        """Apply safety limits to prevent over-filtering - simplified version"""
        
        # Ensure minimum sources are kept
        min_sources = getattr(self.settings, 'min_sources_after_filtering', 3)
        if len(filtered_results) < min_sources:
            # Add back highest quality sources that were filtered out
            filtered_urls = {r.url for r in filtered_results}
            remaining = [r for r in original_results if r.url not in filtered_urls]
            
            if remaining:
                # Sort by simple composite quality
                remaining.sort(
                    key=lambda r: ((r.authority_score or 0.5) + (r.relevance_score or 0.5) + (r.content_quality or 0.5)) / 3,
                    reverse=True
                )
                
                needed = min_sources - len(filtered_results)
                filtered_results.extend(remaining[:needed])
        
        return filtered_results
    
    def _calculate_confidence_boost(self, original_results: List[SearchResult], 
                                  filtered_results: List[SearchResult], strategy: str) -> float:
        """Calculate confidence boost from filtering quality improvement"""
        
        if not original_results or not filtered_results:
            return 0.0
        
        # Calculate average quality before and after filtering
        def avg_quality(results):
            if not results:
                return 0.0
            return sum((r.authority_score or 0.5) + (r.relevance_score or 0.5) + (r.content_quality or 0.5) 
                      for r in results) / (len(results) * 3)
        
        original_quality = avg_quality(original_results)
        filtered_quality = avg_quality(filtered_results)
        
        quality_improvement = filtered_quality - original_quality
        
        # Scale confidence boost based on improvement and strategy
        if strategy == "strict":
            boost_multiplier = 0.15
        elif strategy == "smart":
            boost_multiplier = 0.10
        else:  # lenient
            boost_multiplier = 0.05
        
        confidence_boost = max(0.0, min(0.2, quality_improvement * boost_multiplier))
        
        return round(confidence_boost, 3)
    
    def _generate_filtering_reasoning(self, topic_analysis: Dict, quality_analysis: Dict,
                                    strategy: str, thresholds: Dict, original_count: int, 
                                    final_count: int) -> List[str]:
        """Generate human-readable reasoning for filtering decisions"""
        
        reasoning = []
        
        # Topic analysis
        topic_type = topic_analysis["classification"]
        reasoning.append(f"Topic classified as '{topic_type}' - adjusted filtering strategy accordingly")
        
        # Strategy explanation
        if strategy == "lenient":
            reasoning.append("Applied lenient filtering to preserve sources for specialized/niche topic")
        elif strategy == "strict":
            reasoning.append("Applied strict filtering due to abundant high-quality sources available")
        else:
            reasoning.append("Applied balanced filtering with adaptive quality thresholds")
        
        # Quality distribution
        mean_auth = quality_analysis.get("mean_authority", 0.5)
        reasoning.append(f"Source authority distribution: average {mean_auth:.2f}")
        
        # Filtering results
        filtered_count = original_count - final_count
        if filtered_count > 0:
            filter_pct = (filtered_count / original_count) * 100
            reasoning.append(f"Filtered {filtered_count}/{original_count} sources ({filter_pct:.1f}%) below adaptive quality thresholds")
        else:
            reasoning.append("No sources filtered - all met adaptive quality standards")
        
        # Safety limits
        if final_count == self.settings.min_sources_after_filtering:
            reasoning.append("Applied minimum source safety limit to prevent over-filtering")
        
        return reasoning
    
    def _evaluate_source_quality(self, result: SearchResult) -> bool:
        """
        Smart composite quality evaluation that considers multiple factors
        Uses logical combinations instead of harsh AND requirements
        """
        authority_score = result.authority_score or 0.5
        relevance_score = result.relevance_score or 0.5
        content_quality = result.content_quality or 0.5
        
        # Calculate composite quality score (weighted average)
        composite_score = (
            authority_score * 0.4 +      # Authority is important but not everything
            relevance_score * 0.4 +      # Relevance matters for answering the question  
            content_quality * 0.2        # Content depth/quality as tie-breaker
        )
        
        # Smart pass/fail logic with multiple pathways to success:
        
        # Pathway 1: High composite score (balanced quality)
        if composite_score >= 0.55:
            return True
            
        # Pathway 2: Very high authority (trusted sources, even if relevance is moderate)
        if authority_score >= 0.8 and relevance_score >= 0.2:
            return True
            
        # Pathway 3: High relevance with reasonable authority (good match, decent source)
        if relevance_score >= 0.6 and authority_score >= 0.3:
            return True
            
        # Pathway 4: Firecrawl sources get bonus consideration (full content available)
        if hasattr(result, 'source_type') and result.source_type == 'firecrawl':
            if composite_score >= 0.45:  # Lower threshold for full-content sources
                return True
                
        # Pathway 5: Strong content quality can overcome lower relevance/authority
        if content_quality >= 0.7 and composite_score >= 0.4:
            return True
            
        return False

    def _create_empty_decision(self, reason: str) -> FilteringDecision:
        """Create decision for empty result sets"""
        return FilteringDecision(
            filtered_results=[],
            original_count=0,
            filtered_count=0,
            kept_count=0,
            filtering_strategy="none",
            quality_distribution={},
            reasoning=[f"No filtering applied: {reason}"],
            topic_classification="unknown"
        )
