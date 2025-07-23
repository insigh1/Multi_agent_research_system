#!/usr/bin/env python3
"""
Multi-Agent Research System
Copyright (c) 2025 David Lee (@insigh1) - Fireworks AI
MIT License - see LICENSE file for details

Complete Enhanced Multi-Agent Research System - Main Entry Point
===============================================================

Production-ready research system with comprehensive robustness features:
- SEQUENTIAL processing to avoid rate limiting (KEY FIX)
- Rate limiting, retry logic, and circuit breakers
- Caching, session persistence, and progress tracking  
- Security, monitoring, and health checks
- Multiple output formats and error handling
- Full CLI with health checks and session management
"""

import asyncio
import json
import sqlite3
import time
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import structlog
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Import our modules with fallback handling for different execution contexts
# First try: assume we're being called as a module (from root entry point)
try:
    from backend.config import Settings, QueryRequest
    from backend.exceptions import *
    from backend.utils import (
        SecurityManager, CacheManager, ProgressTracker, 
        setup_logging, start_metrics_server, managed_session,
        get_organized_report_path, create_report_index_entry, get_report_summary
    )
    from backend.enhanced_research_system import (
        DatabaseManager, ResourceManager, SubQuestion, AdaptiveSourceFilter, RetrievalFindings
    )
    from backend.agents import (
        ResearchPlannerAgent, WebSearchRetrieverAgent, SummarizerAgent, 
        ReportSynthesizerAgent, QualityEvaluationAgent
    )
except (ImportError, ModuleNotFoundError):
    # Second try: assume we're in the backend directory
    try:
        from config import Settings, QueryRequest
        from exceptions import *
        from utils import (
            SecurityManager, CacheManager, ProgressTracker, 
            setup_logging, start_metrics_server, managed_session,
            get_organized_report_path, create_report_index_entry, get_report_summary
        )
        from enhanced_research_system import (
            DatabaseManager, ResourceManager, SubQuestion, AdaptiveSourceFilter, RetrievalFindings
        )
        from agents import (
            ResearchPlannerAgent, WebSearchRetrieverAgent, SummarizerAgent, 
            ReportSynthesizerAgent, QualityEvaluationAgent
        )
    except (ImportError, ModuleNotFoundError):
        # Third try: relative import (when imported as package)
        from .config import Settings, QueryRequest
        from .exceptions import *
        from .utils import (
            SecurityManager, CacheManager, ProgressTracker, 
            setup_logging, start_metrics_server, managed_session,
            get_organized_report_path, create_report_index_entry, get_report_summary
        )
        from .enhanced_research_system import (
            DatabaseManager, ResourceManager, SubQuestion, AdaptiveSourceFilter, RetrievalFindings
        )
        from .agents import (
            ResearchPlannerAgent, WebSearchRetrieverAgent, SummarizerAgent, 
            ReportSynthesizerAgent, QualityEvaluationAgent
        )

console = Console()


