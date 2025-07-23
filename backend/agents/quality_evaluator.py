"""
Quality Evaluation Agent for Multi-Agent Research System

This module contains the QualityEvaluationAgent class responsible for evaluating
the quality and relevance of research findings using LLM-based assessment.
"""

import time
from typing import List, Dict, Any

import structlog

from ..config import Settings
from ..utils import CacheManager, SecurityManager

# Import data classes and base agent from enhanced_research_system
from ..enhanced_research_system import (
    ModelManager, ResourceManager, 
    SearchResult, SubQuestion, QualityAssessment
)
from .base_agent import LLMAgent


class QualityEvaluationAgent(LLMAgent):
    """Agent for evaluating search quality using LLM and unified quality assessor"""
    
    def __init__(self, settings: Settings, cache_manager: CacheManager, 
                 security_manager: SecurityManager, model_manager: ModelManager = None):
        super().__init__("QualityEvaluationAgent", "Quality Assessment", settings, cache_manager, security_manager,
                        model_manager, "quality_evaluation")
        # Initialize unified quality assessor
        from ..core.quality_assessor import UnifiedQualityAssessor
        self.unified_assessor = UnifiedQualityAssessor(settings)
    
    async def evaluate_search_quality(self, sub_question: SubQuestion, 
                                    results: List[SearchResult],
                                    insights: List[str], 
                                    facts: List[str],
                                    resource_manager: ResourceManager) -> QualityAssessment:
        """Evaluate search quality using LLM with unified quality assessor fallback"""
        start_time = time.time()
        
        try:
            # First try LLM-based comprehensive assessment
            content = self._prepare_evaluation_content(sub_question, results, insights, facts)
            
            # Attempt LLM-based quality assessment
            assessment = await self._generate_quality_assessment(content, sub_question, resource_manager)
            
            # Record metrics
            if hasattr(self, 'metrics_collector') and self.metrics_collector:
                self.metrics_collector.record_api_call(
                    self.name, "quality_evaluation", "llm_assessment",
                    start_time, time.time(), {}, success=True
                )
            
            return assessment
            
        except Exception as e:
            self.logger.warning(f"LLM quality assessment failed: {e}")
            
            # Fall back to unified quality assessor
            return self._create_fallback_assessment(results, insights, facts)
    
    def _prepare_evaluation_content(self, sub_question: SubQuestion, 
                                  results: List[SearchResult],
                                  insights: List[str], 
                                  facts: List[str]) -> str:
        """Prepare content for LLM quality evaluation"""
        content = f"Research Question: {sub_question.question}\n\n"
        
        # Add search results summary
        content += f"Search Results ({len(results)} total):\n"
        for i, result in enumerate(results[:10], 1):  # Limit to top 10 for evaluation
            content += f"{i}. {result.title}\n"
            content += f"   URL: {result.url}\n"
            content += f"   Snippet: {result.snippet[:200]}...\n"
            content += f"   Source Type: {result.source_type}\n"
            content += f"   Relevance Score: {result.relevance_score:.2f}\n\n"
        
        # Add insights
        if insights:
            content += f"Extracted Insights ({len(insights)} total):\n"
            for i, insight in enumerate(insights[:5], 1):  # Limit to top 5
                content += f"{i}. {insight}\n"
            content += "\n"
        
        # Add facts
        if facts:
            content += f"Extracted Facts ({len(facts)} total):\n"
            for i, fact in enumerate(facts[:10], 1):  # Limit to top 10
                content += f"{i}. {fact}\n"
            content += "\n"
        
        return content
    
    async def _generate_quality_assessment(self, content: str, 
                                         sub_question: SubQuestion,
                                         resource_manager: ResourceManager) -> QualityAssessment:
        """Generate quality assessment using LLM"""
        prompt = f"""
        You are a research quality analyst. Evaluate the quality of search results and extracted information for the given research question.

        {content}

        Provide a comprehensive quality assessment in JSON format with the following structure:
        {{
            "overall_confidence": <float 0.0-1.0>,
            "relevance_score": <float 0.0-1.0>,
            "authority_score": <float 0.0-1.0>,
            "completeness_score": <float 0.0-1.0>,
            "recency_score": <float 0.0-1.0>,
            "consistency_score": <float 0.0-1.0>,
            "quality_feedback": [<list of specific feedback points>],
            "improvement_suggestions": [<list of actionable suggestions>],
            "assessment_reasoning": "<detailed reasoning for the assessment>"
        }}

        Consider:
        - Relevance: How well do the results address the research question?
        - Authority: Are the sources credible and authoritative?
        - Completeness: Does the information provide comprehensive coverage?
        - Recency: How current is the information?
        - Consistency: Are there conflicting pieces of information?
        """
        
        try:
            api_response = await self._call_fireworks_api(
                prompt, 
                max_tokens=1000, 
                resource_manager=resource_manager,
                operation="quality_assessment"
            )
            
            assessment_data = self._parse_assessment_response(api_response)
            
            return QualityAssessment(
                overall_confidence=assessment_data["overall_confidence"],
                relevance_score=assessment_data["relevance_score"],
                authority_score=assessment_data["authority_score"],
                completeness_score=assessment_data["completeness_score"],
                recency_score=assessment_data["recency_score"],
                consistency_score=assessment_data["consistency_score"],
                quality_feedback=assessment_data["quality_feedback"],
                improvement_suggestions=assessment_data["improvement_suggestions"],
                assessment_reasoning=assessment_data["assessment_reasoning"]
            )
            
        except Exception as e:
            self.logger.warning("Failed to generate LLM quality assessment", error=str(e))
            return self._create_fallback_assessment([], [], [])
    
    def _parse_assessment_response(self, api_response: str) -> Dict[str, Any]:
        """Parse LLM assessment response with error handling"""
        try:
            from ..core.response_parser import ResponseParser
            json_response = ResponseParser.extract_json_from_response(api_response)
            data = ResponseParser.parse_json_response(json_response)
            
            # Validate and clamp scores to 0.0-1.0 range
            return {
                "overall_confidence": max(0.0, min(1.0, data.get("overall_confidence", 0.5))),
                "relevance_score": max(0.0, min(1.0, data.get("relevance_score", 0.5))),
                "authority_score": max(0.0, min(1.0, data.get("authority_score", 0.5))),
                "completeness_score": max(0.0, min(1.0, data.get("completeness_score", 0.5))),
                "recency_score": max(0.0, min(1.0, data.get("recency_score", 0.5))),
                "consistency_score": max(0.0, min(1.0, data.get("consistency_score", 0.5))),
                "quality_feedback": data.get("quality_feedback", [
                    "Quality assessment unavailable due to parsing error"
                ]),
                "improvement_suggestions": data.get("improvement_suggestions", [
                    "Unable to provide improvement suggestions"
                ]),
                "assessment_reasoning": data.get("assessment_reasoning", 
                    "Quality assessment reasoning unavailable due to parsing error")
            }
            
        except Exception as e:
            self.logger.warning("Failed to parse quality assessment response", error=str(e))
            return {
                "overall_confidence": 0.4,
                "relevance_score": 0.4,
                "authority_score": 0.4,
                "completeness_score": 0.4,
                "recency_score": 0.4,
                "consistency_score": 0.4,
                "quality_feedback": ["Assessment parsing failed"],
                "improvement_suggestions": ["Retry quality evaluation"],
                "assessment_reasoning": "Unable to complete quality assessment due to technical error"
            }
    
    def _create_fallback_assessment(self, results: List[SearchResult], 
                                  insights: List[str], 
                                  facts: List[str]) -> QualityAssessment:
        """Create fallback assessment using unified quality assessor"""
        try:
            from ..core.quality_assessor import AssessmentRequest, AssessmentMode
            
            # Create assessment request for fallback mode
            request = AssessmentRequest(
                results=results,
                sub_question=None,  # Will be handled gracefully
                insights=insights,
                facts=facts,
                mode=AssessmentMode.FALLBACK_ONLY
            )
            
            # Get quality metrics from unified assessor
            quality_metrics = self.unified_assessor.assess(request)
            
            return QualityAssessment(
                overall_confidence=quality_metrics.overall_confidence,
                relevance_score=quality_metrics.relevance_score,
                authority_score=quality_metrics.authority_score,
                completeness_score=quality_metrics.completeness_score,
                recency_score=quality_metrics.recency_score,
                consistency_score=quality_metrics.consistency_score,
                quality_feedback=quality_metrics.quality_feedback,
                improvement_suggestions=quality_metrics.improvement_suggestions,
                assessment_reasoning=quality_metrics.assessment_reasoning
            )
            
        except Exception as e:
            self.logger.warning(f"Unified quality assessor fallback failed: {e}")
            
            # Ultimate fallback - basic algorithmic assessment
            if results:
                authority_scores = []
                for result in results:
                    if result.source_type in ["academic", "government"]:
                        authority_scores.append(0.85)
                    elif result.source_type in ["news", "organization"]:
                        authority_scores.append(0.6)
                    elif result.source_type in ["wiki", "reference"]:
                        authority_scores.append(0.4)
                    else:
                        authority_scores.append(0.25)
                authority_score = sum(authority_scores) / len(authority_scores)
                
                # Handle None values safely
                relevance_scores = [r.relevance_score or 0.5 for r in results]
                relevance_score = min(0.8, (len(results) / 10) * 0.6 + 
                                    sum(relevance_scores) / len(relevance_scores) * 0.4)
            else:
                authority_score = 0.1
                relevance_score = 0.15
            
            # Completeness score based on insights and facts
            insight_factor = min(len(insights) / 5, 1.0)
            fact_factor = min(len(facts) / 5, 1.0)
            completeness_score = (insight_factor * 0.6 + fact_factor * 0.4) * 0.7
            
            # Conservative estimates
            recency_score = 0.4
            consistency_score = 0.5
            
            # Calculate overall confidence
            overall_confidence = (
                relevance_score * 0.3 +
                authority_score * 0.25 +
                completeness_score * 0.2 +
                consistency_score * 0.15 +
                recency_score * 0.1
            )
            
            return QualityAssessment(
                overall_confidence=round(overall_confidence, 2),
                relevance_score=round(relevance_score, 2),
                authority_score=round(authority_score, 2),
                completeness_score=round(completeness_score, 2),
                recency_score=round(recency_score, 2),
                consistency_score=round(consistency_score, 2),
                quality_feedback=[
                    f"Basic algorithmic assessment: {len(results)} search results analyzed",
                    f"Content extraction: {len(insights)} insights, {len(facts)} facts identified",
                    "LLM-based quality evaluation unavailable - using basic fallback scoring"
                ],
                improvement_suggestions=[
                    "Retry with LLM-based quality evaluation for more accurate assessment",
                    "Consider refining search terms for better source diversity",
                    "Verify API connectivity for enhanced quality analysis"
                ],
                assessment_reasoning=f"Basic fallback assessment based on {len(results)} results with average authority score {authority_score:.2f}. Limited by basic algorithmic analysis - LLM evaluation recommended for comprehensive quality assessment."
            ) 