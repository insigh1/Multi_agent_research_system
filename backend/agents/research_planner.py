"""
Research Planner Agent for Multi-Agent Research System

This module contains the ResearchPlannerAgent class responsible for creating
comprehensive research plans and breaking down complex queries into focused sub-questions.
"""

import asyncio
from typing import Dict, Any, List
import structlog

from ..config import Settings
from ..utils import CacheManager, SecurityManager
from ..core.timeout_manager import with_api_timeout_and_retries
from ..core.error_handler import StandardErrorHandler, ErrorContext, ErrorSeverity, RecoveryStrategy
from ..core.response_parser import ResponseParser

# Import data classes and base agent from enhanced_research_system
from ..enhanced_research_system import (
    ModelManager, ResourceManager, ProgressTracker, 
    QueryRequest, ResearchPlan, SubQuestion
)
from .base_agent import LLMAgent


class ResearchPlannerAgent(LLMAgent):
    """Enhanced research planner with better analysis"""
    
    def __init__(self, settings: Settings, cache_manager: CacheManager, 
                 security_manager: SecurityManager, model_manager: ModelManager = None):
        super().__init__("ResearchPlannerAgent", "Research Planning", settings, cache_manager, security_manager,
                        model_manager, "research_planner")
    
    async def create_research_plan(self, request: QueryRequest, 
                                 resource_manager: ResourceManager, 
                                 progress: ProgressTracker) -> ResearchPlan:
        """Create comprehensive research plan"""
        self.logger.info("Creating research plan", query=request.query)
        progress.update_stage("analyzing_query")
        
        try:
            # Enhanced query analysis
            analysis = self._analyze_query(request.query)
            complexity = self._estimate_complexity(analysis)
            categories = self._classify_categories(request.query, analysis)
            
            # Generate AI-powered research plan
            # Create dynamic JSON template based on requested number of sub-questions
            sub_question_templates = []
            categories_list = ["foundation", "current", "technical", "challenges", "future", "analysis", "implementation"]
            
            for i in range(request.max_sub_questions):
                category = categories_list[i % len(categories_list)]
                priority = 1 if i < 2 else (2 if i < 4 else 3)
                sub_question_templates.append(
                    '{"id": ' + str(i+1) + ', "question": "specific ' + category + ' question", "priority": ' + str(priority) + ', "search_terms": ["term1", "term2"], "category": "' + category + '"}'
                )
            
            sub_questions_json = ",\n        ".join(sub_question_templates)
            
            prompt = f"""You are a research planning specialist. Create a comprehensive research plan for: "{request.query}"

CRITICAL: Respond with ONLY valid JSON. No explanations, no markdown, no additional text.

Generate exactly {request.max_sub_questions} focused sub-questions for thorough coverage.
Consider domain: {analysis['domain']}, complexity: {complexity}, type: {analysis['query_type']}

{{
    "research_strategy": "detailed strategy description (max 200 chars)",
    "estimated_complexity": {int(complexity)},
    "estimated_duration": {complexity * 2.5},
    "sub_questions": [
        {sub_questions_json}
    ]
}}"""
            
            api_response = await self._call_fireworks_api(prompt, None, resource_manager, "research_planning")
            research_plan = self._parse_api_research_plan(request.query, api_response, analysis, categories)
            
            progress.complete_step("research_planning")
            progress.update_stage("research_plan_complete")
            
            self.logger.info("Research plan created", 
                           sub_questions=len(research_plan.sub_questions),
                           estimated_duration=research_plan.estimated_duration)
            
            return research_plan
            
        except Exception as e:
            progress.add_error(f"Research planning failed: {str(e)}")
            
            # Use unified error handler with fallback
            context = ErrorContext(
                operation="create_research_plan",
                component=self.name,
                metadata={"query": request.query}
            )
            handler = StandardErrorHandler()
            
            # Create fallback plan
            fallback_plan = self._create_fallback_plan(request, analysis, categories)
            return handler.handle_error(e, context, ErrorSeverity.MEDIUM, RecoveryStrategy.RETURN_FALLBACK, fallback_plan)
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Enhanced query analysis with company detection"""
        words = query.lower().split()
        
        # Company detection
        company_info = self._detect_company_query(query)
        
        # Query type detection
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which']
        comparison_words = ['vs', 'versus', 'compare', 'difference', 'better']
        how_to_words = ['how to', 'tutorial', 'guide', 'steps']
        
        query_type = "informational"
        if any(word in query.lower() for word in how_to_words):
            query_type = "instructional"
        elif any(word in words for word in comparison_words):
            query_type = "comparative"
        elif any(word in words for word in question_words):
            query_type = "question"
        elif company_info['is_company_query']:
            query_type = "company_research"
        
        # Domain classification with better accuracy
        tech_indicators = ['ai', 'ml', 'software', 'programming', 'api', 'algorithm', 'code']
        science_indicators = ['research', 'study', 'analysis', 'experiment', 'clinical', 'scientific']
        business_indicators = ['market', 'business', 'revenue', 'strategy', 'industry', 'economic']
        medical_indicators = ['health', 'medical', 'disease', 'treatment', 'drug', 'patient']
        
        domain_scores = {
            "technology": sum(1 for word in tech_indicators if word in query.lower()),
            "science": sum(1 for word in science_indicators if word in query.lower()),
            "business": sum(1 for word in business_indicators if word in query.lower()),
            "medical": sum(1 for word in medical_indicators if word in query.lower())
        }
        
        # Boost business domain for company queries
        if company_info['is_company_query']:
            domain_scores['business'] += 2
        
        domain = max(domain_scores, key=domain_scores.get) if max(domain_scores.values()) > 0 else "general"
        
        # Complexity estimation
        complexity_factors = {
            "word_count": min(len(words) / 10, 1.0),
            "domain_specificity": domain_scores.get(domain, 0) / 5,
            "query_type_complexity": {
                "instructional": 0.8, 
                "comparative": 0.9, 
                "question": 0.6, 
                "informational": 0.7,
                "company_research": 0.8
            }[query_type]
        }
        
        complexity = max(1, min(5, sum(complexity_factors.values()) * 2))
        
        return {
            "query_type": query_type,
            "domain": domain,
            "complexity": complexity,
            "word_count": len(words),
            "key_concepts": [word for word in words if len(word) > 4],
            "research_depth": "comprehensive" if complexity > 3 else "focused",
            "domain_scores": domain_scores,
            "company_info": company_info
        }
    
    def _detect_company_query(self, query: str) -> Dict[str, Any]:
        """Simple company detection for research planning - use company_detection.py for comprehensive detection"""
        # Import the clean company detector we created
        from company_detection import CompanyDetector
        
        detector = CompanyDetector()
        company_info = detector.detect_companies(query)
        
        # Convert to the format expected by this class
        return {
            'is_company_query': company_info.is_company_query,
            'detected_companies': company_info.companies,
            'has_company_indicator': len(company_info.indicators) > 0,
            'has_research_indicator': company_info.query_type in ['info', 'analysis', 'research'],
            'confidence': company_info.confidence
        }
    
    def _estimate_complexity(self, analysis: Dict[str, Any]) -> float:
        """Enhanced complexity estimation"""
        base_complexity = analysis["complexity"]
        
        # Domain complexity multipliers
        domain_multipliers = {
            "technology": 1.2,
            "science": 1.3,
            "medical": 1.4,
            "business": 1.1,
            "general": 1.0
        }
        
        # Query type multipliers
        type_multipliers = {
            "comparative": 1.3,
            "instructional": 1.1,
            "question": 1.0,
            "informational": 1.2
        }
        
        complexity_score = (base_complexity * 
                          domain_multipliers.get(analysis["domain"], 1.0) * 
                          type_multipliers.get(analysis["query_type"], 1.0))
        
        return min(5.0, complexity_score)
    
    def _classify_categories(self, query: str, analysis: Dict[str, Any]) -> List[str]:
        """Enhanced category classification"""
        categories = [analysis["domain"]]
        
        query_lower = query.lower()
        
        # Temporal categories
        temporal_indicators = {
            "current_events": ["current", "latest", "recent", "now", "today", "2024", "2023"],
            "trends": ["trend", "future", "emerging", "upcoming", "prediction"],
            "historical": ["history", "past", "evolution", "development", "origin"]
        }
        
        # Content categories
        content_indicators = {
            "comparative": ["vs", "versus", "compare", "difference", "better", "best"],
            "instructional": ["how to", "tutorial", "guide", "steps", "process"],
            "analytical": ["analysis", "research", "study", "investigation"],
            "practical": ["application", "use case", "implementation", "example"]
        }
        
        # Add categories based on indicators
        for category, indicators in {**temporal_indicators, **content_indicators}.items():
            if any(indicator in query_lower for indicator in indicators):
                categories.append(category)
        
        return list(set(categories))
    
    def _parse_api_research_plan(self, user_query: str, api_response: str, 
                               analysis: Dict[str, Any], categories: List[str]) -> ResearchPlan:
        """Parse API response with enhanced error handling"""
        try:
            json_response = ResponseParser.extract_json_from_response(api_response)
            data = ResponseParser.parse_json_response(json_response)
            
            sub_questions = []
            for sq_data in data.get("sub_questions", []):
                sub_question = SubQuestion(
                    id=sq_data["id"],
                    question=sq_data["question"],
                    priority=sq_data["priority"],
                    search_terms=sq_data["search_terms"],
                    estimated_complexity=analysis["complexity"] / 5.0,
                    category=sq_data.get("category", "general")
                )
                sub_questions.append(sub_question)
            
            return ResearchPlan(
                main_query=user_query,
                sub_questions=sub_questions,
                research_strategy=data.get("research_strategy", "Comprehensive AI-assisted research"),
                estimated_complexity=data.get("estimated_complexity", int(analysis["complexity"])),
                estimated_duration=data.get("estimated_duration", analysis["complexity"] * 2.5),
                categories=categories
            )
            
        except Exception as e:
            self.logger.warning("Failed to parse API response", error=str(e))
            return self._create_fallback_plan(QueryRequest(query=user_query), analysis, categories)
    
    def _create_fallback_plan(self, request: QueryRequest, analysis: Dict[str, Any], 
                            categories: List[str]) -> ResearchPlan:
        """Enhanced fallback plan generation"""
        domain = analysis.get("domain", "general")
        query_type = analysis.get("query_type", "informational")
        
        # Domain-specific question templates
        domain_templates = {
            "technology": [
                "What is {topic} and how does it work?",
                "What are the current applications and implementations of {topic}?",
                "What are the advantages and limitations of {topic}?",
                "How does {topic} compare to alternative solutions?",
                "What are the future trends and developments in {topic}?"
            ],
            "business": [
                "What is the current market position and business model of {topic}?",
                "What are the key financial metrics and performance indicators for {topic}?",
                "What are the main challenges and opportunities facing {topic}?",
                "How does {topic} compare to its competitors?",
                "What are the future growth prospects and strategic plans for {topic}?"
            ],
            "science": [
                "What is the current scientific understanding of {topic}?",
                "What are the key research findings and evidence regarding {topic}?",
                "What are the main methodologies and approaches used to study {topic}?",
                "What are the limitations and gaps in current research on {topic}?",
                "What are the future research directions and implications of {topic}?"
            ],
            "medical": [
                "What is the current medical understanding of {topic}?",
                "What are the available treatments and interventions for {topic}?",
                "What are the risk factors and prevention strategies for {topic}?",
                "What are the latest clinical trials and research developments in {topic}?",
                "What are the patient outcomes and quality of life considerations for {topic}?"
            ]
        }
        
        # Get appropriate templates
        templates = domain_templates.get(domain, domain_templates["technology"])
        
        # Create sub-questions using templates
        sub_questions = []
        for i, template in enumerate(templates[:request.max_sub_questions]):
            question = template.format(topic=request.query)
            
            # Generate search terms from the query
            search_terms = [word for word in request.query.lower().split() if len(word) > 2]
            
            sub_question = SubQuestion(
                id=i + 1,
                question=question,
                priority=1 if i < 2 else 2,
                search_terms=search_terms,
                estimated_complexity=analysis.get("complexity", 1.0) / 5.0,
                category=["foundation", "current", "technical", "challenges", "future"][i]
            )
            sub_questions.append(sub_question)
        
        return ResearchPlan(
            main_query=request.query,
            sub_questions=sub_questions,
            research_strategy=f"Fallback {domain} research plan with structured approach",
            estimated_complexity=int(analysis.get("complexity", 3)),
            estimated_duration=analysis.get("complexity", 3) * 2.5,
            categories=categories
        ) 