class EnhancedResearchSystem:
    """Main orchestrator with all robustness features + sequential processing"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger(__name__)
        self.progress_callback = None  # Will be set during research
        
        # Initialize core components
        self.security_manager = SecurityManager(settings.encryption_key)
        self.cache_manager = CacheManager(settings)
        self.db_manager = DatabaseManager(settings.db_path)
        
        # Initialize database
        self.db_manager.initialize()
        
        # Setup logging
        setup_logging(settings)
        
        # Start metrics server if enabled
        if settings.enable_metrics:
            start_metrics_server(settings.metrics_port)
        
        self.logger.info("Enhanced Research System initialized", 
                        version="2.0", 
                        features="sequential_processing,rate_limiting,caching,monitoring,security")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.cache_manager.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.cache_manager.disconnect()
        if exc_type:
            self.logger.error("System error during operation", 
                            exc_type=exc_type.__name__, 
                            error=str(exc_val))
    
    # ==================== HELPER METHODS ====================
    
    async def _update_progress(self, stage_name: str, percentage: int, message: str, 
                             stage_id: int, data=None, agent_name: str = None):
        """Centralized progress update handling"""
        if self.progress_callback:
            await self.progress_callback(stage_name, percentage, message, stage_id, data, agent_name)
    
    def _convert_research_plan_to_dict(self, research_plan) -> dict:
        """Convert research plan to dict for web UI"""
        return {
            "main_query": research_plan.main_query,
            "research_strategy": research_plan.research_strategy,
            "estimated_complexity": research_plan.estimated_complexity,
            "estimated_duration": research_plan.estimated_duration,
            "categories": research_plan.categories,
            "sub_questions": [
                {
                    "id": sq.id,
                    "question": sq.question,
                    "priority": sq.priority,
                    "search_terms": sq.search_terms,
                    "category": sq.category,
                    "estimated_complexity": sq.estimated_complexity
                }
                for sq in research_plan.sub_questions
            ]
        }
    
    def _calculate_final_metrics(self, start_time: float, final_report, valid_findings, valid_summaries) -> dict:
        """Calculate final processing metrics"""
        total_time = time.time() - start_time
        final_report.processing_time = total_time
        final_report.total_sources = sum(len(f.results) for f in valid_findings if hasattr(f, 'results'))
        final_report.total_words = sum(getattr(s, 'word_count', 0) for s in valid_summaries)
        return {
            "total_time": total_time,
            "total_sources": final_report.total_sources,
            "total_words": final_report.total_words
        }
    
    # ==================== RESEARCH STAGES ====================
    
    async def _stage_1_research_planning(self, request: QueryRequest, resource_manager, model_manager) -> tuple:
        """Stage 1: Create research plan with sub-questions"""
        from .enhanced_research_system import metrics_collector
        
        self.progress_tracker.update_stage("Research Planning")
        metrics_collector.start_step("Research Planning", "ResearchPlannerAgent")
        
        await self._update_progress("Research Planning", 10, "Creating research plan...", 0, agent_name="ResearchPlannerAgent")
        
        # Initialize Research Planner Agent
        research_planner = ResearchPlannerAgent(
            self.settings, self.cache_manager, self.security_manager, model_manager
        )
        
        # Create research plan
        research_plan = await research_planner.create_research_plan(
            request, resource_manager, self.progress_tracker
        )
        
        # Convert research plan to dict for web UI
        research_plan_dict = self._convert_research_plan_to_dict(research_plan)
        
        # Send research plan completion update
        await self._update_progress("Research Planning", 95, "Research plan created successfully", 0, research_plan_dict, "ResearchPlannerAgent")
        
        # 🔧 FIX: Add delay to let frontend show in-progress state before moving to next stage
        await asyncio.sleep(0.3)
        
        metrics_collector.end_step(success=True)
        
        # Save intermediate result
        if request.save_session:
            self.db_manager.save_result(request.session_id or "temp", "research_plan", research_plan)
        
        return research_plan, research_plan_dict
    
    async def _stage_3_quality_evaluation(self, valid_findings, research_plan, resource_manager, quality_evaluator) -> list:
        """Stage 3: Evaluate information quality and relevance"""
        from .enhanced_research_system import metrics_collector
        
        self.progress_tracker.update_stage("Quality Evaluation")
        metrics_collector.start_step("Quality Evaluation", "QualityEvaluationAgent")
        
        await self._update_progress("Quality Evaluation", 50, "Evaluating information quality and relevance...", 2, agent_name="QualityEvaluationAgent")
        
        # Perform quality evaluation on all findings
        quality_evaluations = []
        for i, findings in enumerate(valid_findings):
            if i < len(research_plan.sub_questions):
                sub_question = research_plan.sub_questions[i]
                try:
                    quality_assessment = await quality_evaluator.evaluate_search_quality(
                        sub_question, 
                        findings.results if hasattr(findings, 'results') else [],
                        findings.key_insights if hasattr(findings, 'key_insights') else [],
                        findings.extracted_facts if hasattr(findings, 'extracted_facts') else [],
                        resource_manager
                    )
                    quality_evaluations.append(quality_assessment)
                    
                    self.logger.info("Quality evaluation completed", 
                                   sub_question_id=sub_question.id,
                                   confidence=quality_assessment.overall_confidence)
                except Exception as e:
                    self.logger.warning("Quality evaluation failed for sub-question", 
                                      sub_question_id=sub_question.id, error=str(e))
                    quality_evaluations.append(None)
        
        # Update quality evaluations in metrics collector for web UI
        metrics_collector.update_quality_evaluations(quality_evaluations, research_plan.sub_questions, valid_findings)
        
        await self._update_progress("Quality Evaluation", 95, "Quality evaluation completed", 2, agent_name="QualityEvaluationAgent")
        
        self.progress_tracker.complete_step("Quality Evaluation")
        metrics_collector.end_step(success=True)
        
        return quality_evaluations
    
    async def _stage_2_information_gathering(self, research_plan, resource_manager, web_searcher) -> list:
        """Stage 2: OPTIMIZED BATCHED Information Gathering with True Parallel Scraping"""
        from .enhanced_research_system import metrics_collector
        
        self.progress_tracker.update_stage("Information Gathering")
        metrics_collector.start_step("Information Gathering", "WebSearchRetrieverAgent")
        
        await self._update_progress("Information Gathering", 25, "Gathering information from web sources...", 1, agent_name="WebSearchRetrieverAgent")
        
        # 🚀 NEW: TRUE BATCHED PARALLEL PROCESSING WITH OPTIMIZED SCRAPING
        self.logger.info("🔄 Using TRUE BATCHED PARALLEL processing with optimized scraping", 
                       total_questions=len(research_plan.sub_questions))
        
        # 🎯 PHASE 1: Collect all URLs from all sub-questions (search-only phase)
        all_url_results, sub_question_metadata = await self._phase_1_collect_urls(research_plan, resource_manager, web_searcher)
        
        # 🚀 PHASE 2: Batch scrape ALL URLs using Firecrawl's full parallel capacity  
        scraped_results_by_question = await self._phase_2_batch_scrape(all_url_results, resource_manager, web_searcher)
        
        # 🎯 PHASE 3: Process scraped results and create findings for each sub-question
        valid_findings = await self._phase_3_process_findings(research_plan, scraped_results_by_question, sub_question_metadata, resource_manager, web_searcher)
        
        if not valid_findings:
            raise ProcessingError("Information Gathering", "All search operations failed")
        
        successful_searches = len(valid_findings)
        total_urls_scraped = sum(len(results) for results in scraped_results_by_question.values())
        self.logger.info("🎉 BATCHED PARALLEL information gathering completed", 
                       successful_searches=successful_searches,
                       total_urls_scraped=total_urls_scraped,
                       sub_questions=len(research_plan.sub_questions))
        
        metrics_collector.end_step(success=True)
        
        # Send detailed final progress update for information gathering
        total_sources = sum(len(f.results) for f in valid_findings if hasattr(f, 'results'))
        total_insights = sum(len(f.key_insights) for f in valid_findings if hasattr(f, 'key_insights') and f.key_insights)
        total_facts = sum(len(f.extracted_facts) for f in valid_findings if hasattr(f, 'extracted_facts') and f.extracted_facts)
        avg_confidence = sum(f.confidence_score for f in valid_findings if hasattr(f, 'confidence_score')) / len(valid_findings) if valid_findings else 0
        
        await self._update_progress("Information Gathering", 95, 
                               f"Information gathering completed successfully: {total_urls_scraped} URLs scraped, {total_sources} sources analyzed, {total_insights} insights + {total_facts} facts extracted (Avg confidence: {avg_confidence:.1%})", 
                               1, agent_name="WebSearchRetrieverAgent")
        
        return valid_findings
    
    async def _phase_1_collect_urls(self, research_plan, resource_manager, web_searcher) -> tuple:
        """Phase 1: Collect all URLs from all sub-questions (search-only phase)"""
        self.logger.info("📊 PHASE 1: Collecting URLs from all sub-questions...")
        all_url_results = []
        sub_question_metadata = {}
        
        # Process all sub-questions for URL collection in parallel
        async def collect_urls_for_question(sub_question):
            try:
                url_results, company_info = await web_searcher.gather_search_urls_only(
                    sub_question, resource_manager
                )
                sub_question_metadata[sub_question.id] = {
                    "sub_question": sub_question,
                    "company_info": company_info
                }
                return url_results
            except Exception as e:
                self.logger.error("Failed to collect URLs for sub-question", 
                                sub_question_id=sub_question.id, error=str(e))
                return []
        
        # Collect URLs from all sub-questions in parallel
        url_collection_tasks = [
            collect_urls_for_question(sub_question) 
            for sub_question in research_plan.sub_questions
        ]
        
        url_collection_results = await asyncio.gather(*url_collection_tasks, return_exceptions=True)
        
        # Flatten all URL results
        for result in url_collection_results:
            if isinstance(result, list):
                all_url_results.extend(result)
            elif isinstance(result, Exception):
                self.logger.error("URL collection failed", error=str(result))
        
        total_urls_collected = len(all_url_results)
        self.logger.info(f"✅ PHASE 1 COMPLETE: Collected {total_urls_collected} URLs from {len(research_plan.sub_questions)} sub-questions")
        
        await self._update_progress("Information Gathering", 40, f"Collected {total_urls_collected} URLs for batched scraping", 1, agent_name="WebSearchRetrieverAgent")
        
        return all_url_results, sub_question_metadata
    
    async def _phase_2_batch_scrape(self, all_url_results, resource_manager, web_searcher) -> dict:
        """Phase 2: Batch scrape ALL URLs using Firecrawl's full parallel capacity"""
        total_urls_collected = len(all_url_results)
        self.logger.info(f"🚀 PHASE 2: Starting TRUE batched parallel scraping of {total_urls_collected} URLs...")
        
        if all_url_results:
            scraped_results_by_question = await web_searcher.batch_scrape_all_urls(
                all_url_results, resource_manager
            )
            
            # Send progress update
            total_scraped = sum(len(results) for results in scraped_results_by_question.values())
            await self._update_progress("Information Gathering", 60, f"Scraped {total_scraped} URLs in parallel batches", 1, agent_name="WebSearchRetrieverAgent")
            
            self.logger.info(f"✅ PHASE 2 COMPLETE: Scraped {total_scraped} results across {len(scraped_results_by_question)} sub-questions")
        else:
            scraped_results_by_question = {}
            self.logger.warning("No URLs collected for scraping")
        
        return scraped_results_by_question
    
    async def _phase_3_process_findings(self, research_plan, scraped_results_by_question, sub_question_metadata, resource_manager, web_searcher) -> list:
        """Phase 3: Process scraped results and create findings for each sub-question"""
        # Import with fallback handling
        try:
            from backend.enhanced_research_system import metrics_collector
        except (ImportError, ModuleNotFoundError):
            try:
                from enhanced_research_system import metrics_collector
            except (ImportError, ModuleNotFoundError):
                from .enhanced_research_system import metrics_collector
        
        self.logger.info("📊 PHASE 3: Processing scraped results and generating findings...")
        
        all_findings = []
        for sub_question in research_plan.sub_questions:
            try:
                # Get scraped results for this sub-question
                scraped_results = scraped_results_by_question.get(sub_question.id, [])
                metadata = sub_question_metadata.get(sub_question.id, {})
                company_info = metadata.get("company_info", {})
                
                self.logger.info(f"Processing findings for sub-question {sub_question.id}", 
                               scraped_count=len(scraped_results))
                
                if scraped_results:
                    # Apply relevance scoring and filtering
                    if company_info.get('is_company_query', False):
                        scored_results = web_searcher._score_relevance_with_company_priority(
                            scraped_results, sub_question.question, company_info
                        )
                    else:
                        company_info_default = {"is_company_query": False, "detected_companies": []}
                        scored_results = web_searcher._score_relevance_with_company_priority(
                            scraped_results, sub_question.question, company_info_default
                        )
                    
                    # Apply source filtering if enabled
                    if web_searcher.source_filter:
                        filtering_decision = web_searcher.source_filter.filter_sources(scored_results, sub_question)
                        filtered_results = filtering_decision.filtered_results
                        
                        # Update metrics collector with filtering information
                        metrics_collector.update_source_filtering(filtering_decision, scored_results)
                    else:
                        filtered_results = scored_results[:12]
                    
                    # Update metrics collector with current sources
                    metrics_collector.update_sources(filtered_results)
                    
                    # Extract insights and facts using AI
                    key_insights, extracted_facts = await web_searcher._extract_insights_with_ai(
                        filtered_results, sub_question, resource_manager
                    )
                    
                    # Calculate confidence score
                    confidence_score = web_searcher._calculate_confidence_score(
                        filtered_results, key_insights, extracted_facts
                    )
                    
                    # Create findings
                    findings = RetrievalFindings(
                        sub_question_id=sub_question.id,
                        query_used=sub_question.question,
                        results=filtered_results,
                        key_insights=key_insights,
                        extracted_facts=extracted_facts,
                        confidence_score=confidence_score,
                        processing_time=0.0,  # Will be calculated at the end
                        sources_count=len(filtered_results)
                    )
                    
                    all_findings.append(findings)
                    
                    self.logger.info(f"✅ Sub-question {sub_question.id} processed", 
                                   results_count=len(filtered_results),
                                   confidence=confidence_score)
                else:
                    # Create empty findings for sub-questions with no results
                    empty_findings = RetrievalFindings(
                        sub_question_id=sub_question.id,
                        query_used=sub_question.question,
                        results=[],
                        key_insights=["No information found for this question"],
                        extracted_facts=["No facts could be extracted"],
                        confidence_score=0.0,
                        processing_time=0.0,
                        sources_count=0
                    )
                    all_findings.append(empty_findings)
                    
                    self.logger.warning(f"No results for sub-question {sub_question.id}")
                    
            except Exception as e:
                self.logger.error(f"Failed to process sub-question {sub_question.id}", error=str(e))
                # Create fallback findings
                fallback_findings = RetrievalFindings(
                    sub_question_id=sub_question.id,
                    query_used=sub_question.question,
                    results=[],
                    key_insights=["Failed to process this question due to technical issues"],
                    extracted_facts=["No facts could be extracted"],
                    confidence_score=0.0,
                    processing_time=0.0,
                    sources_count=0
                )
                all_findings.append(fallback_findings)
        
        self.logger.info(f"🎉 PHASE 3 COMPLETE: Generated findings for {len(all_findings)} sub-questions")
        return all_findings
    
    async def _stage_4_content_summarization(self, valid_findings, research_plan, quality_evaluations, resource_manager, summarizer) -> list:
        """Stage 4: Content Summarization with parallel processing"""
        # Import with fallback handling
        try:
            from backend.enhanced_research_system import metrics_collector
        except (ImportError, ModuleNotFoundError):
            try:
                from enhanced_research_system import metrics_collector
            except (ImportError, ModuleNotFoundError):
                from .enhanced_research_system import metrics_collector
        
        self.progress_tracker.update_stage("Content Summarization")
        metrics_collector.start_step("Content Summarization", "SummarizerAgent")
        
        await self._update_progress("Content Summarization", 70, "Analyzing and summarizing content...", 3, agent_name="ContentSummarizerAgent")
        
        # 🚀 ENHANCED: Parallel summarization with smart throttling
        async def create_summaries_parallel():
            """Create summaries in parallel with controlled concurrency"""
            summary_semaphore = asyncio.Semaphore(self.settings.max_parallel_summaries)  # Configurable concurrent summaries
            
            async def process_single_summary(findings, question, summary_index, quality_eval):
                async with summary_semaphore:
                    try:
                        if summary_index > 0:
                            await asyncio.sleep(0.5)  # Short delay between summaries
                        
                        summary = await summarizer.create_summary(
                            findings, question, resource_manager, quality_eval
                        )
                        
                        self.logger.info(f"📄 Summary {summary_index+1} completed")
                        return summary
                        
                    except Exception as e:
                        self.logger.error(f"❌ Summary {summary_index+1} failed", error=str(e))
                        return e
            
            # Create summary tasks
            summary_tasks = []
            for i, findings in enumerate(valid_findings):
                if i < len(research_plan.sub_questions):
                    # Get corresponding quality evaluation
                    quality_eval = quality_evaluations[i] if i < len(quality_evaluations) else None
                    task = process_single_summary(
                        findings, 
                        research_plan.sub_questions[i], 
                        i,
                        quality_eval
                    )
                    summary_tasks.append(task)
            
            # Execute summaries in parallel
            self.logger.info("📝 Processing summaries in parallel", 
                           total_summaries=len(summary_tasks))
            
            summary_results = await asyncio.gather(*summary_tasks, return_exceptions=True)
            
            # Filter valid summaries
            valid_summaries = [s for s in summary_results if not isinstance(s, Exception)]
            return valid_summaries
        
        valid_summaries = await create_summaries_parallel()
        
        if not valid_summaries:
            raise ProcessingError("Content Summarization", "All summarization operations failed")
        
        # Update metrics collector with summaries for web UI
        metrics_collector.update_summaries(valid_summaries)
        
        await self._update_progress("Content Summarization", 95, f"Content summarization completed - {len(valid_summaries)} summaries generated", 3, agent_name="ContentSummarizerAgent")
        
        self.progress_tracker.complete_step("Content Summarization")
        metrics_collector.end_step(success=True)
        
        return valid_summaries
    
    async def _stage_5_report_assembly(self, request, valid_summaries, research_plan, resource_manager, quality_evaluations, report_synthesizer, start_time) -> dict:
        """Stage 5: Report Assembly with final metrics"""
        # Import with fallback handling
        try:
            from backend.enhanced_research_system import metrics_collector
        except (ImportError, ModuleNotFoundError):
            try:
                from enhanced_research_system import metrics_collector
            except (ImportError, ModuleNotFoundError):
                from .enhanced_research_system import metrics_collector
        
        self.progress_tracker.update_stage("Report Assembly")
        metrics_collector.start_step("Report Assembly", "ReportSynthesizerAgent")
        
        await self._update_progress("Report Assembly", 85, "Assembling final research report...", 4, agent_name="ReportSynthesizerAgent")
        
        final_report = await report_synthesizer.create_final_report(
            request.query, valid_summaries, research_plan, resource_manager, quality_evaluations
        )
        
        # Update metrics collector with final report data for web UI
        metrics_collector.update_final_report(final_report) 
        
        await self._update_progress("Report Assembly", 95, f"Final research report completed - {len(final_report.detailed_findings)} detailed findings assembled", 4, agent_name="ReportSynthesizerAgent")
        
        self.progress_tracker.complete_step("Report Assembly")
        metrics_collector.end_step(success=True)
        self.progress_tracker.update_stage("Completed")
        
        return final_report

    async def conduct_research(self, request: QueryRequest, progress_callback=None) -> dict:
        """Main research orchestration with SEQUENTIAL processing and comprehensive error handling"""
        
        # Store progress callback for use in helper methods
        self.progress_callback = progress_callback
        
        # Generate session ID if not provided
        session_id = request.session_id or self.security_manager.generate_session_id()
        
        # Initialize metrics tracking
        # Import with fallback handling
        try:
            from backend.enhanced_research_system import metrics_collector, MetricsFormatter
        except (ImportError, ModuleNotFoundError):
            try:
                from enhanced_research_system import metrics_collector, MetricsFormatter
            except (ImportError, ModuleNotFoundError):
                from .enhanced_research_system import metrics_collector, MetricsFormatter
        # Note: pipeline_metrics already started in web_ui.py, don't reinitialize here
        # pipeline_metrics = metrics_collector.start_pipeline(session_id, request.query)
        
        # Debug: Check if pipeline is properly initialized
        current_metrics = metrics_collector.get_metrics_summary()
        print(f"🔍 DEBUG main.py - Pipeline initialized check:")
        print(f"   Pipeline exists: {metrics_collector.current_pipeline is not None}")
        print(f"   Current metrics keys: {list(current_metrics.keys())}")
        print(f"   Total API calls in pipeline: {current_metrics.get('total_api_calls', 'NOT_FOUND')}")
        
        # Initialize progress tracking  
        self.progress_tracker = ProgressTracker(total_steps=7, session_id=session_id)
        
        try:
            async with managed_session(self.db_manager, session_id):
                
                # Check for existing session
                if request.session_id:
                    existing_session = self.db_manager.load_session(session_id)
                    if existing_session:
                        self.logger.info("Resuming existing session", session_id=session_id)
                        # Could implement session resumption logic here
                
                start_time = time.time()
                self.progress_tracker.update_stage("Initializing Research")
                
                # Create resource manager for HTTP requests
                async with ResourceManager(self.settings) as resource_manager:
                    
                    # Initialize Model Manager for multi-model architecture
                    from enhanced_research_system import ModelManager
                    model_manager = ModelManager(self.settings)
                    
                    # Initialize agents with specialized models
                    research_planner = ResearchPlannerAgent(
                        self.settings, self.cache_manager, self.security_manager, model_manager
                    )
                    
                    # Initialize Quality Evaluation Agent
                    quality_evaluator = QualityEvaluationAgent(
                        self.settings, self.cache_manager, self.security_manager, model_manager
                    )
                    
                    web_searcher = WebSearchRetrieverAgent(
                        self.settings, self.cache_manager, self.security_manager, quality_evaluator, model_manager
                    )
                    
                    summarizer = SummarizerAgent(
                        self.settings, self.cache_manager, self.security_manager, model_manager
                    )
                    
                    report_synthesizer = ReportSynthesizerAgent(
                        self.settings, self.cache_manager, self.security_manager, model_manager
                    )
                    
                    self.progress_tracker.complete_step("Agent Initialization")
                    
                    # Stage 1: Research Planning
                    research_plan, research_plan_dict = await self._stage_1_research_planning(
                        request, resource_manager, model_manager
                    )
                    
                    # Stage 2: Information Gathering
                    valid_findings = await self._stage_2_information_gathering(
                        research_plan, resource_manager, web_searcher
                    )
                    
                    # Stage 3: Quality Evaluation
                    quality_evaluations = await self._stage_3_quality_evaluation(
                        valid_findings, research_plan, resource_manager, quality_evaluator
                    )
                    
                    # Stage 4: Content Summarization
                    valid_summaries = await self._stage_4_content_summarization(
                        valid_findings, research_plan, quality_evaluations, resource_manager, summarizer
                    )
                    
                    # Stage 5: Report Assembly
                    final_report = await self._stage_5_report_assembly(
                        request, valid_summaries, research_plan, resource_manager, quality_evaluations, report_synthesizer, start_time
                    )
                    
                    # Add processing metrics
                    final_metrics = self._calculate_final_metrics(start_time, final_report, valid_findings, valid_summaries)
                    
                    # Capture pipeline data BEFORE end_pipeline() clears it
                    pipeline_data = None
                    if metrics_collector.current_pipeline:
                        pipeline_data = {
                            "total_api_calls": metrics_collector.current_pipeline.total_api_calls,
                            "total_tokens": metrics_collector.current_pipeline.total_tokens,
                            "estimated_cost": metrics_collector.current_pipeline.total_cost,
                            "total_cache_hits": metrics_collector.current_pipeline.total_cache_hits
                        }
                    
                    # Finalize pipeline metrics
                    pipeline_metrics = metrics_collector.end_pipeline(success=True)
                    
                    # Get model usage and cost summary
                    cost_summary = model_manager.get_cost_summary()
                    
                    # Display CLI metrics summary with model breakdown
                    print("\n" + MetricsFormatter.format_cli_summary(pipeline_metrics))
                    
                    # Display model usage breakdown
                    if cost_summary['agent_costs']:
                        print("\n🤖 Model Usage Breakdown:")
                        print("-" * 50)
                        for agent_type, agent_data in cost_summary['agent_costs'].items():
                            print(f"{agent_type.replace('_', ' ').title()}:")
                            print(f"  Model: {agent_data['model']}")
                            print(f"  Tokens: {agent_data['total_tokens']:,}")
                            print(f"  Cost: ${agent_data['total_cost']:.4f}")
                        print(f"\nTotal Cost: ${cost_summary['total_cost']:.4f}")
                        print(f"Total Tokens: {cost_summary['total_tokens']:,}")
                    
                    # Add cost summary to session metadata
                    session_metadata = {
                        "metrics": MetricsFormatter.format_web_summary(pipeline_metrics),
                        "processing_time": final_metrics["total_time"],
                        "sources_found": final_metrics["total_sources"],
                        "quality_score": getattr(final_report, 'quality_score', 0),
                        "model_usage": cost_summary
                    }
                    
                    # Save final session
                    if request.save_session:
                        try:
                            session_data = {
                                "request": asdict(request) if is_dataclass(request) else str(request),
                                "research_plan": asdict(research_plan) if is_dataclass(research_plan) else str(research_plan),
                                "findings": [asdict(f) if is_dataclass(f) else str(f) for f in valid_findings],
                                "summaries": [asdict(s) if is_dataclass(s) else str(s) for s in valid_summaries],
                                "final_report": asdict(final_report) if is_dataclass(final_report) else str(final_report),
                                "progress": self.progress_tracker.get_progress()
                            }
                            
                            # session_metadata already defined above with model usage
                            
                            self.db_manager.save_session(
                                session_id, request.query, "completed", session_data, session_metadata
                            )
                        except Exception as save_error:
                            self.logger.warning("Failed to save session", error=str(save_error))
                            # Continue without saving session
                    
                    self.logger.info("✅ Research completed successfully",
                                   session_id=session_id,
                                   processing_time=f"{final_metrics['total_time']:.2f}s",
                                   quality_score=getattr(final_report, 'quality_score', 0),
                                   total_sources=final_metrics["total_sources"])
                    
                    return {
                        "success": True,
                        "session_id": session_id,
                        "report": final_report,
                        "progress": self.progress_tracker.get_progress(),
                        "metrics": MetricsFormatter.format_web_summary(pipeline_metrics),
                        "pipeline_data": pipeline_data,  # Add captured pipeline data for web UI
                        "metadata": {
                            "processing_time": final_metrics["total_time"],
                            "sources_found": final_metrics["total_sources"],
                            "quality_score": getattr(final_report, 'quality_score', 0)
                        }
                    }
        
        except Exception as e:
            # Finalize pipeline metrics with error
            pipeline_metrics = None
            try:
                pipeline_metrics = metrics_collector.end_pipeline(success=False, error=str(e))
                print("\n" + MetricsFormatter.format_cli_summary(pipeline_metrics))
            except:
                pass  # Don't let metrics errors mask the original error
            
            error_details = {
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "progress": self.progress_tracker.get_progress()
            }
            
            self.logger.error("Research failed", **error_details)
            
            # Save failed session with metrics if available
            if request.save_session:
                error_metadata = {}
                if pipeline_metrics:
                    error_metadata["metrics"] = MetricsFormatter.format_web_summary(pipeline_metrics)
                
                self.db_manager.save_session(
                    session_id, request.query, "failed", error_details, error_metadata
                )
            
            # Return error response with partial results if available
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "progress": self.progress_tracker.get_progress(),
                "partial_results": getattr(e, 'partial_results', None)
            }
    
    async def health_check(self) -> dict:
        """Comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {},
            "metrics": {}
        }
        
        try:
            # Check cache system
            cache_health = await self.cache_manager.health_check()
            health_status["services"]["cache"] = cache_health
            
            # Check database
            try:
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    conn.execute("SELECT 1").fetchone()
                health_status["services"]["database"] = {"status": "healthy"}
            except Exception as e:
                health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "degraded"
            
            # Check API keys
            api_status = {}
            if self.security_manager.validate_api_key(self.settings.fireworks_api_key, "fireworks"):
                api_status["fireworks"] = "configured"
            else:
                api_status["fireworks"] = "missing_or_invalid"
                health_status["status"] = "degraded"
            
            if self.settings.brave_api_key:
                if self.security_manager.validate_api_key(self.settings.brave_api_key, "brave"):
                    api_status["brave"] = "configured"
                else:
                    api_status["brave"] = "invalid"
            else:
                api_status["brave"] = "not_configured"
            
            health_status["services"]["apis"] = api_status
            
            # Add system metrics
            health_status["metrics"] = {
                "cache_size": len(self.cache_manager.local_cache),
                "max_concurrent_requests": self.settings.max_concurrent_requests,
                "rate_limit": self.settings.requests_per_minute,
                "processing_mode": "sequential"
            }
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status


# CLI Interface
@click.group()
@click.option('--config-file', default='.env', help='Configuration file path')
@click.option('--log-level', default='INFO', help='Logging level')
@click.pass_context
def cli(ctx, config_file, log_level):
    """Enhanced Multi-Agent Research System with Sequential Processing"""
    ctx.ensure_object(dict)
    
    try:
        settings = Settings(_env_file=config_file)
        settings.log_level = log_level
        ctx.obj['settings'] = settings
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--max-questions', default=5, help='Maximum sub-questions')
@click.option('--output-format', default='console', type=click.Choice(['console', 'json', 'html', 'pdf']))
@click.option('--save-session', is_flag=True, help='Save research session')
@click.option('--session-id', help='Resume existing session')
@click.option('--executive-summary-style', default='comprehensive', 
              type=click.Choice(['brief', 'detailed', 'comprehensive']),
              help='Executive summary style: brief=2-3 sentences, detailed=4-6 sentences with implications, comprehensive=full paragraph with analysis')
@click.pass_context
def research(ctx, query, max_questions, output_format, save_session, session_id, executive_summary_style):
    """Conduct research on a query with sequential processing"""
    
    async def run_research():
        settings = ctx.obj['settings']
        
        # Apply CLI override for executive summary style
        settings.executive_summary_style = executive_summary_style
        
        try:
            # Validate request
            request = QueryRequest(
                query=query,
                max_sub_questions=max_questions,
                output_format=output_format,
                save_session=save_session,
                session_id=session_id
            )
            
            async with EnhancedResearchSystem(settings) as system:
                
                console.print(f"🔍 [bold blue]Starting research:[/bold blue] {query}")
                console.print(f"📊 Max questions: {max_questions}")
                console.print(f"🔄 Processing mode: [bold green]INTELLIGENT PARALLEL[/bold green] (rate-limit safe)")
                console.print(f"📝 Executive summary style: [bold cyan]{executive_summary_style.upper()}[/bold cyan]")
                console.print()
                
                # Show progress
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Researching...", total=None)
                    
                    # Start research
                    result = await system.conduct_research(request)
                    
                    progress.update(task, description="✅ Research completed!")
                
                if result["success"]:
                    # Display results based on format
                    if output_format == 'console':
                        display_console_report(result["report"])
                    elif output_format == 'json':
                        # Pretty print JSON with syntax highlighting and better formatting
                        if is_dataclass(result["report"]):
                            report_data = asdict(result["report"])
                        else:
                            report_data = result["report"]
                        
                        # Use Rich's JSON pretty printing for better terminal display
                        console.print("\n🔍 [bold blue]Research Report (JSON Format)[/bold blue]")
                        console.print("─" * 60)
                        console.print_json(data=report_data)
                        console.print("─" * 60)
                        
                        # Save JSON to organized directory structure
                        json_filepath = get_organized_report_path(
                            result['session_id'], 'json', query
                        )
                        with open(json_filepath, 'w', encoding='utf-8') as f:
                            json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)
                        
                        # Create index entry
                        create_report_index_entry(
                            json_filepath, result['session_id'], query, 'json',
                            result.get('metadata', {})
                        )
                        
                        console.print(f"[green]✓ Report displayed in JSON format[/green]")
                        console.print(f"[green]✓ JSON report saved to {json_filepath}[/green]")
                    elif output_format == 'html':
                        html_output = generate_html_report(result["report"])
                        html_filepath = get_organized_report_path(
                            result['session_id'], 'html', query
                        )
                        html_filepath.write_text(html_output, encoding='utf-8')
                        
                        # Create index entry
                        create_report_index_entry(
                            html_filepath, result['session_id'], query, 'html',
                            result.get('metadata', {})
                        )
                        
                        console.print(f"[green]Report saved to {html_filepath}[/green]")
                    elif output_format == 'pdf':
                        pdf_filepath = generate_pdf_report(result["report"], result['session_id'], query)
                        
                        # Create index entry
                        create_report_index_entry(
                            pdf_filepath, result['session_id'], query, 'pdf',
                            result.get('metadata', {})
                        )
                        
                        console.print(f"[green]Report saved to {pdf_filepath}[/green]")
                    
                    # Show metadata
                    metadata = result["metadata"]
                    console.print(f"\n[bold green]✓ Research completed successfully[/bold green]")
                    console.print(f"Session ID: {result['session_id']}")
                    console.print(f"Processing time: {metadata['processing_time']:.2f}s")
                    console.print(f"Sources found: {metadata['sources_found']}")
                    console.print(f"Quality score: {metadata['quality_score']:.2f}")
                    
                    # Show model usage if available
                    if 'model_usage' in metadata and metadata['model_usage']['total_cost'] > 0:
                        console.print(f"Total cost: ${metadata['model_usage']['total_cost']:.4f}")
                        console.print(f"Total tokens: {metadata['model_usage']['total_tokens']:,}")
                    
                else:
                    console.print(f"[bold red]✗ Research failed[/bold red]")
                    console.print(f"Error: {result['error']}")
                    console.print(f"Session ID: {result['session_id']}")
                    
                    if result.get('partial_results'):
                        console.print("[yellow]Partial results available in session[/yellow]")
        
        except ValidationError as e:
            console.print(f"[red]Validation error: {e.message}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]System error: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(run_research())


@cli.command()
@click.pass_context  
def health(ctx):
    """Check system health"""
    
    async def check_health():
        settings = ctx.obj['settings']
        
        async with EnhancedResearchSystem(settings) as system:
            health_status = await system.health_check()
            
            # Create health table
            table = Table(title="System Health Check")
            table.add_column("Component", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Details")
            
            # Overall status
            status_color = "green" if health_status["status"] == "healthy" else "red"
            table.add_row("Overall", f"[{status_color}]{health_status['status'].upper()}[/{status_color}]", "")
            
            # Services
            for service, details in health_status["services"].items():
                if isinstance(details, dict):
                    if "status" in details:
                        # Standard service status (database, etc.)
                        service_status = details["status"]
                        service_color = "green" if service_status == "healthy" else "red"
                        error_info = details.get("error", "")
                        table.add_row(service.title(), f"[{service_color}]{service_status.upper()}[/{service_color}]", error_info)
                    elif service == "cache":
                        # Special handling for cache service
                        for cache_type, cache_status in details.items():
                            if isinstance(cache_status, dict):
                                # Determine cache status
                                if cache_type == "local_cache":
                                    status = "ENABLED" if cache_status.get("enabled", False) else "DISABLED"
                                    color = "green" if cache_status.get("enabled", False) else "yellow"
                                    info = f"Size: {cache_status.get('size', 0)}"
                                elif cache_type == "redis":
                                    enabled = cache_status.get("enabled", False)
                                    connected = cache_status.get("connected", False)
                                    if enabled and connected:
                                        status = "CONNECTED"
                                        color = "green"
                                        info = ""
                                    elif enabled and not connected:
                                        status = "DISCONNECTED"
                                        color = "yellow"
                                        info = "Enabled but not connected"
                                    else:
                                        status = "DISABLED"
                                        color = "dim"
                                        info = "Not configured"
                                else:
                                    status = "UNKNOWN"
                                    color = "yellow"
                                    info = "Unexpected cache type"
                                
                                table.add_row(f"{service}/{cache_type}", f"[{color}]{status}[/{color}]", info)
                    else:
                        # API status or other simple key-value pairs
                        for api, status in details.items():
                            # Handle case where status might not be a string
                            if isinstance(status, str):
                                api_color = "green" if status == "configured" else "yellow"
                                table.add_row(f"{service}/{api}", f"[{api_color}]{status.upper()}[/{api_color}]", "")
                            else:
                                # Skip non-string status values or show type info
                                table.add_row(f"{service}/{api}", f"[yellow]COMPLEX[/yellow]", f"Type: {type(status).__name__}")
            
            console.print(table)
            
            # Metrics
            if health_status.get("metrics"):
                console.print("\n[bold]System Metrics:[/bold]")
                for metric, value in health_status["metrics"].items():
                    console.print(f"  {metric}: {value}")
    
    asyncio.run(check_health())


@cli.command()
@click.option('--list-sessions', is_flag=True, help='List all sessions')
@click.option('--session-id', help='Show specific session')
@click.pass_context
def sessions(ctx, list_sessions, session_id):
    """Manage research sessions"""
    
    settings = ctx.obj['settings']
    db_manager = DatabaseManager(settings.db_path)
    
    if list_sessions:
        # List all sessions
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.execute("""
                SELECT session_id, query, status, created_at, updated_at 
                FROM research_sessions 
                ORDER BY updated_at DESC 
                LIMIT 20
            """)
            
            sessions_data = cursor.fetchall()
            
            if sessions_data:
                table = Table(title="Recent Research Sessions")
                table.add_column("Session ID", style="cyan")
                table.add_column("Query", max_width=50)
                table.add_column("Status")
                table.add_column("Created", style="dim")
                
                for row in sessions_data:
                    status_color = "green" if row[2] == "completed" else "red" if row[2] == "failed" else "yellow"
                    table.add_row(
                        row[0][:12] + "...",  # Truncated session ID
                        row[1][:47] + "..." if len(row[1]) > 50 else row[1],
                        f"[{status_color}]{row[2]}[/{status_color}]",
                        row[3]
                    )
                
                console.print(table)
            else:
                console.print("[yellow]No sessions found[/yellow]")
    
    elif session_id:
        # Show specific session
        session_data = db_manager.load_session(session_id)
        if session_data:
            console.print_json(json.dumps(session_data, indent=2, default=str))
        else:
            console.print(f"[red]Session {session_id} not found[/red]")
    
    else:
        console.print("Use --list-sessions or --session-id <id>")


@cli.command()
@click.option('--list-reports', is_flag=True, help='List all reports')
@click.option('--summary', is_flag=True, help='Show report summary statistics')
@click.option('--cleanup', type=int, help='Clean up reports older than N days')
@click.option('--format', 'report_format', help='Filter by report format (pdf, html, json)')
@click.pass_context
def reports(ctx, list_reports, summary, cleanup, report_format):
    """Manage research reports"""
    
    if summary:
        # Show report statistics
        stats = get_report_summary()
        
        table = Table(title="Report Summary Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Total Reports", str(stats["total_reports"]))
        table.add_row("Total Size", f"{stats['total_size'] / 1024 / 1024:.1f} MB")
        
        if stats["oldest_report"]:
            table.add_row("Oldest Report", stats["oldest_report"][:19].replace('T', ' '))
        if stats["newest_report"]:
            table.add_row("Newest Report", stats["newest_report"][:19].replace('T', ' '))
        
        console.print(table)
        
        if stats["by_format"]:
            console.print("\n[bold]By Format:[/bold]")
            for fmt, count in stats["by_format"].items():
                console.print(f"  {fmt.upper()}: {count}")
        
        if stats["by_date"]:
            console.print("\n[bold]Recent Activity (by day):[/bold]")
            # Show last 7 days
            recent_dates = sorted(stats["by_date"].items(), reverse=True)[:7]
            for date, count in recent_dates:
                console.print(f"  {date}: {count} reports")
    
    elif list_reports:
        # List all reports
        index_file = Path("exports/reports/index.json")
        if not index_file.exists():
            console.print("[yellow]No reports found[/yellow]")
            return
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            reports = index_data.get("reports", [])
            
            # Filter by format if specified
            if report_format:
                reports = [r for r in reports if r.get("format") == report_format.lower()]
            
            if reports:
                table = Table(title=f"Research Reports{f' ({report_format.upper()})' if report_format else ''}")
                table.add_column("Created", style="dim")
                table.add_column("Query", max_width=40)
                table.add_column("Format", style="cyan")
                table.add_column("Size", justify="right")
                table.add_column("Session ID", style="dim")
                
                for report in reports[:20]:  # Show last 20
                    created = report["created_at"][:19].replace('T', ' ')
                    query = report["query"]
                    if len(query) > 37:
                        query = query[:37] + "..."
                    
                    size_kb = report.get("file_size", 0) / 1024
                    size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                    
                    session_short = report["session_id"][:8] + "..."
                    
                    table.add_row(created, query, report["format"].upper(), size_str, session_short)
                
                console.print(table)
                
                if len(reports) > 20:
                    console.print(f"\n[dim]... and {len(reports) - 20} more reports[/dim]")
            else:
                filter_msg = f" ({report_format.upper()})" if report_format else ""
                console.print(f"[yellow]No reports found{filter_msg}[/yellow]")
                
        except (json.JSONDecodeError, FileNotFoundError) as e:
            console.print(f"[red]Error reading report index: {e}[/red]")
    
    elif cleanup is not None:
        # Clean up old reports
        if cleanup < 1:
            console.print("[red]Cleanup days must be at least 1[/red]")
            return
        
        console.print(f"[yellow]Cleaning up reports older than {cleanup} days...[/yellow]")
        
        from utils import cleanup_old_reports
        stats = cleanup_old_reports(cleanup)
        
        console.print(f"[green]✓ Cleanup completed[/green]")
        console.print(f"  Files deleted: {stats['files_deleted']}")
        console.print(f"  Directories cleaned: {stats['directories_cleaned']}")
        
        if stats.get('index_entries_removed', 0) > 0:
            console.print(f"  Index entries removed: {stats['index_entries_removed']}")
        
        if stats['errors'] > 0:
            console.print(f"[yellow]  Errors encountered: {stats['errors']}[/yellow]")
    
    else:
        console.print("Use --list-reports, --summary, or --cleanup <days>")


@cli.command()
@click.option('--show-config', is_flag=True, help='Show current model configuration')
@click.option('--show-costs', is_flag=True, help='Show model pricing information')
@click.option('--show-usage', is_flag=True, help='Show recent model usage statistics')
@click.pass_context
def models(ctx, show_config, show_costs, show_usage):
    """Manage and view AI model configurations"""
    
    settings = ctx.obj['settings']
    
    if show_config:
        # Show current model configuration
        console.print("[bold blue]🤖 Current Model Configuration[/bold blue]\n")
        
        table = Table(title="Agent Model Assignments")
        table.add_column("Agent Type", style="cyan")
        table.add_column("Model", style="white")
        table.add_column("Max Tokens", justify="center")
        table.add_column("Temperature", justify="center")
        table.add_column("Description", style="dim")
        
        for agent_type, config in settings.agent_models.items():
            model_name = config['model'].split('/')[-1]  # Get just the model name
            table.add_row(
                agent_type.replace('_', ' ').title(),
                model_name,
                str(config['max_tokens']),
                str(config['temperature']),
                config['description']
            )
        
        console.print(table)
        
        console.print(f"\n[bold]Default Model:[/bold] {settings.fireworks_model.split('/')[-1]}")
        console.print(f"[bold]Budget Limit:[/bold] ${settings.max_cost_per_query:.2f} per query")
    
    elif show_costs:
        # Show model pricing information
        from enhanced_research_system import ModelManager
        model_manager = ModelManager(settings)
        
        console.print("[bold blue]💰 Model Pricing Information[/bold blue]\n")
        
        table = Table(title="Model Costs (per 1M tokens)")
        table.add_column("Model", style="cyan")
        table.add_column("Input Cost", justify="right")
        table.add_column("Output Cost", justify="right")
        table.add_column("Used By", style="dim")
        
        # Get models used in configuration
        used_models = set()
        agent_model_map = {}
        for agent_type, config in settings.agent_models.items():
            model = config['model'].split('/')[-1]
            used_models.add(model)
            if model not in agent_model_map:
                agent_model_map[model] = []
            agent_model_map[model].append(agent_type.replace('_', ' ').title())
        
        # Show pricing for used models
        for model_key, pricing in model_manager.model_costs.items():
            if any(model_key in used_model for used_model in used_models):
                agents_using = agent_model_map.get(model_key, ["Not configured"])
                table.add_row(
                    model_key,
                    f"${pricing['input']:.2f}",
                    f"${pricing['output']:.2f}",
                    ", ".join(agents_using)
                )
        
        console.print(table)
        
        console.print(f"\n[dim]💡 Costs are calculated based on token usage")
        console.print(f"[dim]💡 Actual costs may vary based on API provider pricing")
    
    elif show_usage:
        # Show recent usage statistics (would need to be implemented with persistent storage)
        console.print("[bold blue]📊 Model Usage Statistics[/bold blue]\n")
        console.print("[yellow]Usage statistics require running research queries first[/yellow]")
        console.print("Run a research query and check the session metadata for usage information.")
    
    else:
        console.print("Use --show-config, --show-costs, or --show-usage")
        console.print("\nAvailable options:")
        console.print("  --show-config   Show current model assignments for each agent")
        console.print("  --show-costs    Show pricing information for configured models")
        console.print("  --show-usage    Show recent model usage statistics")


@cli.command()
@click.option('--query', prompt='Test query', help='Query to test filtering with')
@click.option('--show-analysis', is_flag=True, help='Show detailed filtering analysis')
@click.option('--show-thresholds', is_flag=True, help='Show adaptive threshold calculations')
@click.option('--test-strategies', is_flag=True, help='Test all filtering strategies')
@click.option('--count', default=10, help='Number of search results to analyze')
@click.pass_context
def test_filtering(ctx, query, show_analysis, show_thresholds, test_strategies, count):
    """Test and analyze the adaptive source filtering system"""
    
    console.print(f"[bold blue]🔍 Testing Adaptive Source Filtering[/bold blue]")
    console.print(f"Query: {query}")
    console.print()
    
    try:
        # Get settings from context (includes .env file)
        settings = ctx.obj['settings']
        cache_manager = CacheManager(settings)
        security_manager = SecurityManager(settings.encryption_key)
        
        # Run the filtering test
        result = asyncio.run(run_filtering_test(
            query, settings, cache_manager, security_manager, 
            count, show_analysis, show_thresholds, test_strategies
        ))
        
        console.print("[green]✅ Filtering test completed successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Filtering test failed: {str(e)}[/red]")
        if ctx.obj.get('debug'):
            import traceback
            console.print(traceback.format_exc())


async def run_filtering_test(query: str, settings: Settings, cache_manager: CacheManager, 
                           security_manager: SecurityManager, count: int, 
                           show_analysis: bool, show_thresholds: bool, test_strategies: bool):
    """Run the filtering test asynchronously"""
    
    # Initialize Model Manager and agents
    from enhanced_research_system import ModelManager
    model_manager = ModelManager(settings)
    
    quality_agent = QualityEvaluationAgent(settings, cache_manager, security_manager, model_manager)
    retriever = WebSearchRetrieverAgent(settings, cache_manager, security_manager, quality_agent, model_manager)
    
    # Create a test sub-question
    sub_question = SubQuestion(
        id=1,
        question=query,
        priority=1,
        search_terms=query.split(),
        estimated_complexity=1.0,
        category="test"
    )
    
    async with ResourceManager(settings) as resource_manager:
        # Get search results
        console.print("🔍 Performing web search...")
        search_results = await retriever._unified_search(query, count, resource_manager)
        
        if not search_results:
            console.print("[yellow]⚠️ No search results found[/yellow]")
            return
        
        console.print(f"📊 Found {len(search_results)} initial results")
        
        # Score results
        scored_results = retriever._score_relevance(search_results, query)
        
        # Show initial results
        console.print("\n[bold]📋 Initial Search Results (Top 5):[/bold]")
        table = Table()
        table.add_column("Rank", style="cyan", width=4)
        table.add_column("Title", style="white", width=40)
        table.add_column("Authority", justify="center", width=9)
        table.add_column("Quality", justify="center", width=7)
        table.add_column("Relevance", justify="center", width=9)
        table.add_column("Source Type", width=12)
        
        for i, result in enumerate(scored_results[:5]):
            table.add_row(
                str(i+1),
                result.title[:37] + "..." if len(result.title) > 40 else result.title,
                f"{result.authority_score:.2f}",
                f"{result.content_quality:.2f}",
                f"{result.relevance_score:.2f}",
                result.source_type
            )
        
        console.print(table)
        
        # Test adaptive filtering
        console.print("\n[bold]🎯 Testing Adaptive Source Filtering:[/bold]")
        
        # Get quality assessment if possible
        quality_assessment = None
        try:
            console.print("📈 Running quality assessment...")
            insights, facts = await retriever._extract_insights_with_ai(
                scored_results[:5], sub_question, resource_manager
            )
            quality_assessment = await quality_agent.evaluate_search_quality(
                sub_question, scored_results, insights, facts, resource_manager
            )
            console.print(f"✅ Quality assessment complete (confidence: {quality_assessment.overall_confidence:.2f})")
        except Exception as e:
            console.print(f"[yellow]⚠️ Quality assessment failed: {str(e)}[/yellow]")
        
        # Apply filtering
        source_filter = AdaptiveSourceFilter(settings, structlog.get_logger("test_filter"))
        
        if test_strategies:
            # Test different strategies
            strategies = ["conservative", "balanced", "aggressive", "domain_diversity", "percentile_based"]
            
            for strategy in strategies:
                console.print(f"\n[bold cyan]Testing {strategy.upper()} strategy:[/bold cyan]")
                
                # Temporarily override strategy for testing
                original_strategy = settings.preferred_filtering_strategy
                settings.preferred_filtering_strategy = strategy
                
                try:
                    filtering_decision = source_filter.filter_sources(
                        scored_results, sub_question, quality_assessment
                    )
                    
                    console.print(f"  📊 {filtering_decision.original_count} → {filtering_decision.kept_count} sources")
                    console.print(f"  🎯 Strategy: {filtering_decision.filtering_strategy}")
                    console.print(f"  📈 Confidence boost: +{filtering_decision.confidence_boost:.3f}")
                    console.print(f"  🏷️ Topic: {filtering_decision.topic_classification}")
                    
                    if show_analysis:
                        console.print("  📝 Reasoning:")
                        for reason in filtering_decision.reasoning[:3]:
                            console.print(f"    • {reason}")
                    
                except Exception as e:
                    console.print(f"  [red]❌ Failed: {str(e)}[/red]")
                
                # Restore original strategy
                settings.preferred_filtering_strategy = original_strategy
        
        else:
            # Single filtering test
            filtering_decision = source_filter.filter_sources(
                scored_results, sub_question, quality_assessment
            )
            
            # Show filtering results
            console.print(f"\n📊 Filtering Results:")
            console.print(f"  Original sources: {filtering_decision.original_count}")
            console.print(f"  Filtered out: {filtering_decision.filtered_count}")
            console.print(f"  Kept sources: {filtering_decision.kept_count}")
            console.print(f"  Strategy used: {filtering_decision.filtering_strategy}")
            console.print(f"  Topic classification: {filtering_decision.topic_classification}")
            console.print(f"  Confidence boost: +{filtering_decision.confidence_boost:.3f}")
            
            if show_analysis:
                console.print(f"\n📈 Quality Distribution:")
                for metric, value in filtering_decision.quality_distribution.items():
                    console.print(f"  {metric}: {value:.3f}")
                
                console.print(f"\n📝 Filtering Reasoning:")
                for reason in filtering_decision.reasoning:
                    console.print(f"  • {reason}")
            
            # Show filtered results
            if filtering_decision.kept_count > 0:
                console.print(f"\n[bold]✅ Filtered Results (Top 5):[/bold]")
                filtered_table = Table()
                filtered_table.add_column("Rank", style="green", width=4)
                filtered_table.add_column("Title", style="white", width=40)
                filtered_table.add_column("Authority", justify="center", width=9)
                filtered_table.add_column("Quality", justify="center", width=7)
                filtered_table.add_column("Relevance", justify="center", width=9)
                filtered_table.add_column("Source Type", width=12)
                
                for i, result in enumerate(filtering_decision.filtered_results[:5]):
                    filtered_table.add_row(
                        str(i+1),
                        result.title[:37] + "..." if len(result.title) > 40 else result.title,
                        f"{result.authority_score:.2f}",
                        f"{result.content_quality:.2f}",
                        f"{result.relevance_score:.2f}",
                        result.source_type
                    )
                
                console.print(filtered_table)
            
            if show_thresholds:
                # Show adaptive thresholds (would need to add this to the filter)
                console.print(f"\n[bold]🎛️ Adaptive Thresholds Used:[/bold]")
                console.print("  (This would show the calculated thresholds)")
        
        console.print(f"\n[bold green]🎯 Filtering Test Complete![/bold green]")


def display_console_report(report):
    """Display report in console format with enhanced formatting"""
    console.print(f"\n[bold blue]Research Report: {report.original_query}[/bold blue]")
    console.print(f"[dim]Completed: {report.completion_timestamp}[/dim]")
    console.print(f"[dim]Quality Score: {report.quality_score:.2f}/1.00[/dim]\n")
    
    console.print("[bold]Executive Summary[/bold]")
    console.print(report.executive_summary)
    
    console.print(f"\n[bold]Detailed Findings ({len(report.detailed_findings)} sections)[/bold]")
    for i, finding in enumerate(report.detailed_findings, 1):
        console.print(f"\n[cyan]{i}. {finding.question}[/cyan]")
        console.print(f"   Confidence: {finding.confidence_level:.2f}")
        console.print(f"   {finding.answer}")
        
        if finding.key_points:
            console.print("   Key Points:")
            for point in finding.key_points[:3]:
                console.print(f"   • {point}")
    
    if report.limitations:
        console.print(f"\n[bold yellow]Limitations[/bold yellow]")
        for limitation in report.limitations:
            console.print(f"• {limitation}")
    
    if hasattr(report, 'recommendations') and report.recommendations:
        console.print(f"\n[bold]💡 Recommendations[/bold]")
        for i, rec in enumerate(report.recommendations, 1):
            console.print(f"  {i}. {rec}")
    
    console.print(f"\n[bold]Sources ({len(report.sources_cited)} total)[/bold]")
    for i, source in enumerate(report.sources_cited[:5], 1):
        console.print(f"{i}. {source}")
    
    if len(report.sources_cited) > 5:
        console.print(f"... and {len(report.sources_cited) - 5} more sources")


def generate_html_report(report) -> str:
    """Generate HTML report"""
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Research Report: {{ report.original_query }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .header { border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
            .finding { margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }
            .sources { margin-top: 30px; font-size: 0.9em; }
            .recommendations { margin-top: 20px; padding: 15px; background-color: #f0f8ff; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{ report.original_query }}</h1>
            <p><strong>Completed:</strong> {{ report.completion_timestamp }}</p>
            <p><strong>Quality Score:</strong> {{ "%.2f"|format(report.quality_score) }}/1.00</p>
            <p><strong>Processing Mode:</strong> Intelligent Parallel (Rate-limit Safe)</p>
        </div>
        
        <h2>Executive Summary</h2>
        <p>{{ report.executive_summary }}</p>
        
        <h2>Detailed Findings</h2>
        {% for finding in report.detailed_findings %}
        <div class="finding">
            <h3>{{ finding.question }}</h3>
            <p><strong>Confidence:</strong> {{ "%.2f"|format(finding.confidence_level) }}</p>
            <p>{{ finding.answer }}</p>
            {% if finding.key_points %}
            <ul>
                {% for point in finding.key_points %}
                <li>{{ point }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
        
        {% if report.recommendations %}
        <div class="recommendations">
            <h2>💡 Recommendations</h2>
            <ol>
                {% for rec in report.recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </ol>
        </div>
        {% endif %}
        
        <div class="sources">
            <h2>Sources ({{ report.sources_cited|length }} total)</h2>
            <ol>
                {% for source in report.sources_cited %}
                <li><a href="{{ source }}">{{ source }}</a></li>
                {% endfor %}
            </ol>
        </div>
    </body>
    </html>
    """
    
    from jinja2 import Template
    return Template(template).render(report=report)


