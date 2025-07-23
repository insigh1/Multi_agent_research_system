# quality_evaluator.py
"""
Unified quality evaluation system
Replaces overlapping quality logic in SearchResult, QualityAssessment, and AdaptiveSourceFilter
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

class QualityDimension(Enum):
    """Quality dimensions for evaluation"""
    AUTHORITY = "authority"
    RELEVANCE = "relevance" 
    CONTENT_QUALITY = "content_quality"
    RECENCY = "recency"
    COMPLETENESS = "completeness"

@dataclass
class QualityScore:
    """Unified quality score with breakdown"""
    overall: float
    dimensions: Dict[QualityDimension, float]
    confidence: float
    reasoning: List[str]
    
    @property
    def is_high_quality(self) -> bool:
        """Simple threshold check"""
        return self.overall >= 0.7 and self.confidence >= 0.6

class QualityEvaluator:
    """Unified quality evaluation with multiple strategies"""
    
    def __init__(self, settings=None):
        self.settings = settings
        self.weights = {
            QualityDimension.AUTHORITY: 0.3,
            QualityDimension.RELEVANCE: 0.4,
            QualityDimension.CONTENT_QUALITY: 0.2,
            QualityDimension.RECENCY: 0.05,
            QualityDimension.COMPLETENESS: 0.05
        }
    
    def evaluate_search_result(self, result, query: str = "", **kwargs) -> QualityScore:
        """Evaluate a single search result"""
        
        dimensions = {}
        reasoning = []
        
        # Authority evaluation
        authority = self._evaluate_authority(result)
        dimensions[QualityDimension.AUTHORITY] = authority
        if authority > 0.8:
            reasoning.append("High authority domain")
        elif authority < 0.3:
            reasoning.append("Low authority domain")
        
        # Relevance evaluation  
        relevance = self._evaluate_relevance(result, query)
        dimensions[QualityDimension.RELEVANCE] = relevance
        if relevance > 0.8:
            reasoning.append("Highly relevant content")
        elif relevance < 0.4:
            reasoning.append("Low relevance to query")
        
        # Content quality
        content_quality = self._evaluate_content_quality(result)
        dimensions[QualityDimension.CONTENT_QUALITY] = content_quality
        
        # Calculate overall score
        overall = sum(
            dimensions.get(dim, 0.5) * weight 
            for dim, weight in self.weights.items()
        )
        
        # Confidence based on available data
        confidence = self._calculate_confidence(result, dimensions)
        
        return QualityScore(
            overall=overall,
            dimensions=dimensions,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _evaluate_authority(self, result) -> float:
        """Evaluate domain authority"""
        url = getattr(result, 'url', '')
        if not url:
            return 0.5
        
        domain = url.split('/')[2].lower() if '://' in url else url
        
        # High authority domains
        high_authority = {
            'wikipedia.org': 0.95,
            'reuters.com': 0.9,
            'bloomberg.com': 0.9,
            'sec.gov': 0.95,
            'nasa.gov': 0.9,
            'nature.com': 0.95,
            'sciencedirect.com': 0.9
        }
        
        # Check for exact matches
        for auth_domain, score in high_authority.items():
            if auth_domain in domain:
                return score
        
        # Domain type scoring
        if domain.endswith('.gov'):
            return 0.85
        elif domain.endswith('.edu'):
            return 0.8
        elif domain.endswith('.org'):
            return 0.7
        elif any(term in domain for term in ['news', 'times', 'post', 'journal']):
            return 0.75
        else:
            return 0.5
    
    def _evaluate_relevance(self, result, query: str) -> float:
        """Evaluate relevance to query"""
        if not query:
            return 0.5
        
        title = getattr(result, 'title', '').lower()
        snippet = getattr(result, 'snippet', '').lower()
        query_lower = query.lower()
        
        # Simple keyword matching
        query_words = set(query_lower.split())
        title_words = set(title.split()) 
        snippet_words = set(snippet.split())
        
        # Calculate overlap
        title_overlap = len(query_words & title_words) / max(len(query_words), 1)
        snippet_overlap = len(query_words & snippet_words) / max(len(query_words), 1)
        
        # Weight title higher than snippet
        relevance = (title_overlap * 0.7 + snippet_overlap * 0.3)
        
        return min(relevance, 1.0)
    
    def _evaluate_content_quality(self, result) -> float:
        """Evaluate content quality indicators"""
        content = getattr(result, 'content', '')
        title = getattr(result, 'title', '')
        
        score = 0.5  # baseline
        
        # Content length (longer usually better, but not always)
        if len(content) > 1000:
            score += 0.2
        elif len(content) > 500:
            score += 0.1
        
        # Title quality (not too short, not too long)
        if 10 <= len(title) <= 100:
            score += 0.1
        
        # Check for quality indicators
        if any(indicator in content.lower() for indicator in ['research', 'study', 'analysis', 'report']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_confidence(self, result, dimensions: Dict) -> float:
        """Calculate confidence in the evaluation"""
        # More data = higher confidence
        confidence = 0.5
        
        if hasattr(result, 'content') and len(result.content) > 100:
            confidence += 0.2
        if hasattr(result, 'title') and result.title:
            confidence += 0.1
        if hasattr(result, 'url') and result.url:
            confidence += 0.1
        
        # Consistency across dimensions also increases confidence
        dimension_values = list(dimensions.values())
        if dimension_values:
            std_dev = (sum((x - sum(dimension_values)/len(dimension_values))**2 for x in dimension_values) / len(dimension_values))**0.5
            if std_dev < 0.2:  # Low variance = more consistent = higher confidence
                confidence += 0.1
        
        return min(confidence, 1.0) 