"""
Unified Quality Assessment System for the Research System.
Combines LLM-based evaluation with algorithmic scoring methods.
"""

import structlog
import time
import re
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from urllib.parse import urlparse
import math

logger = structlog.get_logger(__name__)


class AssessmentMode(Enum):
    """Quality assessment modes"""
    LLM_COMPREHENSIVE = "llm_comprehensive"  # Full LLM evaluation (slow, comprehensive)
    ALGORITHMIC_FAST = "algorithmic_fast"    # Fast algorithmic scoring
    HYBRID_SMART = "hybrid_smart"            # Smart combination of both
    FALLBACK_ONLY = "fallback_only"          # Emergency fallback


class QualityDimension(Enum):
    """Quality dimensions for assessment"""
    RELEVANCE = "relevance"
    AUTHORITY = "authority"
    CONTENT_QUALITY = "content_quality"
    RECENCY = "recency"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics"""
    overall_confidence: float
    relevance_score: float
    authority_score: float
    content_quality: float
    recency_score: float
    consistency_score: float
    completeness_score: float
    assessment_reasoning: str
    quality_feedback: List[str]
    improvement_suggestions: List[str]


@dataclass
class AssessmentRequest:
    """Request for quality assessment"""
    results: List[Any]  # List of SearchResult objects
    sub_question: Optional[Any] = None  # SubQuestion object
    insights: List[str] = None
    facts: List[str] = None
    mode: AssessmentMode = AssessmentMode.HYBRID_SMART
    context: Optional[str] = None


class UnifiedQualityAssessor:
    """
    Unified Quality Assessment system that combines LLM-based evaluation 
    with algorithmic scoring methods.
    """
    
    def __init__(self, settings: Optional[Any] = None):
        """Initialize the unified quality assessor"""
        self.settings = settings
        self.logger = logger
        
        # Initialize default thresholds
        self.default_thresholds = {
            'authority_threshold': 0.6,
            'relevance_threshold': 0.5,
            'content_quality_threshold': 0.4,
            'recency_threshold': 0.3
        }
        
        # Configuration
        self.llm_threshold_count = getattr(settings, 'quality_llm_threshold', 5)
        self.llm_timeout = getattr(settings, 'quality_llm_timeout', 30.0)
        self.enable_hybrid = getattr(settings, 'quality_hybrid_mode', True)
        
        # Domain authority database
        self.authority_domains = {
            # Government and official
            'gov': 0.95, 'edu': 0.90, 'org': 0.75,
            # High authority news/media
            'reuters.com': 0.85, 'bbc.com': 0.85, 'cnn.com': 0.80,
            'nytimes.com': 0.85, 'wsj.com': 0.85, 'bloomberg.com': 0.85,
            # Academic/research
            'scholar.google.com': 0.90, 'pubmed.ncbi.nlm.nih.gov': 0.95,
            'arxiv.org': 0.85, 'researchgate.net': 0.80,
            # Business/professional
            'linkedin.com': 0.70, 'glassdoor.com': 0.75,
            # Reference
            'wikipedia.org': 0.65, 'britannica.com': 0.80
        }
    
    async def assess_quality(self, request: AssessmentRequest) -> QualityMetrics:
        """Main quality assessment method"""
        start_time = time.time()
        
        try:
            # Determine assessment strategy
            mode = self._determine_assessment_mode(request)
            
            if mode == AssessmentMode.LLM_COMPREHENSIVE:
                metrics = await self._llm_comprehensive_assessment(request)
            elif mode == AssessmentMode.HYBRID_SMART:
                metrics = await self._hybrid_smart_assessment(request)
            elif mode == AssessmentMode.ALGORITHMIC_FAST:
                metrics = self._algorithmic_fast_assessment(request)
            else:  # FALLBACK_ONLY
                metrics = self._fallback_assessment(request)
            
            metrics.processing_time = time.time() - start_time
            metrics.assessment_mode = mode
            
            return metrics
            
        except Exception as e:
            self.logger.error("Quality assessment failed", error=str(e))
            # Emergency fallback
            fallback_metrics = self._fallback_assessment(request)
            fallback_metrics.processing_time = time.time() - start_time
            fallback_metrics.assessment_mode = AssessmentMode.FALLBACK_ONLY
            fallback_metrics.fallback_reason = f"Assessment error: {str(e)}"
            return fallback_metrics
    
    def _determine_assessment_mode(self, request: AssessmentRequest) -> AssessmentMode:
        """Intelligently determine which assessment mode to use"""
        
        # Force LLM if requested
        if request.force_llm and self.llm_agent:
            return AssessmentMode.LLM_COMPREHENSIVE
        
        # Use specified mode if provided
        if request.mode != AssessmentMode.HYBRID_SMART:
            return request.mode
        
        # No LLM agent available
        if not self.llm_agent:
            return AssessmentMode.ALGORITHMIC_FAST
        
        # Smart hybrid logic
        result_count = len(request.results)
        has_content = any(getattr(r, 'content', '') for r in request.results)
        
        # Use LLM for complex cases
        if (result_count >= self.llm_threshold_count and 
            has_content and 
            self.enable_hybrid):
            return AssessmentMode.LLM_COMPREHENSIVE
        
        # Use hybrid for medium complexity
        if result_count >= 3 and has_content:
            return AssessmentMode.HYBRID_SMART
        
        # Use algorithmic for simple cases
        return AssessmentMode.ALGORITHMIC_FAST
    
    async def _llm_comprehensive_assessment(self, request: AssessmentRequest) -> QualityMetrics:
        """Full LLM-based quality assessment"""
        try:
            # Use existing QualityEvaluationAgent
            quality_assessment = await self.llm_agent.evaluate_search_quality(
                request.sub_question,
                request.results,
                request.insights or [],
                request.facts or [],
                None  # resource_manager - will be handled by agent
            )
            
            return QualityMetrics(
                relevance_score=quality_assessment.relevance_score,
                authority_score=quality_assessment.authority_score,
                content_quality=quality_assessment.completeness_score,  # Map completeness to content_quality
                completeness_score=quality_assessment.completeness_score,
                recency_score=quality_assessment.recency_score,
                consistency_score=quality_assessment.consistency_score,
                overall_confidence=quality_assessment.overall_confidence,
                llm_used=True
            )
            
        except Exception as e:
            self.logger.warning("LLM assessment failed, falling back to algorithmic", error=str(e))
            return self._algorithmic_fast_assessment(request)
    
    async def _hybrid_smart_assessment(self, request: AssessmentRequest) -> QualityMetrics:
        """Smart hybrid assessment combining LLM and algorithmic methods"""
        
        # Start with fast algorithmic assessment
        algo_metrics = self._algorithmic_fast_assessment(request)
        
        # Use LLM for specific dimensions that benefit from context
        try:
            if self.llm_agent and len(request.results) > 0:
                # Quick LLM assessment for relevance and completeness only
                quality_assessment = await self.llm_agent.evaluate_search_quality(
                    request.sub_question,
                    request.results[:3],  # Limit to top 3 results for speed
                    request.insights or [],
                    request.facts or [],
                    None
                )
                
                # Combine algorithmic and LLM scores intelligently
                return QualityMetrics(
                    relevance_score=quality_assessment.relevance_score,  # LLM better at relevance
                    authority_score=algo_metrics.authority_score,        # Algorithmic better at authority
                    content_quality=algo_metrics.content_quality,        # Algorithmic better at content analysis
                    completeness_score=quality_assessment.completeness_score,  # LLM better at completeness
                    recency_score=algo_metrics.recency_score,            # Algorithmic better at recency
                    consistency_score=quality_assessment.consistency_score,  # LLM better at consistency
                    overall_confidence=(quality_assessment.overall_confidence + algo_metrics.overall_confidence) / 2,
                    llm_used=True
                )
        except Exception as e:
            self.logger.warning("Hybrid LLM component failed, using algorithmic only", error=str(e))
        
        return algo_metrics
    
    def _algorithmic_fast_assessment(self, request: AssessmentRequest) -> QualityMetrics:
        """Fast algorithmic quality assessment"""
        start_time = time.time()
        
        # Calculate individual scores
        relevance_score = self._calculate_relevance_score(request.results, request.sub_question)
        authority_score = self._calculate_authority_score(request.results)
        content_quality = self._calculate_content_quality_score(request.results)
        completeness_score = self._calculate_completeness_score(request.results, request.insights, request.facts)
        recency_score = self._calculate_recency_score(request.results)
        consistency_score = self._calculate_consistency_score(request.results)
        
        # Calculate overall confidence
        overall_confidence = (
            relevance_score * 0.25 +
            authority_score * 0.25 +
            content_quality * 0.20 +
            completeness_score * 0.15 +
            recency_score * 0.10 +
            consistency_score * 0.05
        )
        
        processing_time = time.time() - start_time
        
        return QualityMetrics(
            overall_confidence=overall_confidence,
            relevance_score=relevance_score,
            authority_score=authority_score,
            content_quality=content_quality,
            recency_score=recency_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            assessment_reasoning=f"Algorithmic assessment completed in {processing_time:.3f}s with {len(request.results)} results",
            quality_feedback=[
                f"Processed {len(request.results)} search results",
                f"Authority score: {authority_score:.2f}",
                f"Relevance score: {relevance_score:.2f}",
                f"Content quality: {content_quality:.2f}"
            ],
            improvement_suggestions=[
                "Consider using LLM-based assessment for more nuanced evaluation",
                "Verify source diversity and authority",
                "Check for recent and relevant content"
            ]
        )
    
    def _fallback_assessment(self, request: AssessmentRequest) -> QualityMetrics:
        """Emergency fallback assessment with minimal processing"""
        if not request.results:
            return QualityMetrics(
                overall_confidence=0.1,
                relevance_score=0.1,
                authority_score=0.1,
                content_quality=0.1,
                recency_score=0.3,
                consistency_score=0.3,
                completeness_score=0.1,
                assessment_reasoning="No results available for assessment",
                quality_feedback=["No search results to evaluate"],
                improvement_suggestions=["Retry search with different terms"]
            )
        
        # Very basic scoring
        result_count = len(request.results)
        
        # Simple authority based on source types
        authority_scores = []
        for result in request.results:
            source_type = getattr(result, 'source_type', 'web')
            if source_type in ['academic', 'government']:
                authority_scores.append(0.8)
            elif source_type in ['news', 'organization']:
                authority_scores.append(0.6)
            else:
                authority_scores.append(0.4)
        
        authority_score = sum(authority_scores) / len(authority_scores)
        
        # Basic relevance from existing scores
        relevance_scores = [getattr(r, 'relevance_score', 0.5) for r in request.results]
        relevance_score = sum(relevance_scores) / len(relevance_scores)
        
        # Conservative estimates for other metrics
        content_quality = 0.5  # Neutral assumption
        completeness_score = min(0.7, result_count / 10)  # Based on result count
        recency_score = 0.4  # Conservative assumption
        consistency_score = 0.5  # Neutral assumption
        
        # Simple overall confidence
        overall_confidence = (
            relevance_score * 0.3 +
            authority_score * 0.3 +
            content_quality * 0.2 +
            completeness_score * 0.2
        )
        
        return QualityMetrics(
            overall_confidence=overall_confidence,
            relevance_score=relevance_score,
            authority_score=authority_score,
            content_quality=content_quality,
            recency_score=recency_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            assessment_reasoning=f"Fallback assessment with {result_count} results. Limited algorithmic analysis.",
            quality_feedback=[
                f"Basic assessment of {result_count} results",
                f"Average authority: {authority_score:.2f}",
                "Limited quality analysis available"
            ],
            improvement_suggestions=[
                "Use comprehensive assessment mode for better accuracy",
                "Verify source quality manually",
                "Consider additional search terms"
            ]
        )
    
    def _calculate_relevance_score(self, results: List[Any], sub_question: Optional[Any]) -> float:
        """Calculate relevance score based on search results and question"""
        if not results:
            return 0.1
        
        # Handle case where sub_question is None
        if sub_question is None:
            # Use average relevance scores from results
            relevance_scores = [getattr(r, 'relevance_score', 0.5) for r in results]
            return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5
        
        # Extract question terms for matching
        question_terms = set(sub_question.question.lower().split())
        search_terms = set()
        if hasattr(sub_question, 'search_terms'):
            for term in sub_question.search_terms:
                search_terms.update(term.lower().split())
        
        all_terms = question_terms.union(search_terms)
        
        relevance_scores = []
        for result in results:
            # Use existing relevance score if available
            if hasattr(result, 'relevance_score') and result.relevance_score is not None:
                relevance_scores.append(result.relevance_score)
            else:
                # Calculate based on title and content matching
                title_text = getattr(result, 'title', '').lower()
                content_text = getattr(result, 'content', '').lower()
                snippet_text = getattr(result, 'snippet', '').lower()
                
                combined_text = f"{title_text} {content_text} {snippet_text}"
                
                # Count term matches
                matches = sum(1 for term in all_terms if term in combined_text)
                relevance = min(0.9, matches / max(len(all_terms), 1) + 0.3)
                relevance_scores.append(relevance)
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5
    
    def _calculate_authority_score(self, results: List[Any]) -> float:
        """Calculate authority score based on domain analysis"""
        if not results:
            return 0.0
        
        authority_scores = []
        for result in results:
            url = getattr(result, 'url', '')
            if not url:
                authority_scores.append(0.3)
                continue
            
            domain = urlparse(url).netloc.lower()
            
            # Check known authority domains
            authority = 0.5  # Base score
            
            # Exact domain matches
            if domain in self.authority_domains:
                authority = self.authority_domains[domain]
            else:
                # TLD-based scoring
                if domain.endswith('.gov'):
                    authority = 0.95
                elif domain.endswith('.edu'):
                    authority = 0.90
                elif domain.endswith('.org'):
                    authority = 0.75
                elif any(domain.endswith(tld) for tld in ['.com', '.net', '.io']):
                    authority = 0.60
                
                # Domain characteristics
                if len(domain.split('.')) == 2:  # Simple domain
                    authority += 0.05
                if '-' not in domain:  # No hyphens
                    authority += 0.05
                if len(domain) > 15:  # Long domain names often less authoritative
                    authority -= 0.05
            
            authority_scores.append(min(0.95, max(0.1, authority)))
        
        return sum(authority_scores) / len(authority_scores)
    
    def _calculate_content_quality_score(self, results: List[Any]) -> float:
        """Calculate content quality score"""
        if not results:
            return 0.0
        
        quality_scores = []
        for result in results:
            content = getattr(result, 'content', '')
            title = getattr(result, 'title', '')
            
            if not content:
                quality_scores.append(0.2)
                continue
            
            quality = 0.3  # Base score
            
            # Content length scoring
            word_count = len(content.split())
            if word_count > 100:
                quality += 0.3
            elif word_count > 50:
                quality += 0.2
            elif word_count > 20:
                quality += 0.1
            
            # Content structure indicators
            if any(indicator in content.lower() for indicator in ['introduction', 'conclusion', 'summary']):
                quality += 0.15
            
            # Quality indicators
            sentence_count = len([s for s in content.split('.') if s.strip()])
            if sentence_count > 5:
                quality += 0.1
            
            # Title-content consistency
            if title and any(word in content.lower() for word in title.lower().split()):
                quality += 0.1
            
            quality_scores.append(min(0.95, quality))
        
        return sum(quality_scores) / len(quality_scores)
    
    def _calculate_completeness_score(self, results: List[Any], insights: List[str], facts: List[str]) -> float:
        """Calculate completeness score based on extracted insights and facts"""
        # Handle None parameters
        insights = insights or []
        facts = facts or []
        
        if not results:
            return 0.1
        
        # Base score from number of results
        result_factor = min(len(results) / 10, 0.4)  # Max 0.4 from results count
        
        # Insights factor
        insight_factor = min(len(insights) / 5, 0.3)  # Max 0.3 from insights
        
        # Facts factor  
        fact_factor = min(len(facts) / 8, 0.3)  # Max 0.3 from facts
        
        total_score = result_factor + insight_factor + fact_factor
        
        return min(0.95, max(0.1, total_score))
    
    def _calculate_recency_score(self, results: List[Any]) -> float:
        """Calculate recency score (simplified)"""
        # For now, return a neutral score
        # Could be enhanced with actual date parsing
        return 0.6
    
    def _calculate_consistency_score(self, results: List[Any]) -> float:
        """Calculate consistency score"""
        if len(results) < 2:
            return 0.7
        
        # Simple consistency check based on domain diversity
        domains = set()
        for result in results:
            url = getattr(result, 'url', '')
            if url:
                domains.add(urlparse(url).netloc)
        
        # More diverse domains = more consistent (cross-validation)
        diversity_ratio = len(domains) / len(results)
        return min(0.9, 0.5 + diversity_ratio * 0.4)
    
    def _calculate_overall_confidence(self, relevance: float, authority: float, 
                                    content_quality: float, completeness: float,
                                    recency: float, consistency: float) -> float:
        """Calculate overall confidence score"""
        weights = {
            'relevance': 0.3,
            'authority': 0.25,
            'content_quality': 0.2,
            'completeness': 0.15,
            'recency': 0.05,
            'consistency': 0.05
        }
        
        return (
            relevance * weights['relevance'] +
            authority * weights['authority'] +
            content_quality * weights['content_quality'] +
            completeness * weights['completeness'] +
            recency * weights['recency'] +
            consistency * weights['consistency']
        )

    def assess(self, request: AssessmentRequest) -> QualityMetrics:
        """
        Main entry point for quality assessment.
        Intelligently chooses the best assessment method based on request mode and available resources.
        """
        try:
            if request.mode == AssessmentMode.LLM_COMPREHENSIVE:
                # TODO: Implement LLM-based comprehensive assessment
                # For now, fall back to algorithmic assessment
                self.logger.info("LLM comprehensive assessment not yet implemented, using algorithmic")
                return self._algorithmic_fast_assessment(request)
            
            elif request.mode == AssessmentMode.ALGORITHMIC_FAST:
                return self._algorithmic_fast_assessment(request)
            
            elif request.mode == AssessmentMode.HYBRID_SMART:
                # Use algorithmic for now, can be enhanced to combine LLM + algorithmic
                self.logger.info("Using algorithmic assessment for hybrid mode")
                return self._algorithmic_fast_assessment(request)
            
            elif request.mode == AssessmentMode.FALLBACK_ONLY:
                return self._fallback_assessment(request)
            
            else:
                # Default to algorithmic assessment
                return self._algorithmic_fast_assessment(request)
                
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            # Emergency fallback
            return self._fallback_assessment(request)


# Utility functions for backward compatibility
def create_quality_assessor(settings, cache_manager=None, llm_agent=None) -> UnifiedQualityAssessor:
    """Factory function to create quality assessor"""
    return UnifiedQualityAssessor(settings)


def quick_quality_check(results: List[Any], sub_question: Any) -> bool:
    """Quick quality check for filtering"""
    if not results:
        return False
    
    # Simple heuristic check
    has_content = any(getattr(r, 'content', '') for r in results)
    has_authority = any(getattr(r, 'authority_score', 0) > 0.5 for r in results)
    
    return has_content and has_authority 