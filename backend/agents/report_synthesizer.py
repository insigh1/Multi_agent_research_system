"""
ReportSynthesizerAgent - Handles final report synthesis and assembly
"""

import time
import logging
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime

from .base_agent import LLMAgent
from ..enhanced_research_system import (
    Summary, ResearchPlan, FinalReport, QualityAssessment, 
    ResourceManager
)
from ..config import Settings
from ..utils import CacheManager, SecurityManager
from ..enhanced_research_system import ModelManager


class ReportSynthesizerAgent(LLMAgent):
    """Agent responsible for synthesizing final research reports"""
    
    def __init__(self, settings: Settings, cache_manager: CacheManager, 
                 security_manager: SecurityManager, model_manager: ModelManager = None):
        super().__init__(
            name="ReportSynthesizerAgent",
            role="Synthesizes comprehensive final reports from research summaries",
            settings=settings,
            cache_manager=cache_manager,
            security_manager=security_manager,
            model_manager=model_manager,
            agent_type="report_synthesizer"
        )

    async def create_final_report(self, original_query: str, 
                                summaries: List[Summary], 
                                research_plan: ResearchPlan,
                                resource_manager: ResourceManager,
                                quality_evaluations: List[QualityAssessment] = None) -> FinalReport:
        """Create a comprehensive final report from research summaries"""
        start_time = time.time()
        
        try:
            # Prepare content for report synthesis
            content = self._prepare_report_content(
                original_query, summaries, research_plan, quality_evaluations
            )
            
            # Create report synthesis prompt
            report_prompt = self._create_report_prompt(content, original_query, research_plan)
            
            try:
                # Call LLM for report generation
                api_response = await self._call_fireworks_api(
                    report_prompt, 
                    max_tokens=3000,
                    resource_manager=resource_manager,
                    operation="report_synthesis"
                )
                
                if not api_response or not api_response.strip():
                    return self._create_fallback_report(
                        original_query, summaries, research_plan, start_time, 
                        "No response from API", quality_evaluations
                    )
                
                # Parse the API response
                report_data = self._parse_report_response(api_response)
                
                # Collect all sources
                all_sources = set()
                for summary in summaries:
                    all_sources.update(summary.sources)
                
                # Calculate metrics
                processing_time = time.time() - start_time
                total_words = sum(summary.word_count for summary in summaries)
                
                # Calculate overall quality score
                quality_score = self._calculate_overall_quality_score(summaries, quality_evaluations)
                
                return FinalReport(
                    original_query=original_query,
                    executive_summary=report_data.get('executive_summary', ''),
                    detailed_findings=summaries,
                    methodology=report_data.get('methodology', ''),
                    limitations=report_data.get('limitations', []),
                    recommendations=report_data.get('recommendations', []),
                    sources_cited=list(all_sources),
                    completion_timestamp=datetime.now().isoformat(),
                    quality_score=quality_score,
                    processing_time=processing_time,
                    total_sources=len(all_sources),
                    total_words=total_words,
                    research_categories=research_plan.categories if research_plan else []
                )
                
            except Exception as api_error:
                self.logger.warning(f"API call failed for report synthesis: {api_error}")
                return self._create_fallback_report(
                    original_query, summaries, research_plan, start_time, 
                    str(api_error), quality_evaluations
                )
                
        except Exception as e:
            self.logger.error(f"Error creating final report: {e}")
            return self._create_fallback_report(
                original_query, summaries, research_plan, start_time, 
                str(e), quality_evaluations
            )

    def _prepare_report_content(self, original_query: str, summaries: List[Summary], 
                              research_plan: ResearchPlan, 
                              quality_evaluations: List[QualityAssessment] = None) -> str:
        """Prepare content for report synthesis"""
        content_parts = []
        
        # Add original query
        content_parts.append(f"Original Research Query: {original_query}")
        
        # Add research plan context
        if research_plan:
            content_parts.append(f"\nResearch Strategy: {research_plan.research_strategy}")
            content_parts.append(f"Estimated Complexity: {research_plan.estimated_complexity}")
            if research_plan.categories:
                content_parts.append(f"Research Categories: {', '.join(research_plan.categories)}")
        
        # Add summaries
        content_parts.append("\nResearch Findings:")
        for i, summary in enumerate(summaries, 1):
            content_parts.append(f"\n{i}. Question: {summary.question}")
            content_parts.append(f"   Answer: {summary.answer}")
            content_parts.append(f"   Confidence: {summary.confidence_level:.2f}")
            
            if summary.key_points:
                content_parts.append("   Key Points:")
                for point in summary.key_points:
                    content_parts.append(f"   - {point}")
        
        # Add quality assessment summary
        if quality_evaluations:
            content_parts.append("\nQuality Assessment Summary:")
            avg_confidence = sum(qa.overall_confidence for qa in quality_evaluations) / len(quality_evaluations)
            avg_relevance = sum(qa.relevance_score for qa in quality_evaluations) / len(quality_evaluations)
            content_parts.append(f"Average Confidence: {avg_confidence:.2f}")
            content_parts.append(f"Average Relevance: {avg_relevance:.2f}")
        
        return "\n".join(content_parts)

    def _create_report_prompt(self, content: str, original_query: str, 
                            research_plan: ResearchPlan) -> str:
        """Create the prompt for report synthesis"""
        
        prompt = f"""You are a research analyst tasked with creating a comprehensive final report based on the following research findings.

Research Content:
{content}

Please create a detailed final report that includes:

1. An executive summary (2-3 paragraphs) that provides a high-level overview of the findings
2. A methodology section explaining how the research was conducted
3. Key limitations of the research
4. Actionable recommendations based on the findings

Format your response as a JSON object with the following structure:
{{
    "executive_summary": "Your comprehensive executive summary here",
    "methodology": "Explanation of research methodology",
    "limitations": [
        "Limitation 1",
        "Limitation 2"
    ],
    "recommendations": [
        "Recommendation 1",
        "Recommendation 2"
    ]
}}

Guidelines:
- Executive summary should synthesize all findings into a coherent narrative
- Methodology should explain the multi-step research approach
- Limitations should acknowledge gaps or uncertainties in the research
- Recommendations should be specific and actionable
- Maintain objectivity and cite evidence from the findings
- If findings are contradictory, acknowledge this in the summary
"""
        
        return prompt

    def _calculate_overall_quality_score(self, summaries: List[Summary], 
                                       quality_evaluations: List[QualityAssessment] = None) -> float:
        """Calculate overall quality score for the report"""
        if not summaries:
            return 0.0
        
        # Base score on summary confidence levels
        summary_confidence = sum(summary.confidence_level for summary in summaries) / len(summaries)
        
        # Incorporate quality evaluations if available
        if quality_evaluations:
            qa_confidence = sum(qa.overall_confidence for qa in quality_evaluations) / len(quality_evaluations)
            qa_relevance = sum(qa.relevance_score for qa in quality_evaluations) / len(quality_evaluations)
            
            # Weighted average
            quality_score = (summary_confidence * 0.4 + qa_confidence * 0.4 + qa_relevance * 0.2)
        else:
            quality_score = summary_confidence
        
        return min(1.0, max(0.0, quality_score))

    def _create_fallback_report(self, original_query: str, summaries: List[Summary], 
                              research_plan: ResearchPlan, start_time: float, 
                              error_msg: str, quality_evaluations: List[QualityAssessment] = None) -> FinalReport:
        """Create a fallback report when synthesis fails"""
        
        processing_time = time.time() - start_time
        
        # Create basic executive summary from summaries
        executive_summary = f"Research conducted on: {original_query}\n\n"
        
        if summaries:
            executive_summary += "Key findings include:\n"
            for summary in summaries[:3]:  # Take first 3 summaries
                executive_summary += f"- {summary.answer[:200]}...\n"
        else:
            executive_summary += "No research findings available due to processing errors."
        
        # Basic methodology
        methodology = "Multi-step research process involving query planning, web search, content retrieval, quality evaluation, and summarization."
        
        # Collect sources
        all_sources = set()
        for summary in summaries:
            all_sources.update(summary.sources)
        
        # Calculate metrics
        total_words = sum(summary.word_count for summary in summaries)
        quality_score = self._calculate_overall_quality_score(summaries, quality_evaluations)
        
        return FinalReport(
            original_query=original_query,
            executive_summary=executive_summary,
            detailed_findings=summaries,
            methodology=methodology,
            limitations=[f"Report synthesis error: {error_msg}", "Automated fallback report generated"],
            recommendations=["Review research findings manually", "Consider re-running research with refined query"],
            sources_cited=list(all_sources),
            completion_timestamp=datetime.now().isoformat(),
            quality_score=quality_score,
            processing_time=processing_time,
            total_sources=len(all_sources),
            total_words=total_words,
            research_categories=research_plan.categories if research_plan else []
        )

    def _parse_report_response(self, api_response: str) -> Dict[str, Any]:
        """Parse the API response to extract report data"""
        try:
            # Try to parse as JSON first
            if api_response.strip().startswith('{'):
                return json.loads(api_response)
            
            # If not JSON, try to extract structured information
            report_data = {
                "executive_summary": "",
                "methodology": "",
                "limitations": [],
                "recommendations": []
            }
            
            # Extract executive summary
            exec_match = re.search(r'"executive_summary":\s*"([^"]+)"', api_response, re.DOTALL)
            if exec_match:
                report_data["executive_summary"] = exec_match.group(1)
            else:
                # Take first paragraph as executive summary
                lines = api_response.split('\n')
                for line in lines:
                    if line.strip() and len(line.strip()) > 50:
                        report_data["executive_summary"] = line.strip()
                        break
            
            # Extract methodology
            method_match = re.search(r'"methodology":\s*"([^"]+)"', api_response)
            if method_match:
                report_data["methodology"] = method_match.group(1)
            
            # Extract limitations and recommendations
            limitations = []
            recommendations = []
            
            lines = api_response.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if 'limitation' in line.lower():
                    current_section = 'limitations'
                elif 'recommendation' in line.lower():
                    current_section = 'recommendations'
                elif line.startswith('- ') or line.startswith('* '):
                    if current_section == 'limitations':
                        limitations.append(line[2:])
                    elif current_section == 'recommendations':
                        recommendations.append(line[2:])
            
            if limitations:
                report_data["limitations"] = limitations
            if recommendations:
                report_data["recommendations"] = recommendations
            
            return report_data
            
        except Exception as e:
            self.logger.warning(f"Failed to parse report response: {e}")
            return {
                "executive_summary": api_response[:500] if api_response else "No response received",
                "methodology": "Standard research methodology applied",
                "limitations": ["Response parsing failed"],
                "recommendations": ["Manual review recommended"]
            } 