def generate_pdf_report(report, session_id: str, query: str = None) -> Path:
    """Generate PDF report using WeasyPrint with organized file structure"""
    try:
        from weasyprint import HTML
        import io
        
        # Generate HTML first
        html_content = generate_html_report(report)
        
        # Create organized PDF path
        pdf_filepath = get_organized_report_path(session_id, 'pdf', query)
        
        # Enhanced CSS for better PDF formatting
        enhanced_html = html_content.replace(
            "<style>",
            """<style>
            @page { margin: 1in; }"""
        ).replace(
            "body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }",
            """body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                line-height: 1.6; 
                color: #333;
            }"""
        )
        
        # Generate PDF
        HTML(string=enhanced_html).write_pdf(str(pdf_filepath))
        
        return pdf_filepath
        
    except ImportError:
        # Fallback if WeasyPrint is not available
        console.print("[yellow]WeasyPrint not available, generating HTML instead[/yellow]")
        html_output = generate_html_report(report)
        html_filepath = get_organized_report_path(session_id, 'html', query)
        html_filepath.write_text(html_output, encoding='utf-8')
        return html_filepath
    except Exception as e:
        # Fallback on any PDF generation error
        console.print(f"[yellow]PDF generation failed ({str(e)}), generating HTML instead[/yellow]")
        html_output = generate_html_report(report)
        html_filepath = get_organized_report_path(session_id, 'html', query)
        html_filepath.write_text(html_output, encoding='utf-8')
        return html_filepath


if __name__ == "__main__":
    cli() 