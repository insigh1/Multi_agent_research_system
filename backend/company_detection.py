# company_detection.py
"""
Unified company detection logic
Replaces duplicate methods in ResearchPlannerAgent and WebSearchRetrieverAgent
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class CompanyInfo:
    """Structured company information"""
    name: str
    domains: List[str] = None
    confidence: float = 0.0
    detected_patterns: List[str] = None
    
    def __post_init__(self):
        if self.domains is None:
            self.domains = []
        if self.detected_patterns is None:
            self.detected_patterns = []

@dataclass
class CompanyQueryResult:
    """Result format expected by the existing system"""
    is_company_query: bool
    companies: List[str]
    indicators: List[str]
    query_type: str
    confidence: float

class CompanyDetector:
    """Unified company detection with fallback strategies"""
    
    def __init__(self):
        # Simple, focused patterns instead of one massive regex
        self.company_suffixes = [
            r'Inc\.?', r'Corp\.?', r'Corporation', r'LLC', r'Ltd\.?', r'Limited', 
            r'Co\.?', r'Company', r'Group', r'Holdings', r'Technologies', r'Tech',
            r'Systems', r'Solutions', r'Services', r'Partners', r'Enterprises'
        ]
        
        self.company_patterns = [
            # Company name + suffix
            rf'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:{"|".join(self.company_suffixes)})\b',
            
            # "Company of [name]" or similar
            r'\bcompany\s+(?:of\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            
            # CEO/CTO of [company]
            r'\b(?:CEO|CTO|CFO|COO|CMO|founder|president)\s+(?:of\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            
            # Stock ticker patterns
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\((?:NASDAQ|NYSE|OTC):\s*[A-Z]+\)',
            
            # Simple business terms
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:startup|business|firm|organization)\b'
        ]
        
        # Research intent indicators
        self.research_indicators = [
            'about', 'information', 'overview', 'profile', 'details',
            'history', 'background', 'founded', 'ceo', 'headquarters',
            'products', 'services', 'revenue', 'stock', 'financial',
            'news', 'recent', 'latest', 'update', 'announcement'
        ]
        
        # Company indicators
        self.company_indicators = [
            'company', 'corporation', 'corp', 'inc', 'ltd', 'llc', 'co.',
            'business', 'enterprise', 'firm', 'organization', 'startup'
        ]
    
    def detect_companies(self, query: str) -> CompanyQueryResult:
        """Main detection method that returns the format expected by the existing system"""
        query_lower = query.lower()
        
        # Check for company indicators
        found_indicators = []
        for indicator in self.company_indicators:
            if indicator in query_lower:
                found_indicators.append(indicator)
        
        # Check for research indicators
        found_research_indicators = []
        for indicator in self.research_indicators:
            if indicator in query_lower:
                found_research_indicators.append(indicator)
        
        # Try to detect actual company names using patterns
        detected_companies = []
        confidence = 0.0
        
        for pattern in self.company_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                company_name = match.group(1).strip()
                if self._is_valid_company_name(company_name):
                    detected_companies.append(company_name)
                    confidence = max(confidence, 0.8)
        
        # If no companies found via patterns, try fallback detection
        if not detected_companies:
            fallback_info = self._fallback_detection(query)
            if fallback_info.name:
                detected_companies.append(fallback_info.name)
                confidence = max(confidence, fallback_info.confidence)
        
        # Determine if this is a company query
        is_company_query = bool(detected_companies or found_indicators)
        
        # Determine query type
        if found_research_indicators:
            query_type = 'research'
        elif any(term in query_lower for term in ['financial', 'stock', 'revenue']):
            query_type = 'financial'
        elif any(term in query_lower for term in ['news', 'latest', 'recent']):
            query_type = 'news'
        else:
            query_type = 'general'
        
        # Boost confidence if we have both indicators and companies
        if detected_companies and found_indicators:
            confidence = min(1.0, confidence + 0.1)
        
        return CompanyQueryResult(
            is_company_query=is_company_query,
            companies=detected_companies,
            indicators=found_indicators + found_research_indicators,
            query_type=query_type,
            confidence=confidence
        )
    
    def detect(self, query: str) -> CompanyInfo:
        """Main detection method that tries multiple strategies"""
        
        # Try pattern matching first
        for pattern in self.company_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                # Get the company name group (usually group 1)
                company_name = match.group(1).strip()
                if self._is_valid_company_name(company_name):
                    return CompanyInfo(
                        name=company_name,
                        confidence=0.8,
                        detected_patterns=[pattern]
                    )
        
        # Fallback to simpler heuristics
        return self._fallback_detection(query)
    
    def _is_valid_company_name(self, name: str) -> bool:
        """Validate potential company name"""
        # Filter out common false positives
        stop_words = {'and', 'or', 'the', 'for', 'in', 'on', 'at', 'to', 'from', 'with', 'by'}
        words = name.lower().split()
        
        if len(words) == 1 and words[0] in stop_words:
            return False
        
        if len(name) < 2 or len(name) > 100:
            return False
            
        return True
    
    def _fallback_detection(self, query: str) -> CompanyInfo:
        """Fallback detection using simple heuristics"""
        # Look for capitalized words that might be company names
        words = query.split()
        candidates = []
        
        for i, word in enumerate(words):
            if len(word) > 2 and word[0].isupper():
                # Check if next word is also capitalized (company names often have multiple words)
                if i + 1 < len(words) and len(words[i + 1]) > 0 and words[i + 1][0].isupper():
                    candidate = f"{word} {words[i + 1]}"
                    if self._is_valid_company_name(candidate):
                        candidates.append(candidate)
                elif self._is_valid_company_name(word):
                    candidates.append(word)
        
        if candidates:
            # Return the longest candidate (likely most complete company name)
            best_candidate = max(candidates, key=len)
            return CompanyInfo(
                name=best_candidate,
                confidence=0.4,  # Lower confidence for fallback detection
                detected_patterns=["fallback_heuristic"]
            )
        
        return CompanyInfo(name="", confidence=0.0) 