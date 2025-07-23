"""
SummarizerAgent - Handles summarization of research findings
"""

import time
import logging
from typing import List, Dict, Any, Optional
import json
import re

from .base_agent import LLMAgent
from ..enhanced_research_system import (
    RetrievalFindings, SubQuestion, Summary, QualityAssessment, 
    ResourceManager
)
from ..config import Settings
from ..utils import CacheManager, SecurityManager
from ..enhanced_research_system import ModelManager


class SummarizerAgent(LLMAgent):
    """Agent responsible for creating summaries from research findings"""
    
    def __init__(self, settings: Settings, cache_manager: CacheManager, 
                 security_manager: SecurityManager, model_manager: ModelManager = None):
        super().__init__(
            name="SummarizerAgent",
            role="Creates comprehensive summaries from research findings",
            settings=settings,
            cache_manager=cache_manager,
            security_manager=security_manager,
            model_manager=model_manager,
            agent_type="summarizer"
        )

    async def create_summary(self, findings: RetrievalFindings, 
                           sub_question: SubQuestion, 
                           resource_manager: ResourceManager,
                           quality_assessment: QualityAssessment = None) -> Summary:
        """Create a comprehensive summary from research findings"""
        start_time = time.time()
        
        try:
            # Prepare content for summarization
            content = self._prepare_content_for_summarization(findings, sub_question, quality_assessment)
            
            if not content.strip():
                return self._create_fallback_summary(
                    findings, sub_question, start_time, 
                    "No content available for summarization", quality_assessment
                )
            
            # Create summary prompt
            summary_prompt = self._create_summary_prompt(content, sub_question, quality_assessment)
            
            try:
                # Call LLM for summary generation
                api_response = await self._call_fireworks_api(
                    summary_prompt, 
                    max_tokens=2500,
                    resource_manager=resource_manager,
                    operation="summarization"
                )
                
                if not api_response or not api_response.strip():
                    return self._create_manual_summary(findings, sub_question, quality_assessment)
                
                # Parse the API response
                summary_data = self._parse_summary_response(api_response)
                
                # Extract sources from findings
                sources = [result.url for result in findings.results if result.url]
                
                processing_time = time.time() - start_time
                
                return Summary(
                    sub_question_id=sub_question.id,
                    question=sub_question.question,
                    answer=summary_data.get('answer', ''),
                    key_points=summary_data.get('key_points', []),
                    sources=sources,
                    confidence_level=summary_data.get('confidence_level', 0.5),
                    word_count=len(summary_data.get('answer', '').split()),
                    processing_time=processing_time
                )
                
            except Exception as api_error:
                self.logger.warning(f"API call failed for summarization: {api_error}")
                return self._create_manual_summary(findings, sub_question, quality_assessment)
                
        except Exception as e:
            self.logger.error(f"Error creating summary for sub-question {sub_question.id}: {e}")
            return self._create_fallback_summary(
                findings, sub_question, start_time, str(e), quality_assessment
            )

    def _prepare_content_for_summarization(self, findings: RetrievalFindings, 
                                         sub_question: SubQuestion, 
                                         quality_assessment: QualityAssessment = None) -> str:
        """Prepare content for summarization"""
        content_parts = []
        
        # Add question context
        content_parts.append(f"Question: {sub_question.question}")
        
        # Add key insights
        if findings.key_insights:
            content_parts.append("\nKey Insights:")
            for insight in findings.key_insights:
                content_parts.append(f"- {insight}")
        
        # Add extracted facts
        if findings.extracted_facts:
            content_parts.append("\nExtracted Facts:")
            for fact in findings.extracted_facts:
                content_parts.append(f"- {fact}")
        
        # Add quality assessment if available
        if quality_assessment:
            content_parts.append(f"\nQuality Assessment:")
            content_parts.append(f"- Overall Confidence: {quality_assessment.overall_confidence:.2f}")
            content_parts.append(f"- Relevance Score: {quality_assessment.relevance_score:.2f}")
            if quality_assessment.quality_feedback:
                content_parts.append("- Quality Feedback:")
                for feedback in quality_assessment.quality_feedback:
                    content_parts.append(f"  - {feedback}")
        
        # Add source snippets (limited to prevent token overflow)
        if findings.results:
            content_parts.append("\nSource Information:")
            for i, result in enumerate(findings.results[:5]):  # Limit to top 5 sources
                content_parts.append(f"\nSource {i+1}: {result.title}")
                content_parts.append(f"URL: {result.url}")
                if result.snippet:
                    content_parts.append(f"Snippet: {result.snippet}")
                if result.content and len(result.content) > 100:
                    content_parts.append(f"Content: {result.content[:500]}...")
        
        return "\n".join(content_parts)

    def _create_summary_prompt(self, content: str, sub_question: SubQuestion, 
                             quality_assessment: QualityAssessment = None) -> str:
        """Create the prompt for summary generation"""
        
        confidence_context = ""
        if quality_assessment:
            confidence_context = f"""
Quality Assessment Context:
- Overall Confidence: {quality_assessment.overall_confidence:.2f}
- Relevance Score: {quality_assessment.relevance_score:.2f}
- Assessment Reasoning: {quality_assessment.assessment_reasoning}
"""
        
        prompt = f"""You are a research analyst tasked with creating a comprehensive summary based on the following research findings.

{confidence_context}

Research Content:
{content}

Please create a detailed summary that includes:

1. A direct, comprehensive answer to the question
2. Key points that support the answer (3-5 bullet points)
3. A confidence level (0.0-1.0) based on the quality and completeness of the information

Format your response as a JSON object with the following structure:
{{
    "answer": "Your comprehensive answer here",
    "key_points": [
        "Key point 1",
        "Key point 2",
        "Key point 3"
    ],
    "confidence_level": 0.85
}}

Guidelines:
- Be factual and objective
- Include specific details and numbers when available
- Acknowledge limitations or uncertainties
- Base confidence level on source quality and information completeness
- If information is limited, state this clearly in your answer
"""
        
        return prompt

    def _create_manual_summary(self, findings: RetrievalFindings, sub_question: SubQuestion, 
                              quality_assessment: QualityAssessment = None) -> Dict[str, Any]:
        """Create a manual summary when AI generation fails"""
        
        # Combine insights and facts
        all_points = []
        if findings.key_insights:
            all_points.extend(findings.key_insights)
        if findings.extracted_facts:
            all_points.extend(findings.extracted_facts)
        
        # Create answer from available information
        if all_points:
            answer = f"Based on the research findings for '{sub_question.question}': " + ". ".join(all_points[:3])
        else:
            answer = f"Limited information found for '{sub_question.question}'. Further research may be needed."
        
        # Determine confidence level
        confidence_level = 0.3  # Low confidence for manual summary
        if quality_assessment:
            confidence_level = max(0.3, quality_assessment.overall_confidence * 0.7)
        elif findings.confidence_score > 0:
            confidence_level = max(0.3, findings.confidence_score * 0.7)
        
        # Create key points
        key_points = all_points[:5] if all_points else ["Limited information available"]
        
        return {
            "answer": answer,
            "key_points": key_points,
            "confidence_level": confidence_level
        }

    def _create_fallback_summary(self, findings: RetrievalFindings, sub_question: SubQuestion, 
                               start_time: float, error_msg: str, quality_assessment: QualityAssessment = None) -> Summary:
        """Create a fallback summary when processing fails"""
        
        processing_time = time.time() - start_time
        
        # Try to extract some basic information
        answer = f"Error occurred during summarization: {error_msg}"
        key_points = ["Summarization process encountered an error"]
        
        if findings.key_insights:
            answer = f"Research findings for '{sub_question.question}': " + ". ".join(findings.key_insights[:2])
            key_points = findings.key_insights[:3]
        
        sources = [result.url for result in findings.results if result.url]
        
        return Summary(
            sub_question_id=sub_question.id,
            question=sub_question.question,
            answer=answer,
            key_points=key_points,
            sources=sources,
            confidence_level=0.2,  # Low confidence for fallback
            word_count=len(answer.split()),
            processing_time=processing_time
        )

    def _parse_summary_response(self, api_response: str) -> Dict[str, Any]:
        """Parse the API response to extract summary data"""
        try:
            # Try to parse as JSON first
            if api_response.strip().startswith('{'):
                return json.loads(api_response)
            
            # If not JSON, try to extract structured information
            summary_data = {
                "answer": "",
                "key_points": [],
                "confidence_level": 0.5
            }
            
            # Extract answer
            answer_match = re.search(r'"answer":\s*"([^"]+)"', api_response)
            if answer_match:
                summary_data["answer"] = answer_match.group(1)
            else:
                # Take first paragraph as answer
                lines = api_response.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('-') and not line.startswith('*'):
                        summary_data["answer"] = line.strip()
                        break
            
            # Extract key points
            key_points = []
            lines = api_response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    key_points.append(line[2:])
                elif line.startswith('• '):
                    key_points.append(line[2:])
            
            if key_points:
                summary_data["key_points"] = key_points
            
            # Extract confidence level
            confidence_match = re.search(r'"confidence_level":\s*([0-9.]+)', api_response)
            if confidence_match:
                summary_data["confidence_level"] = float(confidence_match.group(1))
            
            return summary_data
            
        except Exception as e:
            self.logger.warning(f"Failed to parse summary response: {e}")
            return {
                "answer": api_response[:500] if api_response else "No response received",
                "key_points": ["Response parsing failed"],
                "confidence_level": 0.3
            } 